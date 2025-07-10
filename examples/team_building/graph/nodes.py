import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from clients.chromadb import get_chroma_client
from embedding.upstage import get_upstage_embedding_fn
from clients.upstage import get_upstage_client
from graph.state import State
from graph.upstage import (
    solar, 
    solar_role, 
    solar_participant
)
from graph.schema import Roles, Participants

# Load environment variables
load_dotenv(dotenv_path="../../.env")

# Initialize ChromaDB clients once at module level
try:
    chroma_client = get_chroma_client(path="./chromadb")
    embedding_fn = get_upstage_embedding_fn(client=get_upstage_client())
    collection = chroma_client.get_collection(name="projects", embedding_function=embedding_fn)
except Exception as e:
    print(f"Warning: Could not initialize ChromaDB: {e}")
    chroma_client = None
    embedding_fn = None
    collection = None

def role_extraction_agent(state: State):
    messages = state['messages']

    system_prompt = "You are a helpful agent who can extract the required roles of the project."
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), # Static system message
        MessagesPlaceholder(variable_name="messages"), # Placeholder for history/user input
    ])

    chain = prompt | solar_role
    
    response = chain.invoke({"messages": messages})
    response = Roles(**response)
    
    return {"extracted_roles": response}

def paraphrase_agent(state: State):
    messages = state['messages']
    system_prompt = (
        "You are a helpful agent who paraphrase the user's prompt into a query to find "
        "similar projects from the vector database. MUST return the paraphrased query only."
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), # Static system message
        MessagesPlaceholder(variable_name="messages"), # Placeholder for history/user input
    ])

    chain = prompt | solar
    response = chain.invoke({"messages": messages})
    return {"paraphrased_query": str(response)}

def retrieval_node(state: State):
    query = state['paraphrased_query']
    index = state.get("retrieval_index", 0)
    
    if collection is None:
        # Fallback: return empty results if ChromaDB is not available
        return {
            "retrieved_projects": [],
            "retrieval_index": index + 5
        }
    
    try:
        # retrieve next 5
        results = collection.query(query_texts=[query], n_results=index + 5)["metadatas"][0]
        
        return {
            "retrieved_projects": results,
            "retrieval_index": index + 5
        }
    except Exception as e:
        print(f"Error in retrieval_node: {e}")
        return {
            "retrieved_projects": [],
            "retrieval_index": index + 5
        }

def suggestion_agent(state: State):
    extracted_roles = state['extracted_roles']
    retrieved_projects = state['retrieved_projects']

    system_prompt = (
        "You are a helpful agent who suggests who is the best fit for the "
        "extracted roles based on the participants of the retrieved projects. "
        "IMPORTANT: Suggest exactly ONE participant for each extracted role - no more, no less.\n"
        "For each participant, you MUST include:\n"
        "- name: The participant's name\n"
        "- role: Their role in the project (must match one of the extracted roles)\n"
        "- experience_years: Years of experience\n"
        "- skills: List of relevant skills\n"
        "- reason_to_join: A compelling explanation of why this participant is perfect for this specific project\n"
        "Do NOT suggest extra participants beyond the extracted roles."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | solar_participant

    # Create a synthetic message for this step
    content = (
        f"extracted roles: {extracted_roles}\n"
        f"retrieved projects: {retrieved_projects}\n"
    )
    
    messages = [
        {
            "role": "user", 
            "content": content
        }
    ]
    
    print(f"Suggestion agent input - roles count: {len(extracted_roles.roles)}")
    print(f"Suggestion agent input - projects count: {len(retrieved_projects)}")

    response = None
    try:
        response = chain.invoke({"messages": messages})
        print(f"LLM response: {response}")
        
        if response is None:
            print("ERROR: LLM returned None")
            # Return empty participants as fallback
            response = {"participants": []}
        
        response = Participants(**response)
        return {"suggested_participants": response}
    except Exception as e:
        print(f"Error in suggestion_agent: {e}")
        print(f"Response was: {response}")
        # Return empty participants as fallback
        empty_participants = Participants(participants=[])
        return {"suggested_participants": empty_participants}

def check_completion(state: State):
    required = len(state["extracted_roles"].roles)
    suggested = len(state["suggested_participants"].participants)
    
    # Prefer exact match: one participant per role
    if suggested == required:
        return "done"
    elif suggested > required:
        # Too many participants - still done but not ideal
        return "done"
    elif state["retrieval_index"] >= 10:  # max retrieval limit: 2 rounds = 10 documents
        return "done"
    else:
        return "continue"