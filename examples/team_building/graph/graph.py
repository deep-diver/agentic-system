from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END
from graph.state import State
from graph.nodes import (
    role_extraction_agent,
    paraphrase_agent,
    retrieval_node,
    suggestion_agent,
    check_completion
)

def build_graph():
    graph_builder = StateGraph(State)

    graph_builder.add_node("role_extraction_agent", role_extraction_agent)
    graph_builder.add_node("paraphrase_agent", paraphrase_agent)
    graph_builder.add_node("retrieval_node", retrieval_node)
    graph_builder.add_node("sync_roles_and_retrieval", lambda state: state)
    graph_builder.add_node("suggestion_agent", suggestion_agent)

    # Create a sequential workflow to ensure proper execution order
    graph_builder.add_edge(START, "role_extraction_agent")
    graph_builder.add_edge(START, "paraphrase_agent")
    graph_builder.add_edge("paraphrase_agent", "retrieval_node")
    graph_builder.add_edge("role_extraction_agent", "sync_roles_and_retrieval")
    graph_builder.add_edge("retrieval_node", "sync_roles_and_retrieval")
    graph_builder.add_edge("sync_roles_and_retrieval", "suggestion_agent")
    graph_builder.add_conditional_edges(
        "suggestion_agent",
        check_completion,
        {
            "done": END,
            "continue": "retrieval_node"
        }
    )

    graph = graph_builder.compile()
    return graph