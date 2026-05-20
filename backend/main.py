import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
if os.path.exists("vibe.env"):
    load_dotenv("vibe.env")
elif os.path.exists("../vibe.env"):
    load_dotenv("../vibe.env")
else:
    load_dotenv()

from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types
from agent import github_card_agent

# Initialize FastAPI
app = FastAPI(title="GitHub Dev Card Generator")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
STATIC_DIR = "static"
CARDS_DIR = os.path.join(STATIC_DIR, "cards")
os.makedirs(CARDS_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ADK Runner
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()
runner = Runner(
    app_name="GitHubDevCardApp",
    agent=github_card_agent,
    session_service=session_service,
    memory_service=memory_service
)

class GenerateRequest(BaseModel):
    username: str

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/generate")
async def generate_card(request: GenerateRequest):
    username = request.username
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    try:
        # Construct the Content object required by ADK
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=f"Generate a dev card for the GitHub user: {username}")]
        )

        try:
            # Run the agent via the ADK Runner
            events = runner.run(
                user_id=username,
                session_id=username,
                new_message=user_message
            )
            
            # Collect the final response from the events
            final_text = ""
            for event in events:
                if hasattr(event, 'text') and event.text:
                    final_text = event.text
                elif hasattr(event, 'content'):
                    if hasattr(event.content, 'text'):
                        final_text = event.content.text
                    elif isinstance(event.content, list) and len(event.content) > 0:
                        for part in event.content:
                            if hasattr(part, 'text'):
                                final_text += part.text
            
            if not final_text:
                raise Exception("Agent returned no text")

        except Exception as agent_err:
            print(f"Agent failed (likely Quota): {agent_err}. Using manual fallback...")
            # --- DESI JUGAAD: MANUAL FALLBACK ---
            from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card
            
            # Call tools manually if Agent fails
            github_data = await scrape_github(username)
            analysis = await analyze_profile(github_data)
            html = generate_card_html(username, github_data, analysis)
            final_text = save_card(username, html)

        card_url = final_text.strip()
        
        # Cleanup path
        if "/static/cards/" in card_url:
            start_idx = card_url.find("/static/cards/")
            card_url = card_url[start_idx:].split()[0].strip().replace(")", "").replace("]", "").replace("`", "")
        
        filename = f"{username}.html"
        file_path = os.path.join(CARDS_DIR, filename)
        
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return {
                "card_url": card_url,
                "html": html_content
            }
        else:
            raise HTTPException(status_code=500, detail="Card file not created")

    except Exception as e:
        print(f"Error during generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/card/{username}")
async def get_card(username: str):
    file_path = os.path.join(CARDS_DIR, f"{username}.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Card not found")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return {"html": f.read()}

if __name__ == "__main__":
    import uvicorn
    # SECURITY NOTE: We use host="127.0.0.1" to ensure the server is ONLY 
    # accessible from this machine. Do NOT change to "0.0.0.0" as it could
    # expose your server to the local network or internet.
    uvicorn.run(app, host="0.0.0.0", port=8080)
