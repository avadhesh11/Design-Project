"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  Handle,
  Position,
  MarkerType,
  BackgroundVariant,
  ReactFlowProvider,
  NodeTypes,
  NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { toPng } from "html-to-image";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspaceStore";

import {
  Workflow,
  ArrowLeft,
  Save,
  Sparkles,
  History,
  MessageSquare,
  Download,
  Plus,
  Play,
  Cpu,
  HelpCircle,
  Clock,
  StickyNote,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  X,
  FileText,
  Send,
  RefreshCw,
  Tag,
  GitPullRequest,
  Rocket,
  Bell,
  Box,
  UserCheck,
  RotateCcw,
} from "lucide-react";

// --- Node Data Interface ---
export interface FlowNodeData extends Record<string, unknown> {
  label: string;
  description?: string;
  icon?: string;
  color?: string;
  linked_object_type?: string | null;
  linked_object_id?: string | null;
}

// --- Icon Resolver ---
const ICON_MAP: Record<string, React.ElementType> = {
  Play,
  Cpu,
  HelpCircle,
  Clock,
  StickyNote,
  GitPullRequest,
  Rocket,
  AlertTriangle,
  Bell,
  Box,
  UserCheck,
  RotateCcw,
  FileText,
  Tag,
  Workflow,
};

// --- Custom Nodes ---

function TriggerNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const IconComponent = (data.icon && ICON_MAP[data.icon]) ? ICON_MAP[data.icon] : Play;
  return (
    <div
      className={`relative px-4 py-3 rounded-2xl bg-surface/95 border backdrop-blur-md shadow-xl transition-all duration-200 min-w-[200px] max-w-[260px] ${
        selected
          ? "border-purple-500 ring-2 ring-purple-500/30 scale-[1.02]"
          : "border-purple-500/40 hover:border-purple-500/80"
      }`}
    >
      <div className="flex items-center gap-2.5 mb-1.5">
        <div
          className="p-1.5 rounded-lg text-white shadow-inner flex items-center justify-center"
          style={{ backgroundColor: data.color || "#8B5CF6" }}
        >
          <IconComponent className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 block">
            Trigger Event
          </span>
          <h4 className="text-xs font-semibold text-orbit-text truncate">{data.label || "Trigger"}</h4>
        </div>
      </div>

      {data.description && (
        <p className="text-[11px] text-orbit-muted line-clamp-2 leading-relaxed">{data.description}</p>
      )}

      {data.linked_object_type && (
        <div className="mt-2 pt-2 border-t border-orbit-border flex items-center gap-1.5 text-[10px] text-purple-400 font-medium">
          <Tag className="w-3 h-3 text-purple-400" />
          <span>Linked to {data.linked_object_type}</span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-purple-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className="w-3 h-3 !bg-purple-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
    </div>
  );
}

function ActionNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  const IconComponent = (data.icon && ICON_MAP[data.icon]) ? ICON_MAP[data.icon] : Cpu;
  return (
    <div
      className={`relative px-4 py-3 rounded-2xl bg-surface/95 border backdrop-blur-md shadow-xl transition-all duration-200 min-w-[200px] max-w-[260px] ${
        selected
          ? "border-blue-500 ring-2 ring-blue-500/30 scale-[1.02]"
          : "border-blue-500/40 hover:border-blue-500/80"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 !bg-blue-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className="w-3 h-3 !bg-blue-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />

      <div className="flex items-center gap-2.5 mb-1.5">
        <div
          className="p-1.5 rounded-lg text-white shadow-inner flex items-center justify-center"
          style={{ backgroundColor: data.color || "#3B82F6" }}
        >
          <IconComponent className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 block">
            Action Step
          </span>
          <h4 className="text-xs font-semibold text-orbit-text truncate">{data.label || "Action"}</h4>
        </div>
      </div>

      {data.description && (
        <p className="text-[11px] text-orbit-muted line-clamp-2 leading-relaxed">{data.description}</p>
      )}

      {data.linked_object_type && (
        <div className="mt-2 pt-2 border-t border-orbit-border flex items-center gap-1.5 text-[10px] text-blue-400 font-medium">
          <Tag className="w-3 h-3 text-blue-400" />
          <span>Linked to {data.linked_object_type}</span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-blue-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className="w-3 h-3 !bg-blue-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
    </div>
  );
}

function DecisionNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  return (
    <div
      className={`relative px-4 py-3 rounded-2xl bg-surface/95 border backdrop-blur-md shadow-xl transition-all duration-200 min-w-[210px] max-w-[270px] ${
        selected
          ? "border-amber-500 ring-2 ring-amber-500/30 scale-[1.02]"
          : "border-amber-500/40 hover:border-amber-500/80"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 !bg-amber-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className="w-3 h-3 !bg-amber-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />

      <div className="flex items-center gap-2.5 mb-1.5">
        <div className="p-1.5 rounded-lg text-white shadow-inner flex items-center justify-center bg-amber-500">
          <HelpCircle className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 block">
            Decision Gate
          </span>
          <h4 className="text-xs font-semibold text-orbit-text truncate">{data.label || "Decision?"}</h4>
        </div>
      </div>

      {data.description && (
        <p className="text-[11px] text-orbit-muted line-clamp-2 leading-relaxed">{data.description}</p>
      )}

      <div className="mt-2 pt-2 border-t border-orbit-border flex items-center justify-between text-[10px] text-orbit-muted">
        <span className="text-emerald-400 font-medium">➔ Top/Right: Pass</span>
        <span className="text-rose-400 font-medium">➔ Bottom: Fail</span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        id="yes"
        className="w-3 h-3 !bg-emerald-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="no"
        className="w-3 h-3 !bg-rose-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
    </div>
  );
}

function DelayNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  return (
    <div
      className={`relative px-4 py-3 rounded-2xl bg-surface/95 border backdrop-blur-md shadow-xl transition-all duration-200 min-w-[190px] max-w-[240px] ${
        selected
          ? "border-pink-500 ring-2 ring-pink-500/30 scale-[1.02]"
          : "border-pink-500/40 hover:border-pink-500/80"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 !bg-pink-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />

      <div className="flex items-center gap-2.5 mb-1.5">
        <div className="p-1.5 rounded-lg text-white shadow-inner flex items-center justify-center bg-pink-500">
          <Clock className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-[10px] font-bold uppercase tracking-wider text-pink-400 block">
            Delay / Pause
          </span>
          <h4 className="text-xs font-semibold text-orbit-text truncate">{data.label || "Wait"}</h4>
        </div>
      </div>

      {data.description && (
        <p className="text-[11px] text-orbit-muted line-clamp-2 leading-relaxed">{data.description}</p>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-pink-500 !border-2 !border-surface rounded-full hover:scale-125 transition-transform"
      />
    </div>
  );
}

function NoteNode({ data, selected }: NodeProps<Node<FlowNodeData>>) {
  return (
    <div
      className={`relative px-4 py-3 rounded-2xl bg-amber-500/10 border backdrop-blur-md shadow-xl transition-all duration-200 min-w-[200px] max-w-[260px] ${
        selected
          ? "border-amber-400 ring-2 ring-amber-400/30 scale-[1.02]"
          : "border-amber-400/40 hover:border-amber-400/80"
      }`}
    >
      <div className="flex items-center gap-2 mb-1.5 text-amber-500">
        <StickyNote className="w-4 h-4" />
        <h4 className="text-xs font-bold uppercase tracking-wider text-orbit-text">{data.label || "Architecture Note"}</h4>
      </div>

      <p className="text-[11px] text-orbit-muted leading-relaxed whitespace-pre-wrap">
        {data.description || "Add architectural notes, RFC links or operational playbooks here."}
      </p>

      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 !bg-amber-400 !border !border-surface rounded-full"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 !bg-amber-400 !border !border-surface rounded-full"
      />
    </div>
  );
}

const nodeTypesConfig: NodeTypes = {
  trigger: TriggerNode,
  action: ActionNode,
  decision: DecisionNode,
  delay: DelayNode,
  note: NoteNode,
  default: ActionNode,
};

// --- Main Flow Editor Component ---

function FlowCanvas() {
  const params = useParams();
  const router = useRouter();
  const flowId = params?.id as string;
  const { currentWorkspace } = useWorkspaceStore();

  const [flowMeta, setFlowMeta] = useState<{ title: string; description?: string; visibility?: string }>({
    title: "Loading Flow...",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Nodes & Edges State
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<FlowNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<Node<FlowNodeData> | null>(null);

  // Workspace items for linking
  const [tasks, setTasks] = useState<{ id: string; title: string; status: string }[]>([]);
  const [documents, setDocuments] = useState<{ id: string; title: string }[]>([]);

  // Side drawers
  const [activeDrawer, setActiveDrawer] = useState<"none" | "ai" | "versions" | "comments" | "node_config">("none");

  // AI State
  const [aiQuestion, setAiQuestion] = useState("");
  const [aiExplanation, setAiExplanation] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  // Versioning State
  const [versions, setVersions] = useState<{ id: string; version_name: string; created_at: string }[]>([]);
  const [snapshotName, setSnapshotName] = useState("");

  // Comments State
  const [comments, setComments] = useState<{ id: string; user_email?: string; text: string; created_at: string }[]>([]);
  const [newCommentText, setNewCommentText] = useState("");

  const canvasRef = useRef<HTMLDivElement>(null);

interface RawApiNode {
  node_key: string;
  type?: string;
  position_x: number;
  position_y: number;
  label?: string;
  data_json?: {
    description?: string;
    icon?: string;
    color?: string;
  };
  linked_object_type?: string;
  linked_object_id?: string;
}

interface RawApiEdge {
  edge_key: string;
  source_node_key: string;
  target_node_key: string;
  source_handle?: string;
  target_handle?: string;
  label?: string;
}

  // Load Flow Data
  const loadFlow = useCallback(async () => {
    if (!flowId) return;
    try {
      setLoading(true);
      const { data } = await api.get(`/flows/${flowId}`);
      setFlowMeta({
        title: data.title,
        description: data.description,
        visibility: data.visibility,
      });

      // Transform nodes
      const loadedNodes: Node<FlowNodeData>[] = (data.nodes || []).map((n: RawApiNode) => ({
        id: n.node_key,
        type: n.type || "action",
        position: { x: n.position_x, y: n.position_y },
        data: {
          label: n.label || "Step",
          description: n.data_json?.description || "",
          icon: n.data_json?.icon || "Cpu",
          color: n.data_json?.color || "#3B82F6",
          linked_object_type: n.linked_object_type,
          linked_object_id: n.linked_object_id,
        },
      }));

      // Transform edges
      const loadedEdges: Edge[] = (data.edges || []).map((e: RawApiEdge) => ({
        id: e.edge_key,
        source: e.source_node_key,
        target: e.target_node_key,
        sourceHandle: e.source_handle,
        targetHandle: e.target_handle,
        label: e.label || undefined,
        animated: true,
        style: { stroke: "#8B5CF6", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#8B5CF6" },
      }));

      setNodes(loadedNodes);
      setEdges(loadedEdges);
      setVersions(data.versions || []);
      setComments(data.comments || []);
      setHasUnsavedChanges(false);
    } catch (err) {
      console.error("Failed to load flow:", err);
    } finally {
      setLoading(false);
    }
  }, [flowId, setNodes, setEdges]);

  const loadWorkspaceObjects = useCallback(async () => {
    if (!currentWorkspace?.id) return;
    try {
      const [tasksRes, docsRes] = await Promise.allSettled([
        api.get(`/tasks/?workspace_id=${currentWorkspace.id}`),
        api.get(`/documents/?workspace_id=${currentWorkspace.id}`),
      ]);

      if (tasksRes.status === "fulfilled") {
        setTasks(tasksRes.value.data || []);
      }
      if (docsRes.status === "fulfilled") {
        setDocuments(docsRes.value.data || []);
      }
    } catch (err) {
      console.error("Failed to fetch workspace items for linking:", err);
    }
  }, [currentWorkspace?.id]);

  useEffect(() => {
    loadFlow();
    loadWorkspaceObjects();
  }, [loadFlow, loadWorkspaceObjects]);

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            animated: true,
            style: { stroke: "#8B5CF6", strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#8B5CF6" },
          },
          eds
        )
      );
      setHasUnsavedChanges(true);
    },
    [setEdges]
  );

  const handleSave = async () => {
    if (!flowId) return;
    try {
      setSaving(true);
      // 1. Update workflow title and metadata
      await api.put(`/flows/${flowId}`, {
        title: flowMeta.title?.trim() || "Untitled Workflow",
        description: flowMeta.description || undefined,
        visibility: flowMeta.visibility || "workspace",
      });

      // 2. Synchronize canvas nodes and edges
      const syncPayload = {
        nodes: nodes.map((n) => ({
          node_key: n.id,
          type: n.type || "action",
          label: n.data.label || "Step",
          position_x: n.position.x,
          position_y: n.position.y,
          data_json: {
            description: n.data.description,
            icon: n.data.icon,
            color: n.data.color,
          },
          linked_object_type: n.data.linked_object_type || null,
          linked_object_id: n.data.linked_object_id || null,
        })),
        edges: edges.map((e) => ({
          edge_key: e.id,
          source_node_key: e.source,
          target_node_key: e.target,
          source_handle: e.sourceHandle || null,
          target_handle: e.targetHandle || null,
          label: e.label ? String(e.label) : null,
          data_json: {},
        })),
      };

      await api.post(`/flows/${flowId}/sync`, syncPayload);
      setHasUnsavedChanges(false);
    } catch (err) {
      console.error("Save flow failed:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleAddNode = (type: string, label: string, icon: string, color: string) => {
    const id = `node-${Date.now()}`;
    const position = {
      x: 300 + Math.random() * 100,
      y: 200 + Math.random() * 100,
    };

    const newNode: Node<FlowNodeData> = {
      id,
      type,
      position,
      data: {
        label,
        description: "",
        icon,
        color,
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setHasUnsavedChanges(true);
    setSelectedNode(newNode);
    setActiveDrawer("node_config");
  };

  const handleNodeClick = (_: React.MouseEvent, node: Node<FlowNodeData>) => {
    setSelectedNode(node);
    setActiveDrawer("node_config");
  };

  const handleUpdateSelectedNode = (key: keyof FlowNodeData, value: FlowNodeData[keyof FlowNodeData]) => {
    if (!selectedNode) return;
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === selectedNode.id) {
          const updatedData = { ...n.data, [key]: value };
          return { ...n, data: updatedData };
        }
        return n;
      })
    );
    setSelectedNode((prev) => (prev ? { ...prev, data: { ...prev.data, [key]: value } } : null));
    setHasUnsavedChanges(true);
  };

  const handleDeleteSelectedNode = () => {
    if (!selectedNode) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
    setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
    setSelectedNode(null);
    setActiveDrawer("none");
    setHasUnsavedChanges(true);
  };

  // AI Explain
  const handleAIExplain = async () => {
    try {
      setAiLoading(true);
      setActiveDrawer("ai");
      const { data } = await api.post(`/flows/${flowId}/ai-explain`, {
        question: aiQuestion.trim() || undefined,
      });
      setAiExplanation(data.explanation || "No analysis available.");
    } catch (err) {
      console.error("AI Explain failed:", err);
      setAiExplanation("Failed to connect to AI analysis engine.");
    } finally {
      setAiLoading(false);
    }
  };

  // Create Snapshot
  const handleCreateSnapshot = async () => {
    try {
      const { data } = await api.post(`/flows/${flowId}/versions`, {
        version_name: snapshotName.trim() || undefined,
      });
      setVersions((prev) => [data, ...prev]);
      setSnapshotName("");
    } catch (err) {
      console.error("Failed to create snapshot:", err);
    }
  };

  // Restore Snapshot
  const handleRestoreSnapshot = async (versionId: string) => {
    if (!confirm("Restore this version? Unsaved changes will be replaced.")) return;
    try {
      await api.post(`/flows/${flowId}/versions/${versionId}/restore`);
      await loadFlow();
    } catch (err) {
      console.error("Failed to restore version:", err);
    }
  };

  // Add Comment
  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCommentText.trim()) return;
    try {
      const { data } = await api.post(`/flows/${flowId}/comments`, {
        text: newCommentText.trim(),
        node_key: selectedNode ? selectedNode.id : undefined,
      });
      setComments((prev) => [data, ...prev]);
      setNewCommentText("");
    } catch (err) {
      console.error("Failed to add comment:", err);
    }
  };

  // Export as PNG
  const handleExportPNG = async () => {
    if (!canvasRef.current) return;
    try {
      const dataUrl = await toPng(canvasRef.current, {
        backgroundColor: "#09090b",
        quality: 0.95,
      });
      const link = document.createElement("a");
      link.download = `${flowMeta.title.replace(/\s+/g, "_")}_flowchart.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error("PNG export error:", err);
    }
  };

  // Export JSON Blueprint
  const handleExportJSON = () => {
    const blueprint = {
      title: flowMeta.title,
      description: flowMeta.description,
      exported_at: new Date().toISOString(),
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type,
        label: n.data.label,
        data: n.data,
        position: n.position,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
      })),
    };
    const blob = new Blob([JSON.stringify(blueprint, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = `${flowMeta.title.replace(/\s+/g, "_")}_blueprint.json`;
    link.href = url;
    link.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-zinc-400">
        <div className="flex items-center gap-3">
          <RefreshCw className="w-5 h-5 animate-spin text-purple-400" />
          <span>Loading workflow canvas...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full flex flex-col bg-bg overflow-hidden select-none">
      {/* Top Header / Action Bar */}
      <header className="h-14 border-b border-orbit-border bg-surface/90 backdrop-blur-md px-4 flex items-center justify-between z-30 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dashboard/flows")}
            className="p-1.5 rounded-lg text-orbit-muted hover:text-orbit-text hover:bg-surface2 transition-colors"
            title="Back to Flows"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Workflow className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={flowMeta.title}
              onChange={(e) => {
                setFlowMeta((prev) => ({ ...prev, title: e.target.value }));
                setHasUnsavedChanges(true);
              }}
              onBlur={async () => {
                if (flowMeta.title.trim()) {
                  try {
                    await api.put(`/flows/${flowId}`, { title: flowMeta.title.trim() });
                  } catch (e) {
                    console.error("Failed to rename workflow:", e);
                  }
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  (e.target as HTMLInputElement).blur();
                }
              }}
              className="bg-transparent border border-transparent hover:border-orbit-border focus:border-purple-500/50 text-orbit-text font-semibold text-sm focus:outline-none focus:ring-1 focus:ring-purple-500/50 rounded px-1.5 py-0.5 transition-colors"
            />
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            {saving ? (
              <span className="text-orbit-muted flex items-center gap-1">
                <RefreshCw className="w-3 h-3 animate-spin text-purple-400" /> Saving...
              </span>
            ) : hasUnsavedChanges ? (
              <span className="text-amber-400/80 flex items-center gap-1 font-medium">
                • Unsaved changes
              </span>
            ) : (
              <span className="text-emerald-400/80 flex items-center gap-1 font-medium">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Saved
              </span>
            )}

            {/* Visibility Selector */}
            <select
              value={flowMeta.visibility || "workspace"}
              onChange={async (e) => {
                const val = e.target.value;
                setFlowMeta((prev) => ({ ...prev, visibility: val }));
                try {
                  await api.put(`/flows/${flowId}`, { visibility: val });
                } catch (err) {
                  console.error("Failed to update visibility:", err);
                }
              }}
              className="ml-2 px-2.5 py-1 bg-surface2 hover:bg-surface border border-orbit-border rounded-lg text-[11px] font-medium text-orbit-text focus:outline-none focus:border-purple-500 cursor-pointer"
            >
              <option value="workspace">🌐 Workspace (Visible to all)</option>
              <option value="private">🔒 Private (Only creator & admins)</option>
            </select>

            {/* Live Reload / Sync */}
            <button
              onClick={loadFlow}
              className="p-1.5 rounded-lg text-orbit-muted hover:text-orbit-text hover:bg-surface2 transition-colors"
              title="Sync / Refresh latest canvas"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right Tools */}
        <div className="flex items-center gap-2">
          {/* AI Explain */}
          <button
            onClick={handleAIExplain}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 text-purple-300 text-xs font-medium transition-all shadow-inner"
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            AI Explain

          </button>

          {/* Versions / Snapshots */}
          <button
            onClick={() => setActiveDrawer(activeDrawer === "versions" ? "none" : "versions")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all ${
              activeDrawer === "versions"
                ? "bg-zinc-800 text-white border-zinc-600"
                : "bg-zinc-900 hover:bg-zinc-800/80 text-zinc-300 border-zinc-800"
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Snapshots
          </button>

          {/* Comments */}
          <button
            onClick={() => setActiveDrawer(activeDrawer === "comments" ? "none" : "comments")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all ${
              activeDrawer === "comments"
                ? "bg-zinc-800 text-white border-zinc-600"
                : "bg-zinc-900 hover:bg-zinc-800/80 text-zinc-300 border-zinc-800"
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Comments
            {comments.length > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full bg-purple-600 text-white text-[10px]">
                {comments.length}
              </span>
            )}
          </button>

          {/* Export Dropdown */}
          <div className="relative group">
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-zinc-900 hover:bg-zinc-800/80 border border-zinc-800 text-zinc-300 text-xs font-medium transition-all">
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
            <div className="absolute right-0 top-full mt-1 w-44 rounded-xl bg-zinc-900 border border-zinc-800 p-1.5 shadow-2xl hidden group-hover:block z-50">
              <button
                onClick={handleExportPNG}
                className="w-full text-left px-3 py-2 rounded-lg text-xs text-zinc-200 hover:bg-purple-500/10 hover:text-purple-300 flex items-center gap-2"
              >
                <Download className="w-3.5 h-3.5" /> Export PNG Image
              </button>
              <button
                onClick={handleExportJSON}
                className="w-full text-left px-3 py-2 rounded-lg text-xs text-zinc-200 hover:bg-purple-500/10 hover:text-purple-300 flex items-center gap-2"
              >
                <FileText className="w-3.5 h-3.5" /> Export JSON Blueprint
              </button>
            </div>
          </div>

          {/* Save Button */}
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-all shadow-lg shadow-purple-600/20 active:scale-95 disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            Save
          </button>
        </div>
      </header>

      {/* Main Canvas Area */}
      <div className="flex-1 flex relative overflow-hidden" ref={canvasRef}>
        {/* Left Node Palette Sidebar */}
        <aside className="w-56 border-r border-zinc-800/80 bg-zinc-900/60 backdrop-blur-md p-3.5 flex flex-col gap-3 z-20 shrink-0">
          <div className="text-[11px] font-bold tracking-wider uppercase text-zinc-400 flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5 text-purple-400" />
            Add Flow Components
          </div>

          <div className="space-y-2">
            <button
              onClick={() => handleAddNode("trigger", "Event Trigger", "Play", "#8B5CF6")}
              className="w-full p-2.5 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 text-left flex items-center gap-2.5 text-xs text-purple-200 transition-all hover:scale-[1.02]"
            >
              <div className="p-1.5 rounded-lg bg-purple-600 text-white">
                <Play className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="font-semibold text-white">Trigger Node</div>
                <div className="text-[10px] text-zinc-400">Webhook, Push, Cron</div>
              </div>
            </button>

            <button
              onClick={() => handleAddNode("action", "Execute Step", "Cpu", "#3B82F6")}
              className="w-full p-2.5 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-left flex items-center gap-2.5 text-xs text-blue-200 transition-all hover:scale-[1.02]"
            >
              <div className="p-1.5 rounded-lg bg-blue-600 text-white">
                <Cpu className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="font-semibold text-white">Action Step</div>
                <div className="text-[10px] text-zinc-400">Task, API, Notify</div>
              </div>
            </button>

            <button
              onClick={() => handleAddNode("decision", "Condition Gate", "HelpCircle", "#F59E0B")}
              className="w-full p-2.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-left flex items-center gap-2.5 text-xs text-amber-200 transition-all hover:scale-[1.02]"
            >
              <div className="p-1.5 rounded-lg bg-amber-600 text-white">
                <HelpCircle className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="font-semibold text-white">Decision Gate</div>
                <div className="text-[10px] text-zinc-400">Pass / Fail branching</div>
              </div>
            </button>

            <button
              onClick={() => handleAddNode("delay", "Wait / Timer", "Clock", "#EC4899")}
              className="w-full p-2.5 rounded-xl bg-pink-500/10 hover:bg-pink-500/20 border border-pink-500/30 text-left flex items-center gap-2.5 text-xs text-pink-200 transition-all hover:scale-[1.02]"
            >
              <div className="p-1.5 rounded-lg bg-pink-600 text-white">
                <Clock className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="font-semibold text-white">Wait Marker</div>
                <div className="text-[10px] text-zinc-400">Delay / Approval pause</div>
              </div>
            </button>

            <button
              onClick={() => handleAddNode("note", "Team Note", "StickyNote", "#FCD34D")}
              className="w-full p-2.5 rounded-xl bg-yellow-500/10 hover:bg-yellow-500/20 border border-yellow-500/30 text-left flex items-center gap-2.5 text-xs text-yellow-200 transition-all hover:scale-[1.02]"
            >
              <div className="p-1.5 rounded-lg bg-yellow-600 text-black font-bold">
                <StickyNote className="w-3.5 h-3.5 text-white" />
              </div>
              <div>
                <div className="font-semibold text-white">Sticky Note</div>
                <div className="text-[10px] text-zinc-400">Collaborative note</div>
              </div>
            </button>
          </div>

          <div className="mt-auto pt-4 border-t border-zinc-800 text-[11px] text-zinc-500 space-y-1.5">
            <div className="font-medium text-zinc-400">Quick Tips:</div>
            <div>• Drag handles to connect</div>
            <div>• Click any node to link to Task/Doc</div>
            <div>• Press Del to remove selected</div>
          </div>
        </aside>

        {/* React Flow Viewport */}
        <div className="flex-1 h-full relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={(changes) => {
              onNodesChange(changes);
              setHasUnsavedChanges(true);
            }}
            onEdgesChange={(changes) => {
              onEdgesChange(changes);
              setHasUnsavedChanges(true);
            }}
            onConnect={onConnect}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypesConfig}
            fitView
            className="bg-zinc-950"
          >
            <Background color="#27272a" gap={20} size={1.5} variant={BackgroundVariant.Dots} />
            <Controls className="!bg-zinc-900 !border-zinc-800 !text-white rounded-xl shadow-2xl fill-white" />
            <MiniMap
              className="!bg-zinc-900/90 !border-zinc-800 rounded-xl overflow-hidden shadow-2xl"
              nodeColor={(node) => {
                if (node.type === "trigger") return "#8B5CF6";
                if (node.type === "decision") return "#F59E0B";
                if (node.type === "delay") return "#EC4899";
                if (node.type === "note") return "#FCD34D";
                return "#3B82F6";
              }}
            />
          </ReactFlow>
        </div>

        {/* --- Right Slide-out Drawers --- */}

        {/* 1. Node Config & Object Linking Drawer */}
        {activeDrawer === "node_config" && selectedNode && (
          <div className="w-80 border-l border-zinc-800/80 bg-zinc-900/95 backdrop-blur-md p-4 flex flex-col justify-between z-30 shrink-0 animate-in slide-in-from-right duration-200">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-purple-500/20 text-purple-400">
                    <Tag className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-white text-sm">Step Properties</h3>
                </div>
                <button
                  onClick={() => setActiveDrawer("none")}
                  className="p-1 rounded text-zinc-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Title Input */}
              <div>
                <label className="block text-[11px] font-medium text-zinc-400 mb-1">Step Label</label>
                <input
                  type="text"
                  value={String(selectedNode.data.label || "")}
                  onChange={(e) => handleUpdateSelectedNode("label", e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              {/* Description Input */}
              <div>
                <label className="block text-[11px] font-medium text-zinc-400 mb-1">
                  Description / Documentation
                </label>
                <textarea
                  rows={3}
                  value={String(selectedNode.data.description || "")}
                  onChange={(e) => handleUpdateSelectedNode("description", e.target.value)}
                  placeholder="Explain what occurs in this step..."
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500 resize-none"
                />
              </div>

              {/* Linking to Orbit Object (Task / Document) */}
              <div className="pt-2 border-t border-zinc-800/80 space-y-3">
                <div className="flex items-center justify-between">
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-purple-400">
                    Link to Workspace Object
                  </label>
                  {selectedNode.data.linked_object_type && (
                    <button
                      onClick={() => {
                        handleUpdateSelectedNode("linked_object_type", null);
                        handleUpdateSelectedNode("linked_object_id", null);
                      }}
                      className="text-[10px] text-zinc-500 hover:text-red-400"
                    >
                      Clear link
                    </button>
                  )}
                </div>

                <div className="space-y-2">
                  <div>
                    <label className="block text-[10px] text-zinc-400 mb-1">Link to Task</label>
                    <select
                      value={
                        selectedNode.data.linked_object_type === "task"
                          ? String(selectedNode.data.linked_object_id || "")
                          : ""
                      }
                      onChange={(e) => {
                        if (e.target.value) {
                          handleUpdateSelectedNode("linked_object_type", "task");
                          handleUpdateSelectedNode("linked_object_id", e.target.value);
                        } else {
                          handleUpdateSelectedNode("linked_object_type", null);
                          handleUpdateSelectedNode("linked_object_id", null);
                        }
                      }}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-purple-500"
                    >
                      <option value="">-- No task linked --</option>
                      {tasks.map((t) => (
                        <option key={t.id} value={t.id}>
                          [{t.status}] {t.title}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] text-zinc-400 mb-1">Link to Document</label>
                    <select
                      value={
                        selectedNode.data.linked_object_type === "document"
                          ? String(selectedNode.data.linked_object_id || "")
                          : ""
                      }
                      onChange={(e) => {
                        if (e.target.value) {
                          handleUpdateSelectedNode("linked_object_type", "document");
                          handleUpdateSelectedNode("linked_object_id", e.target.value);
                        } else {
                          handleUpdateSelectedNode("linked_object_type", null);
                          handleUpdateSelectedNode("linked_object_id", null);
                        }
                      }}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-zinc-200 focus:outline-none focus:border-purple-500"
                    >
                      <option value="">-- No document linked --</option>
                      {documents.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.title}
                        </option>
                      ))}
                    </select>
                  </div>

                  {selectedNode.data.linked_object_type && (
                    <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs flex items-center justify-between">
                      <span className="truncate">
                        Linked: {String(selectedNode.data.linked_object_type)} #
                        {String(selectedNode.data.linked_object_id || "").slice(0, 8)}
                      </span>
                      <button
                        onClick={() => {
                          const route =
                            selectedNode.data.linked_object_type === "task"
                              ? `/dashboard/tasks`
                              : `/dashboard/documents`;
                          router.push(route);
                        }}
                        className="p-1 hover:text-white"
                        title="Jump to object"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <button
              onClick={handleDeleteSelectedNode}
              className="w-full mt-4 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" /> Delete Step
            </button>
          </div>
        )}

        {/* 2. AI Explain Drawer */}
        {activeDrawer === "ai" && (
          <div className="w-88 border-l border-zinc-800/80 bg-zinc-900/95 backdrop-blur-md p-4 flex flex-col justify-between z-30 shrink-0 animate-in slide-in-from-right duration-200">
            <div className="space-y-4 overflow-y-auto pr-1">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-purple-500/20 text-purple-400">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white text-sm">AI Flow Explainer</h3>
                    <p className="text-[10px] text-zinc-400">Powered by Gemini 2.5 Flash</p>
                  </div>
                </div>
                <button onClick={() => setActiveDrawer("none")} className="p-1 text-zinc-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {aiLoading ? (
                <div className="p-8 text-center space-y-3">
                  <RefreshCw className="w-6 h-6 animate-spin text-purple-400 mx-auto" />
                  <p className="text-xs text-zinc-400">Analyzing nodes, pathways and decision points...</p>
                </div>
              ) : aiExplanation ? (
                <div className="space-y-3">
                  <div className="p-3.5 rounded-xl bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-200 leading-relaxed whitespace-pre-wrap">
                    {aiExplanation}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-zinc-500 text-center py-6">
                  Ask AI to analyze this workflow diagram, trace critical pathways, or draft team SOP docs.
                </p>
              )}
            </div>

            <div className="pt-3 border-t border-zinc-800 space-y-2">
              <input
                type="text"
                placeholder="Ask e.g. What are the decision gates?"
                value={aiQuestion}
                onChange={(e) => setAiQuestion(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500"
              />
              <button
                onClick={handleAIExplain}
                disabled={aiLoading}
                className="w-full py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium flex items-center justify-center gap-1.5 transition-all shadow-lg shadow-purple-600/20"
              >
                <Sparkles className="w-3.5 h-3.5" /> Re-Analyze Flow
              </button>
            </div>
          </div>
        )}

        {/* 3. Version Snapshots Drawer */}
        {activeDrawer === "versions" && (
          <div className="w-80 border-l border-zinc-800/80 bg-zinc-900/95 backdrop-blur-md p-4 flex flex-col justify-between z-30 shrink-0 animate-in slide-in-from-right duration-200">
            <div className="space-y-4 overflow-y-auto pr-1">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-purple-400" />
                  <h3 className="font-semibold text-white text-sm">Version Snapshots</h3>
                </div>
                <button onClick={() => setActiveDrawer("none")} className="p-1 text-zinc-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Create Snapshot Form */}
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Snapshot name (e.g. Pre-Q3 Architecture)"
                  value={snapshotName}
                  onChange={(e) => setSnapshotName(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500"
                />
                <button
                  onClick={handleCreateSnapshot}
                  className="w-full py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium flex items-center justify-center gap-1 transition-all"
                >
                  <Plus className="w-3.5 h-3.5" /> Save Snapshot
                </button>
              </div>

              <div className="space-y-2 pt-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">History</div>
                {versions.length === 0 ? (
                  <p className="text-xs text-zinc-500 text-center py-4">No snapshots saved yet.</p>
                ) : (
                  versions.map((v) => (
                    <div
                      key={v.id}
                      className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="font-medium text-white">{v.version_name}</div>
                        <div className="text-[10px] text-zinc-500">
                          {new Date(v.created_at).toLocaleDateString()} {new Date(v.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                      <button
                        onClick={() => handleRestoreSnapshot(v.id)}
                        className="px-2 py-1 rounded bg-zinc-800 hover:bg-purple-600 hover:text-white text-zinc-300 text-[10px] font-medium transition-colors"
                      >
                        Restore
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* 4. Comments Drawer */}
        {activeDrawer === "comments" && (
          <div className="w-80 border-l border-zinc-800/80 bg-zinc-900/95 backdrop-blur-md p-4 flex flex-col justify-between z-30 shrink-0 animate-in slide-in-from-right duration-200">
            <div className="space-y-4 overflow-y-auto pr-1">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-purple-400" />
                  <h3 className="font-semibold text-white text-sm">Flow Comments</h3>
                </div>
                <button onClick={() => setActiveDrawer("none")} className="p-1 text-zinc-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-2.5">
                {comments.length === 0 ? (
                  <p className="text-xs text-zinc-500 text-center py-6">
                    No comments yet. Start a discussion on this flow diagram.
                  </p>
                ) : (
                  comments.map((c) => (
                    <div key={c.id} className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 space-y-1">
                      <div className="flex items-center justify-between text-[10px] text-zinc-400">
                        <span className="font-medium text-purple-300">{c.user_email || "Teammate"}</span>
                        <span>{new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <p className="text-xs text-zinc-200">{c.text}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            <form onSubmit={handleAddComment} className="pt-3 border-t border-zinc-800 flex gap-2">
              <input
                type="text"
                placeholder={selectedNode ? `Comment on ${selectedNode.data.label}...` : "Write a comment..."}
                value={newCommentText}
                onChange={(e) => setNewCommentText(e.target.value)}
                className="flex-1 px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500"
              />
              <button
                type="submit"
                disabled={!newCommentText.trim()}
                className="p-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

export default function FlowCanvasPage() {
  return (
    <ReactFlowProvider>
      <FlowCanvas />
    </ReactFlowProvider>
  );
}
