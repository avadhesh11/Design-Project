from ..utils.supabase_client import supabase
from .embedder import get_embedding, get_query_embedding
 
from .chunker import chunk_text

def store_embeddings(
    workspace_id: str,
    source_type: str, 
    source_id: str,
    content: str
):
    """Chunk content, embed each chunk, store in pgvector."""
    chunks = chunk_text(content)

    if not chunks:
        return

 
    supabase.table("embeddings").delete().eq(
        "source_id", source_id
    ).execute()

    rows = []
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        rows.append({
            "workspace_id": workspace_id,
            "source_type": source_type,
            "source_id": source_id,
            "chunk_index": i,
            "content": chunk,
            "embedding": embedding
        })

    supabase.table("embeddings").insert(rows).execute()


def search_similar(
    workspace_id: str,
    query: str,
    limit: int = 5
) -> list[dict]:
    """Find most relevant chunks for a query using cosine similarity."""
    query_embedding = get_query_embedding(query)

    result = supabase.rpc("match_embeddings", {
        "query_embedding": query_embedding,
        "match_workspace_id": workspace_id,
        "match_count": limit
    }).execute()

    return result.data or []