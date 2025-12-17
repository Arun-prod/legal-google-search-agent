import os
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

# The ADK will look for subfolders in this directory to find agents
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri="sqlite:///./session.db", 
    web=True  # Enables the /dev-ui/ path for testing
)

if __name__ == "__main__":
    # Get port from environment for deployment (e.g., Streamlit or Cloud Run)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)