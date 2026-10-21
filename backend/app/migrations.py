import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

CREATE_MATCH_EMBEDDINGS_SQL = """
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector,
    match_workspace_id uuid,
    match_count integer DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    workspace_id uuid,
    content text,
    source_type text,
    source_id uuid,
    similarity double precision
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.workspace_id,
        e.content,
        e.source_type,
        e.source_id,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    WHERE e.workspace_id = match_workspace_id
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""


def apply_migrations(engine):
    """
    Ensure all required table columns and database RPC functions exist and are up to date.
    Idempotent and safe to run on startup.
    """
    with engine.begin() as conn:
        # 1. Column migrations
        for col_sql in [
            "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS ai_provider VARCHAR DEFAULT 'gemini'",
            "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS ai_model VARCHAR DEFAULT 'gemini-3.5-flash-lite'",
            "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS ai_ollama_url VARCHAR DEFAULT 'http://localhost:11434'",
            "ALTER TABLE users ALTER COLUMN password DROP NOT NULL",
        ]:
            try:
                conn.execute(text(col_sql))
            except Exception as migrate_err:
                logger.debug(f"Column migration notice: {migrate_err}")

        # 2. match_embeddings RPC with workspace_id in projection
        try:
            check_sql = "SELECT pg_get_function_result(oid) FROM pg_proc WHERE proname = 'match_embeddings';"
            res = conn.execute(text(check_sql)).scalar()
            if not res or "workspace_id" not in res:
                logger.info("Migrating match_embeddings RPC to include workspace_id in return signature...")
                conn.execute(text("DROP FUNCTION IF EXISTS match_embeddings(vector, uuid, integer);"))
                conn.execute(text(CREATE_MATCH_EMBEDDINGS_SQL))
                logger.info("Successfully updated match_embeddings RPC with workspace_id projection.")
        except Exception as rpc_err:
            logger.warning(f"RPC migration notice: {rpc_err}")
