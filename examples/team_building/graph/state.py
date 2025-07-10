from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from graph.schema import Roles, Participants

def add_retrieved_projects(existing: list[dict], new: list[dict]) -> list[dict]:
    """Accumulate retrieved projects across multiple retrieval rounds"""
    if existing is None:
        return new
    return existing + new

def update_retrieval_index(existing: int, new: int) -> int:
    """Always take the latest retrieval index"""
    return new

def update_suggested_participants(existing: Participants, new: Participants) -> Participants:
    """Always take the latest suggested participants"""
    return new

class State(TypedDict):
    messages: Annotated[list, add_messages]
    extracted_roles: Roles
    paraphrased_query: str
    retrieved_projects: Annotated[list[dict], add_retrieved_projects]
    suggested_participants: Annotated[Participants, update_suggested_participants]
    retrieval_index: Annotated[int, update_retrieval_index]  # start at 0, +5 each round