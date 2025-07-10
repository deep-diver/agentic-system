import json
import hashlib
import argparse
from tqdm import tqdm

from clients.chromadb import get_chroma_client
from embedding.upstage import get_upstage_embedding_fn
from clients.upstage import get_upstage_client
from graph.graph import build_graph
from utils import load_dotenv

# Load environment variables from root directory
load_dotenv(dotenv_path="../../.env")

# Global variables
participants = None
graph = None

def generate_hash(text):
    """Generate a hash (SHA-256) based on input string"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def init_database():
    """Initialize the ChromaDB with projects data"""
    # Load the projects data
    with open('projects_data_en.json', 'r', encoding='utf-8') as f:
        projects_data = json.load(f)

    print(f"Loaded {len(projects_data)} projects")

    # Initialize ChromaDB client and embedding function
    chroma_client = get_chroma_client(path="./chromadb")
    embedding_fn = get_upstage_embedding_fn(client=get_upstage_client())

    # Delete existing collection if it exists
    try:
        chroma_client.delete_collection(name="projects")
        print("Collection deleted")
    except Exception as e:
        print(f"Collection deletion info: {e}")

    # Create new collection
    collection = chroma_client.create_collection(name="projects", embedding_function=embedding_fn)
    print("Collection created")

    # Add projects to collection
    for project in tqdm(projects_data):
        id = generate_hash(project["descriptive_summary"])

        collection.add(
            ids=[id],
            documents=[project["descriptive_summary"]],
            metadatas=[{"data": str(project)}]
        )

    print(f"Successfully initialized ChromaDB with {len(projects_data)} projects")

def stream_graph_updates(user_input: str):
    """Stream graph updates for team building suggestions"""
    global participants
    
    print(f"Your request: {user_input}")
    
    for event in graph.stream(
        {
            "messages": [{"role": "user", "content": user_input}],
        }
    ):
        if 'paraphrase_agent' in event:
            print(f"paraphrased query : \n{event['paraphrase_agent']['paraphrased_query']}")
        elif 'role_extraction_agent' in event:
            roles = event['role_extraction_agent']['extracted_roles']
            print(f"extracted roles: \n{roles.model_dump_json(indent=2)}")
        elif 'retrieval_node' in event:
            print(f"retrieved projects: \n{event['retrieval_node']['retrieved_projects']}")
        elif 'suggestion_agent' in event:
            participants = event['suggestion_agent']['suggested_participants']
            print(f"suggested participants: \n{participants.model_dump_json(indent=2)}")

def run_team_building():
    """Run the interactive team building system"""
    global graph
    
    print("Building team building graph...")
    graph = build_graph()
    print("Graph built successfully!")
    print("\nTeam Building Agent System")
    print("Enter your project description to get team suggestions.")
    print("Type 'quit', 'exit', or 'q' to exit.\n")
    
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            stream_graph_updates(user_input)
        except Exception as e:
            print(f"Error: {e}")
            break

def main():
    parser = argparse.ArgumentParser(description="Team Building Agent System")
    parser.add_argument("--init", action="store_true", help="Initialize database with projects data")
    
    args = parser.parse_args()
    
    if args.init:
        init_database()
    else:
        run_team_building()

if __name__ == "__main__":
    main()