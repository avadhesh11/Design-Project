from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# for model in client.models.list():
#     print(model.name)

def get_embedding(text: str) -> list[float]:
    response = client.models.embed_content(
        model="gemini-embedding-2-preview",  # latest embedding model
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768
        )
    )
    return response.embeddings[0].values


def get_query_embedding(text: str) -> list[float]:
    response = client.models.embed_content(
        model="gemini-embedding-2-preview",
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768
        )
    )
    return response.embeddings[0].values