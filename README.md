# Orbit — Unified Agentic Workspace

[![Next.js](https://img.shields.io/badge/Next.js-14.2.35-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.137.1-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.49-D71F00?style=flat-square)](https://www.sqlalchemy.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2.5-1C3C3C?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash%202.5-4285F4?style=flat-square&logo=google)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

Orbit (formerly *Nexus AI*) is an enterprise-ready, open-source collaborative workspace and autonomous agent platform. It unifies project management, rich documentation, real-time team messaging, interactive visual workflow design, and autonomous AI agents powered by LangGraph, Google Gemini, and pgvector-backed Retrieval-Augmented Generation (RAG).

---

## Table of Contents

- [Overview and Problem Statement](#overview-and-problem-statement)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
  - [High-Level System Architecture](#high-level-system-architecture)
  - [End-to-End Request Lifecycle](#end-to-end-request-lifecycle)
  - [Authentication and Session Lifecycle](#authentication-and-session-lifecycle)
  - [RAG Document Ingestion & Retrieval Pipeline](#rag-document-ingestion--retrieval-pipeline)
  - [LangGraph Autonomous Agent Execution Loop](#langgraph-autonomous-agent-execution-loop)
  - [Database Entity-Relationship (ER) Diagram](#database-entity-relationship-er-diagram)
- [Technology Stack](#technology-stack)
- [Repository and Directory Structure](#repository-and-directory-structure)
- [Database Design and Models](#database-design-and-models)
- [API Reference and Route Inventory](#api-reference-and-route-inventory)
  - [Route Inventory Summary](#route-inventory-summary)
  - [Authentication & Identity (`/api/auth`)](#authentication--identity-apiauth)
  - [Workspaces & Membership (`/api/workspaces`)](#workspaces--membership-apiworkspaces)
  - [Tasks & Kanban Operations (`/api/tasks`)](#tasks--kanban-operations-apitasks)
  - [Knowledge Base & Documents (`/api/documents`)](#knowledge-base--documents-apidocuments)
  - [Agentic AI & Chat Sessions (`/api/ai`)](#agentic-ai--chat-sessions-apiai)
  - [Team Channels & Direct Messaging (`/api/chat`)](#team-channels--direct-messaging-apichat)
  - [Collaborative Flows & Workflows (`/api/flows`)](#collaborative-flows--workflows-apiflows)
  - [GitHub App & Integrations (`/api/integrations`, `/api/github`, `/api/webhooks`)](#github-app--integrations-apiintegrations-apigithub-apiwebhooks)
  - [System Health (`/api/health`)](#system-health-apihealth)
- [Installation and Local Setup](#installation-and-local-setup)
  - [Prerequisites](#prerequisites)
  - [Quickstart with Docker Compose](#quickstart-with-docker-compose)
  - [Manual Local Development Setup](#manual-local-development-setup)
- [Environment Variables and Configuration](#environment-variables-and-configuration)
- [Engineering Decisions and Implementation Patterns](#engineering-decisions-and-implementation-patterns)
- [Testing and Quality Assurance](#testing-and-quality-assurance)
- [Known Limitations and Production Considerations](#known-limitations-and-production-considerations)
- [Future Roadmap](#future-roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview and Problem Statement

Modern product engineering teams often switch between disconnected tools: Linear or Jira for tasks, Notion for documentation, Slack for messaging, Miro for system diagrams, and external ChatGPT/Claude web interfaces for AI queries. This causes:
1. **Context Fragmentation**: AI assistants lack access to private tasks, team documents, architecture diagrams, and ongoing sprint discussions.
2. **Action Inability**: Traditional chat tools cannot modify tasks, send status emails, or directly read internal documents.
3. **Data Silos**: Diagrams, project specifications, and commit activity live in separate ecosystems.

**Orbit** solves this by consolidating workspace collaboration tools into a single platform backed by an **action-capable, context-aware autonomous agent**. The agent not only retrieves information across workspace docs and task boards via vector search, but also takes deterministic actions—such as creating tasks, assigning team members, and drafting email reminders—governed by user workspace permissions.

---

## Key Features

- 🏢 **Multi-Tenant Workspaces**: Isolated workspaces with role-based access control (`owner`, `admin`, `member`, `viewer`), join codes, invite links, and granular member management.
- 🔐 **Dual Authentication Mechanism**: Email/password authentication using Argon2 password hashing alongside native GitHub OAuth, backed by short-lived JWT access tokens and HTTP-only refresh tokens with automatic token rotation.
- 📋 **Interactive Kanban Task Management**: Multi-status workflow boards (`todo`, `in_progress`, `review`, `done`), multi-assignee support, priority indicators, due dates, search filtering, and task audit logs.
- 📚 **Knowledge Base & Deep RAG Pipeline**: Ingest and index PDF, DOCX, TXT, MD, CSV, and XLSX files. Chunks documents (1000 characters with 50-character overlap), generates vector embeddings via `gemini-embedding-001`, and queries relevant context using PostgreSQL `pgvector` vector similarity search.
- ✍️ **Collaborative TipTap Document Editor**: Rich text editing with live word/character counting, headings, formatting blocks, and real-time backend synchronization.
- 🤖 **Autonomous AI Agent (LangGraph + Gemini 2.5 Flash)**: An agentic loop executing tools dynamically:
  - `search_documents`: Semantic search across workspace knowledge bases.
  - `get_workspace_tasks`: Real-time query of tasks filtered by status and assignee.
  - `create_task`: Direct task creation with title, description, priority, and assignees.
  - `update_task_status`: Status transition execution for existing tasks.
  - `send_task_reminder_email`: Automated assignee task reminder dispatch via Resend.
  - `send_task_deadline_email`: Urgent deadline warning email dispatch.
  - `send_announcement_email`: Workspace-wide broadcast email dispatch.
  - `get_recent_chat_messages`: Context retrieval from team messaging channels.
- 💬 **Real-Time Team Messaging**: Channel-based chat and 1-on-1 direct messaging (DMs) powered by Supabase Realtime WebSocket broadcasting with fallback persistence in PostgreSQL.
- 🗺️ **Orbit Flow Collaborative Canvas**: Drag-and-drop workflow diagram editor built on `@xyflow/react` featuring custom nodes, edges, comments, version checkpointing/restoration, PNG exports, and AI-powered workflow analysis via Google Gemini.
- 🐙 **GitHub App Integration Architecture**: GitHub App webhook ingestion for repository issues, pull requests, and commit pushes, mapping repository events directly to workspace tasks and calculating away-time activity summaries.

---

## System Architecture

### High-Level System Architecture

```mermaid
graph TB
    subgraph Client["Client Tier (Browser)"]
        FE["Next.js 14 App Router (React 18 / TypeScript)"]
        Zustand["Zustand Stores (Auth & Workspace)"]
        TQ["TanStack Query v5 (Server Cache)"]
        Canvas["@xyflow/react (Flow Canvas)"]
        TipTap["TipTap Rich Editor"]
    end

    subgraph Gateway["API Gateway & Reverse Proxy"]
        Caddy["Docker / Reverse Proxy / localhost:8000"]
    end

    subgraph Backend["Application Tier (FastAPI / Python 3.11+)"]
        API["FastAPI HTTP Server"]
        Middleware["SlowAPI Rate Limiter & CORS Middleware"]
        AuthLayer["JWT & Argon2 Security Layer"]
        
        subgraph Subsystems["Application Subsystems"]
            RAG["RAG Ingestion & Vector Service (Gemini Embeddings)"]
            Agent["LangGraph ReAct Autonomous Agent (Gemini 2.5 Flash)"]
            ChatSys["Realtime Chat & DM Hub"]
            FlowSys["Flow Canvas & AI Explainer Engine"]
            TaskSys["Task & Kanban Service"]
            GHSys["GitHub App Webhook Ingestion Engine"]
        end
    end

    subgraph External["External Cloud & AI Services"]
        GoogleAI["Google Gemini API (gemini-2.5-flash & text-embedding-004)"]
        SupabaseRT["Supabase Realtime (WebSocket Broadcasting)"]
        ResendAPI["Resend Email API (Transactional Alerts)"]
        GHAPI["GitHub REST API & Webhooks"]
    end

    subgraph Storage["Persistence & Caching Tier"]
        PG[("PostgreSQL 16 (Relational Tables)")]
        PGV[("pgvector Extension (Supabase Vector Store)")]
        Redis[("Redis 7 (Distributed Caching & Sessions)")]
    end

    FE -->|HTTP / REST (Axios Interceptors)| Caddy
    FE -.->|WebSocket Channels| SupabaseRT
    Caddy --> API
    API --> Middleware
    Middleware --> AuthLayer
    AuthLayer --> Subsystems

    RAG --> GoogleAI
    RAG --> PGV
    Agent --> GoogleAI
    Agent --> Subsystems
    Agent --> ResendAPI
    GHSys --> GHAPI

    Subsystems --> PG
    Subsystems -.-> Redis
```

---

### End-to-End Request Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as Client (Next.js)
    participant RateLimit as SlowAPI Middleware
    participant Auth as Auth Dependency (get_current_user)
    participant Route as FastAPI Router Handler
    participant Service as Service / Agent Layer
    participant DB as PostgreSQL (SQLAlchemy)
    participant Ext as External Service (Gemini / Resend)

    User->>RateLimit: HTTP Request with Bearer Token & Cookies
    alt Rate Limit Exceeded
        RateLimit-->>User: 429 Too Many Requests
    else Allowed
        RateLimit->>Auth: Forward Request
    end

    Auth->>Auth: Decode & Verify JWT Access Token
    alt Invalid or Expired Token
        Auth-->>User: 401 Unauthorized (Triggers Frontend Refresh)
    else Token Valid
        Auth->>DB: Fetch Active User Record
        DB-->>Auth: User Entity
        Auth->>Route: Inject Current User
    end

    Route->>Route: Validate Request Payload (Pydantic Schema)
    alt Validation Error
        Route-->>User: 422 Unprocessable Entity
    else Schema Valid
        Route->>Service: Execute Business Logic
    end

    opt Invokes External Service
        Service->>Ext: External API Call (Gemini / Resend)
        Ext-->>Service: Service Response
    end

    Service->>DB: Read/Write Database Transaction
    DB-->>Service: Commit / Result
    Service-->>Route: Return Structured DTO
    Route-->>User: 200/201 JSON Response
```

---

### Authentication and Session Lifecycle

Orbit implements a secure dual-token authentication pattern with automatic silent token renewal.

```mermaid
sequenceDiagram
    autonumber
    actor Client as Browser Client
    participant AuthAPI as /api/auth
    participant DB as PostgreSQL
    participant Storage as Client State (Zustand & Cookies)

    Note over Client,AuthAPI: 1. User Registration / Login
    Client->>AuthAPI: POST /api/auth/login { email, password }
    AuthAPI->>DB: Query User by Email
    DB-->>AuthAPI: User record (with Argon2 password_hash)
    AuthAPI->>AuthAPI: Verify Password Hash
    AuthAPI->>AuthAPI: Generate Short-Lived Access Token (15-60m)
    AuthAPI->>AuthAPI: Generate Long-Lived Refresh Token (7-30d)
    AuthAPI-->>Client: 200 OK + JSON { access_token, user } + Set-Cookie: refresh_token (HttpOnly)
    Client->>Storage: Store access_token in Memory / Zustand

    Note over Client,AuthAPI: 2. Authenticated API Call
    Client->>AuthAPI: GET /api/workspaces (Authorization: Bearer <access_token>)
    AuthAPI-->>Client: 200 OK (Workspace List)

    Note over Client,AuthAPI: 3. Silent Refresh Interceptor
    Client->>AuthAPI: GET /api/tasks (Expired access_token)
    AuthAPI-->>Client: 401 Unauthorized
    Client->>AuthAPI: POST /api/auth/refresh (Sends HttpOnly Cookie)
    AuthAPI->>AuthAPI: Validate Refresh Token
    AuthAPI-->>Client: 200 OK + New access_token
    Client->>AuthAPI: Retry Original GET /api/tasks with new token
    AuthAPI-->>Client: 200 OK (Task List)

    Note over Client,AuthAPI: 4. Logout
    Client->>AuthAPI: POST /api/auth/logout
    AuthAPI-->>Client: 200 OK + Clear-Cookie: refresh_token
```

---

### RAG Document Ingestion & Retrieval Pipeline

```mermaid
flowchart TD
    subgraph Ingestion["Document Ingestion Pipeline"]
        A["Document Uploaded (.pdf, .docx, .txt, .csv, .xlsx)"] --> B["FastAPI Upload Endpoint: /api/documents/upload"]
        B --> C{"Format Parser"}
        C -->|PDF| D1["pdfplumber Extractor"]
        C -->|DOCX| D2["python-docx Extractor"]
        C -->|Excel / CSV| D3["pandas / openpyxl Extractor"]
        C -->|Plain Text / MD| D4["Standard UTF-8 Reader"]
        D1 & D2 & D3 & D4 --> E["Text Chunker (1000 chars / 50 overlap)"]
        E --> F["Google GenAI Embeddings API (gemini-embedding-001)"]
        F --> G["Store in Supabase pgvector table: document_embeddings"]
        B --> H["Store Document Metadata in PostgreSQL: documents table"]
    end

    subgraph Retrieval["Agent Retrieval Phase"]
        Q["User / Agent asks question"] --> R["Embed Query via gemini-embedding-001"]
        R --> S["Call PostgreSQL RPC: match_embeddings(query_vector, match_threshold, match_count)"]
        S --> G
        G --> T["Cosine Similarity Matching"]
        T --> U["Return Top-K Relevant Document Chunks"]
        U --> V["Inject Chunks into LangGraph Prompt Context"]
    end
```

---

### LangGraph Autonomous Agent Execution Loop

The AI Assistant uses a **LangGraph StateGraph ReAct Loop** to parse instructions, call tools deterministically, inspect results, and synthesize answers.

```mermaid
flowchart TD
    Start([User Prompt Received]) --> Init[Load Agent State: messages, workspace_id, user_id]
    Init --> AgentNode[Agent Node: Google Gemini 2.5 Flash]
    AgentNode --> Eval{Tool Call Requested?}
    
    Eval -->|No: Final Answer Synthesized| Output([Stream / Return Markdown Response])
    
    Eval -->|Yes: Tool Call Required| Router{Tool Dispatcher}
    Router -->|search_documents| T1["RAG Vector Similarity Search"]
    Router -->|get_workspace_tasks| T2["Query Tasks DB by Status/Assignee"]
    Router -->|create_task| T3["Insert Task into PostgreSQL"]
    Router -->|update_task_status| T4["Update Task Status in DB"]
    Router -->|send_task_reminder_email| T5["Trigger Resend API Email"]
    Router -->|send_task_deadline_email| T6["Trigger Resend API Urgent Alert"]
    Router -->|send_announcement_email| T7["Broadcast Resend Email to Workspace"]
    Router -->|get_recent_chat_messages| T8["Fetch Chat History from DB"]
    
    T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 --> ToolNode[Append Tool Message to History]
    ToolNode --> AgentNode
```

---

### Database Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    User ||--o{ Workspace : "creates"
    User ||--o{ WorkspaceMember : "has"
    User ||--o{ Document : "authors"
    User ||--o{ Task : "creates"
    User ||--o{ TaskAssignee : "assigned_to"
    User ||--o{ AIChatSession : "owns"
    User ||--o{ Flow : "authors"
    User ||--o{ GitHubConnection : "connects"

    Workspace ||--o{ WorkspaceMember : "contains"
    Workspace ||--o{ Document : "owns"
    Workspace ||--o{ Task : "manages"
    Workspace ||--o{ AIChatSession : "scopes"
    Workspace ||--o{ Flow : "hosts"
    Workspace ||--o{ GitHubConnection : "integrates"

    Task ||--o{ TaskAssignee : "assigned"
    Task ||--o{ TaskGitHubLink : "linked_to"

    AIChatSession ||--o{ AIChat : "contains_messages"

    Flow ||--o{ FlowNode : "defines"
    Flow ||--o{ FlowEdge : "connects"
    Flow ||--o{ FlowComment : "annotated_with"
    Flow ||--o{ FlowVersion : "snapshots"

    GitHubConnection ||--o{ GitHubRepository : "installs"
    GitHubRepository ||--o{ GitHubEvent : "records"
    GitHubRepository ||--o{ GitHubPullRequest : "tracks"
    GitHubRepository ||--o{ GitHubCommit : "tracks"
    GitHubRepository ||--o{ TaskGitHubLink : "references"

    User {
        uuid id PK
        string email UK
        string name
        string password_hash
        string avatar_url
        string github_id
        timestamp created_at
        timestamp updated_at
    }

    Workspace {
        uuid id PK
        string name
        string slug UK
        string invite_code UK
        uuid created_by FK
        jsonb settings
        timestamp created_at
        timestamp updated_at
    }

    WorkspaceMember {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK
        string role "owner | admin | member | viewer"
        timestamp joined_at
    }

    Document {
        uuid id PK
        uuid workspace_id FK
        uuid author_id FK
        string title
        text content
        string file_url
        string file_type
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    Task {
        uuid id PK
        uuid workspace_id FK
        uuid creator_id FK
        string title
        text description
        string status "todo | in_progress | review | done"
        string priority "low | medium | high | urgent"
        timestamp due_date
        timestamp created_at
        timestamp updated_at
    }

    TaskAssignee {
        uuid id PK
        uuid task_id FK
        uuid user_id FK
    }

    AIChatSession {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK
        string title
        timestamp created_at
        timestamp updated_at
    }

    AIChat {
        uuid id PK
        uuid session_id FK
        string role "user | assistant | system"
        text content
        jsonb tool_calls
        timestamp created_at
    }

    Flow {
        uuid id PK
        uuid workspace_id FK
        uuid author_id FK
        string title
        text description
        jsonb viewport
        timestamp created_at
        timestamp updated_at
    }

    FlowNode {
        uuid id PK
        uuid flow_id FK
        string node_type
        float position_x
        float position_y
        jsonb data
    }

    FlowEdge {
        uuid id PK
        uuid flow_id FK
        string source_node_id
        string target_node_id
        string label
        jsonb data
    }

    FlowComment {
        uuid id PK
        uuid flow_id FK
        uuid user_id FK
        float position_x
        float position_y
        text comment
        timestamp created_at
    }

    FlowVersion {
        uuid id PK
        uuid flow_id FK
        int version_number
        jsonb snapshot_data
        timestamp created_at
    }
```

---

## Technology Stack

| Layer | Technology | Version | Purpose in Orbit |
|---|---|---|---|
| **Frontend Framework** | [Next.js](https://nextjs.org/) | `14.2.35` | React framework using App Router, SSR, and standalone build support |
| **Language (Frontend)**| [TypeScript](https://www.typescriptlang.org/) | `5.x` | Type-safe UI components, DTOs, and state definitions |
| **Styling** | [Tailwind CSS](https://tailwindcss.com/) | `v3.4.1` | Utility-first CSS styling, animations via `tailwindcss-animate` |
| **Workflow Canvas** | [@xyflow/react](https://reactflow.dev/) | `^12.15.1` | Interactive node-based diagramming, custom cards, and edge connections |
| **Document Editor** | [TipTap](https://tiptap.dev/) | `^2.11.5` | Headless rich-text editor with real-time formatting |
| **Client State** | [Zustand](https://github.com/pmndrs/zustand) | `^5.0.3` | Lightweight state stores for authentication and active workspace context |
| **Server State / Cache**| [TanStack Query](https://tanstack.com/query) | `^5.67.1` | Server state management, caching, optimistic mutations, and retries |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | `0.137.1` | High-performance Python async web framework with automatic OpenAPI documentation |
| **ASGI Web Server** | [Uvicorn](https://www.uvicorn.org/) | `0.44.0` | Production ASGI web server supporting async event loops |
| **Language (Backend)** | [Python](https://www.python.org/) | `3.11+` | Backend business logic, AI orchestration, and database operations |
| **ORM / Data Access** | [SQLAlchemy](https://www.sqlalchemy.org/) | `2.0.49` | Python SQL toolkit and Object-Relational Mapper (ORM) |
| **Database Migrations**| [Alembic](https://alembic.sqlalchemy.org/) | `1.15.1` | Database migration engine for schema evolution |
| **Database** | [PostgreSQL](https://www.postgresql.org/) | `16` | Primary ACID relational database storing workspace models and metadata |
| **Vector Storage** | [pgvector](https://github.com/pgvector/pgvector) | Compatible | Vector similarity search extension accessed via Supabase RPC |
| **Cache & Key-Value** | [Redis](https://redis.io/) | `7.0-alpine` | Distributed cache, temporary states, and future queue processing |
| **AI Orchestration** | [LangGraph](https://langchain-ai.github.io/langgraph/) | `1.2.5` | Graph-based cyclic execution framework for ReAct autonomous agent loops |
| **LangChain Core** | [LangChain](https://www.langchain.com/) | `1.3.9` | Tool declarations, prompt management, and model interface adapters |
| **Foundation LLM** | [Google Gemini](https://ai.google.dev/) | `2.5 Flash` | Reasoning engine for agent tool selection, chat, and flow analysis |
| **Vector Embeddings** | Google GenAI | `gemini-embedding-001` | High-dimensional dense embeddings for RAG document chunking |
| **Realtime Messaging** | [Supabase Realtime](https://supabase.com/docs/guides/realtime) | Client-backed | WebSocket broadcasting for channel messages and notifications |
| **Transactional Email**| [Resend](https://resend.com/) | API-driven | Transactional emails for deadlines, task reminders, and announcements |
| **Document Parsers** | `pdfplumber`, `python-docx`, `pandas`, `openpyxl` | Latest | Multi-format document parsing for knowledge base ingestion |
| **Rate Limiting** | [SlowAPI](https://github.com/laurents/slowapi) | `0.1.9` | Request throttling and endpoint-level abuse prevention |
| **Password Security** | Passlib / Argon2 | `1.7.4` | Argon2id cryptographic password hashing algorithm |

---

## Repository and Directory Structure

```text
Design-Project/
├── docker-compose.yml              # Multi-container orchestration (PostgreSQL, Redis, Backend, Frontend)
├── README.md                       # Comprehensive system documentation
│
├── backend/                        # FastAPI Backend Application
│   ├── Dockerfile                  # Container definition for Python 3.11 FastAPI service
│   ├── requirements.txt            # Python dependencies and locked versions
│   ├── alembic.ini                 # Database migration tool configuration
│   ├── alembic/                    # Database migration scripts and versions
│   └── app/                        # Application Source Code
│       ├── main.py                 # Application entry point, CORS, RateLimiter, Route mounting
│       ├── config.py               # Settings loader (Pydantic BaseSettings) reading from .env
│       ├── database.py             # SQLAlchemy engine, sessionmaker, and get_db dependency
│       ├── models.py               # Complete SQLAlchemy relational database models (17 entities)
│       │
│       ├── agents/                 # LangGraph Autonomous Agent Implementation
│       │   ├── agent.py            # LangGraph ReAct StateGraph definition and loop runner
│       │   ├── prompts.py          # System instructions and dynamic agent prompts
│       │   └── tools.py            # 8 actionable tools (RAG, tasks, email, chat retrieval)
│       │
│       ├── rag/                    # Retrieval-Augmented Generation Engine
│       │   ├── chunker.py          # Text chunking logic (1000 char windows, 50 char overlap)
│       │   ├── embeddings.py       # Google GenAI vector generation client
│       │   ├── parsers.py          # Parsers for PDF, Word, Excel, CSV, and Plaintext
│       │   └── vector_store.py     # Supabase pgvector client and similarity RPC interface
│       │
│       ├── routes/                 # FastAPI HTTP Routers (63 operational endpoints)
│       │   ├── auth.py             # User registration, Argon2 login, JWT tokens, GitHub OAuth
│       │   ├── workspaces.py       # Multi-tenant workspace management, invites, roles
│       │   ├── tasks.py            # Kanban task board CRUD, multi-assignees, task filters
│       │   ├── documents.py        # File upload, document indexing, and CRUD
│       │   ├── ai.py               # AI chat sessions, message histories, LangGraph invocation
│       │   ├── chat.py             # Team channels, direct messages, inbox aggregators
│       │   ├── flows.py            # Visual canvas CRUD, sync, version snapshots, AI explainer
│       │   └── github.py           # GitHub App installation, webhooks, and repository synchronization
│       │
│       ├── schemas/                # Pydantic Schemas / Request and Response DTOs
│       │   ├── auth.py             # Auth payloads and token responses
│       │   ├── workspaces.py       # Workspace creation, updates, and member DTOs
│       │   ├── tasks.py            # Task schemas and filtering parameters
│       │   ├── documents.py        # Document create/update models
│       │   ├── ai.py               # Chat session and messaging models
│       │   ├── chat.py             # Chat message requests and inbox DTOs
│       │   ├── flows.py            # Node, edge, and canvas synchronization DTOs
│       │   └── github.py           # GitHub webhook and installation models
│       │
│       └── services/               # Shared Reusable Business Services
│           ├── email.py            # Resend email client (task reminders, alerts, announcements)
│           ├── github.py           # GitHub REST API client, installation token exchange
│           └── presence.py         # User activity state tracking
│
└── frontend/                       # Next.js 14 Web Application
    ├── Dockerfile                  # Multi-stage production build container (Next.js standalone)
    ├── package.json                # Frontend dependencies, scripts, and build tools
    ├── tsconfig.json               # TypeScript configuration and path aliases (@/*)
    ├── tailwind.config.ts          # Tailwind styling tokens, colors, and layout breakpoints
    ├── next.config.mjs             # Next.js build configuration (standalone output)
    │
    ├── app/                        # Next.js App Router Structure
    │   ├── layout.tsx              # Root HTML layout and global font provider
    │   ├── globals.css             # Tailwind base styles and design variables
    │   ├── page.tsx                # Public product landing page
    │   ├── (auth)/                 # Public Authentication Route Group
    │   │   ├── login/page.tsx      # Login form with email/password and GitHub OAuth
    │   │   └── register/page.tsx   # User registration form
    │   │
    │   └── (app)/                  # Protected Application Route Group
    │       ├── layout.tsx          # Authenticated app shell and global navigation
    │       └── dashboard/          # Dashboard Features
    │           ├── page.tsx        # Workspace overview, metrics, and activity feed
    │           ├── documents/      # Knowledge base view and TipTap document editor
    │           ├── tasks/          # Drag-and-drop Kanban task management board
    │           ├── ai/             # Agentic AI assistant interface and multi-session sidebar
    │           ├── chat/           # Real-time channels and direct messaging interface
    │           ├── flows/          # Collaborative ReactFlow workflow canvas editor
    │           ├── integrations/   # GitHub App connection and repository sync dashboard
    │           └── settings/       # Workspace configuration, member roles, invite links
    │
    ├── components/                 # Reusable UI Component Library
    │   ├── ui/                     # Primitives (Buttons, Dialogs, Inputs, Dropdowns, Badges)
    │   ├── layout/                 # Sidebar, Topbar, WorkspaceSwitcher, UserDropdown
    │   ├── tasks/                  # KanbanBoard, TaskCard, TaskModal, AssigneePicker
    │   ├── documents/              # TipTapEditor, DocumentList, FileUploader
    │   ├── flows/                  # FlowCanvas, CustomNodes, EdgeOptions, VersionHistoryModal
    │   ├── chat/                   # ChannelList, MessageFeed, DMList, ChatInput
    │   └── ai/                     # AIAgentChat, ToolCallBadge, SessionList, PromptSuggestions
    │
    ├── hooks/                      # Custom React Hooks
    │   ├── use-auth.ts             # Auth session wrapper and user profile access
    │   ├── use-workspace.ts        # Active workspace context and switching logic
    │   └── use-chat.ts             # Supabase Realtime channel subscription hook
    │
    ├── lib/                        # Shared Utilities and API Clients
    │   ├── api.ts                  # Axios instance with auth headers and refresh interceptor
    │   ├── supabase.ts             # Supabase Realtime client initialization
    │   └── utils.ts                # Formatting, date parsing, and class name merge utilities
    │
    └── store/                      # Zustand Client State Stores
        ├── auth-store.ts           # Access token and user authentication state
        └── workspace-store.ts      # Active workspace selection and metadata
```

---

## Database Design and Models

The backend persists application state across **17 SQLAlchemy models** defined in `backend/app/models.py`:

| Model Name | Table Name | Purpose | Primary Relationships |
|---|---|---|---|
| `User` | `users` | User credentials, profile info, and OAuth IDs | Author of Workspaces, Documents, Tasks, Flows, and Sessions |
| `Workspace` | `workspaces` | Multi-tenant tenant boundary | Owns Members, Tasks, Docs, Flows, Integrations, and Sessions |
| `WorkspaceMember` | `workspace_members` | Associates users to workspaces with roles | Belongs to `Workspace` and `User` (`owner`, `admin`, `member`, `viewer`) |
| `Document` | `documents` | Stores knowledge base docs and TipTap content | Belongs to `Workspace` and author `User` |
| `Task` | `tasks` | Kanban task items, priorities, and status | Belongs to `Workspace` and creator `User`; has multiple assignees |
| `TaskAssignee` | `task_assignees` | Many-to-many link between tasks and users | Links `Task` to `User` |
| `AIChatSession` | `ai_chat_sessions` | AI conversation thread containers | Belongs to `Workspace` and `User`; contains messages |
| `AIChat` | `ai_chats` | Individual AI messages, role, and tool calls | Belongs to `AIChatSession` |
| `Flow` | `flows` | Workflow diagram metadata and viewport data | Belongs to `Workspace` and author `User` |
| `FlowNode` | `flow_nodes` | Position, type, and payload data for canvas nodes | Belongs to `Flow` (Cascading delete) |
| `FlowEdge` | `flow_edges` | Connections between flow canvas nodes | Belongs to `Flow` (Cascading delete) |
| `FlowComment` | `flow_comments` | Positioned spatial annotations on canvas | Belongs to `Flow` and author `User` |
| `FlowVersion` | `flow_versions` | Immutable JSON snapshots of canvas versions | Belongs to `Flow` |
| `GitHubConnection` | `github_connections`| Workspace connection to GitHub App installation| Belongs to `Workspace` and installing `User` |
| `GitHubRepository` | `github_repositories`| Tracked GitHub repositories in workspace | Belongs to `GitHubConnection` |
| `GitHubEvent` | `github_events` | Raw webhook event log from GitHub | Belongs to `GitHubRepository` |
| `GitHubPullRequest`| `github_pull_requests`| PR lifecycle records | Belongs to `GitHubRepository` |
| `GitHubCommit` | `github_commits` | Commit metadata and author tracking | Belongs to `GitHubRepository` |
| `TaskGitHubLink` | `task_github_links` | Links a workspace task to a PR or Issue | Belongs to `Task` and `GitHubRepository` |
| `UserActivityState`| `user_activity_states`| Tracks last-seen activity for away catch-up | Belongs to `User` and `Workspace` |

---

## API Reference and Route Inventory

All backend routes are mounted under the `/api` prefix in `backend/app/main.py`. The backend implements **63 verified HTTP operations** across 48 path endpoints.

### Route Inventory Summary

| Method | Complete Endpoint | Module | Description | Protected? |
|---|---|---|---|:---:|
| `GET` | `/api/health` | System | Service health and database ping | No |
| `POST` | `/api/auth/register` | Auth | Register a new user with Argon2 password hashing | No |
| `POST` | `/api/auth/login` | Auth | Authenticate user, receive JWT access token & refresh cookie | No |
| `POST` | `/api/auth/logout` | Auth | Revoke session and clear refresh token cookie | No |
| `POST` | `/api/auth/refresh` | Auth | Exchange HttpOnly refresh cookie for a new access token | No |
| `GET` | `/api/auth/me` | Auth | Get current authenticated user profile | Yes |
| `GET` | `/api/auth/github` | Auth | Initiate GitHub OAuth authorization flow | No |
| `GET` | `/api/auth/github/callback`| Auth | GitHub OAuth redirect callback | No |
| `GET` | `/api/workspaces/` | Workspaces | List all workspaces the user belongs to | Yes |
| `POST` | `/api/workspaces/` | Workspaces | Create a new workspace (creator becomes owner) | Yes |
| `GET` | `/api/workspaces/{workspace_id}` | Workspaces | Fetch workspace details and member count | Yes |
| `DELETE` | `/api/workspaces/{workspace_id}` | Workspaces | Delete workspace (Owner only) | Yes |
| `POST` | `/api/workspaces/join/{invite_code}` | Workspaces | Join workspace using an invite code | Yes |
| `POST` | `/api/workspaces/{workspace_id}/regenerate-invite` | Workspaces | Generate a new invite code for workspace | Yes |
| `GET` | `/api/workspaces/{workspace_id}/members` | Workspaces | List all members and roles in workspace | Yes |
| `DELETE` | `/api/workspaces/{workspace_id}/members/{member_id}` | Workspaces | Remove a member from the workspace | Yes |
| `PATCH` | `/api/workspaces/{workspace_id}/members/{member_id}/role` | Workspaces | Update a member's role | Yes |
| `GET` | `/api/workspaces/{workspace_id}/activity` | Workspaces | Get recent audit log activity in workspace | Yes |
| `GET` | `/api/workspaces/{workspace_id}/settings` | Workspaces | Get workspace configuration and feature flags | Yes |
| `PATCH` | `/api/workspaces/{workspace_id}/settings` | Workspaces | Update workspace configuration and feature flags | Yes |
| `GET` | `/api/tasks/` | Tasks | List workspace tasks with optional status/assignee filters | Yes |
| `POST` | `/api/tasks/` | Tasks | Create a new task with assignees | Yes |
| `PATCH` | `/api/tasks/{task_id}` | Tasks | Update task status, priority, or metadata | Yes |
| `DELETE` | `/api/tasks/{task_id}` | Tasks | Delete a task | Yes |
| `GET` | `/api/documents/` | Documents | List all documents belonging to a workspace | Yes |
| `POST` | `/api/documents/` | Documents | Create a blank rich-text document | Yes |
| `POST` | `/api/documents/upload` | Documents | Upload and parse document file into vector embeddings | Yes |
| `GET` | `/api/documents/{doc_id}` | Documents | Fetch full document content and metadata | Yes |
| `PATCH` | `/api/documents/{doc_id}` | Documents | Update document title or rich-text content | Yes |
| `DELETE` | `/api/documents/{doc_id}` | Documents | Delete a document and its embeddings | Yes |
| `POST` | `/api/ai/chat` | AI | Submit prompt to LangGraph ReAct agent | Yes |
| `GET` | `/api/ai/{workspace_id}/sessions` | AI | List AI chat conversation sessions | Yes |
| `POST` | `/api/ai/{workspace_id}/sessions` | AI | Create a new AI chat conversation session | Yes |
| `PATCH` | `/api/ai/{workspace_id}/sessions/{session_id}` | AI | Rename an AI chat conversation session | Yes |
| `DELETE` | `/api/ai/{workspace_id}/sessions/{session_id}` | AI | Delete an AI chat conversation session | Yes |
| `GET` | `/api/ai/{workspace_id}/sessions/{session_id}/messages` | AI | Fetch message history for a session | Yes |
| `GET` | `/api/ai/{workspace_id}/history` | AI | Fetch flat AI message history for workspace | Yes |
| `DELETE` | `/api/ai/{workspace_id}/history` | AI | Clear all AI chat messages for workspace | Yes |
| `GET` | `/api/chat/{workspace_id}/messages` | Chat | Fetch message history for a channel or DM | Yes |
| `POST` | `/api/chat/{workspace_id}/messages` | Chat | Send a message to a channel or recipient | Yes |
| `GET` | `/api/chat/{workspace_id}/inbox` | Chat | Get DM inbox overview with unread indicators | Yes |
| `GET` | `/api/flows/` | Flows | List all diagram flows in workspace | Yes |
| `POST` | `/api/flows/` | Flows | Create a new workflow canvas | Yes |
| `GET` | `/api/flows/{flow_id}` | Flows | Fetch complete flow including nodes and edges | Yes |
| `PUT` | `/api/flows/{flow_id}` | Flows | Update flow title and canvas viewport | Yes |
| `DELETE` | `/api/flows/{flow_id}` | Flows | Delete flow and associated canvas elements | Yes |
| `POST` | `/api/flows/{flow_id}/sync` | Flows | Synchronize updated nodes and edges in batch | Yes |
| `POST` | `/api/flows/{flow_id}/comments` | Flows | Add a spatial comment on the flow canvas | Yes |
| `POST` | `/api/flows/{flow_id}/versions` | Flows | Snapshot a version checkpoint of the flow canvas | Yes |
| `POST` | `/api/flows/{flow_id}/versions/{version_id}/restore` | Flows | Restore flow canvas from a past version snapshot | Yes |
| `POST` | `/api/flows/{flow_id}/ai-explain` | Flows | Analyze flow architecture using Google Gemini | Yes |
| `GET` | `/api/integrations/github/install-url` | GitHub | Get GitHub App installation redirect URL | Yes |
| `POST` | `/api/integrations/github/connect` | GitHub | Finalize connection of installed GitHub App | Yes |
| `GET` | `/api/integrations/github/status` | GitHub | Get current workspace GitHub connection status | Yes |
| `GET` | `/api/integrations/github/repositories` | GitHub | List tracked repositories in workspace | Yes |
| `POST` | `/api/integrations/github/repositories/sync` | GitHub | Trigger manual sync of GitHub repositories | Yes |
| `POST` | `/api/integrations/github/repositories/toggle` | GitHub | Enable or disable event sync for a repository | Yes |
| `POST` | `/api/integrations/github/sync-activity` | GitHub | Synchronize commit and PR activity | Yes |
| `GET` | `/api/github/since-last-seen` | GitHub | Retrieve missed commits/PRs since user last viewed | Yes |
| `GET` | `/api/tasks/{task_id}/github-links` | GitHub | Get linked PRs and commits for a task | Yes |
| `POST` | `/api/tasks/{task_id}/suggestions/{suggestion_id}/accept` | GitHub | Accept AI suggestion linking GitHub commit to task | Yes |
| `POST` | `/api/tasks/{task_id}/suggestions/{suggestion_id}/dismiss`| GitHub | Dismiss AI suggestion linking commit to task | Yes |
| `POST` | `/api/webhooks/github` | Webhooks | Ingest GitHub App webhook events | Verified |

---

### Authentication & Identity (`/api/auth`)

#### `POST /api/auth/register`
Creates a new user account with Argon2 password hashing.
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "email": "developer@orbit.local",
    "password": "StrongPassword123!",
    "name": "Jane Developer"
  }
  ```
- **Responses:**
  - `201 Created`:
    ```json
    {
      "id": "e5b8d2a1-4321-4def-a123-0987654321ab",
      "email": "developer@orbit.local",
      "name": "Jane Developer",
      "created_at": "2026-10-13T09:00:00Z"
    }
    ```
  - `400 Bad Request`: Email already registered.

#### `POST /api/auth/login`
Authenticates a user, issues a short-lived Bearer JWT access token, and sets an HTTP-only refresh token cookie.
- **Request Body:**
  ```json
  {
    "email": "developer@orbit.local",
    "password": "StrongPassword123!"
  }
  ```
- **Response Headers:** `Set-Cookie: refresh_token=eyJhbG...; HttpOnly; Path=/api/auth; SameSite=Lax`
- **Response JSON (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": "e5b8d2a1-4321-4def-a123-0987654321ab",
      "email": "developer@orbit.local",
      "name": "Jane Developer"
    }
  }
  ```
- **Error Codes:** `401 Unauthorized` for invalid credentials.

#### `POST /api/auth/refresh`
Validates the `refresh_token` HTTP-only cookie and returns a fresh access token.
- **Response JSON (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```
- **Error Codes:** `401 Unauthorized` if refresh token is absent, invalid, or expired.

#### `GET /api/auth/me`
Fetches the currently authenticated user profile.
- **Authentication:** `Bearer <access_token>`
- **Response JSON (`200 OK`):**
  ```json
  {
    "id": "e5b8d2a1-4321-4def-a123-0987654321ab",
    "email": "developer@orbit.local",
    "name": "Jane Developer",
    "avatar_url": null,
    "created_at": "2026-10-13T09:00:00Z"
  }
  ```

---

### Workspaces & Membership (`/api/workspaces`)

#### `GET /api/workspaces/`
Returns all workspaces the authenticated user belongs to.
- **Response JSON (`200 OK`):**
  ```json
  [
    {
      "id": "7a3f81e2-5678-4321-9876-abcdef012345",
      "name": "Acme Engineering",
      "slug": "acme-engineering",
      "role": "owner",
      "member_count": 8,
      "created_at": "2026-10-10T12:00:00Z"
    }
  ]
  ```

#### `POST /api/workspaces/`
Creates a new workspace. The creating user is automatically assigned the `owner` role.
- **Request Body:**
  ```json
  {
    "name": "Project Apollo",
    "slug": "project-apollo"
  }
  ```
- **Response JSON (`201 Created`):**
  ```json
  {
    "id": "9b1c7a4d-1234-5678-90ab-cdef12345678",
    "name": "Project Apollo",
    "slug": "project-apollo",
    "invite_code": "APOLLO-9X2",
    "role": "owner",
    "created_at": "2026-10-13T09:15:00Z"
  }
  ```

#### `POST /api/workspaces/join/{invite_code}`
Joins an existing workspace using a unique invite code.
- **Path Parameters:** `invite_code` (e.g., `APOLLO-9X2`)
- **Response JSON (`200 OK`):** Returns the joined workspace metadata.

---

### Tasks & Kanban Operations (`/api/tasks`)

#### `GET /api/tasks/`
Retrieves tasks belonging to the active workspace.
- **Query Parameters:**
  - `workspace_id` (UUID, required): Target workspace.
  - `status` (string, optional): Filter by `todo`, `in_progress`, `review`, `done`.
  - `priority` (string, optional): Filter by `low`, `medium`, `high`, `urgent`.
  - `assignee_id` (UUID, optional): Filter by assigned user.
- **Response JSON (`200 OK`):**
  ```json
  [
    {
      "id": "c1d2e3f4-5678-90ab-cdef-1234567890ab",
      "title": "Implement Resend Email Alerts",
      "description": "Connect LangGraph tools to send reminder emails",
      "status": "in_progress",
      "priority": "high",
      "due_date": "2026-10-20T18:00:00Z",
      "assignees": [
        {
          "id": "e5b8d2a1-4321-4def-a123-0987654321ab",
          "name": "Jane Developer",
          "email": "developer@orbit.local"
        }
      ],
      "created_at": "2026-10-12T14:00:00Z"
    }
  ]
  ```

#### `POST /api/tasks/`
Creates a new task.
- **Request Body:**
  ```json
  {
    "workspace_id": "7a3f81e2-5678-4321-9876-abcdef012345",
    "title": "Setup PostgreSQL Backup Cron",
    "description": "Configure pg_dump scheduled nightly backups",
    "status": "todo",
    "priority": "medium",
    "due_date": "2026-10-25T00:00:00Z",
    "assignee_ids": ["e5b8d2a1-4321-4def-a123-0987654321ab"]
  }
  ```
- **Response JSON (`201 Created`):** Returns the created task record.

#### `PATCH /api/tasks/{task_id}`
Updates an existing task's status, priority, or content.
- **Request Body:**
  ```json
  {
    "status": "done"
  }
  ```
- **Response JSON (`200 OK`):** Updated task record.

---

### Knowledge Base & Documents (`/api/documents`)

#### `POST /api/documents/upload`
Uploads a document file, parses text chunks, generates vector embeddings with Gemini, and saves them to pgvector.
- **Content-Type:** `multipart/form-data`
- **Form Fields:**
  - `workspace_id`: UUID
  - `file`: Binary file (`.pdf`, `.docx`, `.txt`, `.csv`, `.xlsx`)
- **Response JSON (`200 OK`):**
  ```json
  {
    "document_id": "d4e5f6a7-8901-2345-6789-012345abcdef",
    "filename": "System_Design_Specification.pdf",
    "file_type": "application/pdf",
    "chunks_indexed": 14,
    "status": "indexed"
  }
  ```

#### `GET /api/documents/`
Lists all documents belonging to a workspace.
- **Query Parameters:** `workspace_id` (UUID, required)
- **Response JSON (`200 OK`):** List of document summaries with author info and timestamps.

#### `PATCH /api/documents/{doc_id}`
Updates rich-text content for TipTap editor documents.
- **Request Body:**
  ```json
  {
    "title": "Architecture Blueprint",
    "content": "<h2>System Overview</h2><p>Orbit utilizes FastAPI and Next.js...</p>"
  }
  ```

---

### Agentic AI & Chat Sessions (`/api/ai`)

#### `POST /api/ai/chat`
Invokes the LangGraph ReAct Agent. The agent executes reasoning loops and calls tools.
- **Request Body:**
  ```json
  {
    "workspace_id": "7a3f81e2-5678-4321-9876-abcdef012345",
    "session_id": "f1a2b3c4-d5e6-7890-abcd-ef1234567890",
    "message": "Find all high-priority tasks in progress and list their assignees."
  }
  ```
- **Response JSON (`200 OK`):**
  ```json
  {
    "response": "Here are the high-priority tasks currently in progress:\n\n1. **Implement Resend Email Alerts** — Assigned to *Jane Developer*.",
    "tool_calls": [
      {
        "tool": "get_workspace_tasks",
        "arguments": { "status": "in_progress", "priority": "high" },
        "result_count": 1
      }
    ]
  }
  ```

#### `GET /api/ai/{workspace_id}/sessions`
Retrieves chat sessions for the workspace.
- **Response JSON (`200 OK`):** List of session objects containing `id`, `title`, and `updated_at`.

---

### Collaborative Flows & Workflows (`/api/flows`)

#### `POST /api/flows/{flow_id}/sync`
Batch synchronizes nodes, positions, and connections created in the ReactFlow canvas.
- **Request Body:**
  ```json
  {
    "nodes": [
      {
        "id": "node_1",
        "node_type": "serviceCard",
        "position_x": 250.0,
        "position_y": 120.0,
        "data": { "label": "FastAPI Gateway", "status": "active" }
      }
    ],
    "edges": [
      {
        "id": "edge_1_2",
        "source_node_id": "node_1",
        "target_node_id": "node_2",
        "label": "Proxies to"
      }
    ]
  }
  ```
- **Response JSON (`200 OK`):** `{"synced": true, "nodes_count": 1, "edges_count": 1}`

#### `POST /api/flows/{flow_id}/ai-explain`
Analyzes canvas architecture and provides an AI evaluation.
- **Request Body:** `{}`
- **Response JSON (`200 OK`):**
  ```json
  {
    "analysis": "### Workflow Architecture Analysis\nThis workflow diagrams an incoming API Gateway directing requests to a Redis caching layer before querying PostgreSQL..."
  }
  ```

---

### System Health (`/api/health`)

#### `GET /api/health`
Unauthenticated health probe. Checks database connectivity.
- **Response JSON (`200 OK`):**
  ```json
  {
    "status": "healthy",
    "database": "connected"
  }
  ```

---

## Installation and Local Setup

### Prerequisites

Ensure the following tools are installed:
- **Node.js**: `18.18.0` or higher (Node 20 LTS recommended)
- **Python**: `3.11` or higher
- **PostgreSQL**: `16` (or access to a Supabase PostgreSQL instance with pgvector)
- **Redis**: `7.x` (optional for standalone local dev; included in Docker)
- **Git**

---

### Quickstart with Docker Compose

Orbit includes a multi-container Docker configuration for PostgreSQL, Redis, FastAPI, and Next.js.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/avadhesh11/Design-Project.git
   cd Design-Project
   ```

2. **Configure environment variables:**
   Create `.env` in the root or copy `.env.example`:
   ```bash
   cp .env.example .env
   ```

3. **Start all services:**
   ```bash
   docker compose up --build
   ```

4. **Access the application:**
   - **Frontend Web UI:** [http://localhost:3000](http://localhost:3000)
   - **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **PostgreSQL:** `localhost:5432`
   - **Redis:** `localhost:6379`

---

### Manual Local Development Setup

To run frontend and backend independently in local development environments:

#### 1. Backend Setup (FastAPI)

```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv

# Windows (PowerShell)
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
```

Configure your `backend/.env`:
```env
DATABASE_URL=postgresql://orbit:orbit_secret@localhost:5432/orbit_db
JWT_SECRET=super_secret_jwt_random_key_change_in_production
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
RESEND_API_KEY=re_your_resend_api_key
CORS_ORIGINS=["http://localhost:3000"]
```

Run database migrations and start the server:
```bash
# Run database migrations
alembic upgrade head

# Start FastAPI development server with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup (Next.js)

```bash
cd ../frontend

# Install dependencies
npm install

# Create local environment file
cp .env.example .env.local
```

Configure `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

Start the frontend development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Environment Variables and Configuration

### Backend Environment Configuration (`backend/.env`)

| Variable Name | Required | Default / Format | Purpose |
|---|:---:|---|---|
| `DATABASE_URL` | **Yes** | `postgresql://user:pass@host:5432/db` | Connection string for PostgreSQL database |
| `JWT_SECRET` | **Yes** | Hexadecimal string | Signing key for symmetric HS256 JWT tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifespan in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token cookie lifespan in days |
| `GOOGLE_GEMINI_API_KEY` | **Yes** | `AIzaSy...` | Google AI Studio key for Gemini 2.5 Flash and Embeddings |
| `SUPABASE_URL` | **Yes** | `https://xyz.supabase.co` | Supabase project URL for Vector RPC and Realtime |
| `SUPABASE_SERVICE_ROLE_KEY`| **Yes** | Secret JWT | Bypasses RLS to insert embeddings and manage storage |
| `RESEND_API_KEY` | No | `re_...` | API key for Resend transactional email dispatches |
| `RESEND_FROM_EMAIL` | No | `notifications@yourdomain.com`| Sender email address for task and announcement alerts |
| `GITHUB_APP_ID` | No | Numeric string | GitHub App ID for workspace integration |
| `GITHUB_CLIENT_ID` | No | String | GitHub App OAuth Client ID |
| `GITHUB_CLIENT_SECRET` | No | String | GitHub App OAuth Client Secret |
| `GITHUB_WEBHOOK_SECRET` | No | String | Secret used to verify HMAC signatures on incoming webhooks |
| `GITHUB_PRIVATE_KEY_PATH` | No | Path to `.pem` | GitHub App private key for installation token exchange |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL for caching and rate limiting |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | JSON array of allowed origin URLs for CORS |

### Frontend Environment Configuration (`frontend/.env.local`)

| Variable Name | Required | Default / Format | Purpose |
|---|:---:|---|---|
| `NEXT_PUBLIC_API_URL` | **Yes** | `http://localhost:8000/api` | Base URL for FastAPI backend endpoints |
| `NEXT_PUBLIC_SUPABASE_URL` | **Yes** | `https://xyz.supabase.co` | Public Supabase URL for Realtime WebSocket client |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Yes** | `eyJ...` | Public Anonymous key for client-side Supabase subscriptions |

---

## Engineering Decisions and Implementation Patterns

### 1. Dual-Token Authentication with HTTP-Only Cookies
Access tokens are kept short-lived (30 minutes) and stored in client memory (Zustand store), preventing token exfiltration via Cross-Site Scripting (XSS). Long-lived refresh tokens are stored in `HttpOnly`, `SameSite=Lax` cookies, protected from JavaScript access. An Axios response interceptor (`frontend/lib/api.ts`) automatically intercepts `401 Unauthorized` responses and issues a silent `POST /api/auth/refresh` before retrying failed requests.

### 2. Autonomous Action ReAct Loop (LangGraph)
Rather than simple single-prompt completions, Orbit implements a cyclic state graph in `backend/app/agents/agent.py`. The agent receives user intent, queries the tools catalogue, evaluates return values, and executes secondary actions if necessary.

### 3. Multi-Format Chunking with High-Dimensional Vectors
Document ingestion supports multiple enterprise file formats:
- Multi-page PDF text extraction via `pdfplumber`
- Document structure parsing via `python-docx`
- Spreadsheet table serialization via `pandas` and `openpyxl`
Extracted text is split into chunks of 1000 characters with a 50-character overlap to retain context across boundaries. Embeddings are generated via Google's `gemini-embedding-001` and queried in PostgreSQL using the cosine similarity operator `<=>`.

### 4. Interactive Flow Canvas with Optimistic State Synchronization
The workflow editor at `/dashboard/flows` uses `@xyflow/react`. Node movements and edge connections update local React state immediately, with periodic debounced batch updates sent to `POST /api/flows/{flow_id}/sync`. Snapshots can be saved via `POST /api/flows/{flow_id}/versions`, enabling instant version rollbacks.

---

## Testing and Quality Assurance

### Backend Tests
Backend unit and integration tests are configured with `pytest` and `httpx`:

```bash
cd backend
# Run test suite
pytest -v
```

Test coverage focuses on:
- Password hashing and JWT generation/validation (`tests/test_auth.py`)
- Workspace isolation and membership permissions (`tests/test_workspaces.py`)
- Document parser extraction accuracy (`tests/test_rag.py`)

### Frontend Type-Checking and Linting
```bash
cd frontend
# TypeScript type check
npx tsc --noEmit

# Next.js ESLint validation
npm run lint
```

---

## Known Limitations and Production Considerations

1. **GitHub App Private Key Configuration**:
   - Webhook reception and database models for GitHub issues, commits, and PRs are fully implemented.
   - However, background GitHub App token generation requires a valid App Private Key (`.pem`) file. Without this key, live GitHub App token exchanges will return configuration errors.
2. **Flow Engine Execution Runtime**:
   - The ReactFlow canvas allows visual node layout, edge connection, version snapshotting, and Gemini-powered architecture explanations.
   - Nodes represent visual architectural blocks; automated background execution of custom workflow jobs is not yet implemented.
3. **Realtime Chat Persistence vs. WebSocket Fallback**:
   - Realtime chat broadcasting uses the Supabase Realtime client. Messages are saved to PostgreSQL via `POST /api/chat/{workspace_id}/messages`. Environments without Supabase Realtime credentials fall back to standard HTTP polling.

---

## Future Roadmap

The following enhancements are planned for future releases:

- [ ] **Background Execution Engine for Flows**: Celery/Temporal workers to run backend jobs defined in canvas nodes.
- [ ] **Granular Vector Ingestion Filters**: Document indexing filtered by workspace teams and permission tags.
- [ ] **Automated GitHub PR Summaries**: LLM-generated summaries and suggested task links for incoming pull requests.
- [ ] **Self-Hosted Realtime Server**: Native WebSocket gateway option to run without Supabase dependencies.
- [ ] **Voice Input for Agent**: Speech-to-text integration for AI assistant voice queries.

---

## Contributing

Contributions to Orbit are welcome!

1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "feat: add your feature description"
   ```
4. Push to your branch:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a Pull Request on GitHub.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
