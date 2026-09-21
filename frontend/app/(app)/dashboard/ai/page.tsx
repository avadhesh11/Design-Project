"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useAuthStore } from "@/store/authStore";
import { ChatMessage, AIChatMessage, AIChatSession, WorkspaceSettings } from "@/types";
import { Avatar } from "@/components/app/Avatar";
import { Spinner } from "@/components/app/Spinner";
import {
  Send,
  Database,
  Trash2,
  Plus,
  MessageSquare,
  Edit2,
  Check,
  X,
  Copy,
  PanelLeft,
  Search,
  Bot,
} from "lucide-react";
import api from "@/lib/api";

interface AIMessage {
  id?: string;
  role: "user" | "model";
  content: string;
  sources?: number;
  created_at?: string;
}

interface ContentBlock {
  text?: string;
  content?: string;
}

export default function AIPage() {
  const { currentWorkspace } = useWorkspaceStore();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 1. Fetch AI Sessions
  const { data: sessions, isLoading: loadingSessions } = useQuery<AIChatSession[]>({
    queryKey: ["ai-sessions", currentWorkspace?.id],
    queryFn: () => api.get(`/ai/${currentWorkspace?.id}/sessions`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
    staleTime: 10000,
  });

  const sessionList = useMemo(() => sessions || [], [sessions]);

  // 2. Workspace settings & daily quota
  const { data: settings } = useQuery<WorkspaceSettings>({
    queryKey: ["workspace-settings", currentWorkspace?.id],
    queryFn: () => api.get(`/workspaces/${currentWorkspace?.id}/settings`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  // Auto-select latest session
  useEffect(() => {
    if (sessions && sessions.length > 0 && !activeSessionId) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  // 3. Fetch messages for active session
  const { data: sessionMessages, isLoading: loadingMessages } = useQuery<AIChatMessage[]>({
    queryKey: ["ai-session-messages", currentWorkspace?.id, activeSessionId],
    queryFn: () =>
      activeSessionId
        ? api.get(`/ai/${currentWorkspace?.id}/sessions/${activeSessionId}/messages`).then((r) => r.data)
        : Promise.resolve([]),
    enabled: !!currentWorkspace?.id && !!activeSessionId,
    staleTime: 30000,
  });

  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
    } else if (sessionMessages) {
      setMessages(
        sessionMessages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.message,
          created_at: m.created_at,
        }))
      );
    }
  }, [sessionMessages, activeSessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setInput("");
    setErrorBanner(null);
    inputRef.current?.focus();
  };

  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      api.patch(`/ai/${currentWorkspace?.id}/sessions/${id}`, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-sessions", currentWorkspace?.id] });
      setEditingSessionId(null);
      setEditTitle("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/ai/${currentWorkspace?.id}/sessions/${id}`),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["ai-sessions", currentWorkspace?.id] });
      if (activeSessionId === deletedId) {
        const remaining = sessionList.filter((s) => s.id !== deletedId);
        if (remaining.length > 0) {
          setActiveSessionId(remaining[0].id);
        } else {
          handleNewChat();
        }
      }
    },
  });

  const clearAllMutation = useMutation({
    mutationFn: () => api.delete(`/ai/${currentWorkspace?.id}/history`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-sessions", currentWorkspace?.id] });
      queryClient.invalidateQueries({ queryKey: ["workspace-settings", currentWorkspace?.id] });
      handleNewChat();
    },
  });

  const handleStartRename = (s: AIChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(s.id);
    setEditTitle(s.title);
  };

  const handleSaveRename = (s: AIChatSession, e: React.MouseEvent | React.FormEvent) => {
    e.stopPropagation();
    if (!editTitle.trim()) return;
    renameMutation.mutate({ id: s.id, title: editTitle.trim() });
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(null);
    setEditTitle("");
  };

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const sendMessage = async () => {
    if (!input.trim() || loading || !currentWorkspace?.id) return;

    const userText = input.trim();
    const userMsg: AIMessage = { role: "user", content: userText };
    const history: ChatMessage[] = messages.map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setErrorBanner(null);

    try {
      const res = await api.post("/ai/chat", {
        message: userText,
        workspace_id: currentWorkspace.id,
        session_id: activeSessionId || undefined,
        history,
      });

      const responseText =
        typeof res.data.response === "string"
          ? res.data.response
          : Array.isArray(res.data.response)
          ? res.data.response.map((b: ContentBlock) => b.text || b.content || "").join("")
          : JSON.stringify(res.data.response);

      const aiMsg: AIMessage = {
        role: "model",
        content: responseText || "I couldn't process that response.",
        sources: res.data.sources_used,
      };

      setMessages((prev) => [...prev, aiMsg]);

      if (res.data.session_id && res.data.session_id !== activeSessionId) {
        setActiveSessionId(res.data.session_id);
      }

      queryClient.invalidateQueries({ queryKey: ["ai-sessions", currentWorkspace.id] });
      queryClient.invalidateQueries({ queryKey: ["workspace-settings", currentWorkspace.id] });
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } };
      const errorMessage =
        error.response?.data?.detail || "Something went wrong while connecting to Orbit AI. Please try again.";
      setErrorBanner(errorMessage);
      setMessages((prev) => [
        ...prev,
        { role: "model", content: `Error: ${errorMessage}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessionList;
    return sessionList.filter((s) => s.title.toLowerCase().includes(searchQuery.toLowerCase()));
  }, [sessionList, searchQuery]);

  const quotaRemaining = settings?.ai_daily_limit
    ? Math.max(0, settings.ai_daily_limit - (settings.ai_today_usage || 0))
    : null;

  const currentSessionTitle = activeSessionId
    ? sessionList.find((s) => s.id === activeSessionId)?.title || "Session"
    : "New chat";

  const STARTER_PROMPTS = [
    { title: "Summarize sprint goals", desc: "Extract key objectives from workspace documents" },
    { title: "Draft architecture proposal", desc: "Generate technical documentation for new features" },
    { title: "Workspace task status", desc: "Overview of pending and completed tasks" },
    { title: "Check open pull requests", desc: "Review recent code activity and commits" },
  ];

  return (
    <div className="flex h-full overflow-hidden bg-bg">

      {/* ── Sessions sidebar ──────────────────────────────────────── */}
      <aside
        className={`border-r border-orbit-border bg-surface flex flex-col transition-all duration-200 z-20 flex-shrink-0 ${
          sidebarOpen ? "w-56" : "w-0 overflow-hidden border-none"
        }`}
      >
        {/* Top actions */}
        <div className="p-2 border-b border-orbit-border flex items-center gap-1.5">
          <button
            onClick={handleNewChat}
            className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-md bg-accent-dim border border-accent-border text-accent hover:bg-accent/15 transition-colors text-xs font-medium"
          >
            <Plus className="w-3.5 h-3.5" />
            New chat
          </button>
          {sessionList.length > 0 && (
            <button
              onClick={() => {
                if (confirm("Clear all chat history?")) clearAllMutation.mutate();
              }}
              className="p-1.5 text-orbit-muted hover:text-red-500 hover:bg-surface2 rounded-md transition-colors"
              title="Clear all"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Search */}
        {sessionList.length > 3 && (
          <div className="px-2 pt-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-surface2 border border-orbit-border text-xs text-orbit-muted">
              <Search className="w-3 h-3 flex-shrink-0" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-orbit-text placeholder:text-orbit-muted outline-none text-xs w-full"
              />
            </div>
          </div>
        )}

        {/* Session list */}
        <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
          {sessionList.length > 0 && (
            <div className="text-[9px] text-orbit-muted px-2 py-1.5 font-mono tracking-wider uppercase">
              History ({filteredSessions.length})
            </div>
          )}

          {loadingSessions && sessionList.length === 0 ? (
            <div className="flex justify-center py-6">
              <Spinner className="w-4 h-4" />
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="text-center py-8 text-[11px] text-orbit-muted px-3">
              {searchQuery ? "No matching chats" : "No past sessions"}
            </div>
          ) : (
            filteredSessions.map((s) => {
              const isActive = activeSessionId === s.id;
              const isEditing = editingSessionId === s.id;
              return (
                <div
                  key={s.id}
                  onClick={() => !isEditing && setActiveSessionId(s.id)}
                  className={`group relative flex items-center justify-between px-2 py-1.5 rounded-md text-xs transition-all cursor-pointer ${
                    isActive
                      ? "bg-surface2 text-orbit-text"
                      : "text-orbit-muted hover:bg-surface2 hover:text-orbit-text"
                  }`}
                >
                  {isActive && (
                    <div className="absolute left-0 top-1 bottom-1 w-0.5 bg-accent rounded-full" />
                  )}
                  <div className="flex items-center gap-1.5 min-w-0 flex-1 mr-1 pl-1.5">
                    <MessageSquare className="w-3 h-3 flex-shrink-0 text-orbit-muted" />
                    {isEditing ? (
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveRename(s, e);
                          if (e.key === "Escape") handleCancelRename(e as unknown as React.MouseEvent);
                        }}
                        autoFocus
                        className="bg-surface border border-accent text-orbit-text text-xs px-1.5 py-0.5 rounded outline-none w-full"
                      />
                    ) : (
                      <span className="truncate">{s.title}</span>
                    )}
                  </div>

                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                    {isEditing ? (
                      <>
                        <button onClick={(e) => handleSaveRename(s, e)} className="p-1 hover:text-accent text-orbit-muted rounded" title="Save">
                          <Check className="w-3 h-3" />
                        </button>
                        <button onClick={handleCancelRename} className="p-1 hover:text-red-500 text-orbit-muted rounded" title="Cancel">
                          <X className="w-3 h-3" />
                        </button>
                      </>
                    ) : (
                      <>
                        <button onClick={(e) => handleStartRename(s, e)} className="p-1 hover:text-orbit-text text-orbit-muted rounded" title="Rename">
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(s.id); }}
                          className="p-1 hover:text-red-500 text-orbit-muted rounded"
                          title="Delete"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Quota */}
        {settings && (
          <div className="px-3 py-2.5 border-t border-orbit-border text-[10px] text-orbit-muted flex items-center justify-between font-mono">
            <span>Daily limit</span>
            <span className={settings.ai_daily_limit > 0 && quotaRemaining !== null && quotaRemaining <= 5 ? "text-red-400" : "text-orbit-muted"}>
              {settings.settings_ai_daily_limit > 0
                ? `${settings.ai_today_usage} / ${settings.settings_ai_daily_limit}`
                : "Unlimited"}
            </span>
          </div>
        )}
      </aside>

      {/* ── Main chat area ────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-bg">

        {/* Chat header */}
        <div className="border-b border-orbit-border px-3 py-2.5 flex items-center justify-between bg-surface flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded border border-orbit-border text-orbit-muted hover:text-orbit-text hover:bg-surface2 transition-colors"
              title={sidebarOpen ? "Hide sessions" : "Show sessions"}
            >
              <PanelLeft className="w-3.5 h-3.5" />
            </button>

            <div className="flex items-center gap-2">
              <Bot className="w-3.5 h-3.5 text-orbit-muted" />
              <span className="text-sm font-medium text-orbit-text truncate max-w-[200px]">
                {currentSessionTitle}
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-orbit-border text-orbit-muted hidden sm:inline">
                Gemini 2.5 Flash
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {quotaRemaining !== null && (
              <span
                className={`text-[10px] font-mono px-2 py-1 rounded border ${
                  quotaRemaining <= 5
                    ? "bg-red-500/8 border-red-500/25 text-red-400"
                    : "bg-surface2 border-orbit-border text-orbit-muted"
                }`}
              >
                {quotaRemaining} left today
              </span>
            )}
            <button onClick={handleNewChat} className="orbit-btn-ghost text-xs py-1">
              <Plus className="w-3.5 h-3.5" />
              New chat
            </button>
          </div>
        </div>

        {/* Error banner */}
        {errorBanner && (
          <div className="bg-red-500/8 border-b border-red-500/20 px-4 py-2 text-xs text-red-400 flex items-center justify-between">
            <span>{errorBanner}</span>
            <button onClick={() => setErrorBanner(null)} className="ml-3 hover:text-red-300">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-5">
          <div className="max-w-2xl mx-auto space-y-5">

            {loadingMessages && messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-24 gap-3 text-orbit-muted text-sm">
                <Spinner className="w-5 h-5" />
                <span className="text-xs">Loading conversation...</span>
              </div>
            ) : messages.length === 0 ? (
              /* Empty state — starter prompts */
              <div className="text-center pt-12 pb-8 animate-fade-up">
                <div className="w-10 h-10 rounded-lg bg-accent-dim border border-accent-border flex items-center justify-center mx-auto mb-4">
                  <Bot className="w-5 h-5 text-accent" />
                </div>
                <h2 className="text-base font-semibold text-orbit-text mb-1">How can I help?</h2>
                <p className="text-xs text-orbit-muted max-w-sm mx-auto leading-relaxed mb-8">
                  I have full context of your workspace documents and tasks.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg mx-auto text-left">
                  {STARTER_PROMPTS.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => setInput(prompt.title)}
                      className="p-3 rounded-lg border border-orbit-border bg-surface hover:border-orbit-border2 hover:bg-surface2 transition-all text-left"
                    >
                      <div className="text-xs font-medium text-orbit-text mb-0.5">{prompt.title}</div>
                      <div className="text-[10px] text-orbit-muted">{prompt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, index) => {
                const isUser = msg.role === "user";
                return (
                  <div key={index} className={`flex gap-2.5 animate-fade-up ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                    {/* Avatar */}
                    <div className="flex-shrink-0 mt-0.5">
                      {isUser ? (
                        <Avatar email={user?.email || "User"} size={24} />
                      ) : (
                        <div className="w-6 h-6 rounded-md bg-accent-dim border border-accent-border flex items-center justify-center text-accent">
                          <Bot className="w-3 h-3" />
                        </div>
                      )}
                    </div>

                    {/* Bubble */}
                    <div
                      className={`relative group max-w-[85%] px-3.5 py-2.5 rounded-lg text-sm leading-relaxed ${
                        isUser
                          ? "bg-surface border border-orbit-border text-orbit-text rounded-tr-sm"
                          : "bg-surface2 border border-orbit-border text-orbit-text rounded-tl-sm"
                      }`}
                    >
                      {/* Copy button for AI responses */}
                      {!isUser && (
                        <button
                          onClick={() => copyToClipboard(msg.content, index)}
                          className="absolute top-2 right-2 p-1 rounded border border-orbit-border bg-surface text-orbit-muted hover:text-orbit-text opacity-0 group-hover:opacity-100 transition-all"
                          title="Copy"
                        >
                          {copiedIndex === index ? <Check className="w-2.5 h-2.5 text-accent" /> : <Copy className="w-2.5 h-2.5" />}
                        </button>
                      )}

                      <div className="whitespace-pre-wrap break-words">{msg.content}</div>

                      {/* Source badge */}
                      {msg.sources && msg.sources > 0 && (
                        <div className="mt-2 pt-2 border-t border-orbit-border flex items-center gap-1.5 text-[10px] text-orbit-muted font-mono">
                          <Database className="w-2.5 h-2.5 text-accent" />
                          <span>{msg.sources} doc{msg.sources !== 1 ? "s" : ""} referenced</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {/* Loading indicator */}
            {loading && (
              <div className="flex gap-2.5 animate-fade-up">
                <div className="w-6 h-6 rounded-md bg-accent-dim border border-accent-border flex items-center justify-center text-accent flex-shrink-0 mt-0.5">
                  <Bot className="w-3 h-3" />
                </div>
                <div className="bg-surface2 border border-orbit-border rounded-lg rounded-tl-sm px-3.5 py-2.5 flex items-center gap-2 text-xs text-orbit-muted">
                  <Spinner className="w-3 h-3" />
                  <span>Thinking...</span>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input bar */}
        <div className="px-4 py-3 border-t border-orbit-border bg-surface flex-shrink-0">
          <div className="max-w-2xl mx-auto">
            <div className="flex items-end gap-2 bg-bg border border-orbit-border focus-within:border-orbit-border2 rounded-lg p-2 transition-colors">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your workspace..."
                rows={1}
                className="flex-1 bg-transparent text-sm text-orbit-text placeholder:text-orbit-muted resize-none outline-none py-1 px-1.5 max-h-32 min-h-[20px]"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="p-2 rounded-md bg-accent text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-accent-hover transition-colors flex-shrink-0"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="flex items-center justify-between text-[10px] text-orbit-muted mt-1.5 px-1 font-mono">
              <span>Enter to send · Shift+Enter for newline</span>
              <span>Workspace-grounded AI</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}