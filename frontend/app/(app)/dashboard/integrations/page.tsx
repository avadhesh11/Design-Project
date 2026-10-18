"use client";

import { useState, useEffect } from "react";
import { useWorkspaceStore } from "@/store/workspaceStore";
import api from "@/lib/api";
import { Spinner } from "@/components/app/Spinner";
import { GitHubConnection, GitHubRepository, SinceYouWereAway } from "@/types";
import {
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ExternalLink,
  Sparkles,
  GitCommit,
  GitPullRequest,
  GitBranch,
  Clock,
  ArrowUpRight
} from "lucide-react";
import { IntegrationsSkeleton } from "@/components/app/LoadingScreen";



function GithubIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={`fill-current ${className}`} viewBox="0 0 24 24">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

function timeAgo(dateString: string) {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

export default function IntegrationsPage() {
  const { currentWorkspace } = useWorkspaceStore();
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<{
    connected: boolean;
    status: string;
    connection?: GitHubConnection;
    repositories_count: number;
  }>({
    connected: false,
    status: "disconnected",
    repositories_count: 0,
  });
  const [repositories, setRepositories] = useState<GitHubRepository[]>([]);
  const [digest, setDigest] = useState<SinceYouWereAway | null>(null);
  const [installUrl, setInstallUrl] = useState<string>("");
  const [manualInstallId, setManualInstallId] = useState("");
  const [connectingManual, setConnectingManual] = useState(false);
  const [showManualInput, setShowManualInput] = useState(false);
  const [activeTab, setActiveTab] = useState<"commits" | "pull_requests">("commits");

  const fetchData = async () => {
    if (!currentWorkspace?.id) return;
    setLoading(true);
    try {
      // 0. Check if installation_id is present in URL search params (redirected from GitHub)
      if (typeof window !== "undefined") {
        const urlParams = new URLSearchParams(window.location.search);
        const urlInstallId = urlParams.get("installation_id");
        if (urlInstallId) {
          try {
            await api.post(
              `/integrations/github/connect?installation_id=${urlInstallId}&workspace_id=${currentWorkspace.id}`
            );
            window.history.replaceState({}, document.title, window.location.pathname);
          } catch (connectErr) {
            console.error("Auto-connect failed:", connectErr);
          }
        }
      }

      // 1. Get install URL and connection status in parallel
      const [installRes, statusRes] = await Promise.all([
        api.get("/integrations/github/install-url"),
        api.get(`/integrations/github/status?workspace_id=${currentWorkspace.id}`),
      ]);
      setInstallUrl(installRes.data.install_url);
      setConnectionStatus(statusRes.data);

      // 2. If connected, fetch repositories & activity digest, then sync fresh activity in background
      if (statusRes.data.connected) {
        const [reposRes, digestRes] = await Promise.all([
          api.get(`/integrations/github/repositories?workspace_id=${currentWorkspace.id}`),
          api.get(`/github/since-last-seen?workspace_id=${currentWorkspace.id}`),
        ]);
        setRepositories(reposRes.data);
        setDigest(digestRes.data);

        // Background auto-sync with GitHub to pull fresh commits/PRs
        api.post(`/integrations/github/sync-activity?workspace_id=${currentWorkspace.id}`)
          .then(async () => {
            const freshDigest = await api.get(`/github/since-last-seen?workspace_id=${currentWorkspace.id}`);
            setDigest(freshDigest.data);
          })
          .catch((syncErr) => console.log("Background activity sync notice:", syncErr));
      }
    } catch (err) {
      console.error("Failed to load GitHub integration data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleManualConnect = async () => {
    if (!manualInstallId.trim() || !currentWorkspace?.id || connectingManual) return;
    setConnectingManual(true);
    try {
      await api.post(
        `/integrations/github/connect?installation_id=${manualInstallId.trim()}&workspace_id=${currentWorkspace.id}`
      );
      setShowManualInput(false);
      setManualInstallId("");
      await fetchData();
    } catch (err) {
      console.error("Manual connection error:", err);
    } finally {
      setConnectingManual(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkspace?.id]);

  const handleSyncRepositories = async () => {
    if (!currentWorkspace?.id || syncing) return;
    setSyncing(true);
    try {
      const [syncRes, digestRes] = await Promise.all([
        api.post(`/integrations/github/repositories/sync?workspace_id=${currentWorkspace.id}`),
        api.get(`/github/since-last-seen?workspace_id=${currentWorkspace.id}`)
      ]);
      setRepositories(syncRes.data);
      setConnectionStatus((prev) => ({
        ...prev,
        repositories_count: syncRes.data.filter((r: GitHubRepository) => r.is_active).length,
      }));
      setDigest(digestRes.data);
    } catch (err) {
      console.error("Failed to sync repositories:", err);
    } finally {
      setSyncing(false);
    }
  };

  const handleToggleRepository = async (repo: GitHubRepository) => {
    try {
      const { data: updated } = await api.post("/integrations/github/repositories/toggle", {
        repository_id: repo.id,
        is_active: !repo.is_active,
      });

      setRepositories((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
      setConnectionStatus((prev) => ({
        ...prev,
        repositories_count: prev.repositories_count + (updated.is_active ? 1 : -1),
      }));

      // Refresh digest after toggling
      const { data: digestData } = await api.get(
        `/github/since-last-seen?workspace_id=${currentWorkspace?.id}`
      );
      setDigest(digestData);
    } catch (err) {
      console.error("Failed to toggle repository tracking:", err);
    }
  };

  if (loading && repositories.length === 0) {
    return <IntegrationsSkeleton />;
  }


  const recentCommits = digest?.recent_commits || [];
  const recentPRs = digest?.recent_pull_requests || [];

  return (
    <div className="p-6 max-w-5xl space-y-6">
      {/* Header */}
      <div className="animate-fade-up">
        <div className="text-[10px] text-orbit-muted font-mono tracking-widest mb-1">
          WORKSPACE INTEGRATIONS
        </div>
        <h1 className="font-display font-extrabold text-2xl tracking-tight mb-1 text-orbit-text">
          GitHub Intelligence
        </h1>
        <p className="text-orbit-muted text-sm">
          Connect your GitHub App to receive real-time webhooks, track pull requests, and enable AI task correlation.
        </p>
      </div>

      {/* GitHub Connection Card */}
      <div className="orbit-card p-6 animate-[fadeUp_0.5s_0.05s_ease_both]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-surface2 border border-orbit-border flex items-center justify-center flex-shrink-0 text-orbit-text">
              <GithubIcon className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-display font-bold text-base text-orbit-text">GitHub App</span>
                {connectionStatus.connected ? (
                  <span className="flex items-center gap-1 text-[11px] font-mono text-accent bg-accent-dim border border-accent-border px-2 py-0.5 rounded-full">
                    <CheckCircle2 className="w-3 h-3" /> Connected
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-[11px] font-mono text-amber-500 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                    <AlertCircle className="w-3 h-3" /> Setup Required
                  </span>
                )}
              </div>
              <div className="text-xs text-orbit-muted">
                {connectionStatus.connected && connectionStatus.connection ? (
                  <span>
                    Installation ID:{" "}
                    <code className="text-accent font-mono font-medium">
                      {connectionStatus.connection.installation_id}
                    </code>{" "}
                    • {connectionStatus.repositories_count} active repo
                    {connectionStatus.repositories_count === 1 ? "" : "s"}
                  </span>
                ) : (
                  "Install the Orbit GitHub App on your account or organization to select repositories."
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <a
              href={installUrl || "https://github.com/apps/orbit-ai-workspace/installations/new"}
              target="_blank"
              rel="noopener noreferrer"
              className="orbit-btn-primary flex items-center gap-2 text-xs py-2 px-3.5"
            >
              <span>{connectionStatus.connected ? "Manage App" : "Install GitHub App"}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>

            {!connectionStatus.connected && (
              <button
                onClick={() => setShowManualInput(!showManualInput)}
                className="orbit-btn-ghost text-xs font-mono py-2 px-3"
              >
                <span>Link Installation ID</span>
              </button>
            )}

            {connectionStatus.connected && (
              <button
                onClick={handleSyncRepositories}
                disabled={syncing}
                className="orbit-btn-ghost text-xs font-mono py-2 px-3 disabled:opacity-40"
                title="Sync latest commits and PRs from GitHub"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin text-accent" : ""}`} />
                <span>{syncing ? "Syncing..." : "Sync Repos"}</span>
              </button>
            )}
          </div>
        </div>

        {showManualInput && !connectionStatus.connected && (
          <div className="mt-4 pt-4 border-t border-orbit-border flex flex-col sm:flex-row gap-2 items-start sm:items-center">
            <input
              type="text"
              placeholder="e.g. 12345678 (from github.com/settings/installations/ID)"
              value={manualInstallId}
              onChange={(e) => setManualInstallId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleManualConnect()}
              className="orbit-input flex-1 text-xs"
            />
            <button
              onClick={handleManualConnect}
              disabled={connectingManual || !manualInstallId.trim()}
              className="orbit-btn-primary text-xs py-2 px-4 flex-shrink-0 disabled:opacity-40"
            >
              {connectingManual ? <Spinner className="w-3 h-3" /> : "Connect"}
            </button>
          </div>
        )}
      </div>

      {/* Connected Repositories Section */}
      {connectionStatus.connected && (
        <div className="orbit-card p-6 animate-[fadeUp_0.5s_0.1s_ease_both]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold text-sm text-orbit-text">Monitored Repositories</h2>
              <p className="text-xs text-orbit-muted">
                Toggle which repositories Orbit should monitor for commits, PRs, and task automation.
              </p>
            </div>
            <span className="text-[11px] font-mono text-orbit-muted">
              {repositories.filter((r) => r.is_active).length} / {repositories.length} Active
            </span>
          </div>

          {repositories.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-orbit-border rounded-xl text-orbit-muted text-xs">
              No repositories found for this installation. Click &quot;Sync Repos&quot; above to discover them.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {repositories.map((repo) => (
                <div
                  key={repo.id}
                  className="flex items-center justify-between p-3.5 rounded-lg border border-orbit-border bg-surface hover:bg-surface2/50 hover:border-orbit-border2 transition-colors shadow-xs"
                >
                  <div className="flex items-center gap-2.5 min-w-0 pr-2">
                    <div className="w-7 h-7 rounded-md bg-surface2 border border-orbit-border flex items-center justify-center flex-shrink-0 text-orbit-text">
                      <GithubIcon className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-orbit-text truncate">{repo.full_name}</div>
                      <div className="text-[10px] font-mono text-orbit-muted">
                        Branch: {repo.default_branch} {repo.is_private && "• Private"}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleToggleRepository(repo)}
                    className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      repo.is_active ? "bg-accent" : "bg-orbit-border"
                    }`}
                    title={repo.is_active ? "Disable monitoring" : "Enable monitoring"}
                  >
                    <span
                      className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white dark:bg-zinc-200 shadow ring-0 transition duration-200 ease-in-out ${
                        repo.is_active ? "translate-x-4" : "translate-x-0"
                      }`}
                    />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Live Activity & Commits Stream */}
      {connectionStatus.connected && (
        <div className="orbit-card p-6 animate-[fadeUp_0.5s_0.12s_ease_both]">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-5">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-sm text-orbit-text">Recent Repository Activity</h2>
                <span className="flex items-center gap-1 text-[10px] font-mono text-accent bg-accent-dim border border-accent-border px-2 py-0.5 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                  Live Sync
                </span>
              </div>
              <p className="text-xs text-orbit-muted">
                Latest commits, pushes, and pull requests tracked across monitored repositories.
              </p>
            </div>

            {/* Sub-tabs */}
            <div className="flex items-center gap-1.5 p-1 rounded-lg bg-surface2/60 border border-orbit-border">
              <button
                onClick={() => setActiveTab("commits")}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  activeTab === "commits"
                    ? "bg-surface text-orbit-text border border-orbit-border shadow-xs"
                    : "text-orbit-muted hover:text-orbit-text"
                }`}
              >
                <GitCommit className="w-3.5 h-3.5" />
                <span>Commits ({recentCommits.length})</span>
              </button>

              <button
                onClick={() => setActiveTab("pull_requests")}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  activeTab === "pull_requests"
                    ? "bg-surface text-orbit-text border border-orbit-border shadow-xs"
                    : "text-orbit-muted hover:text-orbit-text"
                }`}
              >
                <GitPullRequest className="w-3.5 h-3.5" />
                <span>Pull Requests ({recentPRs.length})</span>
              </button>
            </div>
          </div>

          {/* Commits View */}
          {activeTab === "commits" && (
            <div className="space-y-2.5">
              {recentCommits.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-orbit-border rounded-xl text-orbit-muted text-xs">
                  No commits recorded yet. Click &quot;Sync Repos&quot; to fetch latest pushes.
                </div>
              ) : (
                recentCommits.map((cm) => (
                  <div
                    key={cm.id || cm.sha}
                    className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-lg border border-orbit-border bg-surface hover:border-orbit-border2 hover:bg-surface2/40 transition-all group shadow-xs"
                  >
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="w-7 h-7 rounded-md bg-[#5b8aff]/10 border border-[#5b8aff]/20 flex items-center justify-center flex-shrink-0 text-[#5b8aff] mt-0.5">
                        <GitCommit className="w-4 h-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-medium text-orbit-text line-clamp-2 leading-relaxed">
                          {cm.message}
                        </div>
                        <div className="flex flex-wrap items-center gap-2 mt-1.5 text-[11px] text-orbit-muted font-mono">
                          <span className="text-orbit-text font-medium">@{cm.author_login || "developer"}</span>
                          <span>•</span>
                          <span className="flex items-center gap-1 text-accent">
                            <GitBranch className="w-3 h-3" />
                            {cm.branch || "main"}
                          </span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {timeAgo(cm.committed_at)}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <a
                        href={cm.url || `https://github.com/avadhesh11/Orbit/commit/${cm.sha}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 font-mono text-xs text-orbit-text group-hover:text-accent bg-surface2 hover:bg-surface2/80 px-2.5 py-1.5 rounded-md border border-orbit-border transition-colors shadow-xs"
                      >
                        <code>{cm.sha.slice(0, 7)}</code>
                        <ArrowUpRight className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Pull Requests View */}
          {activeTab === "pull_requests" && (
            <div className="space-y-2.5">
              {recentPRs.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-orbit-border rounded-xl text-orbit-muted text-xs">
                  No pull requests recorded yet for this repository.
                </div>
              ) : (
                recentPRs.map((pr) => (
                  <div
                    key={pr.id || pr.github_pr_id}
                    className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-lg border border-orbit-border bg-surface hover:border-orbit-border2 hover:bg-surface2/40 transition-all group shadow-xs"
                  >
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="w-7 h-7 rounded-md bg-[#22c55e]/10 border border-[#22c55e]/20 flex items-center justify-center flex-shrink-0 text-accent mt-0.5">
                        <GitPullRequest className="w-4 h-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-xs font-semibold text-orbit-text">
                            #{pr.pr_number} {pr.title}
                          </span>
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase ${
                              pr.state === "merged"
                                ? "bg-purple-500/15 text-purple-600 dark:text-purple-400 border border-purple-500/30"
                                : pr.state === "open"
                                ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                                : "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400 border border-zinc-500/30"
                            }`}
                          >
                            {pr.state}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-[11px] text-orbit-muted font-mono">
                          <span className="text-orbit-text font-medium">@{pr.author_login || "developer"}</span>
                          {pr.head_branch && (
                            <>
                              <span>•</span>
                              <span>{pr.head_branch} &rarr; {pr.base_branch || "main"}</span>
                            </>
                          )}
                          <span>•</span>
                          <span>{timeAgo(pr.created_at)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <a
                        href={pr.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 font-mono text-[11px] text-orbit-text group-hover:text-accent bg-surface2 hover:bg-surface2/80 px-2.5 py-1.5 rounded-md border border-orbit-border transition-colors shadow-xs"
                      >
                        <span>View PR</span>
                        <ArrowUpRight className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {/* Intelligence & Webhook Info Card */}
      <div className="grid grid-cols-1 md:grid-cols-1 gap-4 animate-[fadeUp_0.5s_0.15s_ease_both]">
        {/* Since You Were Away Preview */}
        <div className="orbit-card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-accent" />
            <span className="font-semibold text-sm text-orbit-text">Since You Were Away</span>
          </div>
          <p className="text-xs text-orbit-muted mb-4">
            AI-powered activity synthesis of what changed in your workspace repositories.
          </p>
          <div className="p-4 rounded-lg bg-accent-dim border border-accent-border text-xs text-orbit-text leading-relaxed font-normal">
            {digest?.summary ||
              "No new repository changes recorded. Live updates will appear here as webhooks and syncs arrive."}
          </div>
        </div>
      </div>
    </div>
  );
}

