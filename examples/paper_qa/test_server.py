import requests
import json

# Test the FastAPI server
BASE_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    print("Health check:", response.json())

def test_chat():
    data = {
        "message": "Search for the paper 'Attention is All You Need'",
        "session_id": "test_session"
    }
    response = requests.post(f"{BASE_URL}/chat", json=data)
    print("Chat response:", response.json())

def test_streaming():
    data = {
        "message": "What is the main contribution of the Attention is All You Need paper?",
        "session_id": "test_session"
    }
    response = requests.post(f"{BASE_URL}/chat/stream", json=data, stream=True)
    
    print("Streaming response:")
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]  # Remove 'data: ' prefix
                if data == '[DONE]':
                    print("Stream ended")
                    break
                try:
                    parsed = json.loads(data)
                    print(f"Chunk: {parsed['response']}")
                except json.JSONDecodeError:
                    print(f"Raw: {data}")

if __name__ == "__main__":
    print("Testing FastAPI Paper QA Server...")
    
    try:
        test_health()
        test_chat()
        test_streaming()
    except requests.exceptions.ConnectionError:
        print("Server is not running. Start it with: python server.py")