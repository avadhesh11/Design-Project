"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useAuthStore } from "@/store/authStore";
import { Task, WorkspaceMemberDetail, WorkspaceSettings } from "@/types";
import { Spinner } from "@/components/app/Spinner";
import { TasksSkeleton } from "@/components/app/LoadingScreen";
import { TaskCommitLinkModal } from "@/components/app/TaskCommitLinkModal";

import {
  Plus,
  X,
  GripVertical,
  Clock,
  Mail,
  Users,
  Check,
  ShieldCheck,
  GitCommit,
  ExternalLink,
  HelpCircle,
} from "lucide-react";
import { formatDate, formatRelative } from "@/lib/utils";

const COLUMNS = [
  { id: "todo", label: "Todo", dotColor: "#6b6b80" },
  { id: "in_progress", label: "In Progress", dotColor: "#60a5fa" },
  { id: "done", label: "Done", dotColor: "#22c55e" },
] as const;

function TaskCard({
  task,
  onMove,
  onDelete,
  onDragStart,
  onDragEnd,
  isDragging,
  isAdmin,
  onOpenCommitModal,
}: {
  task: Task;
  onMove: (task: Task, status: string) => void;
  onDelete: (id: string) => void;
  onDragStart: (e: React.DragEvent, task: Task) => void;
  onDragEnd: (e: React.DragEvent) => void;
  isDragging: boolean;
  isAdmin: boolean;
  onOpenCommitModal: (task: Task) => void;
}) {
  const priClass =
    { low: "badge-low", medium: "badge-medium", high: "badge-high" }[task.priority] || "badge-low";

  const assigneeEmails = task.assignee_emails?.length
    ? task.assignee_emails
    : task.assignee_email
    ? [task.assignee_email]
    : [];

  // Determine primary linked commit
  const primaryLink = task.github_links?.find((l) => l.commit_id != null && l.status !== "dismissed");
  const linkedCommit = primaryLink?.commit || task.primary_commit;
  const isVerifiedInRepo = primaryLink?.verification_status === "verified_in_repo";

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, task)}
      onDragEnd={onDragEnd}
      className={`group relative p-3 border rounded-lg bg-surface transition-all cursor-grab active:cursor-grabbing select-none ${
        isDragging
          ? "opacity-40 scale-95 border-dashed border-accent"
          : "border-orbit-border hover:border-orbit-border2"
      }`}
    >
      {/* Title row */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <GripVertical className="w-3 h-3 text-orbit-muted/40 group-hover:text-orbit-muted transition-colors flex-shrink-0" />
          <div className="text-xs font-medium leading-snug text-orbit-text truncate">{task.title}</div>
        </div>
        {isAdmin && (
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(task.id); }}
            className="opacity-0 group-hover:opacity-100 text-orbit-muted hover:text-red-500 p-0.5 rounded transition-all flex-shrink-0"
            title="Delete task"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      {task.description && (
        <div className="text-[11px] text-orbit-muted mb-2.5 line-clamp-2 leading-relaxed pl-4">
          {task.description}
        </div>
      )}

      {/* ── Linked Commit Evidence Banner (if present) ──────────────── */}
      {linkedCommit ? (
        <div className="mb-2.5 ml-4 p-2 rounded-md bg-surface2/80 border border-orbit-border/80 text-[11px] space-y-1">
          <div className="flex items-center justify-between gap-1.5">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="flex items-center gap-1 font-mono text-[10px] font-bold text-accent bg-accent/10 border border-accent/20 px-1.5 py-0.2 rounded">
                <GitCommit className="w-2.5 h-2.5" />
                {linkedCommit.sha.slice(0, 7)}
              </span>
              {isVerifiedInRepo ? (
                <span
                  className="flex items-center gap-0.5 text-[9px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1 py-0.2 rounded"
                  title="Commit verified against repository. Note: Confirms code delivery; independent correctness verification recommended."
                >
                  <ShieldCheck className="w-2.5 h-2.5" />
                  Verified in Repo
                </span>
              ) : (
                <span
                  className="text-[9px] font-mono text-blue-400 bg-blue-500/10 border border-blue-500/20 px-1 py-0.2 rounded"
                  title="Manual commit link recorded."
                >
                  Linked
                </span>
              )}
            </div>

            {linkedCommit.url && (
              <a
                href={linkedCommit.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-orbit-muted hover:text-accent p-0.5 transition-colors"
                title="View Commit on GitHub"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>

          <div className="text-[10px] text-orbit-text truncate font-normal">
            &quot;{linkedCommit.message}&quot;
          </div>

          <div className="flex items-center justify-between text-[9px] font-mono text-orbit-muted">
            <span>by @{linkedCommit.author_login || "dev"}</span>
            <span>
              {linkedCommit.committed_at && formatRelative(linkedCommit.committed_at)}
            </span>
          </div>
        </div>
      ) : task.no_commit_reason ? (
        <div className="mb-2.5 ml-4 p-1.5 rounded-md bg-yellow-500/5 border border-yellow-500/20 text-[10px] text-orbit-muted flex items-start gap-1.5">
          <HelpCircle className="w-3 h-3 text-yellow-400/80 flex-shrink-0 mt-0.5" />
          <span className="line-clamp-1">
            <strong className="text-yellow-400/90 font-medium">No commit:</strong> {task.no_commit_reason}
          </span>
        </div>
      ) : null}

      {/* Meta row */}
      <div className="flex items-center justify-between pl-4 flex-wrap gap-1.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={`${priClass}`}>{task.priority}</span>

          {task.task_type && task.task_type !== "feature" && (
            <span className="px-1.5 py-0.5 rounded bg-surface2 border border-orbit-border text-[9px] font-mono uppercase text-orbit-muted">
              {task.task_type}
            </span>
          )}

          {task.requires_commit && (
            <span
              className="flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-[9px] font-mono text-red-400"
              title="Commit evidence enforced for this task"
            >
              <GitCommit className="w-2.5 h-2.5" />
              Required
            </span>
          )}

          {assigneeEmails.length > 0 ? (
            <span
              className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface2 border border-orbit-border text-[10px] text-orbit-muted font-mono"
              title={`Assigned to:\n${assigneeEmails.join("\n")}`}
            >
              <Users className="w-2.5 h-2.5" />
              @{assigneeEmails[0].split("@")[0]}
              {assigneeEmails.length > 1 && (
                <span className="text-[9px] font-bold">+{assigneeEmails.length - 1}</span>
              )}
            </span>
          ) : (
            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface2 border border-orbit-border text-[10px] text-orbit-muted font-mono">
              <Users className="w-2.5 h-2.5" /> All
            </span>
          )}
        </div>

        {task.due_date && (
          <span className="text-[10px] text-orbit-muted font-mono flex items-center gap-0.5">
            <Clock className="w-2.5 h-2.5" />
            {formatDate(task.due_date)}
          </span>
        )}
      </div>

      {/* Quick move & Commit actions */}
      <div className="flex items-center justify-between gap-1 mt-2 pt-2 border-t border-orbit-border opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="flex gap-1">
          {task.status === "todo" && (
            <button
              onClick={() => onMove(task, "in_progress")}
              className="text-[10px] px-2 py-0.5 rounded border border-orbit-border text-orbit-muted hover:border-blue-400 hover:text-blue-400 transition-colors font-mono"
            >
              → In Progress
            </button>
          )}
          {task.status === "in_progress" && (
            <button
              onClick={() => onMove(task, "done")}
              className="text-[10px] px-2 py-0.5 rounded border border-orbit-border text-orbit-muted hover:border-accent hover:text-accent transition-colors font-mono font-medium"
            >
              ✓ Done
            </button>
          )}
          {task.status === "done" && (
            <button
              onClick={() => onMove(task, "in_progress")}
              className="text-[10px] px-2 py-0.5 rounded border border-orbit-border text-orbit-muted hover:border-orbit-border2 hover:text-orbit-text transition-colors font-mono"
            >
              Reopen
            </button>
          )}
        </div>

        {/* Link / Edit Commit Evidence */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onOpenCommitModal(task);
          }}
          className="text-[10px] px-2 py-0.5 rounded border border-orbit-border text-orbit-muted hover:border-accent hover:text-accent transition-colors font-mono flex items-center gap-1"
          title={linkedCommit ? "Manage linked commit" : "Link commit evidence"}
        >
          <GitCommit className="w-2.5 h-2.5" />
          {linkedCommit ? "Evidence" : "+ Commit"}
        </button>
      </div>
    </div>
  );
}

export default function TasksPage() {
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const { currentWorkspace } = useWorkspaceStore();

  const [showModal, setShowModal] = useState(false);
  const [taskForCommitModal, setTaskForCommitModal] = useState<{
    task: Task;
    isCompletionPrompt: boolean;
  } | null>(null);

  const [form, setForm] = useState<{
    title: string;
    description: string;
    priority: "low" | "medium" | "high";
    task_type: "feature" | "bug" | "chore" | "design" | "docs" | "other";
    requires_commit: boolean;
    due_date: string;
    assigned_to_ids: string[];
    notify_assignee: boolean;
  }>({
    title: "",
    description: "",
    priority: "medium",
    task_type: "feature",
    requires_commit: false,
    due_date: "",
    assigned_to_ids: [],
    notify_assignee: false,
  });

  const [draggingTaskId, setDraggingTaskId] = useState<string | null>(null);
  const [dragOverColumnId, setDragOverColumnId] = useState<string | null>(null);

  const { data: settings } = useQuery<WorkspaceSettings>({
    queryKey: ["workspace-settings", currentWorkspace?.id],
    queryFn: () => api.get(`/workspaces/${currentWorkspace?.id}/settings`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  const isAdmin =
    settings?.is_admin ||
    (!!currentWorkspace?.owner_id && !!user?.id && currentWorkspace.owner_id === user.id);

  const { data: members = [] } = useQuery<WorkspaceMemberDetail[]>({
    queryKey: ["workspace-members", currentWorkspace?.id],
    queryFn: () => api.get(`/workspaces/${currentWorkspace?.id}/members`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  const { data: tasks = [], isLoading } = useQuery<Task[]>({
    queryKey: ["tasks", currentWorkspace?.id],
    queryFn: () => api.get(`/tasks/?workspace_id=${currentWorkspace?.id}`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.post("/tasks/", {
        title: form.title,
        description: form.description || undefined,
        priority: form.priority,
        task_type: form.task_type,
        requires_commit: form.requires_commit,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : undefined,
        assigned_to_ids: form.assigned_to_ids.length > 0 ? form.assigned_to_ids : [],
        assigned_to: form.assigned_to_ids.length > 0 ? form.assigned_to_ids[0] : null,
        notify_assignee: form.notify_assignee,
        workspace_id: currentWorkspace?.id,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", currentWorkspace?.id] });
      qc.invalidateQueries({ queryKey: ["workspace-activity", currentWorkspace?.id] });
      qc.invalidateQueries({ queryKey: ["when-you-were-away", currentWorkspace?.id] });
      setShowModal(false);
      setForm({
        title: "",
        description: "",
        priority: "medium",
        task_type: "feature",
        requires_commit: false,
        due_date: "",
        assigned_to_ids: [],
        notify_assignee: false,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/tasks/${id}`, { status }),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ["tasks", currentWorkspace?.id] });
      const previousTasks = qc.getQueryData<Task[]>(["tasks", currentWorkspace?.id]);
      if (previousTasks) {
        qc.setQueryData<Task[]>(
          ["tasks", currentWorkspace?.id],
          previousTasks.map((t) => (t.id === id ? { ...t, status: status as Task["status"] } : t))
        );
      }
      return { previousTasks };
    },
    onError: (err, variables, context) => {
      if (context?.previousTasks) {
        qc.setQueryData(["tasks", currentWorkspace?.id], context.previousTasks);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["tasks", currentWorkspace?.id] });
      qc.invalidateQueries({ queryKey: ["workspace-activity", currentWorkspace?.id] });
      qc.invalidateQueries({ queryKey: ["when-you-were-away", currentWorkspace?.id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/tasks/${id}`),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["tasks", currentWorkspace?.id] });
      const previousTasks = qc.getQueryData<Task[]>(["tasks", currentWorkspace?.id]);
      if (previousTasks) {
        qc.setQueryData<Task[]>(
          ["tasks", currentWorkspace?.id],
          previousTasks.filter((t) => t.id !== id)
        );
      }
      return { previousTasks };
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["tasks", currentWorkspace?.id] });
      qc.invalidateQueries({ queryKey: ["workspace-activity", currentWorkspace?.id] });
      qc.invalidateQueries({ queryKey: ["when-you-were-away", currentWorkspace?.id] });
    },
  });

  // Handler for moving tasks (intercepts move to 'done' if commit evidence required or unlinked)
  const handleMoveTask = (task: Task, targetStatus: string) => {
    if (targetStatus === "done") {
      const hasCommit =
        (task.github_links && task.github_links.some((l) => l.commit_id != null)) ||
        !!task.primary_commit;
      const hasReason = !!task.no_commit_reason;

      // When moving from In Progress to Done: prompt to link a commit or explain why no commit applies
      if (!hasCommit && !hasReason) {
        setTaskForCommitModal({ task, isCompletionPrompt: true });
        return;
      }
    }

    updateMutation.mutate({ id: task.id, status: targetStatus });
  };

  const handleDragStart = (e: React.DragEvent, task: Task) => {
    setDraggingTaskId(task.id);
    e.dataTransfer.setData("text/plain", task.id);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnd = () => {
    setDraggingTaskId(null);
    setDragOverColumnId(null);
  };

  const handleDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dragOverColumnId !== columnId) setDragOverColumnId(columnId);
  };

  const handleDragLeave = (e: React.DragEvent, columnId: string) => {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    if (dragOverColumnId === columnId) setDragOverColumnId(null);
  };

  const handleDrop = (e: React.DragEvent, targetColumnId: string) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData("text/plain") || draggingTaskId;
    setDraggingTaskId(null);
    setDragOverColumnId(null);
    if (!taskId) return;
    const task = tasks.find((t) => t.id === taskId);
    if (task && task.status !== targetColumnId) {
      handleMoveTask(task, targetColumnId);
    }
  };

  const toggleAssignee = (userId: string) => {
    setForm((p) => {
      const exists = p.assigned_to_ids.includes(userId);
      return {
        ...p,
        assigned_to_ids: exists
          ? p.assigned_to_ids.filter((id) => id !== userId)
          : [...p.assigned_to_ids, userId],
      };
    });
  };

  if (isLoading && tasks.length === 0) return <TasksSkeleton />;

  return (
    <div className="p-6 h-full flex flex-col max-w-7xl mx-auto space-y-5">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <div className="section-label mb-1 flex items-center gap-2">
            <span>TASK BOARD</span>
            <span className="text-[10px] text-orbit-muted">• Commit Linking & Verification</span>
          </div>
          <h1 className="text-xl font-bold text-orbit-text">Tasks</h1>
        </div>

        {isAdmin ? (
          <button onClick={() => setShowModal(true)} className="orbit-btn-primary text-xs flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            <span>New task</span>
          </button>
        ) : (
          <div className="text-[11px] text-orbit-muted font-mono bg-surface border border-orbit-border px-2.5 py-1 rounded flex items-center gap-1.5">
            Only admins can create tasks
          </div>
        )}
      </div>

      {/* ── Kanban board ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1 min-h-0">
        {COLUMNS.map((col) => {
          const colTasks = tasks.filter((t) => t.status === col.id);
          const isOver = dragOverColumnId === col.id;

          return (
            <div
              key={col.id}
              onDragOver={(e) => handleDragOver(e, col.id)}
              onDragLeave={(e) => handleDragLeave(e, col.id)}
              onDrop={(e) => handleDrop(e, col.id)}
              className={`flex flex-col overflow-hidden rounded-lg border transition-all duration-150 ${
                isOver
                  ? "border-accent/50 bg-accent-dim"
                  : "border-orbit-border bg-surface2/30"
              }`}
            >
              {/* Column header */}
              <div className="flex items-center gap-2 px-3.5 py-2.5 border-b border-orbit-border bg-surface flex-shrink-0">
                <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: col.dotColor }} />
                <span className="text-xs font-medium text-orbit-text">{col.label}</span>
                <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface2 text-orbit-muted border border-orbit-border">
                  {colTasks.length}
                </span>
              </div>

              {/* Task list */}
              <div className="flex-1 overflow-y-auto p-2.5 flex flex-col gap-2">
                {colTasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    isAdmin={isAdmin}
                    isDragging={draggingTaskId === task.id}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                    onMove={handleMoveTask}
                    onDelete={(id) => deleteMutation.mutate(id)}
                    onOpenCommitModal={(t) =>
                      setTaskForCommitModal({ task: t, isCompletionPrompt: false })
                    }
                  />
                ))}

                {colTasks.length === 0 && (
                  <div
                    className={`text-center py-10 rounded-lg border border-dashed text-xs transition-colors flex flex-col items-center justify-center gap-1 ${
                      isOver
                        ? "border-accent/50 text-accent"
                        : "border-orbit-border text-orbit-muted"
                    }`}
                  >
                    <span>{isOver ? "Drop here" : "No tasks"}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Create task modal ─────────────────────────────────────── */}
      {showModal && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center animate-fade-in p-4"
          onClick={(e) => e.target === e.currentTarget && setShowModal(false)}
        >
          <div className="bg-surface border border-orbit-border rounded-xl p-5 w-full max-w-md shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between mb-4 pb-3.5 border-b border-orbit-border flex-shrink-0">
              <div>
                <h3 className="text-sm font-semibold text-orbit-text">New task</h3>
                <p className="text-[11px] text-orbit-muted mt-0.5">Assign work, type and commit evidence rules</p>
              </div>
              <button onClick={() => setShowModal(false)} className="p-1.5 rounded text-orbit-muted hover:text-orbit-text hover:bg-surface2 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col gap-3.5 overflow-y-auto flex-1">
              {/* Title */}
              <div>
                <label className="block text-xs font-medium text-orbit-text mb-1.5">Title</label>
                <input
                  autoFocus
                  className="orbit-input text-sm"
                  value={form.title}
                  onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                  placeholder="e.g. Implement user authentication"
                  onKeyDown={(e) => e.key === "Enter" && form.title && createMutation.mutate()}
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-orbit-text mb-1.5">
                  Description <span className="text-orbit-muted font-normal">(optional)</span>
                </label>
                <textarea
                  className="orbit-input text-sm resize-none"
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                  placeholder="Context, acceptance criteria, or notes"
                />
              </div>

              {/* Task Type & Commit Enforcement */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-orbit-text mb-1.5">Task Type</label>
                  <select
                    className="orbit-input text-xs"
                    value={form.task_type}
                    onChange={(e) =>
                      setForm((p) => ({
                        ...p,
                        task_type: e.target.value as
                          | "feature"
                          | "bug"
                          | "chore"
                          | "design"
                          | "docs"
                          | "other",
                        // Auto-enable commit enforcement for code-heavy tasks
                        requires_commit: ["feature", "bug", "chore"].includes(e.target.value),
                      }))
                    }
                  >
                    <option value="feature">Feature (Code)</option>
                    <option value="bug">Bug Fix (Code)</option>
                    <option value="chore">Chore (Code)</option>
                    <option value="design">Design (UI/UX)</option>
                    <option value="docs">Documentation</option>
                    <option value="other">Other / Operations</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-orbit-text mb-1.5">Evidence Policy</label>
                  <label className="flex items-center gap-2 p-2 rounded-lg bg-surface2 border border-orbit-border cursor-pointer select-none text-xs">
                    <input
                      type="checkbox"
                      checked={form.requires_commit}
                      onChange={(e) =>
                        setForm((p) => ({ ...p, requires_commit: e.target.checked }))
                      }
                      className="accent-accent rounded"
                    />
                    <span className="text-[11px] font-medium text-orbit-text">
                      Require Commit
                    </span>
                  </label>
                </div>
              </div>

              {/* Assignees */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-orbit-text">
                    Assign to{" "}
                    <span className="text-orbit-muted font-normal">
                      {form.assigned_to_ids.length === 0 ? "(all members)" : `(${form.assigned_to_ids.length} selected)`}
                    </span>
                  </label>
                  {form.assigned_to_ids.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setForm((p) => ({ ...p, assigned_to_ids: [] }))}
                      className="text-[10px] text-accent hover:underline font-mono"
                    >
                      Reset to all
                    </button>
                  )}
                </div>

                <div className="p-1.5 bg-surface2 border border-orbit-border rounded-lg max-h-32 overflow-y-auto flex flex-col gap-0.5">
                  {/* All members option */}
                  <div
                    onClick={() => setForm((p) => ({ ...p, assigned_to_ids: [] }))}
                    className={`flex items-center gap-2 p-1.5 px-2 rounded text-xs cursor-pointer select-none transition-colors ${
                      form.assigned_to_ids.length === 0
                        ? "bg-accent-dim text-accent border border-accent-border"
                        : "text-orbit-muted hover:text-orbit-text hover:bg-surface border border-transparent"
                    }`}
                  >
                    <Users className="w-3 h-3 flex-shrink-0" />
                    <span className="font-medium">All workspace members</span>
                    {form.assigned_to_ids.length === 0 && <Check className="w-3 h-3 ml-auto" />}
                  </div>

                  {members.map((m) => {
                    const isSelected = form.assigned_to_ids.includes(m.user_id);
                    return (
                      <div
                        key={m.user_id}
                        onClick={() => toggleAssignee(m.user_id)}
                        className={`flex items-center justify-between p-1.5 px-2 rounded text-xs cursor-pointer select-none transition-colors ${
                          isSelected
                            ? "bg-accent-dim text-accent border border-accent-border"
                            : "text-orbit-muted hover:text-orbit-text hover:bg-surface border border-transparent"
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <div
                            className={`w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0 transition-colors ${
                              isSelected ? "bg-accent border-accent text-white" : "border-orbit-border bg-surface"
                            }`}
                          >
                            {isSelected && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                          </div>
                          <span className="truncate font-mono text-[11px]">{m.email}</span>
                        </div>
                        <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-surface text-orbit-muted border border-orbit-border flex-shrink-0">
                          {m.role}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Priority + Due date */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-orbit-text mb-1.5">Priority</label>
                  <select
                    className="orbit-input text-sm"
                    value={form.priority}
                    onChange={(e) => setForm((p) => ({ ...p, priority: e.target.value as "low" | "medium" | "high" }))}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-orbit-text mb-1.5">Due date</label>
                  <input
                    type="date"
                    className="orbit-input text-sm"
                    value={form.due_date}
                    onChange={(e) => setForm((p) => ({ ...p, due_date: e.target.value }))}
                  />
                </div>
              </div>

              {/* Email notification */}
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-surface2 border border-orbit-border">
                <input
                  id="notify-assignee"
                  type="checkbox"
                  checked={form.notify_assignee}
                  onChange={(e) => setForm((p) => ({ ...p, notify_assignee: e.target.checked }))}
                  className="mt-0.5 cursor-pointer rounded"
                />
                <label htmlFor="notify-assignee" className="text-xs cursor-pointer select-none">
                  <span className="font-medium text-orbit-text flex items-center gap-1.5">
                    <Mail className="w-3 h-3 text-orbit-muted" />
                    Send email notification
                  </span>
                  <span className="block text-[11px] text-orbit-muted mt-0.5">
                    Notify{" "}
                    {form.assigned_to_ids.length === 0
                      ? "all workspace members"
                      : form.assigned_to_ids.length === 1
                      ? "the assigned member"
                      : `${form.assigned_to_ids.length} assigned members`}{" "}
                    with task details
                  </span>
                </label>
              </div>
            </div>

            <div className="flex gap-2 mt-4 pt-3.5 border-t border-orbit-border flex-shrink-0">
              <button
                className="orbit-btn-primary flex-1 justify-center text-xs"
                onClick={() => createMutation.mutate()}
                disabled={!form.title || createMutation.isPending}
              >
                {createMutation.isPending ? <Spinner className="w-3.5 h-3.5" /> : "Create task"}
              </button>
              <button className="orbit-btn-ghost text-xs" onClick={() => setShowModal(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Commit-to-Task Link & Completion Evidence Modal ───────── */}
      {taskForCommitModal && currentWorkspace?.id && (
        <TaskCommitLinkModal
          task={taskForCommitModal.task}
          workspaceId={currentWorkspace.id}
          isCompletionPrompt={taskForCommitModal.isCompletionPrompt}
          onClose={() => setTaskForCommitModal(null)}
          onSuccess={() => {
            qc.invalidateQueries({ queryKey: ["tasks", currentWorkspace.id] });
          }}
        />
      )}
    </div>
  );
}
