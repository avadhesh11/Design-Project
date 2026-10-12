"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/store/workspaceStore";
import api from "@/lib/api";
import {
  Workflow,
  Plus,
  Search,
  ArrowRight,
  GitPullRequest,
  Rocket,
  AlertTriangle,
  Clock,
  Trash2,
  Sparkles,
  Layers,
  X
} from "lucide-react";

interface FlowItem {
  id: string;
  workspace_id: string;
  title: string;
  description?: string;
  visibility: string;
  created_at: string;
  updated_at: string;
  nodes_count?: number;
  edges_count?: number;
}

const TEMPLATES = [
  {
    id: "github_pr_triage",
    title: "GitHub PR Triage & CI",
    description: "Automated PR checks, test suite validation, code review routing & policy alerts.",
    icon: GitPullRequest,
    badge: "Engineering",
    color: "from-purple-500/20 to-indigo-500/20 border-purple-500/30 text-purple-400"
  },
  {
    id: "release_pipeline",
    title: "Staging ➔ Prod Release",
    description: "Tag triggers, artifact compilation, soak test delay, approval gates & release notes.",
    icon: Rocket,
    badge: "DevOps",
    color: "from-blue-500/20 to-cyan-500/20 border-blue-500/30 text-blue-400"
  },
  {
    id: "incident_response",
    title: "Incident War Room",
    description: "Pager alert triage, automatic Meet room creation, mitigation steps & AI post-mortem.",
    icon: AlertTriangle,
    badge: "Operations",
    color: "from-amber-500/20 to-rose-500/20 border-amber-500/30 text-amber-400"
  },
  {
    id: "blank",
    title: "Blank Canvas",
    description: "Start from a clean slate with custom triggers, decisions, actions, and notes.",
    icon: Layers,
    badge: "Custom",
    color: "from-emerald-500/20 to-teal-500/20 border-emerald-500/30 text-emerald-400"
  }
];

export default function FlowsGalleryPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { currentWorkspace } = useWorkspaceStore();

  const { data: flows = [], isLoading: loading } = useQuery<FlowItem[]>({
    queryKey: ["flows", currentWorkspace?.id],
    queryFn: () => api.get(`/flows/?workspace_id=${currentWorkspace?.id}`).then((r) => r.data || []),
    enabled: !!currentWorkspace?.id,
    staleTime: 60000,
  });

  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("github_pr_triage");
  const [flowTitle, setFlowTitle] = useState("");
  const [flowDescription, setFlowDescription] = useState("");
  const flowVisibility = "workspace";
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleCreateFlow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentWorkspace?.id || !flowTitle.trim()) return;

    try {
      setCreating(true);
      const { data } = await api.post("/flows/", {
        workspace_id: currentWorkspace.id,
        title: flowTitle.trim(),
        description: flowDescription.trim() || undefined,
        visibility: flowVisibility,
        template: selectedTemplate
      });

      queryClient.invalidateQueries({ queryKey: ["flows", currentWorkspace.id] });
      setShowCreateModal(false);
      setFlowTitle("");
      setFlowDescription("");
      router.push(`/dashboard/flows/${data.id}`);
    } catch (err) {
      console.error("Failed to create flow:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteFlow = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this flow canvas?")) return;

    try {
      setDeletingId(id);
      await api.delete(`/flows/${id}`);
      queryClient.invalidateQueries({ queryKey: ["flows", currentWorkspace?.id] });
    } catch (err) {
      console.error("Failed to delete flow:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreateFromTemplateQuick = (templateId: string) => {
    setSelectedTemplate(templateId);
    const template = TEMPLATES.find((t) => t.id === templateId);
    setFlowTitle(template ? template.title : "New Flow");
    setFlowDescription(template ? template.description : "");
    setShowCreateModal(true);
  };

  const filteredFlows = flows.filter(
    (f) =>
      f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (f.description && f.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="min-h-screen p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400 shadow-inner">
              <Workflow className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-2.5">
                Orbit Flow
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-purple-500/10 text-purple-400 border border-purple-500/30">
                  Canvas
                </span>
              </h1>
              <p className="text-sm text-zinc-400 mt-0.5">
                Visual process architecture and workflow diagrams linked directly to your tasks & documents.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={() => {
            setSelectedTemplate("blank");
            setFlowTitle("New Workflow Diagram");
            setFlowDescription("");
            setShowCreateModal(true);
          }}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-medium text-sm transition-all duration-200 shadow-lg shadow-purple-600/20 active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" />
          Create New Flow
        </button>
      </div>

      {/* Starter Templates Section */}
      {/* <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-wide uppercase text-orbit-muted flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            Starter Architecture Templates
          </h2>
          <span className="text-xs text-orbit-muted">1-click to scaffold</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {TEMPLATES.map((tmpl) => {
            const Icon = tmpl.icon;
            return (
              <div
                key={tmpl.id}
                onClick={() => handleCreateFromTemplateQuick(tmpl.id)}
                className={`group relative p-4 rounded-2xl bg-gradient-to-br ${tmpl.color} bg-surface/60 backdrop-blur-sm border border-orbit-border hover:border-purple-500/40 cursor-pointer hover:scale-[1.02] hover:shadow-xl transition-all duration-200 flex flex-col justify-between`}
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="p-2 rounded-xl bg-surface/80 border border-orbit-border shadow-sm">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-surface/80 border border-orbit-border text-orbit-text">
                      {tmpl.badge}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-semibold text-orbit-text text-base group-hover:text-purple-400 transition-colors">
                      {tmpl.title}
                    </h3>
                    <p className="text-xs text-orbit-muted mt-1 line-clamp-2 leading-relaxed">
                      {tmpl.description}
                    </p>
                  </div>
                </div>

                <div className="pt-4 flex items-center text-xs font-medium text-purple-400 group-hover:translate-x-1 transition-transform">
                  Scaffold canvas <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </div>
              </div>
            );
          })}
        </div>
      </div> */}

      {/* Flows List Section */}
      <div className="space-y-4 pt-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <h2 className="text-lg font-semibold text-orbit-text">Your Workspace Flows</h2>
            {loading ? (
              <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-medium">
                <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
                Loading flows...
              </span>
            ) : (
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-surface2 text-orbit-muted border border-orbit-border font-medium">
                {flows.length}
              </span>
            )}
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-orbit-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search flows..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-surface border border-orbit-border rounded-xl text-sm text-orbit-text placeholder-orbit-muted focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-colors"
            />
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="p-5 rounded-2xl bg-surface border border-orbit-border animate-pulse space-y-4 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-purple-500/15 border border-purple-500/25 flex items-center justify-center">
                      <div className="w-4 h-4 rounded bg-purple-500/30" />
                    </div>
                    <div className="space-y-1.5">
                      <div className="h-4 w-32 bg-orbit-border rounded-md" />
                      <div className="h-2.5 w-16 bg-orbit-border/60 rounded" />
                    </div>
                  </div>
                  <div className="w-6 h-6 bg-orbit-border/50 rounded-lg" />
                </div>

                <div className="space-y-2 pt-1">
                  <div className="h-3 w-full bg-orbit-border/70 rounded" />
                  <div className="h-3 w-4/5 bg-orbit-border/50 rounded" />
                </div>

                <div className="pt-4 border-t border-orbit-border flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-14 bg-orbit-border/60 rounded" />
                    <div className="h-3 w-16 bg-orbit-border/40 rounded" />
                  </div>
                  <div className="h-3 w-12 bg-purple-500/20 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredFlows.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-orbit-border p-12 text-center space-y-4 bg-surface/40">
            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mx-auto">
              <Workflow className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-medium text-orbit-text">No workflows found</h3>
              <p className="text-sm text-orbit-muted max-w-md mx-auto">
                {searchQuery
                  ? "No workflows match your search query."
                  : "Create your first visual workflow canvas to map process architectures and link tasks."}
              </p>
            </div>
            {!searchQuery && (
              <button
                onClick={() => handleCreateFromTemplateQuick("github_pr_triage")}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium transition-all shadow-md shadow-purple-600/20"
              >
                <Plus className="w-4 h-4" />
                Scaffold from GitHub Template
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredFlows.map((flow) => (
              <div
                key={flow.id}
                onClick={() => router.push(`/dashboard/flows/${flow.id}`)}
                className="group relative p-5 rounded-2xl bg-surface hover:bg-surface2 border border-orbit-border hover:border-purple-500/40 cursor-pointer transition-all duration-200 flex flex-col justify-between hover:shadow-xl hover:shadow-purple-900/10"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20 group-hover:bg-purple-500/20 transition-colors">
                        <Workflow className="w-4 h-4" />
                      </div>
                      <h3 className="font-semibold text-orbit-text text-base group-hover:text-purple-400 transition-colors line-clamp-1">
                        {flow.title}
                      </h3>
                    </div>

                    <button
                      onClick={(e) => handleDeleteFlow(flow.id, e)}
                      disabled={deletingId === flow.id}
                      className="p-1.5 rounded-lg text-orbit-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Delete flow"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <p className="text-xs text-orbit-muted line-clamp-2 leading-relaxed min-h-[32px]">
                    {flow.description || "Interactive canvas diagram for workspace workflow automation and logic mapping."}
                  </p>
                </div>

                <div className="pt-5 border-t border-orbit-border mt-4 flex items-center justify-between text-xs text-orbit-muted">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 font-medium text-orbit-text">
                      <Layers className="w-3.5 h-3.5 text-purple-400" />
                      {flow.nodes_count || 1} steps
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {new Date(flow.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                    </span>
                  </div>

                  <span className="text-purple-400 font-medium group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                    Open <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Flow Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-surface border border-orbit-border p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-orbit-border pb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  <Workflow className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-orbit-text text-lg">Create Workflow Canvas</h3>
                  <p className="text-xs text-orbit-muted">Design process charts and link to Orbit tasks</p>
                </div>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 rounded-lg text-orbit-muted hover:text-orbit-text hover:bg-surface2"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateFlow} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-orbit-text mb-1.5">
                  Workflow Title <span className="text-purple-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. GitHub PR Triage & CI Policy"
                  value={flowTitle}
                  onChange={(e) => setFlowTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-surface2 border border-orbit-border rounded-xl text-sm text-orbit-text placeholder-orbit-muted focus:outline-none focus:border-purple-500/60 focus:ring-1 focus:ring-purple-500/60 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-orbit-text mb-1.5">
                  Description / Purpose (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Describe what this flowchart documents or maps..."
                  value={flowDescription}
                  onChange={(e) => setFlowDescription(e.target.value)}
                  className="w-full px-3.5 py-2 bg-surface2 border border-orbit-border rounded-xl text-sm text-orbit-text placeholder-orbit-muted focus:outline-none focus:border-purple-500/60 focus:ring-1 focus:ring-purple-500/60 resize-none transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-orbit-text mb-1.5">
                  Choose Starter Template
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {TEMPLATES.map((t) => (
                    <div
                      key={t.id}
                      onClick={() => setSelectedTemplate(t.id)}
                      className={`p-3 rounded-xl border cursor-pointer text-left transition-all ${
                        selectedTemplate === t.id
                          ? "bg-purple-500/10 border-purple-500/60 text-purple-400 font-medium"
                          : "bg-surface2/60 border-orbit-border text-orbit-muted hover:border-orbit-border2 hover:text-orbit-text"
                      }`}
                    >
                      <div className="font-medium text-xs text-orbit-text">{t.title}</div>
                      <div className="text-[10px] text-orbit-muted mt-0.5 line-clamp-1">{t.badge}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-orbit-border flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-orbit-muted hover:text-orbit-text hover:bg-surface2 text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !flowTitle.trim()}
                  className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-sm font-medium transition-all shadow-lg shadow-purple-600/20"
                >
                  {creating ? "Scaffolding..." : "Open Canvas"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
