import os
import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# 1. Initialize the app
# Use a relative path to ensure agents are picked up correctly
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri="sqlite:///./session.db",
    web=True
)

# 2. THE FIX: Custom OpenAPI schema that handles the Pydantic crash
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    # We use a try-except block here because the ADK types crash the default 
    # FastAPI schema generator.
    try:
        openapi_schema = get_openapi(
            title="Multi-Agent Legal Service",
            version="1.0.0",
            description="API for Node.js/React Frontend integration",
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
    except Exception:
        # Fallback: Create a minimal schema if the full generation fails
        # This ensures the /openapi.json endpoint doesn't return a 500 error
        app.openapi_schema = {
            "openapi": "3.1.0",
            "info": {"title": "Multi-Agent API (Minimal Mode)", "version": "1.0.0"},
            "paths": {} # Your agents will still be callable even if not listed here
        }
    
    return app.openapi_schema

app.openapi = custom_openapi

# 3. Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development; restrict this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    # Ensure you are binding to 0.0.0.0 if you want to access this from other network devices
    uvicorn.run(app, host="127.0.0.1", port=8000)