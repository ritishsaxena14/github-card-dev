import os
from google import genai
from dotenv import load_dotenv

if os.path.exists("vibe.env"):
    load_dotenv("vibe.env")
else:
    load_dotenv("../vibe.env")

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Hello, are you working?"
    )
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
