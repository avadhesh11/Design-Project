"""
Load test for the Orbit AI backend (avadhesh11/Orbit).

Install:
    pip install locust

Run (headless, no browser UI):
    locust -f app/locustfile.py --host=http://localhost:8000 \
           --headless -u 50 -r 5 --run-time 60s --csv=results

Run (with browser UI):
    locust -f app/locustfile.py --host=http://localhost:8000
    # Open http://localhost:8089, set users & spawn rate, click Start.

Resume metrics to extract after the run:
  - p50 / p95 / p99 latency per endpoint
  - RPS (requests / second)
  - Failure % (should be ~0% for authenticated endpoints)

HOW THE BUGS WERE FIXED vs the original version
-------------------------------------------------
1. on_start() register/login used self.client → counted in failure stats.
   FIX: wrap with catch_response() and manually call .success() / .failure()
   so only genuine server errors count.

2. self.headers = {} when token is None → all workspace tasks fired WITHOUT
   Authorization → 403/401 → 880/900 failures on list_workspaces.
   FIX: store self._authenticated = False and guard every @task.

3. Argon2 hashing on register takes 200-500ms per user; at 100 concurrent
   users this caused cascading timeouts.
   FIX: bump client timeout to 30s for on_start operations only.
"""

import random
import string
import logging

from locust import HttpUser, task, between, events

logger = logging.getLogger("orbit_load_test")


def random_string(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


class OrbitUser(HttpUser):
    """
    Simulates a real Orbit user:
      • Registers a unique account
      • Logs in and stores the JWT
      • Creates a workspace
      • Exercises CRUD endpoints in a weighted loop
    """

    wait_time = between(1, 3)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_start(self) -> None:
        """
        Runs once per virtual user at spawn time.
        Uses catch_response so setup responses can be explicitly classified
        and clearly separated from the measured workload in the Locust report.

        NOTE: The Orbit login endpoint sets tokens as httponly cookies
        (not in the JSON body). Locust's httpx client persists cookies
        automatically in self.client.cookies, so authenticated requests
        work with cookies alone — no Authorization header needed.
        """
        self.headers: dict = {}   # kept for any future header-auth calls
        self.workspace_id: str | None = None
        self._authenticated: bool = False

        email = f"lt_{random_string(10)}@orbittest.dev"
        password = "LoadTest_123!"

        # ── 1. Register ────────────────────────────────────────────────
        # Argon2 hashing is intentionally slow (~200-500 ms per hash).
        # Allow 15 s so this never times out under concurrent load.
        with self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
            name="[setup] /api/auth/register",
            catch_response=True,
            timeout=15,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            elif resp.status_code == 409:
                resp.success()  # already exists — fine
            else:
                resp.failure(f"Register failed: {resp.status_code} {resp.text[:120]}")
                return

        # ── 2. Login ───────────────────────────────────────────────────
        # The server responds with {"message": "Login successful"} and
        # sets `access_token` + `refresh_token` as httponly cookies.
        # Locust stores these cookies in self.client.cookies automatically.
        with self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            name="[setup] /api/auth/login",
            catch_response=True,
            timeout=15,
        ) as resp:
            if resp.status_code == 200:
                cookie_token = resp.cookies.get("access_token")
                if not cookie_token:
                    resp.failure("Login succeeded but access_token cookie missing")
                    return
                # Also set as Bearer header so workspace/task endpoints
                # work regardless of how get_current_user reads the token
                self.headers = {"Authorization": f"Bearer {cookie_token}"}
                self._authenticated = True
                resp.success()
            else:
                resp.failure(f"Login failed: {resp.status_code} {resp.text[:120]}")
                return

        # ── 3. Create workspace ────────────────────────────────────────
        with self.client.post(
            "/api/workspaces/",
            json={"name": f"LT-{random_string(6)}"},
            headers=self.headers,
            name="[setup] /api/workspaces/ [create]",
            catch_response=True,
            timeout=10,
        ) as resp:
            if resp.status_code in (200, 201):
                self.workspace_id = resp.json().get("id")
                resp.success()
            else:
                resp.failure(f"Workspace create failed: {resp.status_code} {resp.text[:80]}")

    # ── Measured tasks (these go into the stats table) ────────────────────────

    @task(3)
    def list_workspaces(self) -> None:
        """High-frequency read — tests DB query latency under load."""
        if not self._authenticated:
            return
        self.client.get(
            "/api/workspaces/",
            headers=self.headers,
            name="GET /api/workspaces/ [list]",
        )

    @task(2)
    def list_documents(self) -> None:
        if not self._authenticated or not self.workspace_id:
            return
        self.client.get(
            f"/api/documents/?workspace_id={self.workspace_id}",
            headers=self.headers,
            name="GET /api/documents/ [list]",
        )

    @task(2)
    def list_tasks(self) -> None:
        if not self._authenticated or not self.workspace_id:
            return
        self.client.get(
            f"/api/tasks/?workspace_id={self.workspace_id}",
            headers=self.headers,
            name="GET /api/tasks/ [list]",
        )

    @task(2)
    def get_workspace_activity(self) -> None:
        """
        Hits the WorkspaceDevelopmentCache endpoint.
        First call is cold (LLM or DB), subsequent calls should be cache HIT.
        Compare p95 of first vs later runs → quantifies cache latency savings.
        """
        if not self._authenticated or not self.workspace_id:
            return
        self.client.get(
            f"/api/workspaces/{self.workspace_id}/activity",
            headers=self.headers,
            name="GET /api/workspaces/{id}/activity [cache benchmark]",
        )

    @task(0)  # DISABLED: chat messages route calls Supabase client, not local Postgres
    def list_chat_messages(self) -> None:
        if not self._authenticated or not self.workspace_id:
            return
        self.client.get(
            f"/api/chat/{self.workspace_id}/messages",
            headers=self.headers,
            name="GET /api/chat/{id}/messages",
        )

    @task(0)  # DISABLED: create calls store_embeddings() → Gemini Embedding API → rate-limited at load
    def create_document(self) -> None:
        if not self._authenticated or not self.workspace_id:
            return
        with self.client.post(
            "/api/documents/",
            json={
                "workspace_id": self.workspace_id,
                "title": f"LT-doc-{random_string(4)}",
                "content": (
                    "Load-test generated document for RAG ingestion pipeline benchmarking. " * 10
                ),
            },
            headers=self.headers,
            name="POST /api/documents/ [create]",
            catch_response=True,
        ) as resp:
            # 201 = created, 422 = validation err (count as failure), anything else too
            if resp.status_code in (200, 201):
                resp.success()
            else:
                resp.failure(f"{resp.status_code}: {resp.text[:80]}")

    # @task(1)
    # def ai_chat(self) -> None:
    #     """
    #     Heaviest endpoint: RAG vector retrieval + Gemini LLM call.
    #     Timeout is generous (60 s) — we want to measure real latency, not timeouts.
    #     Resume bullet: 'Served AI chat responses at p95 < X s under N concurrent users.'
    #     """
    #     if not self._authenticated or not self.workspace_id:
    #         return
    #     self.client.post(
    #         "/api/ai/chat",
    #         json={
    #             "workspace_id": self.workspace_id,
    #             "message": "Give me a brief summary of the work in this workspace.",
    #         },
    #         headers=self.headers,
    #         name="POST /api/ai/chat [RAG + LLM]",
    #         timeout=60,
    #     )
