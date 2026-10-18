import time
import logging
from ..utils.supabase_client import supabase
from .embedder import get_embedding, get_query_embedding
from .chunker import chunk_text

logger = logging.getLogger(__name__)


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

    try:
        supabase.table("embeddings").delete().eq(
            "source_id", source_id
        ).execute()
    except Exception as del_err:
        logger.warning(f"Failed to clear old embeddings for source {source_id}: {del_err}")

    rows = []
    for i, chunk in enumerate(chunks):
        for attempt in range(3):
            try:
                embedding = get_embedding(chunk)
                rows.append({
                    "workspace_id": workspace_id,
                    "source_type": source_type,
                    "source_id": source_id,
                    "chunk_index": i,
                    "content": chunk,
                    "embedding": embedding
                })
                time.sleep(0.15)  # gentle delay to prevent rate limits (429)
                break
            except Exception as emb_err:
                logger.warning(f"Error embedding chunk {i} (attempt {attempt+1}): {emb_err}")
                time.sleep(1.0)

    if rows:
        try:
            supabase.table("embeddings").insert(rows).execute()
        except Exception as ins_err:
            logger.error(f"Failed to insert embeddings into Supabase: {ins_err}")


def search_similar(
    workspace_id: str,
    query: str,
    limit: int = 5,
    min_similarity: float = 0.55
) -> list[dict]:
    """Find most relevant chunks for a query using cosine similarity, strictly from active documents."""
    query_embedding = get_query_embedding(query)

    try:
        result = supabase.rpc("match_embeddings", {
            "query_embedding": query_embedding,
            "match_workspace_id": workspace_id,
            "match_count": limit * 2
        }).execute()
        raw_chunks = result.data or []
    except Exception as rpc_err:
        logger.warning(f"Error executing match_embeddings RPC: {rpc_err}")
        return []

    if not raw_chunks:
        return []

    # Validate against PostgreSQL documents table to ensure deleted docs are never returned
    try:
        from ..database import SessionLocal
        from ..models import Document
        db = SessionLocal()
        active_doc_ids = {str(d.id) for d in db.query(Document.id).filter(Document.workspace_id == workspace_id).all()}
        db.close()

        filtered = [
            c for c in raw_chunks
            if (c.get("source_type") != "document" or c.get("source_id") in active_doc_ids)
            and c.get("similarity", 1.0) >= min_similarity
        ]
        return filtered[:limit]
    except Exception as filter_err:
        logger.warning(f"Error filtering active document chunks: {filter_err}")
        return raw_chunks[:limit]