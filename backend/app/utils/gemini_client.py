from google import genai
from dotenv import load_dotenv
import os

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

SYSTEM_PROMPT = """
You are Orbit AI — an intelligent workspace assistant.
You help teams with their documents, tasks, and communication.
Be concise, helpful, and professional.
When you have workspace context provided, use it to give accurate answers.
If you don't know something, say so honestly.
"""

def get_client():
    return client