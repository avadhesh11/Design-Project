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
    <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-b from-[#13131a]/95 via-[#0e0e14]/95 to-[#0a0a0e]/98 shadow-[0_8px_32px_rgba(0,0,0,0.6)] backdrop-blur-xl transition-all">
      {/* Top light sheen line */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent" />

      {/* Dual glowing ambient lights */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-72 w-72 rounded-full bg-emerald-500/10 blur-[90px]" />
      <div className="pointer-events-none absolute -left-16 -bottom-16 h-72 w-72 rounded-full bg-teal-500/5 blur-[90px]" />

      {/* ── Top Bar: Title & Window Controls ────────────────────────── */}
      <div className="border-b border-white/[0.06] p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 via-emerald-500/10 to-teal-500/5 border border-emerald-500/30 shadow-[0_0_20px_rgba(34,197,94,0.18)] ring-1 ring-white/10 flex-shrink-0">
              <Sparkles className="h-5 w-5 text-emerald-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="font-display text-base font-semibold text-white tracking-tight">
                  When You Were Away
                </h2>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-mono font-medium text-emerald-400 tracking-wider uppercase backdrop-blur-sm">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400"></span>
                  </span>
                  Recent Developments
                </span>
              </div>
              <p className="mt-0.5 text-xs text-zinc-400">
                Summarizing recorded workspace events since your previous session
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Time Window Pills Container */}
            <div className="flex items-center rounded-xl border border-white/[0.08] bg-black/40 p-1 shadow-inner backdrop-blur-md">
              {windowOptions.map((opt) => {
                const isActive = selectedWindow === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setSelectedWindow(opt.id)}
                    className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                      isActive
                        ? "bg-gradient-to-r from-emerald-500/25 to-teal-500/20 font-semibold text-emerald-300 border border-emerald-500/40 shadow-[0_0_12px_rgba(34,197,94,0.18)]"
                        : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
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
              className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.08] hover:border-white/[0.15] text-zinc-400 hover:text-white transition-all shadow-sm disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isFetching ? "animate-spin text-emerald-400" : ""}`}
              />
            </button>

            {/* Mark as caught up button */}
            <button
              onClick={() => markCaughtUpMutation.mutate()}
              disabled={markCaughtUpMutation.isPending}
              title="Record current time as last seen and mark caught up"
              className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-gradient-to-r from-emerald-500/20 via-emerald-600/15 to-teal-600/20 px-3.5 py-1.5 text-xs font-medium text-emerald-300 shadow-[0_0_16px_rgba(34,197,94,0.14)] hover:shadow-[0_0_24px_rgba(34,197,94,0.25)] hover:border-emerald-500/60 active:scale-[0.98] transition-all disabled:opacity-50"
            >
              {markCaughtUpMutation.isPending ? (
                <RefreshCw className="h-3 w-3 animate-spin text-emerald-400" />
              ) : (
                <Check className="h-3 w-3 text-emerald-400" />
              )}
              <span>{markCaughtUpMutation.isPending ? "Marking..." : "Mark caught up"}</span>
            </button>

            {/* Collapse toggle */}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.08] hover:border-white/[0.15] text-zinc-400 hover:text-white transition-all shadow-sm"
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
          <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-white/[0.06] bg-gradient-to-r from-white/[0.03] via-white/[0.015] to-white/[0.03] px-3.5 py-2 text-xs backdrop-blur-md">
            <div className="flex flex-wrap items-center gap-2 text-zinc-400">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex-shrink-0">
                <Clock className="h-3.5 w-3.5" />
              </div>
              <span>
                <strong className="text-zinc-200 font-medium">Time Window:</strong>{" "}
                <span className="text-zinc-300">{formatExactDate(data.since)} — {formatExactDate(data.until)}</span>
              </span>
              <span className="rounded-md bg-white/[0.05] border border-white/[0.08] px-2 py-0.5 text-[11px] font-mono text-zinc-400">
                ({data.since_label})
              </span>
            </div>

            <div className="flex items-center gap-3 text-[11px] font-mono">
              {data.last_fetched_at && (
                <span className="flex items-center gap-1.5 text-zinc-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Last fetched:</span>
                  <strong className="text-emerald-400 font-medium">{formatExactDate(data.last_fetched_at)}</strong>
                </span>
              )}
              {overdueCount > 0 && (
                <span className="flex items-center gap-1 rounded-md bg-red-500/15 px-2 py-0.5 text-red-300 font-semibold border border-red-500/30 shadow-[0_0_10px_rgba(239,68,68,0.15)]">
                  <AlertTriangle className="h-3 w-3" /> {overdueCount} Overdue
                </span>
              )}
              {approachingCount > 0 && (
                <span className="flex items-center gap-1 rounded-md bg-yellow-500/15 px-2 py-0.5 text-yellow-300 font-semibold border border-yellow-500/30 shadow-[0_0_10px_rgba(234,179,8,0.15)]">
                  <Clock className="h-3 w-3" /> {approachingCount} Due Soon
                </span>
              )}
              <span className="rounded-md bg-white/[0.05] border border-white/[0.08] px-2 py-0.5 text-zinc-300">
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
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <RefreshCw className="h-5 w-5 animate-spin text-emerald-400" />
              </div>
              <p className="text-xs font-mono text-zinc-400">Aggregating workspace developments...</p>
            </div>
          ) : !data ? (
            <div className="py-8 text-center text-xs text-zinc-400">
              Failed to load developments. Please try refreshing.
            </div>
          ) : (
            <>
              {/* ── Executive Brief Synthesis ────────────────────────── */}
              <div className="relative overflow-hidden rounded-xl border border-emerald-500/25 bg-gradient-to-br from-emerald-950/20 via-[#101017] to-[#0d0d12] p-4 sm:p-5 shadow-[0_4px_24px_rgba(0,0,0,0.35)] backdrop-blur-md group">
                {/* Left vertical accent indicator */}
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-emerald-400 via-teal-400 to-transparent" />
                
                {/* Ambient corner glow */}
                <div className="pointer-events-none absolute -right-10 -top-10 h-36 w-36 rounded-full bg-emerald-500/[0.07] blur-2xl" />

                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1.5 pl-1.5">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 uppercase tracking-widest font-mono">
                        <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                        <span>Executive Brief</span>
                      </div>
                      <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-mono text-emerald-300 uppercase tracking-wider">
                        AI Synthesis
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed text-zinc-200 font-normal">
                      {data.summary}
                    </p>
                  </div>
                  <button
                    onClick={handleCopySummary}
                    title="Copy executive brief"
                    className="flex-shrink-0 flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.04] hover:bg-white/[0.08] hover:border-emerald-500/40 text-zinc-400 hover:text-emerald-300 transition-all shadow-sm"
                  >
                    {copiedSummary ? (
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* ── Category Filter Tabs ───────────────────────────── */}
              <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] pb-3">
                <button
                  onClick={() => setActiveTab("all")}
                  className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs transition-all ${
                    activeTab === "all"
                      ? "bg-emerald-500/15 border border-emerald-500/35 text-emerald-300 font-semibold shadow-[0_0_12px_rgba(34,197,94,0.12)]"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] border border-white/[0.05] font-medium"
                  }`}
                >
                  <Layers className="h-3.5 w-3.5 text-emerald-400" />
                  <span>All Events</span>
                  <span
                    className={`ml-0.5 rounded-full px-2 py-0.2 text-[10px] font-mono ${
                      activeTab === "all"
                        ? "bg-emerald-500/20 text-emerald-200 border border-emerald-500/30"
                        : "bg-white/[0.06] text-zinc-400 border border-white/[0.08]"
                    }`}
                  >
                    {data.stats.total_events_count}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab("tasks")}
                  className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs transition-all ${
                    activeTab === "tasks"
                      ? "bg-emerald-500/15 border border-emerald-500/35 text-emerald-300 font-semibold shadow-[0_0_12px_rgba(34,197,94,0.12)]"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] border border-white/[0.05] font-medium"
                  }`}
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Tasks & Deadlines</span>
                  <span
                    className={`ml-0.5 rounded-full px-2 py-0.2 text-[10px] font-mono ${
                      activeTab === "tasks"
                        ? "bg-emerald-500/20 text-emerald-200 border border-emerald-500/30"
                        : "bg-white/[0.06] text-zinc-400 border border-white/[0.08]"
                    }`}
                  >
                    {totalTasks + overdueCount + approachingCount}
                  </span>
                  {overdueCount > 0 && (
                    <span className="h-2 w-2 rounded-full bg-red-400 animate-ping" />
                  )}
                </button>

                <button
                  onClick={() => setActiveTab("github")}
                  className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs transition-all ${
                    activeTab === "github"
                      ? "bg-emerald-500/15 border border-emerald-500/35 text-emerald-300 font-semibold shadow-[0_0_12px_rgba(34,197,94,0.12)]"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] border border-white/[0.05] font-medium"
                  }`}
                >
                  <GitPullRequest className="h-3.5 w-3.5 text-emerald-400" />
                  <span>GitHub & Code</span>
                  <span
                    className={`ml-0.5 rounded-full px-2 py-0.2 text-[10px] font-mono ${
                      activeTab === "github"
                        ? "bg-emerald-500/20 text-emerald-200 border border-emerald-500/30"
                        : "bg-white/[0.06] text-zinc-400 border border-white/[0.08]"
                    }`}
                  >
                    {totalGithub}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab("team")}
                  className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs transition-all ${
                    activeTab === "team"
                      ? "bg-emerald-500/15 border border-emerald-500/35 text-emerald-300 font-semibold shadow-[0_0_12px_rgba(34,197,94,0.12)]"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] border border-white/[0.05] font-medium"
                  }`}
                >
                  <MessageSquare className="h-3.5 w-3.5 text-blue-400" />
                  <span>Team Activity</span>
                  <span
                    className={`ml-0.5 rounded-full px-2 py-0.2 text-[10px] font-mono ${
                      activeTab === "team"
                        ? "bg-emerald-500/20 text-emerald-200 border border-emerald-500/30"
                        : "bg-white/[0.06] text-zinc-400 border border-white/[0.08]"
                    }`}
                  >
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
      <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.025] to-transparent p-10 text-center backdrop-blur-md shadow-inner">
        {/* Soft radial glow */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-30">
          <div className="h-44 w-44 rounded-full bg-emerald-500/15 blur-3xl" />
        </div>

        {/* Concentric check badge */}
        <div className="relative mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 via-emerald-500/10 to-teal-500/5 border border-emerald-500/30 shadow-[0_0_24px_rgba(34,197,94,0.22)] ring-1 ring-white/10 mb-3">
          <CheckCircle2 className="h-7 w-7 text-emerald-400" />
        </div>

        <h3 className="text-base font-semibold text-white tracking-tight">All Caught Up</h3>
        <p className="mt-1.5 text-xs text-zinc-400 max-w-md mx-auto leading-relaxed">
          No new tasks, commits, or conversations were recorded in this workspace during the selected time window ({data.since_label}). Everything is up to date.
        </p>

        {/* Quick action shortcuts */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
          <button
            onClick={() => onNavigate("/dashboard/tasks")}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 text-xs font-medium text-zinc-300 hover:bg-white/[0.08] hover:border-emerald-500/40 hover:text-emerald-300 transition-all shadow-sm"
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span>View Tasks Board</span>
            <ArrowRight className="h-3 w-3 opacity-60" />
          </button>
          <button
            onClick={() => onNavigate("/dashboard/ai")}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 text-xs font-medium text-zinc-300 hover:bg-white/[0.08] hover:border-emerald-500/40 hover:text-emerald-300 transition-all shadow-sm"
          >
            <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
            <span>Ask Orbit AI</span>
            <ArrowRight className="h-3 w-3 opacity-60" />
          </button>
          <button
            onClick={() => onNavigate("/dashboard/documents")}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 text-xs font-medium text-zinc-300 hover:bg-white/[0.08] hover:border-emerald-500/40 hover:text-emerald-300 transition-all shadow-sm"
          >
            <FileText className="h-3.5 w-3.5 text-blue-400" />
            <span>Knowledge Base</span>
            <ArrowRight className="h-3 w-3 opacity-60" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Critical alerts banner if overdue tasks exist */}
      {data.tasks_overdue.length > 0 && (
        <div className="rounded-xl border border-red-500/30 bg-gradient-to-r from-red-950/40 via-red-950/20 to-surface/90 p-4 shadow-[0_0_24px_rgba(239,68,68,0.15)] backdrop-blur-md">
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-red-300">
              <AlertTriangle className="h-4 w-4 text-red-400" />
              <span>Overdue Tasks Requiring Attention ({data.tasks_overdue.length})</span>
            </div>
            <button
              onClick={() => onNavigate("/dashboard/tasks")}
              className="text-[11px] text-red-300 hover:text-red-200 flex items-center gap-1 font-medium underline"
            >
              Open Tasks <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          <div className="space-y-1.5">
            {data.tasks_overdue.map((t) => (
              <div
                key={t.id}
                onClick={() => onNavigate(t.link)}
                className="flex items-center justify-between rounded-xl bg-white/[0.03] p-3 text-xs hover:border-red-500/50 hover:bg-white/[0.06] border border-white/[0.06] cursor-pointer transition-all group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="h-2 w-2 rounded-full bg-red-400 flex-shrink-0 animate-pulse" />
                  <span className="font-medium text-zinc-200 truncate group-hover:text-red-300 transition-colors">
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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {/* Recent Tasks */}
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-3 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-200 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              Task Developments
            </span>
            <button
              onClick={() => onNavigate("/dashboard/tasks")}
              className="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors"
            >
              Board <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          {data.tasks_created.length === 0 && data.tasks_updated.length === 0 ? (
            <p className="text-xs text-zinc-500 italic py-2">
              No new task creation or updates recorded.
            </p>
          ) : (
            <div className="space-y-2">
              {data.tasks_created.slice(0, 3).map((t) => (
                <div
                  key={`new_${t.id}`}
                  onClick={() => onNavigate(t.link)}
                  className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 hover:border-emerald-500/40 hover:bg-white/[0.05] cursor-pointer transition-all group text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-zinc-200 truncate group-hover:text-emerald-400 transition-colors">
                      {t.title}
                    </span>
                    <span className="rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/25 px-2 py-0.5 text-[9px] font-mono uppercase">
                      New
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-zinc-400 font-mono">
                    <span>by @{t.creator_email?.split("@")[0] || "member"}</span>
                    <span>{formatRelative(t.created_at)}</span>
                  </div>
                </div>
              ))}

              {data.tasks_updated.slice(0, 3).map((t) => (
                <div
                  key={`upd_${t.id}`}
                  onClick={() => onNavigate(t.link)}
                  className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 hover:border-blue-500/40 hover:bg-white/[0.05] cursor-pointer transition-all group text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-zinc-200 truncate group-hover:text-blue-400 transition-colors">
                      {t.title}
                    </span>
                    <span className="rounded-md bg-blue-500/10 text-blue-300 border border-blue-500/25 px-2 py-0.5 text-[9px] font-mono uppercase">
                      {t.status}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-zinc-400 font-mono">
                    <span>Status changed</span>
                    <span>{formatRelative(t.updated_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent GitHub Activity */}
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-3 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-200 flex items-center gap-2">
              <GitPullRequest className="h-4 w-4 text-emerald-400" />
              Repository Intelligence
            </span>
            <button
              onClick={() => onNavigate("/dashboard/integrations")}
              className="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors"
            >
              Integrations <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          {data.github_prs.length === 0 && data.github_commits.length === 0 ? (
            <p className="text-xs text-zinc-500 italic py-2">
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
                  className="block rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 hover:border-emerald-500/40 hover:bg-white/[0.05] cursor-pointer transition-all group text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-zinc-200 truncate group-hover:text-emerald-400 transition-colors">
                      PR #{pr.pr_number}: {pr.title}
                    </span>
                    <span
                      className={`rounded-md px-2 py-0.5 text-[9px] font-mono uppercase border ${
                        pr.state === "merged"
                          ? "bg-purple-500/15 text-purple-300 border-purple-500/30"
                          : pr.state === "open"
                          ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                          : "bg-white/[0.05] text-zinc-400 border-white/[0.08]"
                      }`}
                    >
                      {pr.state}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-zinc-400 font-mono">
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
                  className="block rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 hover:border-white/[0.18] hover:bg-white/[0.05] cursor-pointer transition-all group text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-zinc-200 truncate group-hover:text-white transition-colors">
                      {cm.message}
                    </span>
                    <span className="font-mono text-[10px] text-emerald-400 font-semibold">
                      +{cm.additions}/-{cm.deletions}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-zinc-400 font-mono">
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
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-3 backdrop-blur-md">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-zinc-200 flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-blue-400" />
              Team Discussions & Content
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
            {data.team_activities.slice(0, 6).map((act) => (
              <div
                key={act.id}
                onClick={() => onNavigate(act.target_link)}
                className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 hover:border-blue-400/40 hover:bg-white/[0.05] cursor-pointer transition-all group text-xs"
              >
                <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono">
                  <span className="uppercase text-blue-400 font-semibold">{act.action}</span>
                  <span>{formatRelative(act.created_at)}</span>
                </div>
                <div className="mt-1.5 font-medium text-zinc-200 truncate group-hover:text-blue-300 transition-colors">
                  {act.title}
                </div>
                {act.description && (
                  <p className="mt-0.5 text-[11px] text-zinc-400 truncate">
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
      <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.025] to-transparent p-10 text-center backdrop-blur-md">
        <div className="relative mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 via-emerald-500/10 to-teal-500/5 border border-emerald-500/30 shadow-[0_0_24px_rgba(34,197,94,0.22)] ring-1 ring-white/10 mb-3">
          <CheckCircle2 className="h-7 w-7 text-emerald-400" />
        </div>
        <h3 className="text-base font-semibold text-white tracking-tight">No Task Changes</h3>
        <p className="mt-1 text-xs text-zinc-400 max-w-sm mx-auto">
          No new task creations, status updates, or approaching deadlines recorded in this window ({data.since_label}).
        </p>
        <button
          onClick={() => onNavigate("/dashboard/tasks")}
          className="mt-5 inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 text-xs font-medium text-zinc-300 hover:bg-white/[0.08] hover:border-emerald-500/40 hover:text-emerald-300 transition-all shadow-sm"
        >
          <span>Open Tasks Board</span>
          <ArrowRight className="h-3 w-3 opacity-60" />
        </button>
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {data.tasks_approaching.map((t) => (
              <TaskCard key={`appr_${t.id}`} task={t} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}

      {/* Tasks Assigned To Me */}
      {data.tasks_assigned_to_user.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
            <UserCheck className="h-3.5 w-3.5" />
            Assigned to You in This Window ({data.tasks_assigned_to_user.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {data.tasks_assigned_to_user.map((t) => (
              <TaskCard key={`my_${t.id}`} task={t} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}

      {/* Created in Window */}
      {data.tasks_created.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            Newly Created Tasks ({data.tasks_created.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {data.tasks_created.map((t) => (
              <TaskCard key={`new_${t.id}`} task={t} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}

      {/* Status Changed in Window */}
      {data.tasks_updated.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
            <RefreshCw className="h-3.5 w-3.5 text-blue-400" />
            Status & Assignment Updates ({data.tasks_updated.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
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
      ? "text-red-300 border-red-500/30 bg-red-500/15"
      : task.priority === "medium"
      ? "text-yellow-300 border-yellow-500/30 bg-yellow-500/15"
      : "text-zinc-400 border-white/[0.08] bg-white/[0.04]";

  return (
    <div
      onClick={() => onNavigate(task.link)}
      className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3.5 hover:border-white/[0.18] hover:bg-white/[0.05] hover:shadow-[0_4px_20px_rgba(0,0,0,0.4)] transition-all cursor-pointer group flex flex-col justify-between gap-2.5 backdrop-blur-md"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5 min-w-0">
          <div className="font-medium text-xs text-zinc-200 group-hover:text-emerald-400 transition-colors truncate">
            {task.title}
          </div>
          {task.description && (
            <p className="text-[11px] text-zinc-400 line-clamp-1">
              {task.description}
            </p>
          )}
        </div>
        <span
          className={`rounded-md px-2 py-0.5 text-[9px] font-mono uppercase border flex-shrink-0 ${priColor}`}
        >
          {task.priority}
        </span>
      </div>

      <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono pt-1.5 border-t border-white/[0.06]">
        <div className="flex items-center gap-1.5">
          <span className="rounded-md bg-white/[0.06] border border-white/[0.08] px-2 py-0.5 uppercase text-zinc-300">
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
      <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.025] to-transparent p-10 text-center space-y-3 backdrop-blur-md">
        <div className="relative mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 via-emerald-500/10 to-teal-500/5 border border-emerald-500/30 shadow-[0_0_24px_rgba(34,197,94,0.22)] ring-1 ring-white/10">
          <GitPullRequest className="h-7 w-7 text-emerald-400" />
        </div>
        <h3 className="text-base font-semibold text-white tracking-tight">No Repository Events</h3>
        <p className="text-xs text-zinc-400 max-w-sm mx-auto">
          No pull requests or commits were recorded for active repositories in this workspace during {data.since_label}.
        </p>
        <button
          onClick={() => onNavigate("/dashboard/integrations")}
          className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 text-xs font-medium text-zinc-300 hover:bg-white/[0.08] hover:border-emerald-500/40 hover:text-emerald-300 transition-all shadow-sm"
        >
          <span>Manage GitHub Repositories</span>
          <ArrowRight className="h-3 w-3 opacity-60" />
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Pull Requests */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
          <GitPullRequest className="h-3.5 w-3.5 text-emerald-400" />
          Pull Requests ({data.github_prs.length})
        </h4>
        {data.github_prs.length === 0 ? (
          <p className="text-xs text-zinc-500 italic">No PR activity recorded.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {data.github_prs.map((pr) => (
              <a
                key={pr.id}
                href={pr.url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3.5 hover:border-emerald-500/40 hover:bg-white/[0.05] hover:shadow-[0_4px_20px_rgba(0,0,0,0.4)] transition-all cursor-pointer group flex flex-col justify-between gap-2.5 backdrop-blur-md"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5 min-w-0">
                    <div className="font-medium text-xs text-zinc-200 group-hover:text-emerald-400 transition-colors truncate">
                      PR #{pr.pr_number}: {pr.title}
                    </div>
                    <div className="text-[11px] text-zinc-400">
                      Repo: {pr.repository_name}
                    </div>
                  </div>
                  <span
                    className={`rounded-md px-2 py-0.5 text-[9px] font-mono uppercase border ${
                      pr.state === "merged"
                        ? "bg-purple-500/15 text-purple-300 border-purple-500/30"
                        : pr.state === "open"
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                        : "bg-white/[0.05] text-zinc-400 border-white/[0.08]"
                    }`}
                  >
                    {pr.state}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono pt-1.5 border-t border-white/[0.06]">
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
        <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
          <GitCommit className="h-3.5 w-3.5 text-blue-400" />
          Recent Commits ({data.github_commits.length})
        </h4>
        {data.github_commits.length === 0 ? (
          <p className="text-xs text-zinc-500 italic">No commits pushed in this window.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {data.github_commits.map((cm) => (
              <a
                key={cm.id}
                href={cm.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3.5 hover:border-white/[0.18] hover:bg-white/[0.05] hover:shadow-[0_4px_20px_rgba(0,0,0,0.4)] transition-all cursor-pointer group flex flex-col justify-between gap-2.5 backdrop-blur-md"
              >
                <div>
                  <div className="font-medium text-xs text-zinc-200 line-clamp-1 group-hover:text-white transition-colors">
                    {cm.message}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-zinc-400 font-mono">
                    <span>branch: {cm.branch || "main"}</span>
                    <span className="text-emerald-400 font-semibold">
                      +{cm.additions}/-{cm.deletions}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono pt-1.5 border-t border-white/[0.06]">
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
      <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-b from-white/[0.025] to-transparent p-10 text-center backdrop-blur-md">
        <div className="relative mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 via-emerald-500/10 to-teal-500/5 border border-emerald-500/30 shadow-[0_0_24px_rgba(34,197,94,0.22)] ring-1 ring-white/10 mb-3">
          <MessageSquare className="h-7 w-7 text-blue-400" />
        </div>
        <h3 className="text-base font-semibold text-white tracking-tight">No Team Activity</h3>
        <p className="mt-1 text-xs text-zinc-400 max-w-sm mx-auto">
          No new messages, documents, or team member updates were recorded in this workspace during {data.since_label}.
        </p>
      </div>
    );
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "document":
        return <FileText className="h-4 w-4 text-emerald-400" />;
      case "chat":
        return <MessageSquare className="h-4 w-4 text-blue-400" />;
      case "member":
        return <UserCheck className="h-4 w-4 text-emerald-400" />;
      case "workflow":
        return <Workflow className="h-4 w-4 text-purple-400" />;
      default:
        return <CheckCircle2 className="h-4 w-4 text-zinc-400" />;
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">
          All Team Interactions ({data.team_activities.length})
        </h4>
        <span className="text-[11px] text-zinc-400">
          Showing updates you have permission to view
        </span>
      </div>

      <div className="divide-y divide-white/[0.06] rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden backdrop-blur-md">
        {data.team_activities.map((act) => (
          <div
            key={act.id}
            onClick={() => onNavigate(act.target_link)}
            className="flex items-center justify-between p-3.5 hover:bg-white/[0.04] transition-colors cursor-pointer group"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.04] flex-shrink-0">
                {getCategoryIcon(act.category)}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-xs text-zinc-200 group-hover:text-emerald-400 transition-colors truncate">
                    {act.title}
                  </span>
                  <span className="rounded-md bg-white/[0.05] border border-white/[0.08] px-2 py-0.5 text-[9px] font-mono text-zinc-400 uppercase">
                    {act.action}
                  </span>
                </div>
                {act.description && (
                  <p className="text-[11px] text-zinc-400 truncate mt-0.5">
                    {act.description}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3 text-[10px] text-zinc-400 font-mono flex-shrink-0">
              <span>{formatRelative(act.created_at)}</span>
              <ArrowRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

