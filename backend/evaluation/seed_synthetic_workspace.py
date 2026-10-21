import uuid
from datetime import datetime, UTC
import logging
from app.database import SessionLocal
from app.models import (
    User,
    Workspace,
    WorkspaceMember,
    RoleEnum,
    Document,
    Task,
    TaskStatus,
    TaskPriority
)
from app.rag.vector_store import store_embeddings
from app.utils.supabase_client import supabase

logger = logging.getLogger(__name__)

# Deterministic IDs for the synthetic evaluation fixture
SYNTHETIC_WORKSPACE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
SYNTHETIC_OWNER_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
SYNTHETIC_DEV1_ID = uuid.UUID("00000000-0000-4000-8000-000000000003")
SYNTHETIC_QA_ID = uuid.UUID("00000000-0000-4000-8000-000000000004")
SYNTHETIC_DEV2_ID = uuid.UUID("00000000-0000-4000-8000-000000000005")

SYNTHETIC_DOC1_ID = uuid.UUID("00000000-0000-4000-8000-000000000011")
SYNTHETIC_DOC2_ID = uuid.UUID("00000000-0000-4000-8000-000000000012")
SYNTHETIC_DOC3_ID = uuid.UUID("00000000-0000-4000-8000-000000000013")

SYNTHETIC_TASK1_ID = uuid.UUID("00000000-0000-4000-8000-000000000021")
SYNTHETIC_TASK2_ID = uuid.UUID("00000000-0000-4000-8000-000000000022")
SYNTHETIC_TASK3_ID = uuid.UUID("00000000-0000-4000-8000-000000000023")
SYNTHETIC_TASK4_ID = uuid.UUID("00000000-0000-4000-8000-000000000024")


def seed_synthetic_workspace(skip_embeddings: bool = False) -> dict:
    """
    Seed a controlled, deterministic synthetic workspace for research evaluation.
    Only touches records associated with SYNTHETIC_WORKSPACE_ID and synthetic users.
    """
    db = SessionLocal()
    embedding_failures = []
    embeddings_stored_count = 0
    try:
        # 1. Clean existing synthetic tasks, documents, memberships, and workspace
        db.query(Task).filter(Task.workspace_id == SYNTHETIC_WORKSPACE_ID).delete()
        db.query(Document).filter(Document.workspace_id == SYNTHETIC_WORKSPACE_ID).delete()
        db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == SYNTHETIC_WORKSPACE_ID).delete()
        db.query(Workspace).filter(Workspace.id == SYNTHETIC_WORKSPACE_ID).delete()
        db.commit()

        # Clean stale synthetic vector records in Supabase to prevent chunk contamination
        vector_cleanup_error = None
        try:
            supabase.table("embeddings").delete().eq("workspace_id", str(SYNTHETIC_WORKSPACE_ID)).execute()
        except Exception as emb_del_err:
            vector_cleanup_error = f"Supabase vector embeddings purge failed: {emb_del_err}"
            logger.error(vector_cleanup_error)

        # 2. Ensure synthetic users exist
        users_data = [
            (SYNTHETIC_OWNER_ID, "eval-owner@synthetic.orbit.local"),
            (SYNTHETIC_DEV1_ID, "eval-dev1@synthetic.orbit.local"),
            (SYNTHETIC_QA_ID, "eval-qa@synthetic.orbit.local"),
            (SYNTHETIC_DEV2_ID, "eval-dev2@synthetic.orbit.local"),
        ]
        for uid, email in users_data:
            existing = db.query(User).filter(User.id == uid).first()
            if not existing:
                by_email = db.query(User).filter(User.email == email).first()
                if by_email:
                    by_email.id = uid
                else:
                    db.add(User(id=uid, email=email))
        db.commit()

        # 3. Create synthetic workspace
        ws = Workspace(
            id=SYNTHETIC_WORKSPACE_ID,
            name="[SYNTHETIC] Orbit Research Evaluation Workspace",
            description="Controlled deterministic workspace for empirical multi-source evaluation study.",
            invite_code="EVAL-SYNTHETIC-2026",
            owner_id=SYNTHETIC_OWNER_ID,
            ai_provider="gemini",
            ai_model="gemini-3.5-flash-lite"
        )
        db.add(ws)
        db.commit()

        # 4. Add memberships
        memberships = [
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_WORKSPACE_ID, user_id=SYNTHETIC_OWNER_ID, role=RoleEnum.admin),
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_WORKSPACE_ID, user_id=SYNTHETIC_DEV1_ID, role=RoleEnum.member),
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_WORKSPACE_ID, user_id=SYNTHETIC_QA_ID, role=RoleEnum.member),
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_WORKSPACE_ID, user_id=SYNTHETIC_DEV2_ID, role=RoleEnum.member),
        ]
        db.add_all(memberships)
        db.commit()

        # 5. Add synthetic knowledge base documents
        doc1 = Document(
            id=SYNTHETIC_DOC1_ID,
            workspace_id=SYNTHETIC_WORKSPACE_ID,
            title="Architecture and Deployment Specification",
            content=(
                "Orbit Backend Architecture Specification:\n"
                "- The backend API runs on port 8000 using FastAPI.\n"
                "- The frontend web client runs on port 3000 using Next.js.\n"
                "- Redis caching is deployed on port 6379 for real-time pub/sub and distributed rate limiting.\n"
                "- Distributed rate limiting is enforced at 50 requests per minute per IP address.\n"
                "- The database connection pool maintains 30 persistent connections with an overflow limit of 20 connections.\n"
                "- SSL/TLS encryption is strictly enforced for all public HTTP and WebSocket traffic."
            ),
            created_by=SYNTHETIC_OWNER_ID
        )

        doc2 = Document(
            id=SYNTHETIC_DOC2_ID,
            workspace_id=SYNTHETIC_WORKSPACE_ID,
            title="Workspace Security Policy",
            content=(
                "Orbit Workspace Security & Compliance Policy:\n"
                "- Session timeout is enforced at exactly 15 minutes of inactivity.\n"
                "- Two-factor authentication (2FA) is mandatory for all members with administrative roles.\n"
                "- Passwords must contain a minimum of 12 characters including uppercase, lowercase, numbers, and symbols.\n"
                "- Cross-origin resource sharing (CORS) strictly prohibits wildcard origins in production environments."
            ),
            created_by=SYNTHETIC_OWNER_ID
        )

        doc3 = Document(
            id=SYNTHETIC_DOC3_ID,
            workspace_id=SYNTHETIC_WORKSPACE_ID,
            title="Sprint 14 Release Plan",
            content=(
                "Sprint 14 Production Release Schedule:\n"
                "- The final production launch target date is November 15, 2026.\n"
                "- The feature freeze deadline is November 10, 2026 at 23:59 UTC.\n"
                "- All pull requests must pass end-to-end integration testing before merge.\n"
                "- Supported production browser tiers: Chrome 120+, Safari 17+, Firefox 122+, Edge 120+."
            ),
            created_by=SYNTHETIC_OWNER_ID
        )

        db.add_all([doc1, doc2, doc3])
        db.commit()

        # Store vector embeddings for RAG retrieval
        if not skip_embeddings:
            for d in [doc1, doc2, doc3]:
                try:
                    store_embeddings(
                        workspace_id=str(SYNTHETIC_WORKSPACE_ID),
                        source_type="document",
                        source_id=str(d.id),
                        content=d.content
                    )
                    embeddings_stored_count += 1
                except Exception as emb_err:
                    err_msg = f"Embedding generation failed for document {d.id} ({d.title}): {emb_err}"
                    logger.warning(err_msg)
                    embedding_failures.append(err_msg)

        # 6. Add synthetic tasks
        tasks = [
            Task(
                id=SYNTHETIC_TASK1_ID,
                workspace_id=SYNTHETIC_WORKSPACE_ID,
                title="Implement Redis connection pooling",
                description="Increase Redis warm connection pool size to 30 and configure retry handlers.",
                status=TaskStatus.in_progress,
                priority=TaskPriority.high,
                due_date=datetime(2026, 11, 5, 0, 0, 0, tzinfo=UTC),
                created_by=SYNTHETIC_OWNER_ID,
                assigned_to=SYNTHETIC_DEV1_ID
            ),
            Task(
                id=SYNTHETIC_TASK2_ID,
                workspace_id=SYNTHETIC_WORKSPACE_ID,
                title="Update OAuth token refresh logic",
                description="Implement refresh token rotation and handle 401 token expiry seamlessly.",
                status=TaskStatus.todo,
                priority=TaskPriority.medium,
                due_date=datetime(2026, 11, 8, 0, 0, 0, tzinfo=UTC),
                created_by=SYNTHETIC_OWNER_ID,
                assigned_to=SYNTHETIC_DEV1_ID
            ),
            Task(
                id=SYNTHETIC_TASK3_ID,
                workspace_id=SYNTHETIC_WORKSPACE_ID,
                title="Write end-to-end authentication tests",
                description="Automate user registration, session cookies, and 2FA authentication flow tests.",
                status=TaskStatus.done,
                priority=TaskPriority.high,
                due_date=datetime(2026, 10, 30, 0, 0, 0, tzinfo=UTC),
                created_by=SYNTHETIC_OWNER_ID,
                assigned_to=SYNTHETIC_QA_ID
            ),
            Task(
                id=SYNTHETIC_TASK4_ID,
                workspace_id=SYNTHETIC_WORKSPACE_ID,
                title="Audit database indexes for message queries",
                description="Profile slow queries on messages table and add composite index on (workspace_id, created_at).",
                status=TaskStatus.todo,
                priority=TaskPriority.low,
                due_date=datetime(2026, 11, 12, 0, 0, 0, tzinfo=UTC),
                created_by=SYNTHETIC_OWNER_ID,
                assigned_to=SYNTHETIC_DEV2_ID
            ),
        ]
        db.add_all(tasks)
        db.commit()

        # 7. Seed synthetic chat messages in Supabase
        chat_seeded = 0
        try:
            supabase.table("messages").delete().eq("workspace_id", str(SYNTHETIC_WORKSPACE_ID)).execute()
            messages_payload = [
                {
                    "workspace_id": str(SYNTHETIC_WORKSPACE_ID),
                    "sender_id": str(SYNTHETIC_OWNER_ID),
                    "sender_email": "eval-owner@synthetic.orbit.local",
                    "content": "Team, please remember that the Redis pool size was increased to 30 in yesterday's standup."
                },
                {
                    "workspace_id": str(SYNTHETIC_WORKSPACE_ID),
                    "sender_id": str(SYNTHETIC_DEV1_ID),
                    "sender_email": "eval-dev1@synthetic.orbit.local",
                    "content": "Got it. I noticed database query latency during the load test. Who is handling the index audit?"
                },
                {
                    "workspace_id": str(SYNTHETIC_WORKSPACE_ID),
                    "sender_id": str(SYNTHETIC_QA_ID),
                    "sender_email": "eval-qa@synthetic.orbit.local",
                    "content": "I've completed the authentication e2e tests and posted the report. No regressions found on Safari or Chrome."
                },
                {
                    "workspace_id": str(SYNTHETIC_WORKSPACE_ID),
                    "sender_id": str(SYNTHETIC_OWNER_ID),
                    "sender_email": "eval-owner@synthetic.orbit.local",
                    "content": "Awesome. Also note: the Sprint 14 deployment window is moved from 2 PM to 5 PM UTC to avoid customer peak hours."
                }
            ]
            supabase.table("messages").insert(messages_payload).execute()
            chat_seeded = len(messages_payload)
        except Exception as chat_err:
            logger.warning(f"Supabase chat message seeding skipped/failed: {chat_err}")

        failed = bool(vector_cleanup_error) or (not skip_embeddings and bool(embedding_failures))
        status = "failed" if failed else "success"
        all_errors = []
        if vector_cleanup_error:
            all_errors.append(vector_cleanup_error)
        all_errors.extend(embedding_failures)

        return {
            "status": status,
            "workspace_id": str(SYNTHETIC_WORKSPACE_ID),
            "owner_id": str(SYNTHETIC_OWNER_ID),
            "owner_email": "eval-owner@synthetic.orbit.local",
            "dev_user_id": str(SYNTHETIC_DEV1_ID),
            "dev_user_email": "eval-dev1@synthetic.orbit.local",
            "documents_count": 3,
            "tasks_count": 4,
            "chat_messages_count": chat_seeded,
            "embeddings_stored_count": embeddings_stored_count,
            "embedding_failures": embedding_failures,
            "vector_cleanup_error": vector_cleanup_error,
            "errors": all_errors
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def verify_synthetic_workspace_integrity() -> dict:
    """
    Verify the relational and vector integrity of the synthetic evaluation workspace.
    Returns a structured status report with verification checks.
    """
    db = SessionLocal()
    checks = {}
    try:
        # Check workspace
        ws = db.query(Workspace).filter(Workspace.id == SYNTHETIC_WORKSPACE_ID).first()
        checks["workspace_exists"] = ws is not None
        if ws:
            checks["workspace_ai_model"] = ws.ai_model
            checks["workspace_ai_provider"] = ws.ai_provider

        # Check members
        members_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == SYNTHETIC_WORKSPACE_ID).count()
        checks["members_count"] = members_count
        checks["members_valid"] = members_count == 4

        # Check documents
        docs = db.query(Document).filter(Document.workspace_id == SYNTHETIC_WORKSPACE_ID).all()
        checks["documents_count"] = len(docs)
        doc_ids = {d.id for d in docs}
        expected_doc_ids = {SYNTHETIC_DOC1_ID, SYNTHETIC_DOC2_ID, SYNTHETIC_DOC3_ID}
        checks["documents_ids_match"] = (doc_ids == expected_doc_ids)

        # Check tasks
        tasks = db.query(Task).filter(Task.workspace_id == SYNTHETIC_WORKSPACE_ID).all()
        checks["tasks_count"] = len(tasks)
        task_ids = {t.id for t in tasks}
        expected_task_ids = {SYNTHETIC_TASK1_ID, SYNTHETIC_TASK2_ID, SYNTHETIC_TASK3_ID, SYNTHETIC_TASK4_ID}
        checks["tasks_ids_match"] = (task_ids == expected_task_ids)

        # Check Supabase messages
        try:
            msg_res = supabase.table("messages").select("id", count="exact").eq("workspace_id", str(SYNTHETIC_WORKSPACE_ID)).execute()
            checks["chat_messages_count"] = len(msg_res.data) if msg_res.data else 0
            checks["chat_messages_accessible"] = True
        except Exception as e:
            checks["chat_messages_count"] = 0
            checks["chat_messages_accessible"] = False
            checks["chat_error"] = str(e)

        # Check Supabase vector embeddings
        try:
            emb_res = supabase.table("embeddings").select("id", count="exact").eq("workspace_id", str(SYNTHETIC_WORKSPACE_ID)).execute()
            checks["vector_embeddings_count"] = len(emb_res.data) if emb_res.data else 0
            checks["vector_embeddings_accessible"] = True
        except Exception as e:
            checks["vector_embeddings_count"] = 0
            checks["vector_embeddings_accessible"] = False
            checks["vector_error"] = str(e)

        all_ok = (
            checks.get("workspace_exists", False) and
            checks.get("members_valid", False) and
            checks.get("documents_ids_match", False) and
            checks.get("tasks_ids_match", False)
        )
        return {
            "status": "healthy" if all_ok else "unhealthy",
            "checks": checks
        }
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    if "--verify" in sys.argv:
        print("Verifying synthetic workspace integrity...")
        integrity = verify_synthetic_workspace_integrity()
        print(f"Status: {integrity['status']}")
        for k, v in integrity["checks"].items():
            print(f"  {k}: {v}")
    else:
        skip_emb = "--skip-embeddings" in sys.argv
        result = seed_synthetic_workspace(skip_embeddings=skip_emb)
        if result["status"] == "failed":
            print("ERROR: Synthetic workspace seeding encountered failures:")
            for k, v in result.items():
                print(f"  {k}: {v}")
            sys.exit(1)
        else:
            print("Synthetic workspace seeded successfully:")
            for k, v in result.items():
                print(f"  {k}: {v}")

