import os
import json
import requests
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

@tool
def to_paper_search_agent(paper_title: str):
    """Use this tool to search for paper's arXiv URL on the internet"""
    writer = get_stream_writer()
    url = "https://google.serper.dev/search"

    payload = json.dumps({"q": f"{paper_title} on arXiv"})
    headers = {
        'X-API-KEY': os.getenv("SERPER_API_KEY"),
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    search_results = response.json()['organic']

    if len(search_results) == 0:
        writer("Could not find the URL to download the paper")
        return "Count not find the URL to download the paper"

    first_result = search_results[0]
    if not first_result['link'].startswith("https://arxiv.org"):
        writer("Could not find the URL to download the paper")
        return "Could not find the URL to download the paper"

    writer(f"URL to download '{paper_title}': {first_result['link'].replace('abs', 'pdf')}")
    return f"URL to download '{paper_title}': {first_result['link'].replace('abs', 'pdf')}"