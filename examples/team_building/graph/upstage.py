from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_upstage import ChatUpstage
from graph.schema import Roles, Participants

solar = ChatUpstage(model="solar-pro-250422")
solar_role = solar.with_structured_output(convert_to_openai_tool(Roles))
solar_participant = solar.with_structured_output(convert_to_openai_tool(Participants))