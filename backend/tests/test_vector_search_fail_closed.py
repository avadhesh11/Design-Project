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
        {"content": "Active doc chunk", "source_id": str(doc_active_id), "source_type": "document", "similarity": 0.9},
        {"content": "Deleted doc chunk", "source_id": str(doc_deleted_id), "source_type": "document", "similarity": 0.85}
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
        {"content": "Other workspace chunk", "source_id": str(doc_other_id), "source_type": "document", "similarity": 0.95}
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
