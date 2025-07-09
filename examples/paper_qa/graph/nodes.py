from langchain_core.messages import ToolMessage
from langchain_core.prompts import (
    ChatPromptTemplate, 
    MessagesPlaceholder
)
from langgraph.graph import END

from graph.state import State
from graph.upstage import llm

system_prompt = """You are an academic paper analyzer. 
- Basically, you don't have knowledge of the requested paper.
- Hence, you need to use the provided tools to get the paper information from the internet. 
- Your job is to find appropriate tool to transfer to based on the user's request and results of tool calls. 
- If enough information is collected to complete the user request, you should directly answer to the user request.
- Always complete the full workflow: search -> download/parse -> retrieve -> answer."""

class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

# Define the node that will call the LLM
def chatbot(state: State):
    messages = state['messages']

    # --- Use the System Prompt defined at the top ---
    # system_prompt already defined globally
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), # Static system message
        MessagesPlaceholder(variable_name="messages"), # Placeholder for history/user input
    ])

    # Chain the prompt and model
    chain = prompt | llm

    # Invoke the chain with the current messages from the state
    # Note: We pass the messages directly to the placeholder
    response = chain.invoke({"messages": messages})

    # Return the AI's response to be added to the state
    return {"messages": [response]}

def route_tools(
    state: State,
):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END