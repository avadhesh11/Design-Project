"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { Document } from "@/types";
import { Spinner } from "@/components/app/Spinner";
import { DocumentsSkeleton } from "@/components/app/LoadingScreen";
import { formatRelative } from "@/lib/utils";
import { Plus, FileText, Trash2, Upload, X } from "lucide-react";

export default function DocumentsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { currentWorkspace } = useWorkspaceStore();
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  const { data: docs = [], isLoading } = useQuery<Document[]>({
    queryKey: ["documents", currentWorkspace?.id],
    queryFn: async () => {
      const res = await api.get(`/documents/?workspace_id=${currentWorkspace?.id}`);
      return res.data;
    },
    enabled: !!currentWorkspace?.id,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.post("/documents/", {
        title: newTitle.trim() || "Untitled",
        content: "",
        workspace_id: currentWorkspace?.id,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["workspace-activity"] });
      setShowNew(false);
      setNewTitle("");
      router.push(`/dashboard/documents/${res.data.id}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/documents/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["workspace-activity"] });
    },
  });

  const ws = currentWorkspace;
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!ws) return;
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("workspace_id", ws.id);
    try {
      const { data } = await api.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["workspace-activity"] });
      router.push(`/dashboard/documents/${data.id}`);
    } catch (err) {
      console.error(err);
    }
  };

  if (isLoading && docs.length === 0) return <DocumentsSkeleton />;

  return (
    <div className="max-w-3xl mx-auto p-6">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="section-label mb-1">Documents</div>
          <h1 className="page-title">{docs.length} {docs.length === 1 ? "document" : "documents"}</h1>
        </div>
        <div className="flex items-center gap-2">
          <label className="orbit-btn-ghost text-xs cursor-pointer">
            <Upload className="w-3.5 h-3.5" />
            Upload
            <input
              type="file"
              accept=".txt,.pdf,.docx,.csv,.xlsx,.xls,.md"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
          <button className="orbit-btn-primary text-xs" onClick={() => setShowNew(true)}>
            <Plus className="w-3.5 h-3.5" /> New document
          </button>
        </div>
      </div>

      {/* ── Create form ─────────────────────────────────────────── */}
      {showNew && (
        <div className="orbit-card p-3.5 mb-4 animate-fade-up">
          <div className="flex items-center gap-2">
            <input
              autoFocus
              className="orbit-input flex-1 text-sm"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Document title"
              onKeyDown={(e) => {
                if (e.key === "Enter") createMutation.mutate();
                if (e.key === "Escape") setShowNew(false);
              }}
            />
            <button
              className="orbit-btn-primary text-xs"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? <Spinner className="w-3.5 h-3.5" /> : "Create"}
            </button>
            <button
              className="p-2 text-orbit-muted hover:text-orbit-text transition-colors rounded hover:bg-surface2"
              onClick={() => setShowNew(false)}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* ── Document list ────────────────────────────────────────── */}
      {docs.length === 0 && !showNew ? (
        <div className="orbit-card p-10 flex flex-col items-center text-center gap-4">
          <FileText className="w-8 h-8 text-orbit-muted/40" />
          <div>
            <p className="text-sm font-medium text-orbit-text">No documents yet</p>
            <p className="text-xs text-orbit-muted mt-1 max-w-xs">
              Create a document or upload a file. The AI will index it automatically for workspace-aware answers.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button className="orbit-btn-primary text-xs" onClick={() => setShowNew(true)}>
              <Plus className="w-3.5 h-3.5" /> New document
            </button>
            <label className="orbit-btn-ghost text-xs cursor-pointer">
              <Upload className="w-3.5 h-3.5" /> Upload file
              <input
                type="file"
                accept=".txt,.pdf,.docx,.csv,.xlsx,.xls,.md"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>
        </div>
      ) : (
        <div className="orbit-card overflow-hidden divide-y divide-orbit-border">
          {docs.map((doc) => (
            <div
              key={doc.id}
              className="group flex items-center gap-3 px-4 py-3 hover:bg-surface2 transition-colors cursor-pointer"
              onClick={() => router.push(`/dashboard/documents/${doc.id}`)}
            >
              <FileText className="w-3.5 h-3.5 text-orbit-muted flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-orbit-text truncate font-medium">{doc.title}</div>
                <div className="text-[10px] text-orbit-muted font-mono">
                  Updated {formatRelative(doc.updated_at)}
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteMutation.mutate(doc.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1.5 text-orbit-muted hover:text-red-500 rounded hover:bg-surface2 transition-all"
                title="Delete document"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
