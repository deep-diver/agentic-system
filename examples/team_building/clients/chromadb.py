import chromadb

def get_chroma_client(path: str):
    chroma_client = chromadb.PersistentClient(path=path)
    return chroma_client