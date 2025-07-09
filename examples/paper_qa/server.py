from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import AsyncGenerator, List, Dict, Any
import json
import os
import re
import glob
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from graph.graph import build_graph
from utils import load_dotenv
from database import db

# Load environment variables
load_dotenv()

# Global variable to store the graph
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    # Initialize the graph on startup
    graph = build_graph()
    
    # Migrate existing JSON chat history to SQLite
    try:
        migrated_count = db.migrate_from_json("chat_history")
        if migrated_count > 0:
            print(f"Successfully migrated {migrated_count} chat sessions from JSON to SQLite")
    except Exception as e:
        print(f"Migration warning: {e}")
    
    yield
    # Cleanup if needed
    graph = None

app = FastAPI(
    title="Paper QA API",
    description="API for asking questions about academic papers",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CORS middleware handles cross-origin requests

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str

class ChatMessage(BaseModel):
    content: str
    type: str  # 'user' or 'bot'
    timestamp: str

class ChatSession(BaseModel):
    id: str
    title: str
    preview: str
    created_at: str
    updated_at: str
    messages: List[ChatMessage]

class CachedPaper(BaseModel):
    id: str
    title: str
    cached_at: str
    file_count: int

# SQLite database handles chat session storage

def extract_arxiv_id_and_title(folder_name):
    """Extract arxiv ID and title from folder name"""
    if "_" in folder_name:
        # New format: arxivID_paper-title
        parts = folder_name.split("_", 1)
        arxiv_id = parts[0]
        title = parts[1].replace("-", " ").title() if len(parts) > 1 else "Unknown"
        return arxiv_id, title
    else:
        # Old format: just arxiv ID
        return folder_name, f"Paper {folder_name}"

def get_full_paper_title(folder_path):
    """Extract full paper title from response JSON files"""
    try:
        # Try to find response JSON files
        response_files = glob.glob(os.path.join(folder_path, "response_*.json"))
        if not response_files:
            return None
        
        # Sort files to process response_1.json first (most likely to have title)
        response_files.sort(key=lambda x: int(re.search(r'response_(\d+)\.json', x).group(1)) if re.search(r'response_(\d+)\.json', x) else 999)
        
        # Look through response files for the main paper title
        for response_file in response_files:
            try:
                with open(response_file, 'r') as f:
                    data = json.load(f)
                    markdown_content = data.get('content', {}).get('markdown', '')
                    
                    # Find all headings and prioritize likely paper titles
                    lines = markdown_content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('# '):
                            title_candidate = line[2:].strip()
                            
                            # Skip common non-title headings
                            if title_candidate.lower() in ['abstract', 'introduction', 'conclusion', 'references', 'acknowledgments']:
                                continue
                            
                            # Skip numbered section headings (like "4 Why Self-Attention")
                            if re.match(r'^\d+\s+', title_candidate):
                                continue
                            
                            # Clean up the title
                            title = re.sub(r'[^\w\s\-\:\(\),]', '', title_candidate)
                            if title and len(title) > 5:  # Reasonable title length
                                return title
                                
            except Exception as e:
                print(f"Error reading {response_file}: {e}")
                continue
        
        return None
    except Exception as e:
        print(f"Error reading title from {folder_path}: {e}")
        return None

def get_cached_papers() -> List[CachedPaper]:
    """Get list of cached papers"""
    papers = []
    
    # Look for directories with arxiv ID pattern (old format: numbers.numbers)
    for folder in glob.glob("*.*"):
        if os.path.isdir(folder) and "." in folder:
            # Check if it looks like an arxiv ID (old format)
            parts = folder.split(".")
            if len(parts) >= 2 and all(part.isdigit() for part in parts):
                try:
                    stat = os.stat(folder)
                    file_count = len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
                    
                    arxiv_id, title = extract_arxiv_id_and_title(folder)
                    
                    # Try to get full title from JSON files first
                    full_title = get_full_paper_title(folder)
                    final_title = full_title if full_title else title
                    
                    papers.append(CachedPaper(
                        id=arxiv_id,  # Use arxiv_id for API compatibility
                        title=final_title,
                        cached_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        file_count=file_count
                    ))
                except Exception as e:
                    print(f"Error reading paper folder {folder}: {e}")
    
    # Look for directories with new format (arxivID_paper-title)
    for folder in glob.glob("*_*"):
        if os.path.isdir(folder):
            # Check if it starts with arxiv ID pattern
            folder_start = folder.split("_")[0]
            if "." in folder_start:
                parts = folder_start.split(".")
                if len(parts) >= 2 and all(part.isdigit() for part in parts):
                    try:
                        stat = os.stat(folder)
                        file_count = len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
                        
                        arxiv_id, title = extract_arxiv_id_and_title(folder)
                        
                        # Try to get full title from JSON files first
                        full_title = get_full_paper_title(folder)
                        final_title = full_title if full_title else title
                        
                        # Check if we already have this paper (avoid duplicates)
                        existing_paper = next((p for p in papers if p.id == arxiv_id), None)
                        if not existing_paper:
                            papers.append(CachedPaper(
                                id=arxiv_id,  # Use arxiv_id for API compatibility
                                title=final_title,
                                cached_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                file_count=file_count
                            ))
                        elif existing_paper and stat.st_mtime > datetime.fromisoformat(existing_paper.cached_at.replace('Z', '')).timestamp():
                            # Update to newer version if new format is newer
                            existing_paper.title = final_title
                            existing_paper.cached_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
                            existing_paper.file_count = file_count
                    except Exception as e:
                        print(f"Error reading paper folder {folder}: {e}")
    
    # Sort by cached_at descending
    papers.sort(key=lambda x: x.cached_at, reverse=True)
    return papers

def add_message_to_session(session_id: str, message: str, message_type: str, progresses: List[str] = None):
    """Add a message to a chat session"""
    # Check if session exists, create if not
    session = db.get_session(session_id)
    if session is None:
        # Create new session
        title = message[:50] + "..." if len(message) > 50 else message
        preview = message[:100] + "..." if len(message) > 100 else message
        db.create_or_update_session(session_id, title, preview)
    
    # Add message to database
    db.add_message(session_id, message, message_type, progresses)
    
    # Update session preview if this is a user message
    if message_type == "user":
        session_data = db.get_session(session_id)
        if session_data:
            preview = message[:100] + "..." if len(message) > 100 else message
            db.create_or_update_session(session_id, session_data["title"], preview)

@app.get("/")
async def read_root():
    """
    Serve the main UI
    """
    return FileResponse("static/index.html")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a complete response
    """
    try:
        if not graph:
            raise HTTPException(status_code=500, detail="Graph not initialized")
        
        # Save user message to session
        add_message_to_session(request.session_id, request.message, "user")
        
        # Get the final response from the graph
        messages = []
        progresses = []
        for event in graph.stream(
            {"messages": [{"role": "user", "content": request.message}]},
            config={"configurable": {"thread_id": request.session_id}},
            stream_mode=["updates", "custom"]
        ):
            print(f"event: {event}")
            event_type, event_value = event
                        
            if "custom" in event_type:
                progresses.append(event_value)
            else:
                if "tools" in event_value:
                    tool_name = event_value["tools"]['messages'][-1].name
                    if tool_name in "to_paper_search_agent":
                        progresses.append("Searching for relevant paper")
                    elif tool_name in "to_download_and_parse_paper_agent":
                        progresses.append("Downloading and parsing paper")
                    elif tool_name in "to_retrive_paper_content_to_answer_question_agent":
                        progresses.append("Retrieving paper content")
                    
                    print(f"tools: {event_value['tools']}")
                
                for value in event_value.values():
                    if value["messages"] and value["messages"][-1].content:
                        messages.append(value["messages"][-1].content)
        
        # Return the last message as the response
        final_response = messages[-1] if messages else "No response generated"
        
        # Save bot response to session with progress data
        add_message_to_session(request.session_id, final_response, "bot", progresses)
        
        return ChatResponse(
            response=final_response,
            session_id=request.session_id
        )
    
    except Exception as e:
        # Save error message to session
        error_msg = str(e)
        add_message_to_session(request.session_id, f"Error: {error_msg}", "bot")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/chat/stream")
async def chat_stream_get(message: str, session_id: str = "default"):
    """
    Send a message and get a streaming response with progress updates
    """
    try:
        if not graph:
            raise HTTPException(status_code=500, detail="Graph not initialized")
        
        # Save user message to session
        add_message_to_session(session_id, message, "user")
        
        async def generate_response() -> AsyncGenerator[str, None]:
            messages = []
            progresses = []
            
            # Send initial progress update
            initial_progress = {
                "type": "progress",
                "progress": "Processing your request...",
                "session_id": session_id
            }
            print(f"[{datetime.now().isoformat()}] Yielding initial progress: {initial_progress}")
            yield f"data: {json.dumps(initial_progress)}\n\n"
            
            async for event in graph.astream(
                {"messages": [{"role": "user", "content": message}]},
                config={"configurable": {"thread_id": session_id}},
                stream_mode=["custom", "updates"]
            ):
                print(f"event: {event}")
                event_type, event_value = event
                            
                if "custom" in event_type:
                    progresses.append(event_value)
                    # Yield progress update immediately
                    progress_chunk = {
                        "type": "progress",
                        "progress": event_value,
                        "session_id": session_id
                    }
                    print(f"[{datetime.now().isoformat()}] Yielding custom progress: {progress_chunk}")
                    yield f"data: {json.dumps(progress_chunk)}\n\n"
                    
                    # Force async yield
                    await asyncio.sleep(0)
                else:
                    if "tools" in event_value:
                        tool_name = event_value["tools"]['messages'][-1].name
                        progress_message = ""
                        if tool_name == "to_paper_search_agent":
                            progress_message = "Searching for relevant paper"
                        elif tool_name == "to_download_and_parse_paper_agent":
                            progress_message = "Downloading and parsing paper"
                        elif tool_name == "to_retrive_paper_content_to_answer_question_agent":
                            progress_message = "Retrieving paper content"
                        
                        if progress_message:
                            progresses.append(progress_message)
                            # Yield progress update immediately
                            progress_chunk = {
                                "type": "progress",
                                "progress": progress_message,
                                "session_id": session_id
                            }
                            print(f"[{datetime.now().isoformat()}] Yielding tool progress: {progress_chunk}")
                            yield f"data: {json.dumps(progress_chunk)}\n\n"
                            
                            # Force async yield
                            await asyncio.sleep(0)
                        
                        print(f"tools: {event_value['tools']}")
                    
                    for value in event_value.values():
                        if value["messages"] and value["messages"][-1].content:
                            messages.append(value["messages"][-1].content)
                            # Yield partial response
                            chunk = {
                                "type": "message",
                                "response": value["messages"][-1].content,
                                "session_id": session_id
                            }
                            print(f"[{datetime.now().isoformat()}] Yielding message: {chunk}")
                            yield f"data: {json.dumps(chunk)}\n\n"
            
            # Get final response
            final_response = messages[-1] if messages else "No response generated"
            
            # Save bot response to session with progress data
            add_message_to_session(session_id, final_response, "bot", progresses)
            
            # Send final response with all progress data
            final_chunk = {
                "type": "final",
                "response": final_response,
                "progresses": progresses,
                "session_id": session_id
            }
            print(f"[{datetime.now().isoformat()}] Yielding final: {final_chunk}")
            yield f"data: {json.dumps(final_chunk)}\n\n"
            
            # Send end signal
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    except Exception as e:
        # Save error message to session
        error_msg = str(e)
        add_message_to_session(session_id, f"Error: {error_msg}", "bot")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/chat/sessions")
async def get_chat_sessions():
    """
    Get list of all chat sessions
    """
    return {"sessions": db.get_all_sessions()}

@app.get("/chat/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """
    Get a specific chat session with all messages
    """
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.delete("/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """
    Delete a chat session
    """
    success = db.delete_session(session_id)
    if success:
        return {"message": "Session deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.post("/admin/migrate-chat-history")
async def migrate_chat_history():
    """
    Manually migrate JSON chat history to SQLite (admin endpoint)
    """
    try:
        migrated_count = db.migrate_from_json("chat_history")
        return {
            "message": f"Successfully migrated {migrated_count} chat sessions",
            "migrated_count": migrated_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@app.get("/papers/cached")
async def get_cached_papers_list():
    """
    Get list of cached papers
    """
    return {"papers": get_cached_papers()}

def find_paper_directory(arxiv_id: str) -> str:
    """Find the actual directory for a paper given its arxiv ID"""
    # First check old format (just arxiv_id)
    if os.path.exists(arxiv_id) and os.path.isdir(arxiv_id):
        return arxiv_id
    
    # Then check new format (arxiv_id_title)
    import glob
    matching_dirs = glob.glob(f"{arxiv_id}_*")
    if matching_dirs:
        return matching_dirs[0]  # Return first match
    
    return None

@app.get("/papers/cached/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str):
    """
    Serve the PDF file for a cached paper
    """
    # Find the actual directory for this paper
    paper_directory = find_paper_directory(paper_id)
    
    if not paper_directory:
        raise HTTPException(status_code=404, detail="Paper directory not found")
    
    pdf_path = os.path.join(paper_directory, "paper.pdf")
    if os.path.exists(pdf_path) and os.path.isfile(pdf_path):
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"{paper_id}.pdf",
            headers={
                "Content-Disposition": f"inline; filename={paper_id}.pdf",
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    else:
        raise HTTPException(status_code=404, detail="PDF not found")

@app.options("/papers/cached/{paper_id}/pdf")
async def options_paper_pdf(paper_id: str):
    """
    Handle CORS preflight requests for PDF endpoint
    """
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.delete("/papers/cached/{paper_id}")
async def delete_cached_paper(paper_id: str):
    """
    Delete a cached paper folder
    """
    import shutil
    
    # Find the actual directory for this paper
    paper_directory = find_paper_directory(paper_id)
    
    if not paper_directory:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
        shutil.rmtree(paper_directory)
        return {"message": f"Paper {paper_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete paper: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "graph_initialized": graph is not None}

# Mount static files for CSS, JS, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Paper QA FastAPI Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
    parser.add_argument("--timeout", type=int, default=300, help="Request timeout in seconds (default: 300)")
    
    args = parser.parse_args()
    
    print(f"Starting Paper QA server on {args.host}:{args.port}")
    print(f"Request timeout set to {args.timeout} seconds")
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        timeout_keep_alive=args.timeout,
        timeout_graceful_shutdown=30
    )