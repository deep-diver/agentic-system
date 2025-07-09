from graph.state import State
from graph.nodes import (
    chatbot, 
    route_tools, 
    BasicToolNode
)
from graph.upstage import tools, llm

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def build_graph():
    memory = MemorySaver()

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)

    tool_node = BasicToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_conditional_edges(
        "chatbot",
        route_tools,
        {"tools": "tools", END: END},
    )
    # Any time a tool is called, we return to the chatbot to decide the next step
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")
    graph = graph_builder.compile(checkpointer=memory)
    return graph