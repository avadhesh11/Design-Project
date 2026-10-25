import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import uuid
from datetime import datetime, UTC
import logging
from typing import Dict, Any, Optional

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

# Deterministic IDs for the Phase 3 synthetic evaluation fixture (Workspace 3)
SYNTHETIC_PHASE3_WORKSPACE_ID = uuid.UUID("00000000-0000-4000-8000-000000000003")

# Synthetic Phase 3 Users
SYNTHETIC_PHASE3_OWNER_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")
SYNTHETIC_PHASE3_PRIYA_ID = uuid.UUID("00000000-0000-4000-8000-000000000031")
SYNTHETIC_PHASE3_OMAR_ID  = uuid.UUID("00000000-0000-4000-8000-000000000032")
SYNTHETIC_PHASE3_LIN_ID   = uuid.UUID("00000000-0000-4000-8000-000000000033")
SYNTHETIC_PHASE3_MATEO_ID = uuid.UUID("00000000-0000-4000-8000-000000000034")
SYNTHETIC_PHASE3_NINA_ID  = uuid.UUID("00000000-0000-4000-8000-000000000035")

# Synthetic Document UUIDs
SYNTHETIC_PHASE3_DOC1_ID = uuid.UUID("00000000-0000-4000-8000-000000000041")
SYNTHETIC_PHASE3_DOC2_ID = uuid.UUID("00000000-0000-4000-8000-000000000042")
SYNTHETIC_PHASE3_DOC3_ID = uuid.UUID("00000000-0000-4000-8000-000000000043")


def clean_synthetic_workspace_phase3() -> Dict[str, Any]:
    """
    Safely purge ONLY records belonging to SYNTHETIC_PHASE3_WORKSPACE_ID.
    Guarantees no effect on non-test workspaces or the baseline Q01-Q20 workspace.
    """
    db = SessionLocal()
    purged_counts = {}
    try:
        t_count = db.query(Task).filter(Task.workspace_id == SYNTHETIC_PHASE3_WORKSPACE_ID).delete()
        d_count = db.query(Document).filter(Document.workspace_id == SYNTHETIC_PHASE3_WORKSPACE_ID).delete()
        m_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == SYNTHETIC_PHASE3_WORKSPACE_ID).delete()
        w_count = db.query(Workspace).filter(Workspace.id == SYNTHETIC_PHASE3_WORKSPACE_ID).delete()
        db.commit()

        purged_counts["tasks"] = t_count
        purged_counts["documents"] = d_count
        purged_counts["memberships"] = m_count
        purged_counts["workspace"] = w_count

        try:
            supabase.table("embeddings").delete().eq("workspace_id", str(SYNTHETIC_PHASE3_WORKSPACE_ID)).execute()
            purged_counts["embeddings"] = "purged"
        except Exception as e:
            purged_counts["embeddings_error"] = str(e)

        try:
            supabase.table("messages").delete().eq("workspace_id", str(SYNTHETIC_PHASE3_WORKSPACE_ID)).execute()
            purged_counts["messages"] = "purged"
        except Exception as e:
            purged_counts["messages_error"] = str(e)

        return purged_counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_synthetic_workspace_phase3(skip_embeddings: bool = False) -> Dict[str, Any]:
    """
    Idempotent fixture seeder for Phase 3 (Q21-Q100).
    Populates documents, tasks, and chat messages into SYNTHETIC_PHASE3_WORKSPACE_ID.
    """
    db = SessionLocal()
    embedding_failures = []
    embeddings_stored_count = 0

    try:
        # 1. Clean existing records for this workspace only
        clean_synthetic_workspace_phase3()

        # 2. Ensure Phase 3 synthetic users exist
        users_data = [
            (SYNTHETIC_PHASE3_OWNER_ID, "eval-owner@synthetic.orbit.local"),
            (SYNTHETIC_PHASE3_PRIYA_ID, "eval-priya@synthetic.orbit.local"),
            (SYNTHETIC_PHASE3_OMAR_ID,  "eval-omar@synthetic.orbit.local"),
            (SYNTHETIC_PHASE3_LIN_ID,   "eval-lin@synthetic.orbit.local"),
            (SYNTHETIC_PHASE3_MATEO_ID, "eval-mateo@synthetic.orbit.local"),
            (SYNTHETIC_PHASE3_NINA_ID,  "eval-nina@synthetic.orbit.local"),
        ]
        for uid, email in users_data:
            existing_user = db.query(User).filter(User.id == uid).first()
            if not existing_user:
                by_email = db.query(User).filter(User.email == email).first()
                if not by_email:
                    db.add(User(id=uid, email=email))
        db.commit()

        # 3. Create isolated Phase 3 workspace
        ws = Workspace(
            id=SYNTHETIC_PHASE3_WORKSPACE_ID,
            name="[SYNTHETIC] Orbit Phase 3 Evaluation Workspace",
            description="Isolated workspace for Orbit Phase 3 (Q21-Q100) multi-source benchmark evaluation.",
            invite_code="EVAL-PHASE3-2026",
            owner_id=SYNTHETIC_PHASE3_OWNER_ID,
            ai_provider="gemini",
            ai_model="gemini-3.5-flash-lite"
        )
        db.add(ws)
        db.commit()



        # 4. Add memberships
        memberships = [
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID, user_id=SYNTHETIC_PHASE3_OWNER_ID, role=RoleEnum.admin),
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID, user_id=SYNTHETIC_PHASE3_PRIYA_ID, role=RoleEnum.member),
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID, user_id=SYNTHETIC_PHASE3_OMAR_ID, role=RoleEnum.member),
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID, user_id=SYNTHETIC_PHASE3_LIN_ID, role=RoleEnum.member),
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID, user_id=SYNTHETIC_PHASE3_MATEO_ID, role=RoleEnum.member),
            WorkspaceMember(id=uuid.uuid4(), workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID, user_id=SYNTHETIC_PHASE3_NINA_ID, role=RoleEnum.member),
        ]
        db.add_all(memberships)
        db.commit()

        # 5. Add synthetic documents (Architecture Specification, Security Policy, Sprint 15 Release Plan)
        doc1 = Document(
            id=SYNTHETIC_PHASE3_DOC1_ID,
            workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID,
            title="Architecture Specification",
            content=(
                "Orbit Architecture Specification:\n"
                "- The Orbit API uses REST endpoints under the /api/v2 prefix.\n"
                "- The production web frontend is deployed to Vercel.\n"
                "- The primary application database is PostgreSQL.\n"
                "- Background jobs use a Redis-backed worker queue.\n"
                "- The API rate limit is 120 requests per minute per user.\n"
                "- The maximum supported upload size is 25 MB per file.\n"
                "- Uploaded documents are indexed asynchronously after upload.\n"
                "- Document embeddings are stored in pgvector.\n"
                "- API timestamps are normalized to UTC.\n"
                "- This release supports English-language document retrieval only.\n"
                "- The public status page is hosted separately from the application API.\n"
                "- API error responses include a request_id field."
            ),
            created_by=SYNTHETIC_PHASE3_OWNER_ID
        )

        doc2 = Document(
            id=SYNTHETIC_PHASE3_DOC2_ID,
            workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID,
            title="Security Policy",
            content=(
                "Orbit Security Policy:\n"
                "- Web sessions expire after 15 minutes of inactivity.\n"
                "- Workspace owners must use multi-factor authentication.\n"
                "- Service-account credentials must be rotated every 90 days.\n"
                "- Production customer data must not be copied into development workspaces.\n"
                "- Audit logs are retained for 180 days.\n"
                "- Private team chat requires workspace membership.\n"
                "- Confidential exported reports must be encrypted at rest.\n"
                "- API keys must never be committed to source control.\n"
                "- Workspace administrator access reviews occur quarterly.\n"
                "- Confirmed security incidents must be reported within 30 minutes.\n"
                "- Backups are encrypted before transfer to off-site storage.\n"
                "- New service accounts use least-privilege access by default."
            ),
            created_by=SYNTHETIC_PHASE3_OWNER_ID
        )

        doc3 = Document(
            id=SYNTHETIC_PHASE3_DOC3_ID,
            workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID,
            title="Release Plan Sprint 15",
            content=(
                "Orbit Release Plan Sprint 15:\n"
                "- Sprint 15 runs from 2 November through 13 November 2026.\n"
                "- The release candidate is planned for 11 November 2026.\n"
                "- The target production launch date is 16 November 2026.\n"
                "- The release requires zero open P0 or P1 defects.\n"
                "- Priya owns the document export feature.\n"
                "- Omar owns the workspace search improvement.\n"
                "- Lin owns the mobile layout fixes.\n"
                "- Feature scope freezes at 5 PM UTC on 10 November 2026.\n"
                "- The release retrospective is scheduled for 18 November 2026.\n"
                "- A successful database migration rehearsal is required before release.\n"
                "- The rollout plan uses a 10 percent canary before full production rollout.\n"
                "- The release manager owns the rollback decision."
            ),
            created_by=SYNTHETIC_PHASE3_OWNER_ID
        )

        db.add_all([doc1, doc2, doc3])
        db.commit()

        # Vector embeddings storage
        if not skip_embeddings:
            for d in [doc1, doc2, doc3]:
                try:
                    store_embeddings(
                        workspace_id=str(SYNTHETIC_PHASE3_WORKSPACE_ID),
                        source_type="document",
                        source_id=str(d.id),
                        content=d.content
                    )
                    embeddings_stored_count += 1
                except Exception as emb_err:
                    err_msg = f"Embedding generation failed for document {d.id} ({d.title}): {emb_err}"
                    logger.warning(err_msg)
                    embedding_failures.append(err_msg)

        # 6. Add synthetic tasks (T01 through T16)
        tasks_data = [
            (
                "T01", "Document export", "in_progress", TaskPriority.medium,
                datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_PRIYA_ID,
                "Task T01: Document export. Owner: Priya. Status: in_progress. Due: 7 November 2026. Add CSV and PDF export for saved workspace reports."
            ),
            (
                "T02", "Search relevance tuning", "todo", TaskPriority.medium,
                datetime(2026, 11, 9, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_OMAR_ID,
                "Task T02: Search relevance tuning. Owner: Omar. Status: todo. Due: 9 November 2026. Tune ranking for exact title matches."
            ),
            (
                "T03", "Mobile navigation fixes", "in_progress", TaskPriority.medium,
                datetime(2026, 11, 6, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_LIN_ID,
                "Task T03: Mobile navigation fixes. Owner: Lin. Status: in_progress. Due: 6 November 2026. Fix collapsed navigation on small screens."
            ),
            (
                "T04", "Migration rehearsal", "todo", TaskPriority.high,
                datetime(2026, 11, 10, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_MATEO_ID,
                "Task T04: Migration rehearsal. Owner: Mateo. Status: todo. Due: 10 November 2026. Run a staging rehearsal of the production database migration."
            ),
            (
                "T05", "P0/P1 defect triage", "in_progress", TaskPriority.high,
                datetime(2026, 11, 2, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_NINA_ID,
                "Task T05: P0/P1 defect triage. Owner: Nina. Status: in_progress. Due: daily. Review all open P0 and P1 defects before release."
            ),
            (
                "T06", "Canary rollout checklist", "todo", TaskPriority.medium,
                datetime(2026, 11, 12, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_MATEO_ID,
                "Task T06: Canary rollout checklist. Owner: Mateo. Status: todo. Due: 12 November 2026. Prepare the 10 percent canary rollout checklist."
            ),
            (
                "T07", "Audit log export review", "todo", TaskPriority.medium,
                datetime(2026, 11, 11, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_PRIYA_ID,
                "Task T07: Audit log export review. Owner: Priya. Status: todo. Due: 11 November 2026. Verify encryption requirements for exported audit logs."
            ),
            (
                "T08", "Service account rotation", "todo", TaskPriority.medium,
                datetime(2026, 11, 13, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_OMAR_ID,
                "Task T08: Service account rotation. Owner: Omar. Status: todo. Due: 13 November 2026. Rotate the integration service account credentials."
            ),
            (
                "T09", "Status page separation check", "done", TaskPriority.medium,
                datetime(2026, 11, 5, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_LIN_ID,
                "Task T09: Status page separation check. Owner: Lin. Status: done. Due: 5 November 2026. Confirm the status page remains separate from the API."
            ),
            (
                "T10", "English retrieval test", "done", TaskPriority.medium,
                datetime(2026, 11, 5, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_NINA_ID,
                "Task T10: English retrieval test. Owner: Nina. Status: done. Due: 5 November 2026. Verify English-only retrieval behavior."
            ),
            (
                "T11", "Request ID error test", "in_progress", TaskPriority.medium,
                datetime(2026, 11, 8, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_MATEO_ID,
                "Task T11: Request ID error test. Owner: Mateo. Status: in_progress. Due: 8 November 2026. Check request_id in API error responses."
            ),
            (
                "T12", "Session expiry regression test", "todo", TaskPriority.medium,
                datetime(2026, 11, 9, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_NINA_ID,
                "Task T12: Session expiry regression test. Owner: Nina. Status: todo. Due: 9 November 2026. Test session expiration after inactivity."
            ),
            (
                "T13", "Quarterly access review", "todo", TaskPriority.medium,
                datetime(2026, 11, 30, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_OMAR_ID,
                "Task T13: Quarterly access review. Owner: Omar. Status: todo. Due: 30 November 2026. Collect workspace administrator access review evidence."
            ),
            (
                "T14", "Incident reporting drill", "todo", TaskPriority.medium,
                datetime(2026, 11, 12, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_PRIYA_ID,
                "Task T14: Incident reporting drill. Owner: Priya. Status: todo. Due: 12 November 2026. Rehearse the security reporting process."
            ),
            (
                "T15", "Backup restore check", "in_progress", TaskPriority.medium,
                datetime(2026, 11, 11, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_MATEO_ID,
                "Task T15: Backup restore check. Owner: Mateo. Status: in_progress. Due: 11 November 2026. Verify encrypted off-site backup restoration."
            ),
            (
                "T16", "Embedding pipeline monitor", "done", TaskPriority.medium,
                datetime(2026, 11, 4, 0, 0, 0, tzinfo=UTC), SYNTHETIC_PHASE3_LIN_ID,
                "Task T16: Embedding pipeline monitor. Owner: Lin. Status: done. Due: 4 November 2026. Confirm document indexing completes asynchronously."
            ),
        ]

        task_models = []
        for code, title, status_str, priority, due, assignee, desc in tasks_data:
            idx = int(code[1:])
            tid = uuid.UUID(f"00000000-0000-4000-8000-{50 + idx:012d}")
            task_models.append(
                Task(
                    id=tid,
                    workspace_id=SYNTHETIC_PHASE3_WORKSPACE_ID,
                    title=title,
                    description=desc,
                    status=TaskStatus[status_str],
                    priority=priority,
                    due_date=due,
                    created_by=SYNTHETIC_PHASE3_OWNER_ID,
                    assigned_to=assignee
                )
            )
        db.add_all(task_models)
        db.commit()

        # 7. Add synthetic team chat messages (C01 through C16)
        chat_data = [
            ("C01", SYNTHETIC_PHASE3_PRIYA_ID, "eval-priya@synthetic.orbit.local", "Priya: The export task is in progress; I expect to finish the first pass by 7 November."),
            ("C02", SYNTHETIC_PHASE3_OMAR_ID,  "eval-omar@synthetic.orbit.local",  "Omar: Search relevance tuning is blocked until the exact-title test cases are merged."),
            ("C03", SYNTHETIC_PHASE3_LIN_ID,   "eval-lin@synthetic.orbit.local",   "Lin: The mobile navigation fix passed on a narrow viewport, but tablet verification remains."),
            ("C04", SYNTHETIC_PHASE3_MATEO_ID, "eval-mateo@synthetic.orbit.local", "Mateo: I will run the migration rehearsal on 10 November, provided staging data refresh finishes first."),
            ("C05", SYNTHETIC_PHASE3_NINA_ID,  "eval-nina@synthetic.orbit.local",  "Nina: We currently have one P1 defect open, so the release gate is not satisfied yet."),
            ("C06", SYNTHETIC_PHASE3_MATEO_ID, "eval-mateo@synthetic.orbit.local", "Mateo: Keep the canary at 10 percent until the release manager reviews the dashboard."),
            ("C07", SYNTHETIC_PHASE3_PRIYA_ID, "eval-priya@synthetic.orbit.local", "Priya: I will check confidential audit exports are encrypted before marking the review complete."),
            ("C08", SYNTHETIC_PHASE3_OMAR_ID,  "eval-omar@synthetic.orbit.local",  "Omar: The integration service-account rotation is planned for 13 November."),
            ("C09", SYNTHETIC_PHASE3_LIN_ID,   "eval-lin@synthetic.orbit.local",   "Lin: I confirmed the public status page is hosted separately from the API."),
            ("C10", SYNTHETIC_PHASE3_NINA_ID,  "eval-nina@synthetic.orbit.local",  "Nina: The retrieval test only covers English documents for this release."),
            ("C11", SYNTHETIC_PHASE3_MATEO_ID, "eval-mateo@synthetic.orbit.local", "Mateo: The error response test should verify request_id on failed API requests."),
            ("C12", SYNTHETIC_PHASE3_NINA_ID,  "eval-nina@synthetic.orbit.local",  "Nina: I added a regression case for the 15-minute idle session expiry."),
            ("C13", SYNTHETIC_PHASE3_OMAR_ID,  "eval-omar@synthetic.orbit.local",  "Omar: Administrator access review evidence should be ready by the end of November."),
            ("C14", SYNTHETIC_PHASE3_PRIYA_ID, "eval-priya@synthetic.orbit.local", "Priya: The incident drill should use the policy's 30-minute reporting requirement."),
            ("C15", SYNTHETIC_PHASE3_MATEO_ID, "eval-mateo@synthetic.orbit.local", "Mateo: The restore check will verify backups are encrypted before off-site transfer."),
            ("C16", SYNTHETIC_PHASE3_LIN_ID,   "eval-lin@synthetic.orbit.local",   "Lin: The embedding monitor confirms indexing is asynchronous; I will watch failed jobs."),
        ]

        messages_payload = [
            {
                "workspace_id": str(SYNTHETIC_PHASE3_WORKSPACE_ID),
                "sender_id": str(uid),
                "sender_email": email,
                "content": content
            }
            for code, uid, email, content in chat_data
        ]
        chat_seeded = 0
        try:
            supabase.table("messages").delete().eq("workspace_id", str(SYNTHETIC_PHASE3_WORKSPACE_ID)).execute()
            supabase.table("messages").insert(messages_payload).execute()
            chat_seeded = len(messages_payload)
        except Exception as chat_err:
            logger.warning(f"Chat message seeding failed in Supabase: {chat_err}")

        return {
            "status": "success",
            "workspace_id": str(SYNTHETIC_PHASE3_WORKSPACE_ID),
            "users_count": len(users_data),
            "documents_count": 3,
            "tasks_count": len(tasks_data),
            "chat_messages_count": chat_seeded,
            "embeddings_stored": embeddings_stored_count,
            "embedding_failures": embedding_failures
        }

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed Synthetic Phase 3 Evaluation Workspace (Isolated)")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip Supabase pgvector embedding generation")
    args = parser.parse_args()

    print("Seeding Phase 3 isolated synthetic workspace...")
    summary = seed_synthetic_workspace_phase3(skip_embeddings=args.skip_embeddings)
    print("Seed Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
