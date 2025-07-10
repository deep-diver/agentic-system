from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import AsyncGenerator, List, Dict, Any
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from graph.graph import build_graph
from dotenv import load_dotenv

# Load environment variables from root directory
load_dotenv(dotenv_path="../../.env")

# Global variable to store the graph
graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    # Initialize the graph on startup
    graph = build_graph()
    print("Team Building graph initialized successfully")
    yield
    # Cleanup if needed
    graph = None

app = FastAPI(
    title="Team Building API",
    description="API for team building suggestions based on project requirements",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TeamBuildingRequest(BaseModel):
    message: str
    session_id: str = "default"

class TeamBuildingResponse(BaseModel):
    response: str
    session_id: str

@app.post("/team-building", response_model=TeamBuildingResponse)
async def team_building(request: TeamBuildingRequest):
    """
    Send a message and get a complete team building response
    """
    try:
        if not graph:
            raise HTTPException(status_code=500, detail="Graph not initialized")
        
        # Get the final response from the graph
        final_response = ""
        for event in graph.stream(
            {"messages": [{"role": "user", "content": request.message}]},
            config={"configurable": {"thread_id": request.session_id}}
        ):
            for key, value in event.items():
                if key == 'suggestion_agent' and 'suggested_participants' in value:
                    participants = value['suggested_participants']
                    final_response = participants.model_dump_json(indent=2)
        
        return TeamBuildingResponse(
            response=final_response,
            session_id=request.session_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/team-building/stream")
async def team_building_stream(message: str, session_id: str = "default"):
    """
    Send a message and get a streaming response with progress updates - REAL LANGGRAPH VERSION
    """
    try:
        if not graph:
            raise HTTPException(status_code=500, detail="Graph not initialized")
        
        async def generate_response() -> AsyncGenerator[str, None]:
            progresses = []
            final_response = ""
            
            try:
                # Send initial progress update - WORKING FORMAT
                initial_progress = {
                    "type": "progress",
                    "progress": "Processing your team building request...",
                    "session_id": session_id
                }
                print(f"[{datetime.now().isoformat()}] Yielding initial progress: {initial_progress}")
                yield f"data: {json.dumps(initial_progress)}\n\n"  # WORKING FORMAT: \n\n not \\n\\n
                await asyncio.sleep(0.1)  # WORKING PATTERN: await after each yield
                
                # REAL LANGGRAPH EXECUTION
                async for event in graph.astream(
                    {"messages": [{"role": "user", "content": message}]},
                    config={"configurable": {"thread_id": session_id}}
                ):
                    # Safe logging without large objects
                    try:
                        event_keys = list(event.keys())
                        print(f"Processing event: {event_keys}")
                    except:
                        pass
                    
                    for key, value in event.items():
                        if key == 'role_extraction_agent':
                            progress_msg = "Extracting required roles from project description"
                            progresses.append(progress_msg)
                            progress_chunk = {
                                "type": "progress",
                                "progress": progress_msg,
                                "session_id": session_id
                            }
                            yield f"data: {json.dumps(progress_chunk)}\n\n"
                            
                            # Also yield the extracted roles
                            if 'extracted_roles' in value:
                                roles_chunk = {
                                    "type": "roles",
                                    "roles": value['extracted_roles'].model_dump(),
                                    "session_id": session_id
                                }
                                yield f"data: {json.dumps(roles_chunk)}\n\n"
                            
                            await asyncio.sleep(0)
                        
                        elif key == 'paraphrase_agent':
                            progress_msg = "Paraphrasing query for project similarity search"
                            progresses.append(progress_msg)
                            progress_chunk = {
                                "type": "progress",
                                "progress": progress_msg,
                                "session_id": session_id
                            }
                            yield f"data: {json.dumps(progress_chunk)}\n\n"
                            
                            # Also yield the paraphrased query
                            if 'paraphrased_query' in value:
                                query_chunk = {
                                    "type": "query",
                                    "query": str(value['paraphrased_query']),  # Convert to string safely
                                    "session_id": session_id
                                }
                                yield f"data: {json.dumps(query_chunk)}\n\n"
                            
                            await asyncio.sleep(0)
                        
                        elif key == 'retrieval_node':
                            progress_msg = "Searching for similar projects in database"
                            progresses.append(progress_msg)
                            progress_chunk = {
                                "type": "progress",
                                "progress": progress_msg,
                                "session_id": session_id
                            }
                            yield f"data: {json.dumps(progress_chunk)}\n\n"
                            
                            # Also yield the retrieved projects count
                            if 'retrieved_projects' in value:
                                projects_count = len(value['retrieved_projects'])
                                projects_chunk = {
                                    "type": "projects",
                                    "count": projects_count,
                                    "session_id": session_id
                                }
                                yield f"data: {json.dumps(projects_chunk)}\n\n"
                            
                            await asyncio.sleep(0)
                        
                        elif key == 'suggestion_agent':
                            progress_msg = "Analyzing participants and suggesting optimal team"
                            progresses.append(progress_msg)
                            progress_chunk = {
                                "type": "progress",
                                "progress": progress_msg,
                                "session_id": session_id
                            }
                            yield f"data: {json.dumps(progress_chunk)}\n\n"
                            
                            # Also yield the suggested participants
                            if 'suggested_participants' in value:
                                participants = value['suggested_participants']
                                final_response = participants.model_dump_json(indent=2)
                                
                                participants_chunk = {
                                    "type": "participants",
                                    "participants": participants.model_dump(),
                                    "session_id": session_id
                                }
                                yield f"data: {json.dumps(participants_chunk)}\n\n"
                            
                            await asyncio.sleep(0)
            
                # Send final response with all progress data
                final_chunk = {
                    "type": "final",
                    "response": final_response,
                    "progresses": progresses,
                    "session_id": session_id
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                
            except Exception as e:
                # Send error message with safe error handling
                error_chunk = {
                    "type": "error",
                    "error": str(e)[:200],  # Limit error message length
                    "session_id": session_id
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
            
            finally:
                # Always send end signal
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_root():
    """
    Serve the main UI
    """
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "graph_initialized": graph is not None}

# Mount static files for CSS, JS, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Team Building FastAPI Server")
    parser.add_argument("--port", type=int, default=8002, help="Port to run the server on (default: 8002)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
    parser.add_argument("--timeout", type=int, default=300, help="Request timeout in seconds (default: 300)")
    
    args = parser.parse_args()
    
    print(f"Starting Team Building server on {args.host}:{args.port}")
    print(f"Request timeout set to {args.timeout} seconds")
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        timeout_keep_alive=args.timeout,
        timeout_graceful_shutdown=30
    )