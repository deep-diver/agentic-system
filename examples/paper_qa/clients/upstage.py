import os
from openai import OpenAI

def get_upstage_client():
    client = OpenAI(
        base_url="https://api.upstage.ai/v1",
        api_key=os.getenv("UPSTAGE_API_KEY")
    )
    return client