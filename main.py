import os
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv
 
# Load environment variables from .env file
load_dotenv()
 
# Import ADK components
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
 
# Import the agent
from legal_search_Agent.agent import root_agent
 
# 1. Initialize FastAPI app
app = FastAPI(
    title="Legal Search Agent API",
    description="FastAPI wrapper for Google ADK Legal Counsel Agent with Swagger documentation",
    version="1.0.0"
)
 
# 2. Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict this in production
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# 3. Initialize Session Manager and Runner
session_manager = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="legal_search_Agent",
    session_service=session_manager
)
 
# 4. Pydantic Models for Request/Response
class MessagePart(BaseModel):
    text: str = Field(..., description="The text content of the message")
 
class MessageInput(BaseModel):
    role: str = Field(default="user", description="Role of the message sender (user/model)")
    parts: List[MessagePart] = Field(..., description="Message parts containing text")
 
class ChatRequest(BaseModel):
    user_id: str = Field(default="default_user", description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session ID (optional, will create new if not provided)")
    message: str = Field(..., description="The message to send to the agent")
 
class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Session ID for continuing the conversation")
    response: str = Field(..., description="Agent response text")
    model: str = Field(..., description="Model used for generation")
 
class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    app_name: str
 
class CreateSessionRequest(BaseModel):
    user_id: str = Field(default="default_user", description="User identifier")
 
# 5. API Endpoints
 
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Legal Search Agent API is running"}
 
 
@app.post("/sessions", response_model=SessionInfo, tags=["Sessions"])
async def create_session(request: CreateSessionRequest):
    """
    Create a new chat session.
   
    Returns a session ID that can be used for subsequent chat requests.
    """
    session_id = str(uuid.uuid4())
    session = await session_manager.create_session(
        app_name="legal_search_Agent",
        user_id=request.user_id,
        session_id=session_id
    )
    return SessionInfo(
        session_id=session.id,
        user_id=request.user_id,
        app_name="legal_search_Agent"
    )
 
 
@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Send a message to the Legal Counsel Agent and get a response.
   
    If no session_id is provided, a new session will be created automatically.
    The agent uses Google Search to find relevant legal information and provides cited responses.
    """
    # Create or get session
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        await session_manager.create_session(
            app_name="legal_search_Agent",
            user_id=request.user_id,
            session_id=session_id
        )
    else:
        # Verify session exists
        session = await session_manager.get_session(
            app_name="legal_search_Agent",
            user_id=request.user_id,
            session_id=session_id
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
   
    # Create the message content
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=request.message)]
    )
   
    # Run the agent
    response_text = ""
    model_version = "gemini-2.5-flash"
   
    async for event in runner.run_async(
        user_id=request.user_id,
        session_id=session_id,
        new_message=user_content
    ):
        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text
        if hasattr(event, 'model_version'):
            model_version = event.model_version
   
    return ChatResponse(
        session_id=session_id,
        response=response_text,
        model=model_version
    )
 
 
@app.get("/sessions/{user_id}", tags=["Sessions"])
async def list_sessions(user_id: str):
    """
    List all sessions for a user.
    """
    sessions = await session_manager.list_sessions(
        app_name="legal_search_Agent",
        user_id=user_id
    )
    return {"user_id": user_id, "sessions": [s.id for s in sessions]}
 
 
@app.delete("/sessions/{user_id}/{session_id}", tags=["Sessions"])
async def delete_session(user_id: str, session_id: str):
    """
    Delete a specific session.
    """
    await session_manager.delete_session(
        app_name="legal_search_Agent",
        user_id=user_id,
        session_id=session_id
    )
    return {"status": "deleted", "session_id": session_id}
 
 
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)