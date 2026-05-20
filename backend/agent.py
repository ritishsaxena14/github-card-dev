from google.adk import Agent
from google.adk.tools import McpToolset
from mcp import StdioServerParameters
import os
from dotenv import load_dotenv

# Load environment variables
if os.path.exists("vibe.env"):
    load_dotenv("vibe.env")
elif os.path.exists("../vibe.env"):
    load_dotenv("../vibe.env")
else:
    load_dotenv()

# Define the MCP connection parameters
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
mcp_script = os.path.join(current_dir, "mcp_server.py")

params = StdioServerParameters(
    command=sys.executable,
    args=[mcp_script],
    env=os.environ.copy()
)

# Define the MCP toolset using the connection parameters
mcp_tools = McpToolset(connection_params=params)

# Define the GitHub Card Agent
github_card_agent = Agent(
    name="github_card_agent",
    model="gemini-2.0-flash",
    instruction="""
    You are a GitHub profile analyst and dev card generator. 
    When a user gives you a GitHub username, you ALWAYS follow this exact sequence: 
    1. Call 'scrape_github' to get the raw data.
    2. Call 'analyze_profile' with that data to get insights.
    3. Call 'generate_card_html' with the username, raw data, and analysis.
    4. Call 'save_card' with the username and HTML.
    
    Never skip steps. Be enthusiastic about developers' work. 
    If the profile is private or doesn't exist, say so clearly.
    Respond ONLY with the final URL of the saved card (e.g., /static/cards/username.html).
    """,
    tools=[mcp_tools]
)
