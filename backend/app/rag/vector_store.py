import time
import uuid
import logging
from ..utils.supabase_client import supabase
from ..database import SessionLocal
from ..models import Document
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
    """
    Find most relevant chunks for a query using cosine similarity, strictly from active documents
    in the specified workspace.
    Fails closed: If active document validation fails, returns an empty list to prevent data leakage.
    """
    import uuid

    if not workspace_id:
        logger.warning("search_similar called without workspace_id; failing closed.")
        return []

    ws_str = str(workspace_id)
    try:
        query_embedding = get_query_embedding(query)
    except Exception as emb_err:
        logger.warning(f"Error generating query embedding for search: {emb_err}")
        return []

    try:
        result = supabase.rpc("match_embeddings", {
            "query_embedding": query_embedding,
            "match_workspace_id": ws_str,
            "match_count": limit * 2
        }).execute()
        raw_chunks = result.data or []
    except Exception as rpc_err:
        logger.warning(f"Error executing match_embeddings RPC: {rpc_err}")
        return []

    if not raw_chunks:
        return []

    # Validate against PostgreSQL documents table to ensure deleted or foreign docs are never returned.
    # Security: If validation fails, FAIL CLOSED and return an empty list rather than unvalidated chunks.
    try:
        try:
            ws_uuid = uuid.UUID(ws_str)
        except (ValueError, TypeError, AttributeError):
            ws_uuid = ws_str

        db = SessionLocal()
        try:
            active_docs = db.query(Document.id).filter(Document.workspace_id == ws_uuid).all()
            active_doc_ids = {str(d.id) for d in active_docs}
        finally:
            db.close()

        filtered = [
            c for c in raw_chunks
            if (
                # Must match target workspace
                (not c.get("workspace_id") or str(c.get("workspace_id")) == ws_str)
                # Must be an active, non-deleted document in this workspace
                and (c.get("source_type") != "document" or str(c.get("source_id")) in active_doc_ids)
                and c.get("similarity", 1.0) >= min_similarity
            )
        ]
        return filtered[:limit]
    except Exception as filter_err:
        logger.error(f"Security: Failed to validate active documents in database; failing closed: {filter_err}")
        return []