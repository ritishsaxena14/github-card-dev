import os
import sys
from dotenv import load_dotenv

# Load environment variables
if os.path.exists("vibe.env"):
    load_dotenv("vibe.env")
else:
    load_dotenv("../vibe.env")

from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types
from agent import github_card_agent

def test_agent():
    username = "karpathy"
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    runner = Runner(
        app_name="TestApp",
        agent=github_card_agent,
        session_service=session_service,
        memory_service=memory_service
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=f"Generate a dev card for the GitHub user: {username}")]
    )

    print(f"Running agent for {username}...")
    try:
        events = runner.run(
            user_id=username,
            session_id=username,
            new_message=user_message
        )
        
        for event in events:
            print(f"Event: {event}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_agent()
