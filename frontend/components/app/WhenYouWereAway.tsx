"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import {
  WhenYouWereAwayResponse,
  WhenYouWereAwayTask,
} from "@/types";
import { formatRelative } from "@/lib/utils";
import {
  Sparkles,
  Clock,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FileText,
  GitPullRequest,
  GitCommit,
  MessageSquare,
  UserCheck,
  Workflow,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Check,
  Copy,
  Layers,
} from "lucide-react";

interface WhenYouWereAwayProps {
  workspaceId: string;
}

type TimeWindowOption = "since_last_visit" | "24h" | "3d" | "7d" | "30d";

export function WhenYouWereAway({ workspaceId }: WhenYouWereAwayProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedWindow, setSelectedWindow] = useState<TimeWindowOption>("since_last_visit");
  const [activeTab, setActiveTab] = useState<"all" | "tasks" | "github" | "team">("all");
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);

  // Fetch When You Were Away intelligence
  const {
    data,
    isLoading,
    isFetching,
    refetch,
  } = useQuery<WhenYouWereAwayResponse>({
    queryKey: ["when-you-were-away", workspaceId, selectedWindow],
    queryFn: () =>
      api
        .get(
          `/dashboard/when-you-were-away?workspace_id=${workspaceId}&time_window=${selectedWindow}`
        )
        .then((res) => res.data),
    enabled: !!workspaceId,
    staleTime: 30000,
  });

  // Mutation to mark caught up
  const markCaughtUpMutation = useMutation({
    mutationFn: () =>
      api.post(`/dashboard/heartbeat?workspace_id=${workspaceId}&reset_seen=true`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["when-you-were-away", workspaceId] });
      refetch();
    },
  });

  const handleCopySummary = () => {
    if (data?.summary) {
      navigator.clipboard.writeText(data.summary);
      setCopiedSummary(true);
      setTimeout(() => setCopiedSummary(false), 2000);
    }
  };

  const windowOptions: { id: TimeWindowOption; label: string }[] = [
    { id: "since_last_visit", label: "Since Last Visit" },
    { id: "24h", label: "Past 24h" },
    { id: "3d", label: "Past 3 Days" },
    { id: "7d", label: "Past 7 Days" },
    { id: "30d", label: "Past 30 Days" },
  ];

  const formatExactDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return isoStr;
    }
  };

  const stats = data?.stats;
  const overdueCount = stats?.tasks_overdue_count || 0;
  const approachingCount = stats?.tasks_approaching_count || 0;
  const totalTasks =
    (stats?.tasks_created_count || 0) + (stats?.tasks_updated_count || 0);
  const totalGithub =
    (stats?.github_prs_count || 0) + (stats?.github_commits_count || 0);
  const totalTeam =
    (stats?.team_docs_count || 0) +
    (stats?.team_chats_count || 0) +
    (stats?.team_members_count || 0);

  return (
    <div className="orbit-card relative overflow-hidden border border-orbit-border/80 bg-surface/90 shadow-xl backdrop-blur-md transition-all">
      {/* Background glowing ambient light */}
      <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-accent/5 blur-3xl" />
      <div className="pointer-events-none absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-blue-500/5 blur-3xl" />

      {/* ── Top Bar: Title & Window Controls ────────────────────────── */}
      <div className="border-b border-orbit-border/60 p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-accent/20 bg-accent/10 shadow-inner">
              <Sparkles className="h-4 w-4 text-accent animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-display text-base font-semibold text-orbit-text tracking-tight">
                  When You Were Away
                </h2>
                <span className="rounded-full border border-orbit-border bg-surface2 px-2 py-0.5 text-[10px] font-mono text-orbit-muted uppercase tracking-wider">
                  Recent Developments
                </span>
              </div>
              <p className="mt-0.5 text-xs text-orbit-muted">
                Summarizing recorded workspace events since your previous session
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Time Window Pills */}
            <div className="flex items-center rounded-lg border border-orbit-border bg-surface2/60 p-0.5 shadow-sm">
              {windowOptions.map((opt) => {
                const isActive = selectedWindow === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setSelectedWindow(opt.id)}
                    className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
                      isActive
                        ? "bg-surface font-semibold text-accent shadow-sm"
                        : "text-orbit-muted hover:text-orbit-text"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>

            {/* Refresh button */}
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              title="Refresh Developments"
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-orbit-border bg-surface2 hover:border-orbit-border2 hover:text-orbit-text transition-all text-orbit-muted disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isFetching ? "animate-spin text-accent" : ""}`}
              />
            </button>

            {/* Mark as caught up button */}
            <button
              onClick={() => markCaughtUpMutation.mutate()}
              disabled={markCaughtUpMutation.isPending}
              title="Record current time as last seen and mark caught up"
              className="flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent/20 transition-all shadow-sm disabled:opacity-50"
            >
              {markCaughtUpMutation.isPending ? (
                <RefreshCw className="h-3 w-3 animate-spin" />
              ) : (
                <Check className="h-3 w-3" />
              )}
              <span>{markCaughtUpMutation.isPending ? "Marking..." : "Mark caught up"}</span>
            </button>

            {/* Collapse toggle */}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-orbit-border bg-surface2 text-orbit-muted hover:text-orbit-text transition-all"
            >
              {isCollapsed ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronUp className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        {/* Time Window Details & Period Banner */}
        {data && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-orbit-border/50 bg-surface2/30 px-3 py-2 text-xs">
            <div className="flex flex-wrap items-center gap-2 text-orbit-muted">
              <Clock className="h-3.5 w-3.5 text-accent flex-shrink-0" />
              <span>
                <strong className="text-orbit-text font-medium">Time Window:</strong>{" "}
                {formatExactDate(data.since)} — {formatExactDate(data.until)}
              </span>
              <span className="font-mono text-[11px] text-orbit-muted/80">
                ({data.since_label})
              </span>
            </div>

            <div className="flex items-center gap-3 text-[11px] font-mono">
              {data.last_fetched_at && (
                <span className="text-orbit-muted">
                  Last fetched: <strong className="text-accent">{formatExactDate(data.last_fetched_at)}</strong>
                </span>
              )}
              {overdueCount > 0 && (
                <span className="flex items-center gap-1 rounded bg-red-500/10 px-1.5 py-0.5 text-red-400 font-semibold border border-red-500/20">
                  <AlertTriangle className="h-3 w-3" /> {overdueCount} Overdue
                </span>
              )}
              {approachingCount > 0 && (
                <span className="flex items-center gap-1 rounded bg-yellow-500/10 px-1.5 py-0.5 text-yellow-400 font-semibold border border-yellow-500/20">
                  <Clock className="h-3 w-3" /> {approachingCount} Due Soon
                </span>
              )}
              <span className="text-orbit-muted">
                {stats?.total_events_count || 0} Recorded Event
                {(stats?.total_events_count || 0) !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
        )}
      </div>

      {!isCollapsed && (
        <div className="p-4 sm:p-5 space-y-5">
          {isLoading ? (
            <div className="py-8 flex flex-col items-center justify-center gap-3 text-orbit-muted">
              <RefreshCw className="h-6 w-6 animate-spin text-accent" />
              <p className="text-xs font-mono">Aggregating workspace developments...</p>
            </div>
          ) : !data ? (
            <div className="py-6 text-center text-xs text-orbit-muted">
              Failed to load developments. Please try refreshing.
            </div>
          ) : (
            <>
              {/* ── Executive Brief Synthesis ────────────────────────── */}
              <div className="relative rounded-xl border border-accent/25 bg-gradient-to-r from-accent/10 via-surface2 to-surface p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-accent uppercase tracking-wider">
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Executive Brief</span>
                    </div>
                    <p className="text-sm leading-relaxed text-orbit-text font-normal">
                      {data.summary}
                    </p>
                  </div>
                  <button
                    onClick={handleCopySummary}
                    title="Copy executive brief"
                    className="flex-shrink-0 flex h-7 w-7 items-center justify-center rounded border border-orbit-border bg-surface hover:text-accent transition-colors text-orbit-muted"
                  >
                    {copiedSummary ? (
                      <Check className="h-3.5 w-3.5 text-accent" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* ── Category Filter Tabs ───────────────────────────── */}
              <div className="flex flex-wrap items-center gap-2 border-b border-orbit-border/50 pb-2">
                <button
                  onClick={() => setActiveTab("all")}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                    activeTab === "all"
                      ? "bg-surface2 text-accent border border-orbit-border shadow-sm"
                      : "text-orbit-muted hover:text-orbit-text"
                  }`}
                >
                  <Layers className="h-3.5 w-3.5" />
                  <span>All Events</span>
                  <span className="ml-1 rounded-full bg-surface px-1.5 py-0.2 text-[10px] font-mono">
                    {data.stats.total_events_count}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab("tasks")}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                    activeTab === "tasks"
                      ? "bg-surface2 text-accent border border-orbit-border shadow-sm"
                      : "text-orbit-muted hover:text-orbit-text"
                  }`}
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Tasks & Deadlines</span>
                  <span className="ml-1 rounded-full bg-surface px-1.5 py-0.2 text-[10px] font-mono">
                    {totalTasks + overdueCount + approachingCount}
                  </span>
                  {overdueCount > 0 && (
                    <span className="h-2 w-2 rounded-full bg-red-400 animate-ping" />
                  )}
                </button>

                <button
                  onClick={() => setActiveTab("github")}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                    activeTab === "github"
                      ? "bg-surface2 text-accent border border-orbit-border shadow-sm"
                      : "text-orbit-muted hover:text-orbit-text"
                  }`}
                >
                  <GitPullRequest className="h-3.5 w-3.5" />
                  <span>GitHub & Code</span>
                  <span className="ml-1 rounded-full bg-surface px-1.5 py-0.2 text-[10px] font-mono">
                    {totalGithub}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab("team")}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                    activeTab === "team"
                      ? "bg-surface2 text-accent border border-orbit-border shadow-sm"
                      : "text-orbit-muted hover:text-orbit-text"
                  }`}
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  <span>Team Activity</span>
                  <span className="ml-1 rounded-full bg-surface px-1.5 py-0.2 text-[10px] font-mono">
                    {totalTeam}
                  </span>
                </button>
              </div>

              {/* ── Content Panes ─────────────────────────────────── */}
              {activeTab === "all" && (
                <AllDevelopmentsTimeline
                  data={data}
                  onNavigate={(href) => router.push(href)}
                />
              )}

              {activeTab === "tasks" && (
                <TasksSection
                  data={data}
                  onNavigate={(href) => router.push(href)}
                />
              )}

              {activeTab === "github" && (
                <GitHubSection
                  data={data}
                  onNavigate={(href) => router.push(href)}
                />
              )}

              {activeTab === "team" && (
                <TeamActivitySection
                  data={data}
                  onNavigate={(href) => router.push(href)}
                />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Subcomponents
// ─────────────────────────────────────────────────────────────────────────────

interface SectionProps {
  data: WhenYouWereAwayResponse;
  onNavigate: (href: string) => void;
}

function AllDevelopmentsTimeline({ data, onNavigate }: SectionProps) {
  if (!data.has_events) {
    return (
      <div className="rounded-xl border border-dashed border-orbit-border p-8 text-center">
        <CheckCircle2 className="mx-auto h-8 w-8 text-orbit-muted/50" />
        <h3 className="mt-2 text-sm font-medium text-orbit-text">All Caught Up</h3>
        <p className="mt-1 text-xs text-orbit-muted max-w-sm mx-auto">
          No new tasks, commits, or conversations were recorded in this workspace during the selected time window ({data.since_label}).
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Critical alerts banner if overdue tasks exist */}
      {data.tasks_overdue.length > 0 && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3.5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-red-400">
              <AlertTriangle className="h-4 w-4" />
              <span>Overdue Tasks Requiring Attention ({data.tasks_overdue.length})</span>
            </div>
            <button
              onClick={() => onNavigate("/dashboard/tasks")}
              className="text-[11px] text-red-400 hover:text-red-300 flex items-center gap-1 font-medium underline"
            >
              Open Tasks <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          <div className="space-y-1.5">
            {data.tasks_overdue.map((t) => (
              <div
                key={t.id}
                onClick={() => onNavigate(t.link)}
                className="flex items-center justify-between rounded-lg bg-surface/80 p-2.5 text-xs hover:border-red-500/40 border border-transparent cursor-pointer transition-all group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="h-2 w-2 rounded-full bg-red-500 flex-shrink-0" />
                  <span className="font-medium text-orbit-text truncate group-hover:text-red-400 transition-colors">
                    {t.title}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono text-red-400/90 flex-shrink-0">
                  <span>Due {t.due_date ? formatRelative(t.due_date) : "past"}</span>
                  <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid summarizing latest recorded activities */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Recent Tasks */}
        <div className="rounded-xl border border-orbit-border bg-surface2/30 p-3.5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-orbit-text flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
              Task Developments
            </span>
            <button
              onClick={() => onNavigate("/dashboard/tasks")}
              className="text-[11px] text-orbit-muted hover:text-orbit-text flex items-center gap-1"
            >
              Board <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          {data.tasks_created.length === 0 && data.tasks_updated.length === 0 ? (
            <p className="text-xs text-orbit-muted italic py-2">
              No new task creation or updates recorded.
            </p>
          ) : (
            <div className="space-y-2">
              {data.tasks_created.slice(0, 3).map((t) => (
                <div
                  key={`new_${t.id}`}
                  onClick={() => onNavigate(t.link)}
                  className="rounded-lg border border-orbit-border/60 bg-surface p-2.5 hover:border-orbit-border2 cursor-pointer transition-all group text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-orbit-text truncate group-hover:text-accent transition-colors">
                      {t.title}
                    </span>
                    <span className="rounded bg-accent/10 text-accent border border-accent/20 px-1.5 py-0.5 text-[9px] font-mono uppercase">
                      New
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[10px] text-orbit-muted font-mono">
                    <span>by @{t.creator_email?.split("@")[0] || "member"}</span>
                    <span>{formatRelative(t.created_at)}</span>
                  </div>
                </div>
              ))}

              {data.tasks_updated.slice(0, 3).map((t) => (
                <div
                  key={`upd_${t.id}`}
                  onClick={() => onNavigate(t.link)}
                  className="rounded-lg border border-orbit-border/60 bg-surface p-2.5 hover:border-orbit-border2 cursor-pointer transition-all group text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-orbit-text truncate group-hover:text-blue-400 transition-colors">
                      {t.title}
                    </span>
                    <span className="rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 text-[9px] font-mono uppercase">
                      {t.status}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[10px] text-orbit-muted font-mono">
                    <span>Status changed</span>
                    <span>{formatRelative(t.updated_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent GitHub Activity */}
        <div className="rounded-xl border border-orbit-border bg-surface2/30 p-3.5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-orbit-text flex items-center gap-1.5">
              <GitPullRequest className="h-3.5 w-3.5 text-emerald-400" />
              Repository Intelligence
            </span>
            <button
              onClick={() => onNavigate("/dashboard/integrations")}
              className="text-[11px] text-orbit-muted hover:text-orbit-text flex items-center gap-1"
            >
              Integrations <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          {data.github_prs.length === 0 && data.github_commits.length === 0 ? (
            <p className="text-xs text-orbit-muted italic py-2">
              No repository commits or pull requests recorded in this window.
            </p>
          ) : (
            <div className="space-y-2">
              {data.github_prs.slice(0, 3).map((pr) => (
                <a
                  key={pr.id}
                  href={pr.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-lg border border-orbit-border/60 bg-surface p-2.5 hover:border-emerald-500/40 cursor-pointer transition-all group text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-orbit-text truncate group-hover:text-emerald-400 transition-colors">
                      PR #{pr.pr_number}: {pr.title}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[9px] font-mono uppercase border ${
                        pr.state === "merged"
                          ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                          : pr.state === "open"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : "bg-surface2 text-orbit-muted border-orbit-border"
                      }`}
                    >
                      {pr.state}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[10px] text-orbit-muted font-mono">
                    <span>@{pr.author_login || "dev"} • {pr.repository_name}</span>
                    <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </a>
              ))}

              {data.github_commits.slice(0, 3).map((cm) => (
                <a
                  key={cm.id}
                  href={cm.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-lg border border-orbit-border/60 bg-surface p-2.5 hover:border-orbit-border2 cursor-pointer transition-all group text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-orbit-text truncate group-hover:text-orbit-text">
                      {cm.message}
                    </span>
                    <span className="font-mono text-[10px] text-accent">
                      +{cm.additions}/-{cm.deletions}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[10px] text-orbit-muted font-mono">
                    <span>[{cm.sha.slice(0, 7)}] by @{cm.author_login || "dev"}</span>
                    <span>{formatRelative(cm.committed_at)}</span>
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Team Activity Strip */}
      {data.team_activities.length > 0 && (
        <div className="rounded-xl border border-orbit-border bg-surface2/30 p-3.5 space-y-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-orbit-text flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5 text-blue-400" />
              Team Discussions & Content
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {data.team_activities.slice(0, 6).map((act) => (
              <div
                key={act.id}
                onClick={() => onNavigate(act.target_link)}
                className="rounded-lg border border-orbit-border/60 bg-surface p-2.5 hover:border-blue-400/40 cursor-pointer transition-all group text-xs"
              >
                <div className="flex items-center justify-between text-[10px] text-orbit-muted font-mono">
                  <span className="uppercase text-blue-400/80">{act.action}</span>
                  <span>{formatRelative(act.created_at)}</span>
                </div>
                <div className="mt-1 font-medium text-orbit-text truncate group-hover:text-blue-400 transition-colors">
                  {act.title}
                </div>
                {act.description && (
                  <p className="mt-0.5 text-[11px] text-orbit-muted line-clamp-1">
                    {act.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TasksSection({ data, onNavigate }: SectionProps) {
  const allTasksCount =
    data.tasks_created.length +
    data.tasks_updated.length +
    data.tasks_overdue.length +
    data.tasks_approaching.length;

  if (allTasksCount === 0) {
    return (
      <div className="rounded-xl border border-dashed border-orbit-border p-8 text-center">
        <CheckCircle2 className="mx-auto h-8 w-8 text-orbit-muted/50" />
        <h3 className="mt-2 text-sm font-medium text-orbit-text">No Task Changes</h3>
        <p className="mt-1 text-xs text-orbit-muted max-w-sm mx-auto">
          No new task creations, status updates, or approaching deadlines recorded in this window ({data.since_label}).
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Overdue Tasks Alert */}
      {data.tasks_overdue.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5" />
            Overdue Deadlines ({data.tasks_overdue.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {data.tasks_overdue.map((t) => (
              <TaskCard key={`over_${t.id}`} task={t} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}

      {/* Approaching Deadlines */}
      {data.tasks_approaching.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-yellow-400 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            Approaching Deadlines (Next 72h) ({data.tasks_approaching.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {data.tasks_approaching.map((t) => (
              <TaskCard key={`appr_${t.id}`} task={t} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}

      {/* Tasks Assigned To Me */}
      {data.tasks_assigned_to_user.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-accent uppercase tracking-wider flex items-center gap-1.5">
            <UserCheck className="h-3.5 w-3.5" />
            Assigned to You in This Window ({data.tasks_assigned_to_user.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {data.tasks_assigned_to_user.map((t) => (
              <TaskCard key={`my_${t.id}`} task={t} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}

      {/* Created in Window */}
      {data.tasks_created.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-orbit-text uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
            Newly Created Tasks ({data.tasks_created.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {data.tasks_created.map((t) => (
              <TaskCard key={`new_${t.id}`} task={t} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}

      {/* Status Changed in Window */}
      {data.tasks_updated.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-orbit-text uppercase tracking-wider flex items-center gap-1.5">
            <RefreshCw className="h-3.5 w-3.5 text-blue-400" />
            Status & Assignment Updates ({data.tasks_updated.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {data.tasks_updated.map((t) => (
              <TaskCard key={`upd_${t.id}`} task={t} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TaskCard({
  task,
  onNavigate,
}: {
  task: WhenYouWereAwayTask;
  onNavigate: (href: string) => void;
}) {
  const priColor =
    task.priority === "high"
      ? "text-red-400 border-red-500/20 bg-red-500/10"
      : task.priority === "medium"
      ? "text-yellow-400 border-yellow-500/20 bg-yellow-500/10"
      : "text-orbit-muted border-orbit-border bg-surface2";

  return (
    <div
      onClick={() => onNavigate(task.link)}
      className="orbit-card p-3 hover:border-orbit-border2 transition-all cursor-pointer group flex flex-col justify-between gap-2"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5 min-w-0">
          <div className="font-medium text-xs text-orbit-text group-hover:text-accent transition-colors truncate">
            {task.title}
          </div>
          {task.description && (
            <p className="text-[11px] text-orbit-muted line-clamp-1">
              {task.description}
            </p>
          )}
        </div>
        <span
          className={`rounded px-1.5 py-0.5 text-[9px] font-mono uppercase border flex-shrink-0 ${priColor}`}
        >
          {task.priority}
        </span>
      </div>

      <div className="flex items-center justify-between text-[10px] text-orbit-muted font-mono pt-1 border-t border-orbit-border/40">
        <div className="flex items-center gap-1.5">
          <span className="rounded bg-surface2 px-1.5 py-0.5 uppercase text-orbit-text">
            {task.status}
          </span>
          {task.is_overdue && (
            <span className="text-red-400 font-bold">OVERDUE</span>
          )}
        </div>
        <div>
          {task.due_date ? `Due ${formatRelative(task.due_date)}` : `Updated ${formatRelative(task.updated_at)}`}
        </div>
      </div>
    </div>
  );
}

function GitHubSection({ data, onNavigate }: SectionProps) {
  const totalItems = data.github_prs.length + data.github_commits.length;

  if (totalItems === 0) {
    return (
      <div className="rounded-xl border border-dashed border-orbit-border p-8 text-center space-y-3">
        <GitPullRequest className="mx-auto h-8 w-8 text-orbit-muted/50" />
        <h3 className="text-sm font-medium text-orbit-text">No Repository Events</h3>
        <p className="text-xs text-orbit-muted max-w-sm mx-auto">
          No pull requests or commits were recorded for active repositories in this workspace during {data.since_label}.
        </p>
        <button
          onClick={() => onNavigate("/dashboard/integrations")}
          className="orbit-btn-secondary text-xs inline-flex items-center gap-1.5"
        >
          <span>Manage GitHub Repositories</span>
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Pull Requests */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-orbit-text uppercase tracking-wider flex items-center gap-1.5">
          <GitPullRequest className="h-3.5 w-3.5 text-emerald-400" />
          Pull Requests ({data.github_prs.length})
        </h4>
        {data.github_prs.length === 0 ? (
          <p className="text-xs text-orbit-muted italic">No PR activity recorded.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {data.github_prs.map((pr) => (
              <a
                key={pr.id}
                href={pr.url}
                target="_blank"
                rel="noopener noreferrer"
                className="orbit-card p-3 hover:border-emerald-500/40 transition-all cursor-pointer group flex flex-col justify-between gap-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5 min-w-0">
                    <div className="font-medium text-xs text-orbit-text group-hover:text-emerald-400 transition-colors truncate">
                      PR #{pr.pr_number}: {pr.title}
                    </div>
                    <div className="text-[11px] text-orbit-muted">
                      Repo: {pr.repository_name}
                    </div>
                  </div>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[9px] font-mono uppercase border ${
                      pr.state === "merged"
                        ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                        : pr.state === "open"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        : "bg-surface2 text-orbit-muted border-orbit-border"
                    }`}
                  >
                    {pr.state}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-orbit-muted font-mono pt-1 border-t border-orbit-border/40">
                  <span>@{pr.author_login || "dev"}</span>
                  <span className="flex items-center gap-1">
                    {formatRelative(pr.created_at)}
                    <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </span>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Commits */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-orbit-text uppercase tracking-wider flex items-center gap-1.5">
          <GitCommit className="h-3.5 w-3.5 text-blue-400" />
          Recent Commits ({data.github_commits.length})
        </h4>
        {data.github_commits.length === 0 ? (
          <p className="text-xs text-orbit-muted italic">No commits pushed in this window.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {data.github_commits.map((cm) => (
              <a
                key={cm.id}
                href={cm.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="orbit-card p-3 hover:border-orbit-border2 transition-all cursor-pointer group flex flex-col justify-between gap-2"
              >
                <div>
                  <div className="font-medium text-xs text-orbit-text line-clamp-1">
                    {cm.message}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-orbit-muted font-mono">
                    <span>branch: {cm.branch || "main"}</span>
                    <span className="text-accent font-semibold">
                      +{cm.additions}/-{cm.deletions}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-[10px] text-orbit-muted font-mono pt-1 border-t border-orbit-border/40">
                  <span>[{cm.sha.slice(0, 7)}] by @{cm.author_login || "dev"}</span>
                  <span>{formatRelative(cm.committed_at)}</span>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TeamActivitySection({ data, onNavigate }: SectionProps) {
  if (data.team_activities.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-orbit-border p-8 text-center">
        <MessageSquare className="mx-auto h-8 w-8 text-orbit-muted/50" />
        <h3 className="mt-2 text-sm font-medium text-orbit-text">No Team Activity</h3>
        <p className="mt-1 text-xs text-orbit-muted max-w-sm mx-auto">
          No new messages, documents, or team member updates were recorded in this workspace during {data.since_label}.
        </p>
      </div>
    );
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "document":
        return <FileText className="h-3.5 w-3.5 text-accent" />;
      case "chat":
        return <MessageSquare className="h-3.5 w-3.5 text-blue-400" />;
      case "member":
        return <UserCheck className="h-3.5 w-3.5 text-emerald-400" />;
      case "workflow":
        return <Workflow className="h-3.5 w-3.5 text-purple-400" />;
      default:
        return <CheckCircle2 className="h-3.5 w-3.5 text-orbit-muted" />;
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-orbit-text uppercase tracking-wider">
          All Team Interactions ({data.team_activities.length})
        </h4>
        <span className="text-[11px] text-orbit-muted">
          Showing updates you have permission to view
        </span>
      </div>

      <div className="divide-y divide-orbit-border/60 rounded-xl border border-orbit-border bg-surface overflow-hidden">
        {data.team_activities.map((act) => (
          <div
            key={act.id}
            onClick={() => onNavigate(act.target_link)}
            className="flex items-center justify-between p-3 hover:bg-surface2 transition-colors cursor-pointer group"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-orbit-border bg-surface2 flex-shrink-0">
                {getCategoryIcon(act.category)}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-xs text-orbit-text group-hover:text-accent transition-colors truncate">
                    {act.title}
                  </span>
                  <span className="rounded bg-surface2 px-1.5 py-0.2 text-[9px] font-mono text-orbit-muted uppercase">
                    {act.action}
                  </span>
                </div>
                {act.description && (
                  <p className="text-[11px] text-orbit-muted truncate mt-0.5">
                    {act.description}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3 text-[10px] text-orbit-muted font-mono flex-shrink-0">
              <span>{formatRelative(act.created_at)}</span>
              <ArrowRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
