# Orbit AI — Frontend

## Setup

1. Install dependencies:
```bash
npm install
```

2. Fill in your environment variables in `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_SUPABASE_URL=https://[your-project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

3. Run development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🛠️ Technology Stack
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v3, `tailwindcss-animate`
- **Canvas / Workflows**: `@xyflow/react` (React Flow), `html-to-image`
- **State Management**: Zustand (auth session & active workspace state)
- **Server State & Data Fetching**: TanStack Query v5, Axios (with automatic cookie refresh interceptor)
- **Real-Time WebSockets**: Supabase Realtime JS Client
- **Rich Document Editor**: TipTap (StarterKit, CharacterCount, Placeholder)
- **Icons**: Lucide React

---

## 🧭 Pages & Routes
- `/` — Landing page
- `/login` — Sign in (Email/Password & GitHub OAuth)
- `/register` — Account creation with Argon2 backend hashing
- `/status` — System health & backend service operational status
- `/dashboard` — Main workspace overview and real-time activity feed
- `/dashboard/documents` — Workspace document list & multi-format upload (RAG indexing)
- `/dashboard/documents/[id]` — Rich TipTap document editor
- `/dashboard/chat` — Real-time team chat & isolated direct messaging (DMs)
- `/dashboard/tasks` — Drag-and-drop Kanban task board with multi-assignees
- `/dashboard/ai` — LangGraph ReAct Agentic AI assistant with multi-session history
- `/dashboard/flows` — Orbit Flow collaborative node-based workflow & flowchart canvas
- `/dashboard/integrations` — GitHub App connection, repo monitoring, and webhook events
- `/dashboard/settings` — Workspace administration, invite codes, role management & AI quotas
