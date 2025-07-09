import os
import json
import re
import requests
from PyPDF2 import PdfReader, PdfWriter
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from clients.upstage import get_upstage_client
from embedding.upstage import get_upstage_embedding_fn
from clients.chromadb import get_chroma_client

embedding_context_length = 4000

def clean_arxiv_id(arxiv_id):
    """Clean arXiv ID by removing version suffixes like v1, v2, etc."""
    # Remove version suffix (e.g., 2402.08164v2 -> 2402.08164)
    cleaned_id = re.sub(r'v\d+$', '', arxiv_id)
    return cleaned_id

def extract_paper_title(markdown_content):
    """Extract paper title from markdown content, looking for first # heading"""
    if not markdown_content:
        return "Unknown"
    
    lines = markdown_content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            # Remove "# " prefix and clean up
            title = line[2:].strip()
            # Remove any trailing punctuation or extra characters
            title = re.sub(r'[^\w\s\-]', '', title)
            return title if title else "Unknown"
    return "Unknown"

def sanitize_title_for_filesystem(title):
    """Sanitize paper title for use in filesystem directory names"""
    if not title or title == "Unknown":
        return "Unknown"
    
    # Remove or replace problematic characters for filesystem
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces and multiple whitespace with hyphens
    sanitized = re.sub(r'\s+', '-', sanitized)
    # Remove consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    # Limit length to avoid filesystem issues
    sanitized = sanitized[:50]
    # Ensure it's not empty after sanitization
    return sanitized if sanitized else "Unknown"

def create_paper_directory_name(arxiv_id, title):
    """Create directory name in format: arxivID_paper-title"""
    sanitized_title = sanitize_title_for_filesystem(title)
    return f"{arxiv_id}_{sanitized_title}"

def get_document_parse_response(filename, api_key):
    url = "https://api.upstage.ai/v1/document-ai/document-parse"

    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"document": open(filename, "rb")}
    data = {"output_formats": "['markdown']"}

    response = requests.post(url, headers=headers, files=files, data=data)
    upstage_response = json.loads(response.text)
    return upstage_response

def split_pdf_by_pages(input_pdf_path, root_path, pages_per_pdf=10):
    try:
        # Open the PDF
        pdf = PdfReader(input_pdf_path)
        total_pages = len(pdf.pages)
    except Exception as e:
        print(f"Error reading PDF {input_pdf_path}: {e}")
        # If PDF is corrupted, try to continue with original file
        raise Exception(f"PDF parsing failed: {e}. The PDF file might be corrupted or incomplete.")

    # Calculate number of output PDFs needed
    num_pdfs = (total_pages + pages_per_pdf - 1) // pages_per_pdf

    output_paths = []

    # Split into multiple PDFs
    for i in range(num_pdfs):
        writer = PdfWriter()

        # Calculate start and end pages for this split
        start_page = i * pages_per_pdf
        end_page = min((i + 1) * pages_per_pdf, total_pages)

        # Add pages to writer
        for page_num in range(start_page, end_page):
            writer.add_page(pdf.pages[page_num])

        # Save the split PDF
        output_path = f"{root_path}/{i+1}.pdf"
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
        output_paths.append(output_path)

    return output_paths

def get_md_with_document_parse(root_path, paper_url, arxiv_id):
    response = requests.get(paper_url)
    
    # Check if we got a valid PDF response
    if response.status_code != 200:
        raise Exception(f"Failed to download PDF: HTTP {response.status_code}")
    
    # Check content type
    content_type = response.headers.get('content-type', '').lower()
    if 'pdf' not in content_type and len(response.content) < 1000:
        raise Exception(f"Downloaded content doesn't appear to be a valid PDF. Content-Type: {content_type}")
    
    # Save the PDF to a temporary file
    pdf_path = f"{root_path}/paper.pdf"
    with open(pdf_path, "wb") as f:
        f.write(response.content)
    
    # Verify the PDF file size
    if os.path.getsize(pdf_path) < 1000:
        raise Exception("Downloaded PDF file is too small, likely corrupted or not a valid PDF")

    split_factor = 1
    markdown = ""
    total_responses = []
    
    try:
        # Try to split the PDF first
        split_pdfs = split_pdf_by_pages(pdf_path, root_path, split_factor)
        
        for i, split_pdf in enumerate(split_pdfs):
            upstage_response = get_document_parse_response(split_pdf, os.getenv("UPSTAGE_API_KEY"))

            # Append the response to the total_responses list
            total_responses.append({f"page_{i+1 * split_factor}": upstage_response})
            # Also write the response to a JSON file for persistence
            json_output_path = f"{root_path}/response_{i+1}.json"
            with open(json_output_path, "w") as json_file:
                json.dump(upstage_response, json_file, indent=2)

            try:
                markdown += upstage_response['content']['markdown']
            except KeyError:
                pass
                
    except Exception as pdf_error:
        print(f"PDF splitting failed: {pdf_error}")
        print("Attempting to process original PDF directly...")
        
        try:
            # Fallback: process the original PDF directly
            upstage_response = get_document_parse_response(pdf_path, os.getenv("UPSTAGE_API_KEY"))
            
            total_responses.append({"full_document": upstage_response})
            json_output_path = f"{root_path}/response_full.json"
            with open(json_output_path, "w") as json_file:
                json.dump(upstage_response, json_file, indent=2)
            
            try:
                markdown = upstage_response['content']['markdown']
            except KeyError:
                markdown = ""
                
        except Exception as upstage_error:
            raise Exception(f"Both PDF splitting and direct processing failed. PDF Error: {pdf_error}, Upstage Error: {upstage_error}")

    chroma_client = get_chroma_client(path="./chromadb")
    embedding_fn = get_upstage_embedding_fn(client=get_upstage_client())

    # Use arxiv_id for ChromaDB collection (maintain backward compatibility)
    try:
        collection = chroma_client.create_collection(name=arxiv_id, embedding_function=embedding_fn)
    except Exception as e:
        # Collection might already exist, try to get it
        if "already exists" in str(e).lower():
            print(f"Collection {arxiv_id} already exists, using existing collection")
            collection = chroma_client.get_collection(name=arxiv_id, embedding_function=embedding_fn)
        else:
            raise e

    processed_input = []
    if len(markdown) > embedding_context_length:
        chunks = [markdown[i:i+embedding_context_length] for i in range(0, len(markdown), embedding_context_length)]
        processed_input.extend(chunks)
    else:
        processed_input.append(markdown)

    ids = []
    for i in range(len(processed_input)):
        ids.append(f"{arxiv_id}_{i}")

    # Check if we're adding to an existing collection and avoid duplicate IDs
    try:
        collection.add(documents=processed_input, ids=ids)
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print(f"Some documents already exist in collection {arxiv_id}, skipping duplicates")
            # Try to add documents one by one, skipping duplicates
            for i, (doc, doc_id) in enumerate(zip(processed_input, ids)):
                try:
                    collection.add(documents=[doc], ids=[doc_id])
                except Exception:
                    # Skip if this specific document already exists
                    continue
        else:
            raise e
    return collection, markdown

@tool
def to_download_and_parse_paper_agent(paper_url: str):
    """Use this tool to download and parse paper. Use this tool when paper URL is already found."""
    writer = get_stream_writer()
    raw_arxiv_id = paper_url.split("/")[-1]
    arxiv_id = clean_arxiv_id(raw_arxiv_id)  # Remove version suffixes
    
    print(f"Processing arXiv paper: {raw_arxiv_id} -> {arxiv_id}")
    
    from clients.upstage import get_upstage_client
    from embedding.upstage import get_upstage_embedding_fn
    from clients.chromadb import get_chroma_client
    
    # Check if paper already exists with old naming format (just arxiv_id)
    old_format_path = arxiv_id
    if os.path.exists(old_format_path):
        # Also check if ChromaDB collection exists
        try:
            chroma_client = get_chroma_client(path="./chromadb")
            embedding_fn = get_upstage_embedding_fn(client=get_upstage_client())
            collection = chroma_client.get_collection(name=arxiv_id, embedding_function=embedding_fn)
            print(f"Found cached markdown for {arxiv_id} (old format) with ChromaDB collection")
            writer(f"we already have the paper content stored in our database in the id of {arxiv_id}")
            return f"we already have the paper content stored in our database in the id of {arxiv_id}"
        except Exception:
            print(f"Found directory {old_format_path} but no ChromaDB collection, will recreate")
    
    # Check for new format directories (arxiv_id_title)
    import glob
    existing_dirs = glob.glob(f"{arxiv_id}_*")
    if existing_dirs:
        existing_dir = existing_dirs[0]
        # Also check if ChromaDB collection exists
        try:
            chroma_client = get_chroma_client(path="./chromadb")
            embedding_fn = get_upstage_embedding_fn(client=get_upstage_client())
            collection = chroma_client.get_collection(name=arxiv_id, embedding_function=embedding_fn)
            print(f"Found cached markdown for {arxiv_id} in directory {existing_dir} with ChromaDB collection")
            writer(f"we already have the paper content stored in our database in the id of {arxiv_id}")
            return f"we already have the paper content stored in our database in the id of {arxiv_id}"
        except Exception:
            print(f"Found directory {existing_dir} but no ChromaDB collection, will recreate")
    
    # No cached version found, proceed with download and parsing
    print(f"No cached markdown found for {arxiv_id}, parsing from URL")
    print("Parsing in progress.....")
    
    # Create temporary directory with arxiv_id first
    temp_path = f"temp_{arxiv_id}"
    os.makedirs(temp_path, exist_ok=True)
    
    try:
        # Parse the paper and get markdown content
        collection, markdown = get_md_with_document_parse(temp_path, paper_url, arxiv_id)
        
        # Extract title from markdown
        paper_title = extract_paper_title(markdown)
        
        # Create final directory name with title
        final_directory_name = create_paper_directory_name(arxiv_id, paper_title)
        
        # Rename temporary directory to final name
        if os.path.exists(final_directory_name):
            # If final directory exists, remove temp and use existing
            import shutil
            shutil.rmtree(temp_path)
            print(f"Directory {final_directory_name} already exists, using existing")
            writer(f"Directory {final_directory_name} already exists, using existing")
        else:
            os.rename(temp_path, final_directory_name)
            print(f"Created directory: {final_directory_name}")
            writer(f"Created directory: {final_directory_name}")
        
        print("Parsing done ✅")
        writer("Parsing done ✅")
        return f"we have parsed the paper '{paper_title}' and stored in our database in the id of {arxiv_id}. Next step would be to retrieve it and answer user question."
        
    except Exception as e:
        # Clean up temp directory if something went wrong
        if os.path.exists(temp_path):
            import shutil
            shutil.rmtree(temp_path)
        print(f"Error during parsing: {e}")
        writer(f"Error during parsing: {e}")
        raise e