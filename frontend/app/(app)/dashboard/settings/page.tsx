"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useAuthStore } from "@/store/authStore";
import { WorkspaceMemberDetail, WorkspaceSettings } from "@/types";
import { Avatar } from "@/components/app/Avatar";
import { Spinner } from "@/components/app/Spinner";
import { formatDate } from "@/lib/utils";
import {
  Shield,
  MessageSquare,
  UploadCloud,
  Lock,
  Users,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  Save,
  CheckCircle2,
  Zap,
} from "lucide-react";

export default function SettingsPage() {
  const { currentWorkspace, setCurrentWorkspace } = useWorkspaceStore();
  const { user } = useAuthStore();
  const qc = useQueryClient();

  const [copied, setCopied] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Local state for settings form
  const [allowDM, setAllowDM] = useState(true);
  const [aiLimit, setAiLimit] = useState(50);
  const [allowUploads, setAllowUploads] = useState(true);
  const [restrictInvites, setRestrictInvites] = useState(false);

  // 1. Fetch Workspace Settings
  const { data: settings, isLoading: loadingSettings } = useQuery<WorkspaceSettings>({
    queryKey: ["workspace-settings", currentWorkspace?.id],
    queryFn: () => api.get(`/workspaces/${currentWorkspace?.id}/settings`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  // 2. Fetch Workspace Members
  const { data: members = [] } = useQuery<WorkspaceMemberDetail[]>({
    queryKey: ["workspace-members", currentWorkspace?.id],
    queryFn: () => api.get(`/workspaces/${currentWorkspace?.id}/members`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  useEffect(() => {
    if (settings) {
      setAllowDM(settings.settings_allow_dm);
      setAiLimit(settings.settings_ai_daily_limit);
      setAllowUploads(settings.settings_allow_file_uploads);
      setRestrictInvites(settings.settings_restrict_invites);
    }
  }, [settings]);

  // Update Settings Mutation
  const updateSettingsMutation = useMutation({
    mutationFn: (newSettings: {
      settings_allow_dm: boolean;
      settings_ai_daily_limit: number;
      settings_allow_file_uploads: boolean;
      settings_restrict_invites: boolean;
    }) => api.patch(`/workspaces/${currentWorkspace?.id}/settings`, newSettings),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspace-settings", currentWorkspace?.id] });
      setSuccessToast("Workspace settings saved successfully!");
      setTimeout(() => setSuccessToast(null), 3000);
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } } };
      alert(error.response?.data?.detail || "Failed to update workspace settings");
    },
  });

  // Update Member Role Mutation
  const updateRoleMutation = useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: string }) =>
      api.patch(`/workspaces/${currentWorkspace?.id}/members/${memberId}/role`, { role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspace-members", currentWorkspace?.id] });
      setSuccessToast("Member role updated!");
      setTimeout(() => setSuccessToast(null), 2500);
    },
  });

  // Remove Member Mutation
  const removeMemberMutation = useMutation({
    mutationFn: (memberId: string) =>
      api.delete(`/workspaces/${currentWorkspace?.id}/members/${memberId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspace-members", currentWorkspace?.id] });
      setSuccessToast("Member removed from workspace");
      setTimeout(() => setSuccessToast(null), 2500);
    },
  });

  // Regenerate Invite Code Mutation
  const regenerateInviteMutation = useMutation({
    mutationFn: () => api.post(`/workspaces/${currentWorkspace?.id}/regenerate-invite`),
    onSuccess: (res) => {
      setCurrentWorkspace(res.data);
      setSuccessToast("New invite code generated!");
      setTimeout(() => setSuccessToast(null), 2500);
    },
  });

  const handleSaveSettings = () => {
    updateSettingsMutation.mutate({
      settings_allow_dm: allowDM,
      settings_ai_daily_limit: Number(aiLimit),
      settings_allow_file_uploads: allowUploads,
      settings_restrict_invites: restrictInvites,
    });
  };

  const copyInvite = () => {
    if (currentWorkspace) {
      navigator.clipboard.writeText(currentWorkspace.invite_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isAdmin = settings?.is_admin || currentWorkspace?.owner_id === user?.id;

  if (loadingSettings && !settings) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="w-5 h-5 text-accent" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] text-orbit-muted font-mono tracking-widest mb-1">
            WORKSPACE GOVERNANCE
          </div>
          <h1 className="font-display font-extrabold text-2xl tracking-tight flex items-center gap-2 text-orbit-text">
            <span>Workspace Settings & Controls</span>
            {isAdmin ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-dim border border-accent-border text-accent">
                Admin Mode
              </span>
            ) : (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface2 text-orbit-muted border border-orbit-border">
                Member View
              </span>
            )}
          </h1>
          <p className="text-orbit-muted text-xs mt-0.5">
            Configure team communication permissions, AI usage quotas, and manage members.
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={handleSaveSettings}
            disabled={updateSettingsMutation.isPending}
            className="orbit-btn-primary text-xs px-4 py-2 flex items-center gap-1.5 shadow-md shadow-accent/10"
          >
            {updateSettingsMutation.isPending ? (
              <Spinner className="w-3.5 h-3.5" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            <span>Save Settings</span>
          </button>
        )}
      </div>

      {/* Success Toast */}
      {successToast && (
        <div className="p-3 rounded-xl bg-accent/10 border border-accent/30 text-xs text-accent flex items-center gap-2 animate-fade-up">
          <CheckCircle2 className="w-4 h-4" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Invite Code & Overview */}
      <div className="orbit-card p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs font-bold text-orbit-text mb-1">Workspace Invite Code</div>
            <div className="text-[11px] text-orbit-muted">
              Share this code with team members to join{" "}
              <strong className="text-orbit-text">{currentWorkspace?.name}</strong>.
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface2 border border-orbit-border font-mono text-xs text-accent">
              <span>{currentWorkspace?.invite_code}</span>
              <button
                onClick={copyInvite}
                className="hover:text-orbit-text text-orbit-muted transition-colors"
                title="Copy code"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-accent" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>

            {isAdmin && (
              <button
                onClick={() => regenerateInviteMutation.mutate()}
                disabled={regenerateInviteMutation.isPending}
                className="orbit-btn-ghost text-xs px-2.5 py-1.5 flex items-center gap-1"
                title="Regenerate code"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${regenerateInviteMutation.isPending ? "animate-spin" : ""}`}
                />
                <span className="hidden sm:inline">Regenerate</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Governance & Control Center */}
      <div className="orbit-card p-5 space-y-5">
        <div className="flex items-center gap-2 pb-3 border-b border-orbit-border">
          <Shield className="w-4 h-4 text-accent" />
          <span className="font-display font-bold text-sm text-orbit-text">Policy & Feature Controls</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Direct Messaging Toggle */}
          <div className="p-4 rounded-xl border border-orbit-border bg-surface2/40 flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-semibold text-orbit-text">
                <MessageSquare className="w-3.5 h-3.5 text-accent" />
                <span>Direct Messaging (1-on-1)</span>
              </div>
              <p className="text-[11px] text-orbit-muted leading-relaxed">
                Allow members to initiate private, 1-on-1 direct message conversations with each other.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer mt-0.5">
              <input
                type="checkbox"
                checked={allowDM}
                disabled={!isAdmin}
                onChange={(e) => setAllowDM(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-surface2 border border-orbit-border peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent disabled:opacity-40" />
            </label>
          </div>

          {/* Document Uploads Toggle */}
          <div className="p-4 rounded-xl border border-orbit-border bg-surface2/40 flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-semibold text-orbit-text">
                <UploadCloud className="w-3.5 h-3.5 text-accent" />
                <span>Document & File Uploads</span>
              </div>
              <p className="text-[11px] text-orbit-muted leading-relaxed">
                Allow workspace members to upload PDF, DOCX, and TXT files for AI grounding.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer mt-0.5">
              <input
                type="checkbox"
                checked={allowUploads}
                disabled={!isAdmin}
                onChange={(e) => setAllowUploads(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-surface2 border border-orbit-border peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent disabled:opacity-40" />
            </label>
          </div>

          {/* Daily AI Rate Limit */}
          <div className="p-4 rounded-xl border border-orbit-border bg-surface2/40 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-orbit-text">
                <Zap className="w-3.5 h-3.5 text-accent" />
                <span>Daily AI Quota per User</span>
              </div>
              <span className="text-xs font-mono font-bold text-accent">
                {aiLimit === 0 ? "Unlimited" : `${aiLimit} msgs / day`}
              </span>
            </div>
            <p className="text-[11px] text-orbit-muted leading-relaxed">
              Limit the maximum number of AI prompts each team member can send every 24 hours. (0 = unlimited).
            </p>
            {isAdmin && (
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="range"
                  min="0"
                  max="200"
                  step="10"
                  value={aiLimit}
                  onChange={(e) => setAiLimit(Number(e.target.value))}
                  className="w-full accent-accent bg-surface2 rounded-lg h-1.5 cursor-pointer"
                />
                <div className="flex gap-1">
                  {[10, 50, 100, 0].map((preset) => (
                    <button
                      key={preset}
                      onClick={() => setAiLimit(preset)}
                      className={`text-[10px] px-2 py-0.5 rounded border transition-colors font-mono ${
                        aiLimit === preset
                          ? "bg-accent text-black border-accent font-bold"
                          : "border-orbit-border text-orbit-muted hover:text-orbit-text bg-surface"
                      }`}
                    >
                      {preset === 0 ? "∞" : preset}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Restrict Invite Code */}
          <div className="p-4 rounded-xl border border-orbit-border bg-surface2/40 flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-semibold text-orbit-text">
                <Lock className="w-3.5 h-3.5 text-accent" />
                <span>Restrict Invite Visibility</span>
              </div>
              <p className="text-[11px] text-orbit-muted leading-relaxed">
                When enabled, only Workspace Admins can view or copy the workspace invite code.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer mt-0.5">
              <input
                type="checkbox"
                checked={restrictInvites}
                disabled={!isAdmin}
                onChange={(e) => setRestrictInvites(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-surface2 border border-orbit-border peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent disabled:opacity-40" />
            </label>
          </div>
        </div>
      </div>

      {/* Member Governance & Roles */}
      <div className="orbit-card p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-orbit-border">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-accent" />
            <span className="font-display font-bold text-sm text-orbit-text">
              Workspace Members ({members.length})
            </span>
          </div>
          <span className="text-[11px] text-orbit-muted font-mono">
            {members.filter((m) => m.role === "admin").length} Admins
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-orbit-border text-orbit-muted font-mono text-[10px] uppercase">
                <th className="py-2.5 px-3">Member</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Joined Date</th>
                {isAdmin && <th className="py-2.5 px-3 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-orbit-border">
              {members.map((m) => {
                const isOwner = m.user_id === currentWorkspace?.owner_id;
                const isSelf = m.user_id === user?.id;

                return (
                  <tr key={m.id} className="hover:bg-surface2/60 transition-colors">
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2.5">
                        <Avatar email={m.email} size={28} />
                        <div>
                          <div className="font-medium text-orbit-text flex items-center gap-1.5">
                            <span>{m.email.split("@")[0]}</span>
                            {isSelf && (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-accent-dim text-accent font-mono">
                                you
                              </span>
                            )}
                            {isOwner && (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-500 font-mono">
                                owner
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-orbit-muted">{m.email}</div>
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-3">
                      {isAdmin && !isOwner ? (
                        <div className="flex items-center gap-2">
                          <select
                            value={m.role}
                            onChange={(e) =>
                              updateRoleMutation.mutate({ memberId: m.id, role: e.target.value })
                            }
                            className="bg-surface2 border border-orbit-border rounded-lg px-2 py-1 text-xs text-orbit-text outline-none focus:border-accent"
                          >
                            <option value="admin">Admin</option>
                            <option value="member">Member</option>
                            <option value="viewer">Viewer</option>
                          </select>
                        </div>
                      ) : (
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                            m.role === "admin"
                              ? "bg-accent-dim text-accent border border-accent-border"
                              : "bg-surface2 text-orbit-muted"
                          }`}
                        >
                          {m.role}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-3 text-orbit-muted font-mono text-[11px]">
                      {formatDate(m.joined_at)}
                    </td>

                    {isAdmin && (
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {!isOwner && !isSelf && (
                            <>
                              {m.role !== "admin" ? (
                                <button
                                  onClick={() =>
                                    updateRoleMutation.mutate({ memberId: m.id, role: "admin" })
                                  }
                                  className="flex items-center gap-1 px-2 py-1 rounded bg-accent-dim border border-accent-border text-accent hover:bg-accent/20 text-[11px] font-medium transition-colors"
                                  title="Promote this user to Admin"
                                >
                                  <Shield className="w-3 h-3" />
                                  <span>Promote to Admin</span>
                                </button>
                              ) : (
                                <button
                                  onClick={() =>
                                    updateRoleMutation.mutate({ memberId: m.id, role: "member" })
                                  }
                                  className="flex items-center gap-1 px-2 py-1 rounded bg-surface2 hover:bg-surface text-orbit-muted hover:text-orbit-text text-[11px] transition-colors border border-orbit-border"
                                  title="Demote to Member"
                                >
                                  <span>Demote to Member</span>
                                </button>
                              )}

                              <button
                                onClick={() => {
                                  if (confirm(`Remove ${m.email} from this workspace?`)) {
                                    removeMemberMutation.mutate(m.id);
                                  }
                                }}
                                className="p-1.5 text-orbit-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                title="Remove member"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
