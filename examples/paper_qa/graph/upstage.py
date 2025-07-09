from langchain_upstage import ChatUpstage
from tools.paper_search import to_paper_search_agent
from tools.download_and_parse import to_download_and_parse_paper_agent
from tools.retrive import to_retrive_paper_content_to_answer_question_agent

tools = [
    to_paper_search_agent,
    to_download_and_parse_paper_agent,
    to_retrive_paper_content_to_answer_question_agent
]

llm = ChatUpstage()
llm = llm.bind_tools(tools)