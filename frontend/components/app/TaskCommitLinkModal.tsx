"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Task, GitHubCommit, GitHubPullRequest } from "@/types";
import { formatRelative } from "@/lib/utils";
import {
  GitCommit,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Search,
  Check,
  X,
  HelpCircle,
} from "lucide-react";

interface TaskCommitLinkModalProps {
  task: Task;
  workspaceId: string;
  isCompletionPrompt?: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function TaskCommitLinkModal({
  task,
  workspaceId,
  isCompletionPrompt = false,
  onClose,
  onSuccess,
}: TaskCommitLinkModalProps) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"commit" | "no_commit">(
    task.requires_commit ? "commit" : "commit"
  );
  const [selectedCommitId, setSelectedCommitId] = useState<string>("");
  const [manualSha, setManualSha] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [noCommitReasonCategory, setNoCommitReasonCategory] = useState<string>(
    "Design deliverable / Figma mockup"
  );
  const [customExplanation, setCustomExplanation] = useState<string>("");
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    message?: string;
    commit?: GitHubCommit;
  } | null>(null);

  // Fetch recent commits and PRs from workspace repositories
  const { data: repoData, isLoading: isLoadingCommits } = useQuery<{
    repositories: { id: string; name: string; full_name: string; default_branch: string }[];
    commits: (GitHubCommit & { repository_name?: string })[];
    pull_requests: (GitHubPullRequest & { repository_name?: string })[];
  }>({
    queryKey: ["workspace-repo-commits", workspaceId],
    queryFn: () =>
      api
        .get(`/tasks/workspace/${workspaceId}/repository-commits-and-prs`)
        .then((r) => r.data),
    enabled: !!workspaceId,
  });

  const commitsList = repoData?.commits || [];
  const reposList = repoData?.repositories || [];

  // Filter commits by search query
  const filteredCommits = commitsList.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.message.toLowerCase().includes(q) ||
      c.sha.toLowerCase().includes(q) ||
      (c.author_login && c.author_login.toLowerCase().includes(q))
    );
  });

  // Validate commit SHA via API
  const handleValidateSha = async () => {
    const cleanSha = manualSha.trim().toLowerCase();
    if (!cleanSha || cleanSha.length < 6) {
      setValidationResult({
        valid: false,
        message: "Please enter a valid commit SHA (at least 7 hex characters).",
      });
      return;
    }

    setIsValidating(true);
    setValidationResult(null);

    // First check if already in loaded commits
    const matched = commitsList.find((c) =>
      c.sha.toLowerCase().startsWith(cleanSha)
    );
    if (matched) {
      setValidationResult({
        valid: true,
        message: "Commit verified in repository records.",
        commit: matched,
      });
      setSelectedCommitId(matched.id);
      setIsValidating(false);
      return;
    }

    // Try linking/validating test with backend
    try {
      const res = await api.post(`/tasks/${task.id}/link-commit`, {
        commit_sha: cleanSha,
      });
      const updatedTask: Task = res.data;
      const foundLink = updatedTask.github_links?.find(
        (l) => l.commit?.sha.toLowerCase().startsWith(cleanSha)
      );

      if (foundLink && foundLink.commit) {
        setValidationResult({
          valid: true,
          message: foundLink.verification_notes || "Commit verified against GitHub repository API.",
          commit: foundLink.commit,
        });
        setSelectedCommitId(foundLink.commit.id);
      } else {
        setValidationResult({
          valid: true,
          message: `Commit SHA recorded. Verification status: unconfirmed on remote.`,
        });
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setValidationResult({
        valid: false,
        message:
          axiosErr.response?.data?.detail ||
          "Could not verify commit SHA on connected repository. Check the hash and try again.",
      });
    } finally {
      setIsValidating(false);
    }
  };

  // Submit link commit or complete task
  const submitMutation = useMutation({
    mutationFn: async () => {
      if (isCompletionPrompt) {
        // Completing task
        const payload: {
          commit_sha?: string;
          commit_id?: string;
          no_commit_reason?: string;
          completion_notes?: string;
        } = {};

        if (mode === "commit") {
          if (selectedCommitId) {
            payload.commit_id = selectedCommitId;
          } else if (manualSha.trim()) {
            payload.commit_sha = manualSha.trim();
          }
        } else {
          payload.no_commit_reason = customExplanation.trim()
            ? `${noCommitReasonCategory}: ${customExplanation.trim()}`
            : noCommitReasonCategory;
        }

        return api.post(`/tasks/${task.id}/complete`, payload);
      } else {
        // Just linking commit
        if (selectedCommitId) {
          return api.post(`/tasks/${task.id}/link-commit`, {
            commit_id: selectedCommitId,
          });
        } else if (manualSha.trim()) {
          return api.post(`/tasks/${task.id}/link-commit`, {
            commit_sha: manualSha.trim(),
          });
        }
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", workspaceId] });
      qc.invalidateQueries({ queryKey: ["when-you-were-away", workspaceId] });
      onSuccess?.();
      onClose();
    },
  });

  const canSubmit =
    mode === "commit"
      ? !!selectedCommitId || manualSha.trim().length >= 7
      : !!noCommitReasonCategory;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="orbit-card w-full max-w-2xl max-h-[90vh] flex flex-col bg-surface border border-orbit-border shadow-2xl rounded-xl overflow-hidden animate-scale-up">
        {/* ── Modal Header ─────────────────────────────────────────── */}
        <div className="p-4 sm:p-5 border-b border-orbit-border/80 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-accent/30 bg-accent/10 flex-shrink-0">
              <GitCommit className="h-5 w-5 text-accent" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-display text-base font-semibold text-orbit-text">
                  {isCompletionPrompt
                    ? "Complete Task & Link Commit Evidence"
                    : "Link GitHub Commit Evidence"}
                </h3>
                {task.requires_commit && (
                  <span className="rounded bg-red-500/10 text-red-400 border border-red-500/20 px-1.5 py-0.5 text-[10px] font-mono uppercase">
                    Commit Enforced
                  </span>
                )}
              </div>
              <p className="text-xs text-orbit-muted line-clamp-1 mt-0.5">
                Task: <span className="text-orbit-text font-medium">{task.title}</span>
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-orbit-muted hover:text-orbit-text p-1 rounded-lg hover:bg-surface2 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ── Verification & Correctness Disclaimer ───────────────── */}
        <div className="px-4 py-2.5 sm:px-5 bg-surface2/40 border-b border-orbit-border/60 text-xs text-orbit-muted flex items-start gap-2.5">
          <ShieldCheck className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong className="text-orbit-text font-medium">
              Evidence Verification Policy:
            </strong>{" "}
            Linking a commit verifies code delivery in the connected repository.
            <span className="text-orbit-muted/90 ml-1">
              Note: Commit existence alone does not certify full acceptance criteria or correctness.
            </span>
          </div>
        </div>

        {/* ── Mode Switcher (if completion prompt) ────────────────── */}
        {isCompletionPrompt && (
          <div className="p-4 sm:px-5 pb-0">
            <div className="grid grid-cols-2 gap-2 p-1 rounded-lg bg-surface2/60 border border-orbit-border text-xs font-medium">
              <button
                type="button"
                onClick={() => setMode("commit")}
                className={`py-2 px-3 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                  mode === "commit"
                    ? "bg-surface font-semibold text-accent shadow-sm"
                    : "text-orbit-muted hover:text-orbit-text"
                }`}
              >
                <GitCommit className="h-3.5 w-3.5" />
                <span>Link Commit Evidence</span>
              </button>
              <button
                type="button"
                onClick={() => setMode("no_commit")}
                className={`py-2 px-3 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                  mode === "no_commit"
                    ? "bg-surface font-semibold text-yellow-400 shadow-sm"
                    : "text-orbit-muted hover:text-orbit-text"
                }`}
              >
                <HelpCircle className="h-3.5 w-3.5" />
                <span>No Commit Required</span>
              </button>
            </div>
          </div>
        )}

        {/* ── Modal Body (Scrollable) ──────────────────────────────── */}
        <div className="p-4 sm:p-5 overflow-y-auto space-y-4 flex-1">
          {mode === "commit" ? (
            <div className="space-y-4">
              {/* Manual SHA input + Live validate */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-orbit-text uppercase tracking-wider flex items-center justify-between">
                  <span>Enter or Paste Commit SHA</span>
                  <span className="text-[10px] text-orbit-muted font-normal">
                    Supports short (7-char) or full 40-char SHA
                  </span>
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      value={manualSha}
                      onChange={(e) => {
                        setManualSha(e.target.value);
                        setSelectedCommitId("");
                        setValidationResult(null);
                      }}
                      placeholder="e.g. 7f4a2b9 or full git commit hash"
                      className="orbit-input w-full font-mono text-xs pl-3 pr-8"
                    />
                    {manualSha && (
                      <button
                        onClick={() => {
                          setManualSha("");
                          setValidationResult(null);
                        }}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-orbit-muted hover:text-orbit-text"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={handleValidateSha}
                    disabled={isValidating || !manualSha.trim()}
                    className="orbit-btn-secondary text-xs px-3 flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {isValidating ? (
                      <span className="flex items-center gap-1">
                        <span className="h-3 w-3 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                        Validating...
                      </span>
                    ) : (
                      <>
                        <ShieldCheck className="h-3.5 w-3.5 text-accent" />
                        <span>Validate SHA</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Live validation feedback */}
                {validationResult && (
                  <div
                    className={`mt-2 p-3 rounded-lg border text-xs flex items-start gap-2.5 animate-fade-in ${
                      validationResult.valid
                        ? "bg-accent/10 border-accent/30 text-orbit-text"
                        : "bg-red-500/10 border-red-500/30 text-red-400"
                    }`}
                  >
                    {validationResult.valid ? (
                      <CheckCircle2 className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-1 min-w-0">
                      <div className="font-medium">{validationResult.message}</div>
                      {validationResult.commit && (
                        <div className="text-[11px] text-orbit-muted font-mono space-y-0.5">
                          <div className="truncate text-orbit-text font-normal">
                            &quot;{validationResult.commit.message}&quot;
                          </div>
                          <div className="flex items-center gap-2">
                            <span>Author: @{validationResult.commit.author_login || "dev"}</span>
                            <span>•</span>
                            <span className="text-accent">
                              +{validationResult.commit.additions}/-{validationResult.commit.deletions}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Select from connected repository commits */}
              <div className="space-y-2 pt-2 border-t border-orbit-border/50">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-orbit-text uppercase tracking-wider flex items-center gap-1.5">
                    <GitCommit className="h-3.5 w-3.5 text-accent" />
                    <span>Or Select from Connected Repository Commits</span>
                  </label>
                  <span className="text-[11px] text-orbit-muted">
                    {commitsList.length} available
                  </span>
                </div>

                {reposList.length === 0 ? (
                  <div className="p-4 rounded-lg border border-dashed border-orbit-border text-center text-xs text-orbit-muted space-y-1">
                    <p>No active GitHub repositories connected to this workspace.</p>
                    <p className="text-[11px]">
                      You can enter a commit SHA manually above, or connect a repository in Integrations.
                    </p>
                  </div>
                ) : (
                  <>
                    {/* Search bar */}
                    <div className="relative">
                      <Search className="h-3.5 w-3.5 text-orbit-muted absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search commits by message, SHA, or author..."
                        className="orbit-input w-full pl-8 text-xs font-mono"
                      />
                    </div>

                    {/* Commits list */}
                    {isLoadingCommits ? (
                      <div className="py-6 text-center text-xs text-orbit-muted">
                        Loading repository commits...
                      </div>
                    ) : filteredCommits.length === 0 ? (
                      <div className="py-4 text-center text-xs text-orbit-muted italic">
                        No commits matching your search.
                      </div>
                    ) : (
                      <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1 divide-y divide-orbit-border/30">
                        {filteredCommits.map((c) => {
                          const isSelected = selectedCommitId === c.id;
                          return (
                            <div
                              key={c.id}
                              onClick={() => {
                                setSelectedCommitId(c.id);
                                setManualSha(c.sha);
                                setValidationResult({
                                  valid: true,
                                  message: "Selected verified repository commit.",
                                  commit: c,
                                });
                              }}
                              className={`p-2.5 rounded-lg border transition-all cursor-pointer text-xs flex items-start justify-between gap-3 ${
                                isSelected
                                  ? "bg-accent/10 border-accent text-orbit-text shadow-sm"
                                  : "border-orbit-border/60 bg-surface2/30 hover:border-orbit-border2 hover:bg-surface2/60 text-orbit-muted"
                              }`}
                            >
                              <div className="space-y-1 min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono text-[11px] font-bold text-accent bg-accent/10 border border-accent/20 px-1.5 py-0.2 rounded">
                                    {c.sha.slice(0, 7)}
                                  </span>
                                  <span className="font-medium text-orbit-text truncate">
                                    {c.message}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 text-[10px] text-orbit-muted font-mono">
                                  <span>@{c.author_login || "dev"}</span>
                                  <span>•</span>
                                  <span>{c.branch || "main"}</span>
                                  <span>•</span>
                                  <span>{formatRelative(c.committed_at)}</span>
                                  <span>•</span>
                                  <span className="text-accent font-semibold">
                                    +{c.additions}/-{c.deletions}
                                  </span>
                                </div>
                              </div>

                              <div className="flex-shrink-0 pt-0.5">
                                {isSelected ? (
                                  <div className="h-4 w-4 rounded-full bg-accent flex items-center justify-center text-black font-bold">
                                    <Check className="h-2.5 w-2.5 stroke-[3]" />
                                  </div>
                                ) : (
                                  <div className="h-4 w-4 rounded-full border border-orbit-border" />
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ) : (
            /* ── Explain No Commit Applies ───────────────────────── */
            <div className="space-y-4 animate-fade-in">
              <div className="p-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 text-xs text-orbit-text space-y-1">
                <div className="font-medium text-yellow-400 flex items-center gap-1.5">
                  <HelpCircle className="h-4 w-4" />
                  <span>Deliverable Documentation</span>
                </div>
                <p className="text-[11px] text-orbit-muted leading-relaxed">
                  For tasks that produce non-code deliverables (e.g. design assets, specs, meetings), please record why no repository commit applies.
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-orbit-text uppercase tracking-wider">
                  Select Deliverable Reason
                </label>
                <div className="space-y-1.5">
                  {[
                    "Design deliverable / Figma mockup",
                    "Documentation / Product Spec writing",
                    "Research / Architecture planning / Meeting",
                    "DevOps / Infrastructure configuration outside repo",
                    "Customer support / Manual operational task",
                    "Other deliverable",
                  ].map((cat) => (
                    <label
                      key={cat}
                      className={`flex items-center gap-2.5 p-2.5 rounded-lg border cursor-pointer text-xs transition-all ${
                        noCommitReasonCategory === cat
                          ? "bg-surface2 border-accent text-orbit-text font-medium"
                          : "border-orbit-border/60 hover:bg-surface2/50 text-orbit-muted"
                      }`}
                    >
                      <input
                        type="radio"
                        name="reason_category"
                        checked={noCommitReasonCategory === cat}
                        onChange={() => setNoCommitReasonCategory(cat)}
                        className="accent-accent"
                      />
                      <span>{cat}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-orbit-text uppercase tracking-wider">
                  Additional Notes or Links (Optional)
                </label>
                <textarea
                  rows={2}
                  value={customExplanation}
                  onChange={(e) => setCustomExplanation(e.target.value)}
                  placeholder="e.g. Figma link, Notion doc URL, or summary of deliverable..."
                  className="orbit-input w-full text-xs"
                />
              </div>
            </div>
          )}
        </div>

        {/* ── Modal Footer ─────────────────────────────────────────── */}
        <div className="p-4 sm:p-5 border-t border-orbit-border/80 flex items-center justify-between gap-3 bg-surface2/20">
          <button
            type="button"
            onClick={onClose}
            className="orbit-btn-secondary text-xs px-4"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={() => submitMutation.mutate()}
            disabled={!canSubmit || submitMutation.isPending}
            className="orbit-btn-primary text-xs px-5 flex items-center gap-1.5 disabled:opacity-50"
          >
            {submitMutation.isPending ? (
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-full border-2 border-black border-t-transparent animate-spin" />
                <span>Saving...</span>
              </span>
            ) : (
              <>
                <Check className="h-3.5 w-3.5" />
                <span>
                  {isCompletionPrompt
                    ? mode === "commit"
                      ? "Complete with Commit Evidence"
                      : "Complete with Explanation"
                    : "Link & Verify Commit"}
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
