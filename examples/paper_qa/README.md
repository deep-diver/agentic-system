# Paper QA FastAPI Server

A FastAPI server wrapper for the Paper QA system that allows you to ask questions about academic papers through HTTP endpoints.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export UPSTAGE_API_KEY="your_upstage_api_key"
export SERPER_API_KEY="your_serper_api_key"
```

3. Start the server:
```bash
python server.py
```

The server will run on `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /health
```
Returns server health status and graph initialization status.

### Chat (Complete Response)
```
POST /chat
```
Send a message and receive a complete response.

Request body:
```json
{
  "message": "Search for the paper 'Attention is All You Need'",
  "session_id": "optional_session_id"
}
```

Response:
```json
{
  "response": "URL to download 'Attention is All You Need': https://arxiv.org/pdf/1706.03762",
  "session_id": "optional_session_id"
}
```

### Chat (Streaming Response)
```
POST /chat/stream
```
Send a message and receive a streaming response (Server-Sent Events).

Request body: Same as `/chat`

Response: Stream of JSON chunks followed by `[DONE]`

## Testing

Run the test script:
```bash
python test_server.py
```

## Usage Examples

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for Attention is All You Need", "session_id": "test"}'

# Streaming
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is transformer architecture?", "session_id": "test"}'
```

### Using Python

```python
import requests

# Regular chat
response = requests.post("http://localhost:8000/chat", json={
    "message": "Search for the paper 'BERT'",
    "session_id": "my_session"
})
print(response.json())

# Streaming chat
response = requests.post("http://localhost:8000/chat/stream", json={
    "message": "What is BERT?",
    "session_id": "my_session"
}, stream=True)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

## Features

- **Session Management**: Each conversation can have a unique session ID
- **Streaming Support**: Real-time response streaming
- **Error Handling**: Proper HTTP error responses
- **Health Monitoring**: Health check endpoint
- **Auto-Documentation**: FastAPI auto-generates API docs at `/docs`