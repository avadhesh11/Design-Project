"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { useWorkspaceStore } from "@/store/workspaceStore";
import api from "@/lib/api";
import { DashboardSkeleton } from "@/components/app/LoadingScreen";
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
  Settings,
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
            className="orbit-card p-4 text-left hover:border-orbit-border2 hover:bg-surface2 transition-all group"
          >
            <div className={`${iconColor} mb-3`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="font-display font-bold text-2xl text-orbit-text leading-none mb-1">
              {value}
            </div>
            <div className="text-[11px] text-orbit-muted">{label}</div>
          </button>
        ))}
      </div>

      {/* ── Two column grid ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* ── Recent Documents ──────────────────────────────────── */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-orbit-text uppercase tracking-wider">
              Recent Documents
            </h2>
            <button
              onClick={() => router.push("/dashboard/documents")}
              className="text-[11px] text-orbit-muted hover:text-orbit-text transition-colors flex items-center gap-1"
            >
              All docs <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {recentDocs.length === 0 ? (
            <div className="orbit-card p-6 flex flex-col items-center text-center gap-3">
              <FileText className="w-6 h-6 text-orbit-muted/50" />
              <div>
                <p className="text-sm text-orbit-text">No documents yet</p>
                <p className="text-[11px] text-orbit-muted mt-0.5">Create a document to get started</p>
              </div>
              <button
                onClick={() => router.push("/dashboard/documents")}
                className="orbit-btn-primary text-xs"
              >
                <Plus className="w-3.5 h-3.5" /> New document
              </button>
            </div>
          ) : (
            <div className="orbit-card overflow-hidden divide-y divide-orbit-border">
              {recentDocs.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => router.push(`/dashboard/documents/${doc.id}`)}
                  className="w-full flex items-center gap-3 px-3.5 py-2.5 hover:bg-surface2 transition-colors text-left group"
                >
                  <FileText className="w-3.5 h-3.5 text-orbit-muted flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-orbit-text truncate group-hover:text-accent transition-colors">
                      {doc.title}
                    </div>
                    <div className="text-[10px] text-orbit-muted font-mono">
                      {formatRelative(doc.updated_at)}
                    </div>
                  </div>
                  <ArrowRight className="w-3 h-3 text-orbit-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── Active Tasks ──────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-orbit-text uppercase tracking-wider">
              Active Tasks
            </h2>
            <button
              onClick={() => router.push("/dashboard/tasks")}
              className="text-[11px] text-orbit-muted hover:text-orbit-text transition-colors flex items-center gap-1"
            >
              All tasks <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {activeTasks.length === 0 ? (
            <div className="orbit-card p-6 flex flex-col items-center text-center gap-3">
              <CheckSquare className="w-6 h-6 text-orbit-muted/50" />
              <div>
                <p className="text-sm text-orbit-text">No active tasks</p>
                <p className="text-[11px] text-orbit-muted mt-0.5">All caught up, or create a new task</p>
              </div>
              <button
                onClick={() => router.push("/dashboard/tasks")}
                className="orbit-btn-primary text-xs"
              >
                <Plus className="w-3.5 h-3.5" /> New task
              </button>
            </div>
          ) : (
            <div className="orbit-card overflow-hidden divide-y divide-orbit-border">
              {activeTasks.map((task) => {
                const statusIcon =
                  task.status === "in_progress" ? (
                    <Timer className="w-3.5 h-3.5 text-blue-400" />
                  ) : (
                    <Circle className="w-3.5 h-3.5 text-orbit-muted" />
                  );
                const priColor =
                  task.priority === "high"
                    ? "text-red-400"
                    : task.priority === "medium"
                    ? "text-yellow-500"
                    : "text-orbit-muted";
                return (
                  <button
                    key={task.id}
                    onClick={() => router.push("/dashboard/tasks")}
                    className="w-full flex items-center gap-3 px-3.5 py-2.5 hover:bg-surface2 transition-colors text-left group"
                  >
                    <div className="flex-shrink-0">{statusIcon}</div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-orbit-text truncate">{task.title}</div>
                      {task.due_date && (
                        <div className="text-[10px] text-orbit-muted font-mono">
                          Due {formatRelative(task.due_date)}
                        </div>
                      )}
                    </div>
                    <span className={`text-[10px] font-mono uppercase ${priColor} flex-shrink-0`}>
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
          className="orbit-card p-4 flex items-center gap-3.5 hover:border-orbit-border2 hover:bg-surface2 transition-all cursor-pointer group"
          onClick={() => router.push("/dashboard/ai")}
        >
          <div className="w-9 h-9 rounded-lg bg-accent-dim border border-accent-border flex items-center justify-center flex-shrink-0">
            <Bot className="w-4 h-4 text-accent" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-orbit-text group-hover:text-accent transition-colors">AI Assistant</div>
            <div className="text-[11px] text-orbit-muted truncate">
              Query docs & automated actions
            </div>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-orbit-muted group-hover:text-orbit-text transition-colors flex-shrink-0" />
        </div>

        <div
          className="orbit-card p-4 flex items-center gap-3.5 hover:border-orbit-border2 hover:bg-surface2 transition-all cursor-pointer group"
          onClick={() => router.push("/dashboard/chat")}
        >
          <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
            <MessageSquare className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-orbit-text group-hover:text-blue-400 transition-colors">Realtime Chat</div>
            <div className="text-[11px] text-orbit-muted truncate">
              Channels & Direct Messages
            </div>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-orbit-muted group-hover:text-orbit-text transition-colors flex-shrink-0" />
        </div>

        <div
          className="orbit-card p-4 flex items-center gap-3.5 hover:border-orbit-border2 hover:bg-surface2 transition-all cursor-pointer group"
          onClick={() => router.push("/dashboard/flows")}
        >
          <div className="w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center flex-shrink-0">
            <Workflow className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-orbit-text group-hover:text-purple-400 transition-colors">Visual Flows</div>
            <div className="text-[11px] text-orbit-muted truncate">
              Canvas orchestration & CI
            </div>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-orbit-muted group-hover:text-orbit-text transition-colors flex-shrink-0" />
        </div>

        <div
          className="orbit-card p-4 flex items-center gap-3.5 hover:border-orbit-border2 hover:bg-surface2 transition-all cursor-pointer group"
          onClick={() => router.push("/dashboard/integrations")}
        >
          <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
            <GitBranch className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-orbit-text group-hover:text-emerald-400 transition-colors">Integrations</div>
            <div className="text-[11px] text-orbit-muted truncate">
              GitHub activity & webhooks
            </div>
          </div>
          <ArrowRight className="w-3.5 h-3.5 text-orbit-muted group-hover:text-orbit-text transition-colors flex-shrink-0" />
        </div>
      </div>

    </div>
  );
}