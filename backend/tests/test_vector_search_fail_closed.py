import uuid
from unittest.mock import patch, MagicMock
import pytest
from app.rag.vector_store import search_similar
from app.models import Document


def test_vector_search_fail_closed_on_db_error():
    """
    CRITICAL SECURITY REGRESSION TEST:
    When document validation in Postgres fails (e.g. database down, query error),
    search_similar MUST fail closed by returning an empty list [].
    It must NEVER fall back to returning unverified raw vector chunks.
    """
    ws_id = str(uuid.uuid4())
    fake_raw_chunks = [
        {
            "content": "Secret unverified document chunk",
            "source_id": str(uuid.uuid4()),
            "workspace_id": ws_id,
            "source_type": "document",
            "similarity": 0.88
        }
    ]

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        # Supabase returns raw chunks
        mock_sb.rpc.return_value.execute.return_value.data = fake_raw_chunks

        # Postgres database raises an OperationalError during validation
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database connection pool exhausted")
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_id, query="secret data", limit=5)

        # Fail-closed guarantee: Must return [] and NOT leak fake_raw_chunks
        assert results == [], "Expected fail-closed empty list when DB validation fails"


def test_vector_search_excludes_deleted_documents():
    """
    Test that chunks from documents marked as deleted or missing from Postgres are filtered out.
    """
    ws_id = str(uuid.uuid4())
    doc_active_id = uuid.uuid4()
    doc_deleted_id = uuid.uuid4()

    fake_raw_chunks = [
        {"content": "Active doc chunk", "source_id": str(doc_active_id), "workspace_id": ws_id, "source_type": "document", "similarity": 0.9},
        {"content": "Deleted doc chunk", "source_id": str(doc_deleted_id), "workspace_id": ws_id, "source_type": "document", "similarity": 0.85}
    ]

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        mock_sb.rpc.return_value.execute.return_value.data = fake_raw_chunks

        # DB only returns doc_active_id as active and belonging to workspace
        mock_db = MagicMock()
        active_doc = MagicMock()
        active_doc.id = doc_active_id
        active_doc.workspace_id = uuid.UUID(ws_id)
        mock_db.query.return_value.filter.return_value.all.return_value = [active_doc]
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_id, query="test query", limit=5)

        assert len(results) == 1
        assert results[0]["source_id"] == str(doc_active_id)
        assert results[0]["content"] == "Active doc chunk"


def test_vector_search_excludes_documents_from_other_workspace():
    """
    Test workspace isolation: chunks from another workspace must never be returned.
    """
    ws_target_id = str(uuid.uuid4())
    ws_other_id = uuid.uuid4()
    doc_other_id = uuid.uuid4()

    fake_raw_chunks = [
        {"content": "Other workspace chunk", "source_id": str(doc_other_id), "workspace_id": ws_target_id, "source_type": "document", "similarity": 0.95}
    ]

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        mock_sb.rpc.return_value.execute.return_value.data = fake_raw_chunks

        # In DB, this document belongs to ws_other_id, not ws_target_id
        mock_db = MagicMock()
        # Query filtered by ws_target_id returns empty
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_target_id, query="other data", limit=5)

        assert results == []


def test_vector_search_empty_raw_result():
    """Test behavior when vector search returns no matching chunks."""
    ws_id = str(uuid.uuid4())
    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb:

        mock_sb.rpc.return_value.execute.return_value.data = []
        results = search_similar(workspace_id=ws_id, query="empty query")
        assert results == []


def test_vector_search_query_embedding_failure():
    """Test behavior when embedding service fails: returns [] gracefully without crashing."""
    ws_id = str(uuid.uuid4())
    with patch("app.rag.vector_store.get_query_embedding", side_effect=Exception("Embedding API 503")):
        results = search_similar(workspace_id=ws_id, query="failing query")
        assert results == []


def test_vector_search_rejects_mismatched_workspace_metadata():
    """Test that chunks containing a different workspace_id are strictly rejected."""
    ws_id = str(uuid.uuid4())
    other_ws_id = str(uuid.uuid4())
    doc_id = uuid.uuid4()

    fake_raw_chunks = [
        {
            "content": "Foreign chunk",
            "source_id": str(doc_id),
            "workspace_id": other_ws_id,  # Mismatched!
            "source_type": "document",
            "similarity": 0.95
        }
    ]

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        mock_sb.rpc.return_value.execute.return_value.data = fake_raw_chunks

        mock_db = MagicMock()
        active_doc = MagicMock()
        active_doc.id = doc_id
        active_doc.workspace_id = uuid.UUID(ws_id)
        mock_db.query.return_value.filter.return_value.all.return_value = [active_doc]
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_id, query="test query")
        assert results == [], "Expected chunk with foreign workspace_id to be rejected"


def test_vector_search_rejects_missing_or_malformed_source_id():
    """Test that chunks with missing or non-UUID source_id are rejected."""
    ws_id = str(uuid.uuid4())

    fake_raw_chunks = [
        {"content": "Missing source id", "source_id": None, "workspace_id": ws_id, "source_type": "document", "similarity": 0.9},
        {"content": "Malformed source id", "source_id": "not-a-valid-uuid", "workspace_id": ws_id, "source_type": "document", "similarity": 0.9},
        {"content": "Empty source id", "source_id": "", "workspace_id": ws_id, "source_type": "document", "similarity": 0.9}
    ]

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        mock_sb.rpc.return_value.execute.return_value.data = fake_raw_chunks
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_id, query="test query")
        assert results == [], "Expected all malformed source_id chunks to be rejected"


def test_vector_search_rejects_missing_or_unsupported_source_type():
    """
    Test that chunks with missing, empty, or unsupported source_type
    (e.g. 'task', 'chat', 'unknown') are strictly rejected.
    Only 'document' source_type is supported by the current vector store schema.
    """
    ws_id = str(uuid.uuid4())
    doc_id = uuid.uuid4()

    fake_raw_chunks = [
        {"content": "Missing source_type", "source_id": str(doc_id), "workspace_id": ws_id, "similarity": 0.92},
        {"content": "None source_type", "source_id": str(doc_id), "workspace_id": ws_id, "source_type": None, "similarity": 0.92},
        {"content": "Empty source_type", "source_id": str(doc_id), "workspace_id": ws_id, "source_type": "", "similarity": 0.92},
        {"content": "Task source_type", "source_id": str(doc_id), "workspace_id": ws_id, "source_type": "task", "similarity": 0.92},
        {"content": "Chat source_type", "source_id": str(doc_id), "workspace_id": ws_id, "source_type": "chat", "similarity": 0.92},
        {"content": "Unknown source_type", "source_id": str(doc_id), "workspace_id": ws_id, "source_type": "unknown", "similarity": 0.92},
    ]

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        mock_sb.rpc.return_value.execute.return_value.data = fake_raw_chunks
        mock_db = MagicMock()
        active_doc = MagicMock()
        active_doc.id = doc_id
        active_doc.workspace_id = uuid.UUID(ws_id)
        mock_db.query.return_value.filter.return_value.all.return_value = [active_doc]
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_id, query="test query")
        assert results == [], "Expected all chunks with missing or unsupported source_type to be rejected"


def test_vector_search_ensures_explicit_workspace_id_on_returned_chunks():
    """
    Test that a chunk missing workspace metadata (or having empty/malformed workspace_id)
    is strictly rejected and NEVER stamped with manufactured workspace metadata.
    """
    ws_id = str(uuid.uuid4())
    doc_id = uuid.uuid4()

    fake_raw_chunks = [
        {"content": "Missing ws_id", "source_id": str(doc_id), "source_type": "document", "similarity": 0.92},
        {"content": "None ws_id", "source_id": str(doc_id), "workspace_id": None, "source_type": "document", "similarity": 0.92},
        {"content": "Empty ws_id", "source_id": str(doc_id), "workspace_id": "", "source_type": "document", "similarity": 0.92},
        {"content": "Malformed ws_id", "source_id": str(doc_id), "workspace_id": "not-a-uuid", "source_type": "document", "similarity": 0.92},
    ]

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        mock_sb.rpc.return_value.execute.return_value.data = fake_raw_chunks
        mock_db = MagicMock()
        active_doc = MagicMock()
        active_doc.id = doc_id
        active_doc.workspace_id = uuid.UUID(ws_id)
        mock_db.query.return_value.filter.return_value.all.return_value = [active_doc]
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_id, query="test query")
        assert results == [], "Expected all chunks with missing, empty, or malformed workspace_id to be rejected"


def test_vector_search_accepts_valid_matching_workspace_metadata():
    """
    Positive test proving that a chunk with valid, matching workspace metadata
    can still be returned after document validation.
    """
    ws_id = str(uuid.uuid4())
    doc_id = uuid.uuid4()

    fake_raw_chunks = [
        {
            "content": "Valid chunk",
            "source_id": str(doc_id),
            "workspace_id": ws_id,
            "source_type": "document",
            "similarity": 0.92
        }
    ]

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        mock_sb.rpc.return_value.execute.return_value.data = fake_raw_chunks
        mock_db = MagicMock()
        active_doc = MagicMock()
        active_doc.id = doc_id
        active_doc.workspace_id = uuid.UUID(ws_id)
        mock_db.query.return_value.filter.return_value.all.return_value = [active_doc]
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_id, query="test query")
        assert len(results) == 1
        assert results[0]["workspace_id"] == ws_id
        assert results[0]["source_id"] == str(doc_id)
        assert results[0]["source_type"] == "document"
        assert results[0]["content"] == "Valid chunk"


def test_vector_search_actual_rpc_contract_includes_workspace_id():
    """
    REGRESSION TEST:
    Verifies that chunks matching the actual PostgreSQL match_embeddings RPC contract
    (including 'id', 'workspace_id', 'content', 'source_type', 'source_id', 'similarity')
    are accepted and validated without missing-workspace_id rejections.
    """
    ws_id = str(uuid.uuid4())
    doc_id = uuid.uuid4()
    chunk_id = str(uuid.uuid4())

    # Actual contract returned by match_embeddings RPC:
    # TABLE (id uuid, workspace_id uuid, content text, source_type text, source_id uuid, similarity double precision)
    rpc_chunk = {
        "id": chunk_id,
        "workspace_id": ws_id,
        "content": "Orbit Workspace Security Policy: Session timeout is 15 minutes.",
        "source_type": "document",
        "source_id": str(doc_id),
        "similarity": 0.85
    }

    with patch("app.rag.vector_store.get_query_embedding", return_value=[0.1] * 768), \
         patch("app.rag.vector_store.supabase") as mock_sb, \
         patch("app.rag.vector_store.SessionLocal") as mock_session:

        mock_sb.rpc.return_value.execute.return_value.data = [rpc_chunk]
        mock_db = MagicMock()
        active_doc = MagicMock()
        active_doc.id = doc_id
        active_doc.workspace_id = uuid.UUID(ws_id)
        mock_db.query.return_value.filter.return_value.all.return_value = [active_doc]
        mock_session.return_value = mock_db

        results = search_similar(workspace_id=ws_id, query="What is the session timeout?")
        assert len(results) == 1
        assert results[0]["id"] == chunk_id
        assert results[0]["workspace_id"] == ws_id
        assert results[0]["source_id"] == str(doc_id)
        assert results[0]["source_type"] == "document"
        assert "Session timeout is 15 minutes" in results[0]["content"]


