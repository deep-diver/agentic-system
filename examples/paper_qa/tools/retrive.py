from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from clients.chromadb import get_chroma_client
from embedding.upstage import get_upstage_embedding_fn
from clients.upstage import get_upstage_client

@tool
def to_retrive_paper_content_to_answer_question_agent(question: str, paper_id: str):
    """Use this tool to retrieve information about the paper from the database, then answer user query about the paper."""
    writer = get_stream_writer()
    chroma_client = get_chroma_client(path="./chromadb")
    embedding_fn = get_upstage_embedding_fn(client=get_upstage_client())
    
    collection = chroma_client.get_collection(name=paper_id, embedding_function=embedding_fn)
    writer("Retrieving paper content....")
    results = collection.query(query_texts=[question], n_results=10)
    writer(f"{len(results)} number of paper content retrieved")
    results_str = ["Below is the retrieved content of the Paper.\n-----------------------------------\n"]
    for i in range(len(results['documents'])):
        results_str.append(f"{i}: {results['documents'][i]}")
    results_str.append("Based on the retrieved content, answer the user question.")
    writer("Based on the retrieved content, answer the user question.")
    return "\n".join(results_str)