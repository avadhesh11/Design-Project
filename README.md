# Orbit — Unified Agentic Workspace

[![Next.js](https://img.shields.io/badge/Next.js-14.2.35-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.137.1-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.49-D71F00?style=flat-square)](https://www.sqlalchemy.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2.5-1C3C3C?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash%202.5%20%7C%203.5-4285F4?style=flat-square&logo=google)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

Orbit is an open-source collaborative engineering workspace and autonomous agent platform. It unifies project management, rich technical documentation, real-time team messaging, interactive visual workflow diagrams, and action-oriented AI agents powered by LangGraph, Google Gemini, local Ollama models, and pgvector-backed Retrieval-Augmented Generation (RAG).

---

## Overview

Modern product engineering teams face acute context fragmentation across disconnected tools: issue trackers (Linear/Jira), wikis (Notion), team chat (Slack), architecture canvases (Miro), and external LLM web chats. General-purpose chat interfaces lack access to internal project tickets, sprint discussions, and architectural diagrams, and cannot take actions on behalf of engineers.

**Orbit** solves this challenge by unifying workspace collaboration into a single, cohesive platform backed by an **action-capable, context-aware autonomous agent**. Rather than serving as a passive question-answering tool, the agent actively inspects tasks, queries domain documents using vector similarity search, traverses team chat history, creates or updates task tickets, and sends automated email notifications through an authenticated LangGraph ReAct execution loop.

### Key Differentiators

- **Action-Oriented ReAct Architecture:** The AI agent does not just summarize text; it uses function calling to query databases, modify task trackers, and dispatch operational notifications within strict role-based permission boundaries.
- **Fail-Closed Retrieval Security:** Document chunks are verified against workspace membership and active database records at query time, preventing cross-tenant data leakage or orphaned chunk hallucinations.
- **Hybrid Provider Support:** Supports cloud inference via Google Gemini alongside local, private execution via Ollama (e.g., Llama 3.2) with automatic model verification and resilient fallbacks.
- **Visual Architecture & Workflow Canvas:** Features an interactive node-and-edge workflow builder powered by `@xyflow/react` with version snapshotting, state restoration, and automated AI architectural explanation.
- **Bi-Directional Developer Integrations:** Integrates with GitHub via GitHub App webhooks to synchronize issues, pull requests, and commit pushes, automatically surfacing "When You Were Away" catch-up digests.

---

## Key Features

### 1. Multi-Tenant Workspaces & Role-Based Access Control
- Isolated workspace scoping for all data entities (tasks, documents, chat messages, flow diagrams, and embeddings).
- Role-based permissions (`owner`, `admin`, `member`) enforced across both REST API endpoints and autonomous agent tool invocations.
- Secure invite codes with one-click regeneration and validation.

### 2. Dual-Token Authentication & Identity
- Secure credential management using Argon2 password hashing via `passlib`.
- Dual-token session model: short-lived access tokens (JWT) paired with long-lived, HTTP-only refresh cookies.
- Native GitHub OAuth integration for single-click developer onboarding.
- Rate-limiting protection on authentication routes powered by SlowAPI.

### 3. Deep Knowledge Base & Multi-Format RAG Pipeline
- Ingestion support for `.pdf`, `.docx`, `.txt`, `.md`, `.csv`, `.xlsx`, and `.xls` files (up to 10 MB).
- Multi-format extraction with structural preservation: extracts markdown-formatted tables from PDF and Word documents via `pdfplumber` and `python-docx`, alongside structured CSV/Excel parsing via `pandas`.
- Chunking engine splitting text into 1,000-word segments with 50-word overlaps.
- High-dimensional vector embeddings generated via `gemini-embedding-2-preview` (768 dimensions).
- Cosine similarity vector search executed via PostgreSQL pgvector RPC function (`match_embeddings`) with strict fail-closed workspace isolation.

### 4. Autonomous Agent Engine (LangGraph + Gemini / Ollama)
- Built on LangGraph's prebuilt ReAct agent pattern with conversational memory.
- Dynamic tool discovery scoped to user authorization:
  - `search_workspace_tool`: Performs semantic similarity search across workspace knowledge bases.
  - `get_tasks_tool`: Retrieves real-time tasks filtered by workflow status and assignees.
  - `get_recent_chat_tool`: Inspects recent team channel discussions to capture immediate context.
  - `create_task_tool`: Directly provisions tasks with title, description, priority, and assignees (admin only).
  - `update_task_tool`: Executes task state transitions and metadata updates (admin only).
  - `send_task_reminder_email_tool`: Dispatches task assignment reminders via SMTP (admin only).
  - `send_deadline_alert_email_tool`: Scans for tasks due within 48 hours and alerts assignees (admin only).
  - `send_important_info_email_tool`: Broadcasts critical operational announcements to workspace members (admin only).

### 5. Interactive Kanban Task Tracker
- Multi-column workflow boards (`todo`, `in_progress`, `review`, `done`).
- Granular task metadata: priority levels (`low`, `medium`, `high`, `urgent`), due dates, assignees, and audit timestamps.
- Direct commit and pull request association: links Git commit hashes (7–40 hex characters) to tasks, automatically transitioning ticket statuses.

### 6. Interactive Visual Workflow Builder (Orbit Flow)
- Node-and-edge visual canvas built with `@xyflow/react`.
- Supports custom system component nodes, directional connection handles, and canvas annotations.
- Full state synchronization, version checkpoint snapshots, and rollback restoration.
- **AI Graph Explanation:** Ingests the canvas graph topology and generates structured architectural explanations using Gemini.

### 7. Real-Time Team Messaging & Collaboration
- Team workspace channels and direct messaging.
- Real-time message broadcasting powered by Supabase Realtime WebSocket subscriptions with persistent PostgreSQL storage.
- Document editor powered by TipTap with word counting and live content autosave.

### 8. GitHub Integration & Catch-Up Digest
- Webhook processor for GitHub App events (`issues`, `pull_request`, `push`, `installation`).
- Automated "When You Were Away" digest calculating recent commits, opened pull requests, task changes, and missed conversations since the user's last heartbeat.

---

## Tech Stack

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Library:** React 18, TypeScript 5
- **Styling:** Tailwind CSS, PostCSS, Lucide React
- **UI Components:** Radix UI Primitives, Class Variance Authority (CVA)
- **State Management:** Zustand, TanStack Query v5
- **Canvas / Diagramming:** `@xyflow/react` (React Flow v12)
- **Rich Text Editing:** TipTap (`@tiptap/react`, `@tiptap/starter-kit`)
- **HTTP Client:** Axios

### Backend
- **Framework:** FastAPI 0.137.1 (Python 3.11+)
- **Server:** Uvicorn (ASGI)
- **Agent Orchestration:** LangGraph 1.2.5, LangChain Core
- **LLM Integrations:** `langchain-google-genai` (Gemini 2.5/3.5), `langchain-ollama` (Local Llama/Ollama)
- **ORM & Data Layer:** SQLAlchemy 2.0, Alembic
- **Validation & Settings:** Pydantic v2, Pydantic Settings
- **Security & Cryptography:** Passlib (Argon2), PyJWT, Cryptography
- **Rate Limiting:** SlowAPI (Limits)
- **Document Processing:** PyPDF, `pdfplumber`, `python-docx`, `pandas`, `openpyxl`

### Storage & Infrastructure
- **Primary Relational Database:** PostgreSQL 16
- **Vector Search Engine:** PostgreSQL `pgvector` extension (768-dimensional embeddings via Supabase RPC)
- **Caching & Broker:** Redis 7 Alpine
- **Realtime Layer:** Supabase Realtime (WebSockets)
- **Containerization:** Docker, Docker Compose (multi-stage builds)

---

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph ClientTier["Client Tier (Browser)"]
        NextJS["Next.js 14 App Router"]
        Zustand["Zustand Client Stores"]
        ReactQuery["TanStack Query v5"]
        FlowCanvas["@xyflow/react Canvas"]
        TipTapEditor["TipTap Rich Editor"]
    end

    subgraph GatewayTier["Gateway & Middleware"]
        FastAPIApp["FastAPI Application Gateway"]
        SlowAPILimiter["SlowAPI Rate Limiter"]
        AuthMiddleware["JWT & Cookie Auth Validator"]
    end

    subgraph ServiceTier["Core Application Services"]
        AuthService["Authentication & GitHub OAuth"]
        WorkspaceService["Workspace & Member Service"]
        TaskService["Kanban & GitHub Link Service"]
        DocService["Document Ingestion & Parser"]
        FlowService["Workflow Canvas & Versioning Engine"]
        AgentService["LangGraph ReAct Autonomous Agent"]
    end

    subgraph DataTier["Data & Inference Tier"]
        PostgreSQL[("PostgreSQL 16 (Primary DB)")]
        PGVector[("Supabase / pgvector (Embeddings)")]
        RedisCache[("Redis 7 (Session & Cache)")]
        GeminiAPI["Google Gemini LLM & Embeddings"]
        OllamaLocal["Local Ollama Server (Optional)"]
        SMTPServer["SMTP Email Gateway"]
    end

    ClientTier -->|REST API / JSON| FastAPIApp
    ClientTier -->|WebSocket Subscriptions| PGVector

    FastAPIApp --> SlowAPILimiter --> AuthMiddleware
    AuthMiddleware --> ServiceTier

    DocService -->|Extract Text| DocService
    DocService -->|Generate 768d Vectors| GeminiAPI
    DocService -->|Store Vectors| PGVector
    DocService -->|Store Metadata| PostgreSQL

    AgentService -->|Semantic Search| PGVector
    AgentService -->|Read / Write Tasks| TaskService
    AgentService -->|Dispatch Notifications| SMTPServer
    AgentService -->|ReAct Reasoning Loop| GeminiAPI
    AgentService -.->|Local Inference| OllamaLocal

    ServiceTier --> PostgreSQL
    ServiceTier --> RedisCache
```

### End-to-End Request & Agent ReAct Execution Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant API as FastAPI Router
    participant Auth as Auth & Permission Gate
    participant Agent as LangGraph ReAct Engine
    participant LLM as Google Gemini / Ollama
    participant Tools as Tool Execution Layer
    participant DB as PostgreSQL & pgvector

    User->>API: POST /api/ai/chat { message, workspace_id }
    API->>Auth: Validate JWT / Session & Check Membership
    Auth-->>API: User Context (role, user_id, is_admin)
    
    API->>Agent: Initialize ReAct Loop with Contextual Tools
    Agent->>DB: Pre-inject Relevant Document Chunks (Vector Search)
    DB-->>Agent: Top matching document chunks
    
    loop Dynamic Reasoning & Tool Calling
        Agent->>LLM: Prompt + Conversation History + Available Tools
        LLM-->>Agent: Action Decision (e.g. call `get_tasks_tool` or `search_workspace_tool`)
        alt Tool Invocation Required
            Agent->>Tools: Execute Scoped Tool (with workspace_id closure)
            Tools->>DB: Query / Mutate Records
            DB-->>Tools: Structured Result
            Tools-->>Agent: Observation Data
        else Final Answer Ready
            LLM-->>Agent: Synthesized Markdown Response
        end
    end

    Agent->>DB: Save Message History in `ai_chats`
    Agent-->>API: Final Answer + Source Attribution
    API-->>User: 200 OK Response
```

### RAG Ingestion and Fail-Closed Vector Search

```mermaid
flowchart TD
    subgraph Ingestion["Document Ingestion Pipeline"]
        Upload["File Upload: .pdf, .docx, .txt, .csv, .xlsx"] --> Parse{"Document Parser"}
        Parse -->|PDF| P1["pdfplumber (Text & Markdown Tables)"]
        Parse -->|DOCX| P2["python-docx (Text & Structural Tables)"]
        Parse -->|CSV / Excel| P3["pandas (Dataframe to Structured Text)"]
        Parse -->|Plain Text| P4["UTF-8 Raw Extractor"]
        
        P1 & P2 & P3 & P4 --> Chunk["Word Chunker (1,000 words, 50-word overlap)"]
        Chunk --> Embed["Gemini Embedding 2 Preview (768-dim)"]
        Embed --> Upsert["Insert into Supabase 'embeddings' table"]
        Upload --> Meta["Record Document in PostgreSQL 'documents' table"]
    end

    subgraph Retrieval["Fail-Closed Vector Retrieval Pipeline"]
        Query["User Query / Agent Search"] --> QEmbed["Query Vector Embedding (768-dim)"]
        QEmbed --> RPC["Call PostgreSQL RPC: match_embeddings"]
        RPC --> Cosine["Calculate Cosine Similarity: 1 - (embedding <=> query)"]
        Cosine --> Filter["Filter: workspace_id == target AND similarity >= 0.55"]
        Filter --> Validate{"Verify Source Doc in PostgreSQL"}
        Validate -->|Active Doc Found| ReturnChunks["Return Validated Evidence Chunks"]
        Validate -->|Doc Missing / Deleted| Discard["Drop Chunk (Prevent Leakage)"]
    end
```

### Database Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USERS ||--o{ WORKSPACE_MEMBERS : "belongs_to"
    USERS ||--o{ TASKS : "assigns"
    USERS ||--o{ FLOWS : "authors"
    USERS ||--o{ DOCUMENTS : "uploads"
    USERS ||--o{ AI_CHAT_SESSIONS : "creates"
    USERS ||--o{ GITHUB_CONNECTIONS : "authorizes"

    WORKSPACES ||--o{ WORKSPACE_MEMBERS : "contains"
    WORKSPACES ||--o{ TASKS : "manages"
    WORKSPACES ||--o{ DOCUMENTS : "owns"
    WORKSPACES ||--o{ FLOWS : "contains"
    WORKSPACES ||--o{ AI_CHAT_SESSIONS : "scopes"
    WORKSPACES ||--o{ GITHUB_REPOSITORIES : "tracks"

    TASKS ||--o{ TASK_ASSIGNEES : "has"
    USERS ||--o{ TASK_ASSIGNEES : "assigned"
    TASKS ||--o{ TASK_GITHUB_LINKS : "links"
    GITHUB_COMMITS ||--o{ TASK_GITHUB_LINKS : "associated_with"
    GITHUB_PULL_REQUESTS ||--o{ TASK_GITHUB_LINKS : "associated_with"

    FLOWS ||--o{ FLOW_NODES : "contains"
    FLOWS ||--o{ FLOW_EDGES : "contains"
    FLOWS ||--o{ FLOW_COMMENTS : "has"
    FLOWS ||--o{ FLOW_VERSIONS : "snapshots"

    AI_CHAT_SESSIONS ||--o{ AI_CHATS : "records"
```

---

## Project Structure

```text
Design-Project/
├── docker-compose.yml          # Multi-container orchestration (Backend, Frontend, Postgres, Redis)
├── LICENSE                     # MIT License
├── README.md                   # Primary project documentation
├── fesign project.md           # Preserved legacy technical reference
├── backend/
│   ├── Dockerfile              # Python 3.11-slim production container
│   ├── requirements.txt        # Pinned Python package dependencies
│   ├── .env.example            # Backend environment template
│   ├── app/
│   │   ├── main.py             # FastAPI entrypoint, middleware, rate limiter, and health check
│   │   ├── database.py         # SQLAlchemy engine, session factory, Base declarative
│   │   ├── models.py           # Relational SQLAlchemy ORM schemas
│   │   ├── schemas.py          # Pydantic request and response contracts
│   │   ├── dependencies.py     # Auth session injection and permission dependencies
│   │   ├── migrations.py       # Idempotent database migrations and RPC function definitions
│   │   ├── agents/
│   │   │   ├── agent.py        # LangGraph ReAct agent loop and dynamic tool factory
│   │   │   ├── state.py        # Agent state definitions
│   │   │   └── tools.py        # Workspace-bound tool implementations (search, tasks, email)
│   │   ├── rag/
│   │   │   ├── chunker.py      # Overlapping word-level text chunking engine
│   │   │   ├── embedder.py     # Google GenAI 768-dim embedding client
│   │   │   └── vector_store.py # Fail-closed pgvector search and persistence
│   │   ├── routes/
│   │   │   ├── auth.py         # Registration, login, token refresh, logout, GitHub OAuth
│   │   │   ├── workspaces.py   # Multi-tenant workspace lifecycle, members, and settings
│   │   │   ├── tasks.py        # Kanban task CRUD, commit linking, and completion
│   │   │   ├── documents.py    # Document upload, extraction, and vector indexation
│   │   │   ├── ai.py           # Agent session management and conversational chat
│   │   │   ├── chat.py         # Workspace team messaging channels and inbox
│   │   │   ├── flows.py        # Visual canvas CRUD, sync, versioning, and AI explanation
│   │   │   ├── github.py       # GitHub App webhooks, repository sync, and activity digest
│   │   │   └── dashboard.py    # User presence heartbeats and catch-up analytics
│   │   ├── services/
│   │   │   └── github_app.py   # GitHub App JWT generator and Octokit API integration
│   │   └── utils/
│   │       ├── document_parser.py # PDF, DOCX, CSV, Excel structural text extractors
│   │       ├── llm_factory.py     # Multi-provider LLM factory (Gemini + Local Ollama)
│   │       └── supabase_client.py # Supabase client wrapper
│   ├── evaluation/             # Research evaluation benchmark infrastructure
│   │   ├── configs.py          # Empirical evaluation configurations (A/B/C testing)
│   │   ├── run_evaluation.py   # Benchmark execution runner
│   │   ├── score_results.py    # Deterministic scoring rubrics and factual metric evaluators
│   │   ├── questions.json      # Grounded 20-question evaluation dataset
│   │   └── questions_phase3_100.json # 100-question empirical evaluation benchmark
│   └── tests/                  # Pytest test suite (unit, integration, permission isolation)
└── frontend/
    ├── Dockerfile              # Multi-stage Next.js standalone container
    ├── package.json            # Node.js dependencies and run scripts
    ├── next.config.mjs         # Next.js standalone build configuration
    ├── tailwind.config.ts      # Tailwind CSS styling and theme configuration
    ├── app/
    │   ├── (auth)/             # Authentication views (login, registration)
    │   ├── (app)/dashboard/    # Protected application dashboard layout and views
    │   │   ├── ai/             # Autonomous agent assistant and chat interface
    │   │   ├── tasks/          # Interactive Kanban board
    │   │   ├── documents/      # Knowledge base repository and TipTap rich editor
    │   │   ├── flows/          # Orbit Flow visual architecture canvas
    │   │   ├── chat/           # Real-time team messaging interface
    │   │   ├── integrations/   # GitHub App connection and repository controls
    │   │   └── settings/       # Workspace member controls and AI provider settings
    │   └── status/             # System health status page
    ├── components/             # Reusable UI component library (Radix UI wrappers)
    ├── hooks/                  # Custom React hooks
    ├── lib/                    # API clients and utilities
    ├── store/                  # Zustand stores (authentication, workspace state)
    └── types/                  # TypeScript interface definitions
```

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose:** Docker Engine 24+ and Docker Compose v2.
- *Alternatively for manual setup:*
  - **Python:** 3.11 or 3.12
  - **Node.js:** 20.x LTS or higher and `npm`
  - **PostgreSQL:** 16+ with `pgvector` extension enabled
  - **Redis:** 7+ (optional for local caching)
- **Google Gemini API Key:** Required for default cloud inference and document embeddings. Obtain one at [Google AI Studio](https://aistudio.google.com/).

---

### Quickstart with Docker Compose

The fastest way to run Orbit locally with all services (PostgreSQL, Redis, FastAPI backend, and Next.js frontend) is using Docker Compose:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/Design-Project.git
   cd Design-Project
   ```

2. **Configure environment variables:**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```
   Open `backend/.env` and insert your `GEMINI_API_KEY` and a secure `JWT_SECRET`.

3. **Start all services:**
   ```bash
   docker compose up --build
   ```

4. **Access the application:**
   - **Frontend UI:** [http://localhost:3000](http://localhost:3000)
   - **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Manual Local Development Setup

#### 1. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install pinned Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your `.env` file:
   ```bash
   cp .env.example .env
   ```
   Update `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `GEMINI_API_KEY`.

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### 2. Frontend Setup (Next.js)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure your local environment file:
   ```bash
   cp .env.example .env.local
   ```
   Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` is set.

4. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Description | Required | Default / Example |
|---|---|:---:|---|
| `FRONTEND_URL` | Allowed origin for CORS validation | Yes | `http://localhost:3000` |
| `PRODUCTION` | Production environment flag | No | `False` |
| `DATABASE_URL` | PostgreSQL connection string | Yes | `postgresql://user:pass@localhost:5432/nexusai` |
| `REDIS_URL` | Redis connection URL | No | `redis://localhost:6379/0` |
| `SUPABASE_URL` | Supabase project URL (for pgvector & Realtime) | Yes | `https://your-project.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (bypasses RLS for backend) | Yes | `your-service-role-key` |
| `JWT_SECRET` | Secret key used to sign and verify JWT tokens | Yes | `your-super-secret-jwt-key` |
| `JWT_ALGORITHM` | Cryptographic algorithm for JWT | No | `HS256` |
| `JWT_EXPIRE_MINUTES` | Access token expiration lifetime in minutes | No | `10080` (7 days) |
| `LLM_PROVIDER` | Primary AI provider (`gemini` or `ollama`) | No | `gemini` |
| `GEMINI_API_KEY` | Google Gemini API key | Yes* | `your-gemini-api-key` (*if using Gemini) |
| `GEMINI_MODEL` | Gemini model name | No | `gemini-3.5-flash-lite` |
| `OLLAMA_MODEL` | Model tag for local Ollama inference | No | `llama3.2` |
| `OLLAMA_BASE_URL` | Base endpoint URL for Ollama | No | `http://localhost:11434` |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | No | `your-github-client-id` |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth client secret | No | `your-github-client-secret` |
| `GITHUB_APP_SLUG` | GitHub App public slug | No | `your-github-app-slug` |
| `GITHUB_APP_ID` | GitHub App numerical ID | No | `your-github-app-id` |
| `GITHUB_WEBHOOK_SECRET`| Secret key verifying GitHub webhook payloads | No | `your-github-webhook-secret` |
| `GITHUB_APP_PRIVATE_KEY_PATH` | Path to GitHub App `.pem` private key | No | `nexusai-github.private-key.pem` |
| `SMTP_HOST` | Outgoing SMTP host for email notifications | No | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port with STARTTLS | No | `587` |
| `SMTP_USER` | SMTP username / sender email | No | `your-email@gmail.com` |
| `SMTP_PASS` | SMTP application password | No | `your-smtp-app-password` |

### Frontend Configuration (`frontend/.env.local`)

| Variable | Description | Required | Default / Example |
|---|---|:---:|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the backend FastAPI service | Yes | `http://localhost:8000` |
| `NEXT_PUBLIC_SUPABASE_URL` | Public Supabase project URL | Yes | `https://your-project.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public Supabase anonymous client key | Yes | `your-supabase-anon-key` |

---

## API Documentation

Interactive OpenAPI documentation is automatically served at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the backend is running. Below is a reference of the core API routes:

### Authentication & Identity (`/api/auth`)

| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| `POST` | `/api/auth/register` | No | Register a new user account (rate-limited to 3/min) |
| `POST` | `/api/auth/login` | No | Authenticate with email/password; returns JWT and sets HTTP-only refresh cookie (rate-limited to 5/min) |
| `POST` | `/api/auth/refresh` | No | Rotate expired access token using HTTP-only refresh cookie |
| `POST` | `/api/auth/logout` | No | Invalidate session and clear HTTP-only cookies |
| `GET` | `/api/auth/me` | Bearer Token | Retrieve authenticated user profile |
| `GET` | `/api/auth/github` | No | Initiate GitHub OAuth authorization flow |
| `GET` | `/api/auth/github/callback` | No | Handle GitHub OAuth callback and issue session tokens |

### Workspaces & Membership (`/api/workspaces`)

| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| `POST` | `/api/workspaces/` | Bearer Token | Create a new isolated workspace |
| `GET` | `/api/workspaces/` | Bearer Token | List all workspaces the current user belongs to |
| `GET` | `/api/workspaces/{workspace_id}` | Bearer Token | Retrieve workspace details |
| `POST` | `/api/workspaces/join/{invite_code}` | Bearer Token | Join a workspace using an invite code |
| `POST` | `/api/workspaces/{workspace_id}/regenerate-invite`| Bearer Token | Regenerate invite code (admin/owner only) |
| `GET` | `/api/workspaces/{workspace_id}/members` | Bearer Token | List members and roles for a workspace |
| `PATCH` | `/api/workspaces/{workspace_id}/members/{member_id}/role` | Bearer Token | Update member role (admin/owner only) |
| `DELETE`| `/api/workspaces/{workspace_id}/members/{member_id}` | Bearer Token | Remove member from workspace |
| `GET` | `/api/workspaces/{workspace_id}/settings` | Bearer Token | Retrieve workspace AI and provider settings |
| `PATCH` | `/api/workspaces/{workspace_id}/settings` | Bearer Token | Update AI provider, model, and Ollama configuration |
| `POST` | `/api/workspaces/{workspace_id}/test-ollama` | Bearer Token | Test connectivity to a configured Ollama endpoint |

### Tasks & Kanban Management (`/api/tasks`)

| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| `POST` | `/api/tasks/` | Bearer Token | Create a new task ticket |
| `GET` | `/api/tasks/` | Bearer Token | List tasks filtered by workspace, status, or assignee |
| `PATCH` | `/api/tasks/{task_id}` | Bearer Token | Update task title, description, status, priority, or due date |
| `POST` | `/api/tasks/{task_id}/complete` | Bearer Token | Mark task as completed |
| `POST` | `/api/tasks/{task_id}/link-commit` | Bearer Token | Associate a validated Git commit SHA to a task |
| `DELETE`| `/api/tasks/{task_id}/links/{link_id}` | Bearer Token | Remove commit/PR link from task |
| `DELETE`| `/api/tasks/{task_id}` | Bearer Token | Delete a task (admin/owner only) |

### Knowledge Base & Documents (`/api/documents`)

| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| `POST` | `/api/documents/upload` | Bearer Token | Upload document (`.pdf`, `.docx`, `.txt`, `.csv`, `.xlsx`), parse content, chunk, and index embeddings |
| `GET` | `/api/documents/` | Bearer Token | List all documents belonging to a workspace |
| `GET` | `/api/documents/{doc_id}` | Bearer Token | Retrieve full document content and metadata |
| `PATCH` | `/api/documents/{doc_id}` | Bearer Token | Update document title or content and refresh vector embeddings |
| `DELETE`| `/api/documents/{doc_id}` | Bearer Token | Delete document and remove all associated vector embeddings |

### Agentic AI & Chat (`/api/ai`)

| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| `POST` | `/api/ai/chat` | Bearer Token | Execute LangGraph autonomous agent with workspace tools |
| `GET` | `/api/ai/{workspace_id}/sessions` | Bearer Token | List conversation sessions in a workspace |
| `POST` | `/api/ai/{workspace_id}/sessions` | Bearer Token | Create a new conversational session |
| `GET` | `/api/ai/{workspace_id}/sessions/{session_id}/messages` | Bearer Token | Retrieve message history for a session |
| `DELETE`| `/api/ai/{workspace_id}/sessions/{session_id}` | Bearer Token | Delete a conversation session |

### Collaborative Flows (`/api/flows`)

| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| `GET` | `/api/flows/` | Bearer Token | List all workflow diagram canvases |
| `POST` | `/api/flows/` | Bearer Token | Create a new workflow canvas |
| `GET` | `/api/flows/{flow_id}` | Bearer Token | Retrieve canvas nodes, edges, and comments |
| `POST` | `/api/flows/{flow_id}/sync` | Bearer Token | Batch synchronize node positions and edge connections |
| `POST` | `/api/flows/{flow_id}/versions` | Bearer Token | Snapshot a named version checkpoint |
| `POST` | `/api/flows/{flow_id}/versions/{version_id}/restore` | Bearer Token | Restore canvas to a historic version snapshot |
| `POST` | `/api/flows/{flow_id}/ai-explain` | Bearer Token | Analyze canvas topology and generate AI architecture explanation |

### GitHub Integration & Dashboard (`/api/github`, `/api/dashboard`, `/api/webhooks`)

| Method | Endpoint | Auth Required | Description |
|---|---|:---:|---|
| `GET` | `/api/integrations/github/install-url` | Bearer Token | Generate GitHub App installation URL |
| `GET` | `/api/integrations/github/repositories` | Bearer Token | List linked GitHub repositories |
| `POST` | `/api/integrations/github/repositories/sync` | Bearer Token | Sync pull requests and commits from GitHub |
| `POST` | `/api/webhooks/github` | Webhook Secret | Ingest and process GitHub App webhook events |
| `POST` | `/api/dashboard/heartbeat` | Bearer Token | Update user activity state timestamp |
| `GET` | `/api/dashboard/when-you-were-away` | Bearer Token | Retrieve summary of commits, PRs, and tasks since last seen |
| `GET` | `/api/health` | No | System health check (API, database, agent status) |

---

## How It Works

### 1. LangGraph Autonomous ReAct Execution Loop
The agent is orchestrated via `langgraph.prebuilt.create_react_agent`. When a prompt arrives at `/api/ai/chat`:
1. **Dynamic Context Closure:** Tools are instantiated via `get_agent_tools(...)` using lexical closures that bake the current `workspace_id` and `user_id` directly into the tool function. This prevents parameter tampering or cross-tenant leakage while maintaining strict Pydantic argument validation for LLM function calling.
2. **Context Pre-Injection:** Before invoking the model, Orbit generates query embeddings and performs a vector search against pgvector to extract the top 2 most relevant document chunks, appending them as verified ground truth in the system prompt.
3. **Execution & Reasoning:** The agent reasons iteratively. If it determines that an action is needed (e.g. querying tasks or sending an alert), it halts generation, emits a structured tool invocation, receives the execution output, and continues until it produces a conclusive markdown response.

### 2. Fail-Closed RAG Vector Search
Document security is paramount in collaborative multi-tenant systems. Traditional RAG setups often query a vector database and trust the returned IDs without cross-checking relational permissions. Orbit implements a **fail-closed verification layer**:
- Chunks are stored in the `embeddings` table alongside `workspace_id` and `source_id`.
- The `match_embeddings` stored procedure performs cosine similarity search filtered strictly by the caller's `workspace_id`.
- Retrieved chunks are subsequently validated against the active PostgreSQL `documents` table. If a document has been deleted or archived, its chunks are instantly discarded before being returned to the agent context.

### 3. Visual Workflow Builder & AI Architecture Explanation
The Orbit Flow canvas (`@xyflow/react`) translates system diagrams into interactive graphs:
- Canvas topology (nodes and directional edges) is stored relationally across `flow_nodes` and `flow_edges`.
- The `/api/flows/{flow_id}/ai-explain` endpoint serializes node identifiers, types, labels, and adjacency matrices into an architectural prompt. Google Gemini processes the graph topology to identify architectural patterns, potential bottlenecks, and execution flows, returning a structured architectural critique.

---

## Testing and Quality Assurance

Orbit includes a comprehensive automated test suite covering unit tests, permission isolation, evaluation benchmarks, and fail-closed security properties.

### Running Backend Tests

Run all unit and integration tests from the `backend/` directory:

```bash
cd backend
python -m pytest tests
```

#### Test Suite Highlights

- `test_agent_tool_permissions.py`: Verifies that member roles are strictly barred from destructive tools (`create_task`, `update_task`, email dispatch), and confirms proper execution for admins.
- `test_vector_search_fail_closed.py`: Validates that similarity searches fail closed when document validation fails or when queries target unauthorized workspaces.
- `test_evaluation_config.py`: Tests tool filtering and pre-injection behaviors under various evaluation modes.
- `test_offline_smoke_harness.py`: Validates end-to-end evaluation runner flows in 100% offline mode using mock LLM harnesses.

### Frontend Quality Checks

```bash
cd frontend

# Run TypeScript type check
npx tsc --noEmit

# Run ESLint validation
npm run lint
```

---

## Research Evaluation Framework

Located in `backend/evaluation/`, Orbit includes an empirical benchmark suite designed to evaluate multi-source workspace reasoning across three configurations:

1. **`plain_llm`**: Minimal baseline prompt without workspace access.
2. **`rag_docs_only`**: Documents-only vector search without task or chat context.
3. **`full_agent`**: Full Orbit ReAct agent integrating documents, tasks, and team chat.

The benchmark evaluates grounded performance on single-source, multi-source synthesis, and unanswerable questions with deterministic rubric scoring. To run the evaluation offline without incurring API costs:

```bash
cd backend
python -m evaluation.run_evaluation --mock-llm --dataset evaluation/questions.json
```

---

## Deployment

### Containerized Deployment (Docker)

Orbit is production-ready for containerized environments:

- **Backend Container:** Runs Python 3.11 with Uvicorn. The Dockerfile supports dynamic port allocation via `${PORT:-8000}`, making it directly compatible with cloud platforms like Render, AWS ECS, GCP Cloud Run, or Railway.
- **Frontend Container:** Utilizes a multi-stage Alpine build outputting a standalone Next.js server (`server.js`) executed by a non-root user (`nextjs:nodejs`), keeping container sizes minimal and secure.

### Health Probing

All orchestrators and load balancers can probe the dedicated health check endpoint:

```http
GET /api/health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "services": {
    "api": "operational",
    "database": "operational",
    "agent_engine": "operational"
  }
}
```

---

## Future Improvements

- [ ] **Streaming Token Responses:** Stream agent token generation via Server-Sent Events (SSE) or WebSockets to reduce perceived latency during extended ReAct loops.
- [ ] **Granular Workspace Auditing:** Comprehensive audit logging for all agent-mediated mutations and email dispatches.
- [ ] **Local Embedding Fallback:** Enable local SentenceTransformer embedding models when running fully disconnected with Ollama.
- [ ] **Granular Channel Permissions:** Private team messaging channels with invite-only access control.

---

## Contributing

Contributions are welcomed! To contribute:

1. Fork the repository.
2. Create a descriptive feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit your changes following standard commit conventions:
   ```bash
   git commit -m "feat: implement feature description"
   ```
4. Verify all tests pass:
   ```bash
   cd backend && python -m pytest tests
   cd ../frontend && npm run lint
   ```
5. Push to your branch and open a Pull Request.

---

## License

This project is licensed under the [MIT License](LICENSE) — Copyright (c) 2026 Avadhesh Nagar.
