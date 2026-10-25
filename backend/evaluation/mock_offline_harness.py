"""
Deterministic, fully offline evaluation harness for Orbit AI Phase 3 benchmark smoke testing.

Supplies in-memory synthetic fixture data (documents, tasks, chat messages)
and installs negative guards blocking all network, database, and embedding API calls.
"""

import os
import re
import json
import uuid
import socket
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
from unittest.mock import patch
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

# Deterministic IDs matching Phase 3 synthetic fixture
SYNTHETIC_PHASE3_WORKSPACE_ID = "00000000-0000-4000-8000-000000000003"
SYNTHETIC_PHASE3_OWNER_ID = "00000000-0000-4000-8000-000000000002"

# In-memory document chunks
OFFLINE_DOCUMENTS = [
    {
        "id": "00000000-0000-4000-8000-000000000041",
        "title": "Architecture Specification",
        "workspace_id": SYNTHETIC_PHASE3_WORKSPACE_ID,
        "content": (
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
        )
    },
    {
        "id": "00000000-0000-4000-8000-000000000042",
        "title": "Security Policy",
        "workspace_id": SYNTHETIC_PHASE3_WORKSPACE_ID,
        "content": (
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
        )
    },
    {
        "id": "00000000-0000-4000-8000-000000000043",
        "title": "Release Plan Sprint 15",
        "workspace_id": SYNTHETIC_PHASE3_WORKSPACE_ID,
        "content": (
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
        )
    }
]

# In-memory tasks
OFFLINE_TASKS = [
    {"id": "00000000-0000-4000-8000-000000000051", "title": "Document export", "status": "in_progress", "priority": "medium", "due_date": "2026-11-07T00:00:00Z", "assigned_to": "Priya", "description": "Task T01: Document export. Owner: Priya. Status: in_progress. Due: 7 November 2026. Add CSV and PDF export for saved workspace reports."},
    {"id": "00000000-0000-4000-8000-000000000052", "title": "Search relevance tuning", "status": "todo", "priority": "medium", "due_date": "2026-11-09T00:00:00Z", "assigned_to": "Omar", "description": "Task T02: Search relevance tuning. Owner: Omar. Status: todo. Due: 9 November 2026. Tune ranking for exact title matches."},
    {"id": "00000000-0000-4000-8000-000000000053", "title": "Mobile navigation fixes", "status": "in_progress", "priority": "medium", "due_date": "2026-11-06T00:00:00Z", "assigned_to": "Lin", "description": "Task T03: Mobile navigation fixes. Owner: Lin. Status: in_progress. Due: 6 November 2026. Fix collapsed navigation on small screens."},
    {"id": "00000000-0000-4000-8000-000000000054", "title": "Migration rehearsal", "status": "todo", "priority": "high", "due_date": "2026-11-10T00:00:00Z", "assigned_to": "Mateo", "description": "Task T04: Migration rehearsal. Owner: Mateo. Status: todo. Due: 10 November 2026. Run a staging rehearsal of the production database migration."},
    {"id": "00000000-0000-4000-8000-000000000055", "title": "P0/P1 defect triage", "status": "in_progress", "priority": "high", "due_date": "2026-11-02T00:00:00Z", "assigned_to": "Nina", "description": "Task T05: P0/P1 defect triage. Owner: Nina. Status: in_progress. Due: daily. Review all open P0 and P1 defects before release."},
    {"id": "00000000-0000-4000-8000-000000000056", "title": "Canary rollout checklist", "status": "todo", "priority": "medium", "due_date": "2026-11-12T00:00:00Z", "assigned_to": "Mateo", "description": "Task T06: Canary rollout checklist. Owner: Mateo. Status: todo. Due: 12 November 2026. Prepare the 10 percent canary rollout checklist."},
    {"id": "00000000-0000-4000-8000-000000000057", "title": "Audit log export review", "status": "todo", "priority": "medium", "due_date": "2026-11-11T00:00:00Z", "assigned_to": "Priya", "description": "Task T07: Audit log export review. Owner: Priya. Status: todo. Due: 11 November 2026. Verify encryption requirements for exported audit logs."},
    {"id": "00000000-0000-4000-8000-000000000058", "title": "Service account rotation", "status": "todo", "priority": "medium", "due_date": "2026-11-13T00:00:00Z", "assigned_to": "Omar", "description": "Task T08: Service account rotation. Owner: Omar. Status: todo. Due: 13 November 2026. Rotate the integration service account credentials."},
    {"id": "00000000-0000-4000-8000-000000000059", "title": "Status page separation check", "status": "done", "priority": "medium", "due_date": "2026-11-05T00:00:00Z", "assigned_to": "Lin", "description": "Task T09: Status page separation check. Owner: Lin. Status: done. Due: 5 November 2026. Confirm the status page remains separate from the API."},
    {"id": "00000000-0000-4000-8000-000000000060", "title": "English retrieval test", "status": "done", "priority": "medium", "due_date": "2026-11-05T00:00:00Z", "assigned_to": "Nina", "description": "Task T10: English retrieval test. Owner: Nina. Status: done. Due: 5 November 2026. Verify English-only retrieval behavior."},
    {"id": "00000000-0000-4000-8000-000000000061", "title": "Request ID error test", "status": "in_progress", "priority": "medium", "due_date": "2026-11-08T00:00:00Z", "assigned_to": "Mateo", "description": "Task T11: Request ID error test. Owner: Mateo. Status: in_progress. Due: 8 November 2026. Check request_id in API error responses."},
    {"id": "00000000-0000-4000-8000-000000000062", "title": "Session expiry regression test", "status": "todo", "priority": "medium", "due_date": "2026-11-09T00:00:00Z", "assigned_to": "Nina", "description": "Task T12: Session expiry regression test. Owner: Nina. Status: todo. Due: 9 November 2026. Test session expiration after inactivity."},
    {"id": "00000000-0000-4000-8000-000000000063", "title": "Quarterly access review", "status": "todo", "priority": "medium", "due_date": "2026-11-30T00:00:00Z", "assigned_to": "Omar", "description": "Task T13: Quarterly access review. Owner: Omar. Status: todo. Due: 30 November 2026. Collect workspace administrator access review evidence."},
    {"id": "00000000-0000-4000-8000-000000000064", "title": "Incident reporting drill", "status": "todo", "priority": "medium", "due_date": "2026-11-12T00:00:00Z", "assigned_to": "Priya", "description": "Task T14: Incident reporting drill. Owner: Priya. Status: todo. Due: 12 November 2026. Rehearse the security reporting process."},
    {"id": "00000000-0000-4000-8000-000000000065", "title": "Backup restore check", "status": "in_progress", "priority": "medium", "due_date": "2026-11-11T00:00:00Z", "assigned_to": "Mateo", "description": "Task T15: Backup restore check. Owner: Mateo. Status: in_progress. Due: 11 November 2026. Verify encrypted off-site backup restoration."},
    {"id": "00000000-0000-4000-8000-000000000066", "title": "Embedding pipeline monitor", "status": "done", "priority": "medium", "due_date": "2026-11-04T00:00:00Z", "assigned_to": "Lin", "description": "Task T16: Embedding pipeline monitor. Owner: Lin. Status: done. Due: 4 November 2026. Confirm document indexing completes asynchronously."}
]

# In-memory chat messages
OFFLINE_CHAT_MESSAGES = [
    ("eval-priya@synthetic.orbit.local", "Priya: The export task is in progress; I expect to finish the first pass by 7 November."),
    ("eval-omar@synthetic.orbit.local", "Omar: Search relevance tuning is blocked until the exact-title test cases are merged."),
    ("eval-lin@synthetic.orbit.local", "Lin: The mobile navigation fix passed on a narrow viewport, but tablet verification remains."),
    ("eval-mateo@synthetic.orbit.local", "Mateo: I will run the migration rehearsal on 10 November, provided staging data refresh finishes first."),
    ("eval-nina@synthetic.orbit.local", "Nina: We currently have one P1 defect open, so the release gate is not satisfied yet."),
    ("eval-mateo@synthetic.orbit.local", "Mateo: Keep the canary at 10 percent until the release manager reviews the dashboard."),
    ("eval-priya@synthetic.orbit.local", "Priya: I will check confidential audit exports are encrypted before marking the review complete."),
    ("eval-omar@synthetic.orbit.local", "Omar: The integration service-account rotation is planned for 13 November."),
    ("eval-lin@synthetic.orbit.local", "Lin: I confirmed the public status page is hosted separately from the API."),
    ("eval-nina@synthetic.orbit.local", "Nina: The retrieval test only covers English documents for this release."),
    ("eval-mateo@synthetic.orbit.local", "Mateo: The error response test should verify request_id on failed API requests."),
    ("eval-nina@synthetic.orbit.local", "Nina: I added a regression case for the 15-minute idle session expiry."),
    ("eval-omar@synthetic.orbit.local", "Omar: Administrator access review evidence should be ready by the end of November."),
    ("eval-priya@synthetic.orbit.local", "Priya: The incident drill should use the policy's 30-minute reporting requirement."),
    ("eval-mateo@synthetic.orbit.local", "Mateo: The restore check will verify backups are encrypted before off-site transfer."),
    ("eval-lin@synthetic.orbit.local", "Lin: The embedding monitor confirms indexing is asynchronous; I will watch failed jobs.")
]


def mock_search_similar(workspace_id: str, query: str, limit: int = 5, min_similarity: float = 0.55) -> List[Dict[str, Any]]:
    """Deterministic in-memory vector search simulation based on keyword matching."""
    if not query:
        return []

    q_words = set(query.lower().split())
    scored = []
    for doc in OFFLINE_DOCUMENTS:
        content_lower = doc["content"].lower()
        title_lower = doc["title"].lower()
        matches = sum(1 for w in q_words if len(w) > 3 and (w in content_lower or w in title_lower))
        score = 0.6 + (matches * 0.1)
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc in scored[:limit]:
        results.append({
            "content": doc["content"],
            "title": doc["title"],
            "document_id": doc["id"],
            "workspace_id": doc["workspace_id"],
            "similarity": min(score, 0.99)
        })
    return results


def mock_get_tasks(workspace_id: str, status: Optional[str] = None, db: Any = None) -> str:
    """Deterministic in-memory task retrieval."""
    tasks = OFFLINE_TASKS
    if status:
        clean_status = str(status).strip().lower()
        tasks = [t for t in tasks if t["status"] == clean_status]
    return json.dumps(tasks, indent=2)


def mock_get_recent_chat(workspace_id: str, limit: int = 20) -> str:
    """Deterministic in-memory chat retrieval."""
    lines = [f"{email}: {content}" for email, content in OFFLINE_CHAT_MESSAGES[:limit]]
    return "\n".join(lines)


from langchain_core.runnables import Runnable


class OfflineMockEvaluationLLM(Runnable):
    """
    Mock LLM that generates responses respecting configuration context:
    - plain_llm: has no workspace context; generates generic answers or refusals for unanswerable questions.
    - rag_docs_only: has pre-injected document context; answers document questions.
    - full_agent: has document context and tools; answers multi-source synthesis questions.
    """
    def __init__(self, model_name: str = "mock-offline-llm", temperature: float = 0.0):
        self.model = model_name
        self.model_name = model_name
        self.temperature = temperature

    def _extract_text(self, input_data: Any) -> str:
        if isinstance(input_data, str):
            return input_data
        if isinstance(input_data, dict):
            msgs = input_data.get("messages", [])
            return " ".join(self._extract_text(m) for m in msgs)
        if isinstance(input_data, list):
            return " ".join(self._extract_text(m) for m in input_data)
        if hasattr(input_data, "content"):
            content = input_data.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return " ".join(str(p.get("text", "") if isinstance(p, dict) else str(p)) for p in content)
        return str(input_data)

    def _extract_query(self, input_data: Any) -> str:
        """Extract only the user query/question, ignoring preinjected document context in system prompt."""
        if isinstance(input_data, dict) and "messages" in input_data:
            msgs = input_data["messages"]
            if isinstance(msgs, list) and msgs:
                last_m = msgs[-1]
                content = getattr(last_m, "content", "") if hasattr(last_m, "content") else (last_m.get("content", "") if isinstance(last_m, dict) else str(last_m))
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return " ".join(str(p.get("text", "") if isinstance(p, dict) else str(p)) for p in content)
        if isinstance(input_data, list) and input_data:
            last_m = input_data[-1]
            content = getattr(last_m, "content", "") if hasattr(last_m, "content") else (last_m.get("content", "") if isinstance(last_m, dict) else str(last_m))
            if isinstance(content, str):
                return content
        return self._extract_text(input_data)

    def _generate_response(self, input_data: Any) -> AIMessage:
        prompt_text = self._extract_query(input_data).lower()

        # Check for unanswerable questions (e.g. AWS, Madrid, budget, €45,000, 2028 roadmap, next major, mobile app)
        unanswerable_signals = [
            "aws", "madrid", "budget", "45,000", "roadmap 2028", "tokyo", "salary",
            "not available", "is there a dedicated android", "offline sync protocol",
            "compliance officer", "penetration test", "soc 2", "next major", "mobile app",
            "exact date and time", "android app", "ios app", "offline sync", "unanswerable"
        ]
        if any(sig in prompt_text for sig in unanswerable_signals):
            ans = "This information is not available in the workspace documents, tasks, or chat messages."
        # Q53 multi-source (release candidate date + document export due date)
        elif "release candidate" in prompt_text and "export" in prompt_text:
            ans = "The Sprint 15 release candidate is planned for 11 November 2026, and Priya's document export task is due on 7 November 2026."
        # Q69 multi-source (feature freeze + mobile navigation)
        elif "freeze" in prompt_text and "mobile" in prompt_text:
            ans = "Feature scope freezes at 5 PM UTC on 10 November 2026 according to the release plan, and the mobile navigation task is due on 6 November 2026 in the tracker."
        # Q01 (port)
        elif re.search(r"\bports?\b", prompt_text):
            ans = "The backend API runs on port 8000 using FastAPI and the frontend web client on port 3000 using Next.js."
        # Q02 (timeout)
        elif "timeout" in prompt_text or ("idle" in prompt_text and "session" in prompt_text):
            ans = "The session timeout is enforced at exactly 15 minutes of inactivity."
        # Q21 single-source document (REST endpoint prefix)
        elif "endpoint prefix" in prompt_text or ("api" in prompt_text and "prefix" in prompt_text):
            ans = "The Orbit API uses REST endpoints under the /api/v2 prefix."
        # Q23 single-source document (PostgreSQL)
        elif "primary application database" in prompt_text:
            ans = "The primary application database is PostgreSQL."
        # Q24 single-source document (rate limit)
        elif "rate limit" in prompt_text:
            ans = "The API rate limit is 120 requests per minute per user."
        # Q25 single-source document (session expiry)
        elif "session" in prompt_text and "expire" in prompt_text:
            ans = "Web sessions expire after 15 minutes of inactivity."
        else:
            ans = "Synthetic offline evaluation answer for research verification."

        msg = AIMessage(content=ans)
        msg.usage_metadata = {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}
        msg.response_metadata = {"token_usage": msg.usage_metadata}
        return msg

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        return self._generate_response(input)

    async def ainvoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        return self._generate_response(input)

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self


def blocked_database_access(*args, **kwargs):
    """Guard raising an exception if database access is attempted during offline evaluation."""
    raise RuntimeError("Database access is strictly blocked during offline evaluation smoke test!")


def blocked_network_access(*args, **kwargs):
    """Guard raising an exception if network socket access is attempted during offline evaluation."""
    raise RuntimeError("Network access is strictly blocked during offline evaluation smoke test!")


@contextmanager
def offline_evaluation_harness(strict_negative_guards: bool = True):
    """
    Context manager activating the offline mock retrieval layer and guards:
    - In-memory document vector search
    - In-memory task retrieval
    - In-memory chat retrieval
    - Negative guards blocking database and network connections
    """
    orig_tracing = os.environ.get("LANGCHAIN_TRACING_V2")
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    patches = [
        patch("app.rag.vector_store.search_similar", side_effect=mock_search_similar),
        patch("app.agents.tools.get_tasks", side_effect=mock_get_tasks),
        patch("app.agents.tools.get_recent_chat", side_effect=mock_get_recent_chat),
        patch("app.agents.tools.search_workspace.func", side_effect=lambda query, workspace_id: json.dumps(mock_search_similar(workspace_id, query))),
    ]

    if strict_negative_guards:
        patches.extend([
            patch("app.database.SessionLocal", side_effect=blocked_database_access),
            patch("app.utils.supabase_client.supabase.table", side_effect=blocked_database_access),
            patch("socket.socket.connect", side_effect=blocked_network_access),
        ])

    for p in patches:
        p.start()

    try:
        yield
    finally:
        for p in reversed(patches):
            p.stop()
        if orig_tracing is not None:
            os.environ["LANGCHAIN_TRACING_V2"] = orig_tracing
        else:
            os.environ.pop("LANGCHAIN_TRACING_V2", None)
