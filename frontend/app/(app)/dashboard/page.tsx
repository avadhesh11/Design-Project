"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { useWorkspaceStore } from "@/store/workspaceStore";
import api from "@/lib/api";
import { DashboardSkeleton } from "@/components/app/LoadingScreen";
import { WhenYouWereAway } from "@/components/app/WhenYouWereAway";
import { Document, Task } from "@/types";
import { formatRelative } from "@/lib/utils";
import {
  FileText,
  CheckSquare,
  Bot,
  Plus,
  ArrowRight,
  Circle,
  Timer,
  CheckCircle2,
  MessageSquare,
  Workflow,
  GitBranch,
} from "lucide-react";

const greeting = () => {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
};

const dateLabel = new Date().toLocaleDateString("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
});

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { currentWorkspace } = useWorkspaceStore();

  const { data: docs = [], isLoading: docsLoading } = useQuery<Document[]>({
    queryKey: ["documents", currentWorkspace?.id],
    queryFn: () => api.get(`/documents/?workspace_id=${currentWorkspace?.id}`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  const { data: tasks = [], isLoading: tasksLoading } = useQuery<Task[]>({
    queryKey: ["tasks", currentWorkspace?.id],
    queryFn: () => api.get(`/tasks/?workspace_id=${currentWorkspace?.id}`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  const docsList = Array.isArray(docs) ? docs : [];
  const tasksList = Array.isArray(tasks) ? tasks : [];

  const todoTasks = tasksList.filter((t) => t.status === "todo");
  const inProgressTasks = tasksList.filter((t) => t.status === "in_progress");
  const doneTasks = tasksList.filter((t) => t.status === "done");

  const recentDocs = [...docsList]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 6);

  const activeTasks = [...inProgressTasks, ...todoTasks].slice(0, 6);

  const isLoading = (docsLoading && docs.length === 0) || (tasksLoading && tasks.length === 0);
  if (isLoading) return <DashboardSkeleton />;

  const stats = [
    {
      label: "Documents",
      value: docsList.length,
      icon: FileText,
      href: "/dashboard/documents",
      iconColor: "text-accent",
    },
    {
      label: "To do",
      value: todoTasks.length,
      icon: Circle,
      href: "/dashboard/tasks",
      iconColor: "text-orbit-muted",
    },
    {
      label: "In progress",
      value: inProgressTasks.length,
      icon: Timer,
      href: "/dashboard/tasks",
      iconColor: "text-blue-400",
    },
    {
      label: "Completed",
      value: doneTasks.length,
      icon: CheckCircle2,
      href: "/dashboard/tasks",
      iconColor: "text-accent",
    },
  ];

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8 animate-fade-in">

      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="space-y-1 animate-fade-up">
        <div className="text-[10px] font-mono tracking-widest text-orbit-muted uppercase">
          {dateLabel}
        </div>
        <h1 className="font-display font-bold text-2xl text-orbit-text tracking-tight">
          {greeting()}, {user?.email?.split("@")[0]}
        </h1>
        <p className="text-sm text-orbit-muted">
          {currentWorkspace?.name} workspace
        </p>
      </div>

      {/* ── Stats ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {stats.map(({ label, value, icon: Icon, href, iconColor }) => (
          <button
            key={label}
            onClick={() => router.push(href)}
            className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-gradient-to-b from-white/[0.03] to-white/[0.01] p-4 text-left hover:border-white/[0.18] hover:bg-white/[0.04] hover:shadow-[0_4px_24px_rgba(0,0,0,0.4)] backdrop-blur-md transition-all group"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.04] border border-white/[0.06] group-hover:scale-105 transition-transform">
                <Icon className={`w-4 h-4 ${iconColor}`} />
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
            </div>
            <div className="font-display font-bold text-2xl text-white leading-none mb-1 tracking-tight">
              {value}
            </div>
            <div className="text-[11px] text-zinc-400 font-medium">{label}</div>
          </button>
        ))}
      </div>

      {/* ── When You Were Away Intelligence ────────────────────────── */}
      {currentWorkspace?.id && (
        <WhenYouWereAway workspaceId={currentWorkspace.id} />
      )}

      {/* ── Two column grid ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* ── Recent Documents ──────────────────────────────────── */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
              Recent Documents
            </h2>
            <button
              onClick={() => router.push("/dashboard/documents")}
              className="text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1"
            >
              All docs <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {recentDocs.length === 0 ? (
            <div className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] p-6 flex flex-col items-center text-center gap-3 backdrop-blur-md">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <FileText className="w-5 h-5 text-zinc-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">No documents yet</p>
                <p className="text-[11px] text-zinc-400 mt-0.5">Create a document to get started</p>
              </div>
              <button
                onClick={() => router.push("/dashboard/documents")}
                className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/15 hover:bg-emerald-500/25 px-3.5 py-1.5 text-xs font-medium text-emerald-300 transition-all shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" /> New document
              </button>
            </div>
          ) : (
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden divide-y divide-white/[0.06] backdrop-blur-md">
              {recentDocs.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => router.push(`/dashboard/documents/${doc.id}`)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/[0.04] transition-colors text-left group"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.03] border border-white/[0.06] text-zinc-400 group-hover:text-emerald-400 group-hover:border-emerald-500/30 transition-colors flex-shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-zinc-200 truncate group-hover:text-emerald-300 transition-colors">
                      {doc.title}
                    </div>
                    <div className="text-[10px] text-zinc-500 font-mono">
                      {formatRelative(doc.updated_at)}
                    </div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── Active Tasks ──────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
              Active Tasks
            </h2>
            <button
              onClick={() => router.push("/dashboard/tasks")}
              className="text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1"
            >
              All tasks <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {activeTasks.length === 0 ? (
            <div className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] p-6 flex flex-col items-center text-center gap-3 backdrop-blur-md">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <CheckSquare className="w-5 h-5 text-zinc-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">No active tasks</p>
                <p className="text-[11px] text-zinc-400 mt-0.5">All caught up, or create a new task</p>
              </div>
              <button
                onClick={() => router.push("/dashboard/tasks")}
                className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/15 hover:bg-emerald-500/25 px-3.5 py-1.5 text-xs font-medium text-emerald-300 transition-all shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" /> New task
              </button>
            </div>
          ) : (
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden divide-y divide-white/[0.06] backdrop-blur-md">
              {activeTasks.map((task) => {
                const statusIcon =
                  task.status === "in_progress" ? (
                    <Timer className="w-3.5 h-3.5 text-blue-400" />
                  ) : (
                    <Circle className="w-3.5 h-3.5 text-zinc-500" />
                  );
                const priColor =
                  task.priority === "high"
                    ? "text-red-400 border border-red-500/30 bg-red-500/10"
                    : task.priority === "medium"
                    ? "text-yellow-400 border border-yellow-500/30 bg-yellow-500/10"
                    : "text-zinc-400 border border-white/[0.08] bg-white/[0.04]";
                return (
                  <button
                    key={task.id}
                    onClick={() => router.push("/dashboard/tasks")}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/[0.04] transition-colors text-left group"
                  >
                    <div className="flex-shrink-0">{statusIcon}</div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-zinc-200 truncate group-hover:text-emerald-300 transition-colors">{task.title}</div>
                      {task.due_date && (
                        <div className="text-[10px] text-zinc-500 font-mono">
                          Due {formatRelative(task.due_date)}
                        </div>
                      )}
                    </div>
                    <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-md ${priColor} flex-shrink-0`}>
                      {task.priority}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Quick Feature Access ─────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 flex items-center gap-3.5 hover:border-emerald-500/40 hover:bg-white/[0.05] hover:shadow-[0_4px_24px_rgba(0,0,0,0.4)] backdrop-blur-md transition-all cursor-pointer group"
          onClick={() => router.push("/dashboard/ai")}
        >
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
            <Bot className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-zinc-200 group-hover:text-emerald-300 transition-colors">AI Assistant</div>
            <div className="text-[11px] text-zinc-400 truncate">
              Query docs & automated actions
            </div>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
        </div>

        <div
          className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 flex items-center gap-3.5 hover:border-blue-500/40 hover:bg-white/[0.05] hover:shadow-[0_4px_24px_rgba(0,0,0,0.4)] backdrop-blur-md transition-all cursor-pointer group"
          onClick={() => router.push("/dashboard/chat")}
        >
          <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
            <MessageSquare className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-zinc-200 group-hover:text-blue-300 transition-colors">Realtime Chat</div>
            <div className="text-[11px] text-zinc-400 truncate">
              Channels & Direct Messages
            </div>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
        </div>

        <div
          className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 flex items-center gap-3.5 hover:border-purple-500/40 hover:bg-white/[0.05] hover:shadow-[0_4px_24px_rgba(0,0,0,0.4)] backdrop-blur-md transition-all cursor-pointer group"
          onClick={() => router.push("/dashboard/flows")}
        >
          <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
            <Workflow className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-zinc-200 group-hover:text-purple-300 transition-colors">Visual Flows</div>
            <div className="text-[11px] text-zinc-400 truncate">
              Canvas orchestration & CI
            </div>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
        </div>

        <div
          className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 flex items-center gap-3.5 hover:border-emerald-500/40 hover:bg-white/[0.05] hover:shadow-[0_4px_24px_rgba(0,0,0,0.4)] backdrop-blur-md transition-all cursor-pointer group"
          onClick={() => router.push("/dashboard/integrations")}
        >
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
            <GitBranch className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-zinc-200 group-hover:text-emerald-300 transition-colors">Integrations</div>
            <div className="text-[11px] text-zinc-400 truncate">
              GitHub activity & webhooks
            </div>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
        </div>
      </div>

    </div>
  );
}