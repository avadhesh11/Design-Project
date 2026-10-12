"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useAuthStore } from "@/store/authStore";
import { Message, WorkspaceMemberDetail, WorkspaceSettings } from "@/types";
import { Avatar } from "@/components/app/Avatar";
import { Spinner } from "@/components/app/Spinner";
import { formatTime, formatRelative } from "@/lib/utils";
import {
  Send,
  Hash,
  User as UserIcon,
  Search,
  Lock,
  MessageSquare,
  Users,
  AlertCircle,
} from "lucide-react";

interface LastMessageInfo {
  content: string;
  created_at: string;
  isMe?: boolean;
}

export default function ChatPage() {
  const { currentWorkspace } = useWorkspaceStore();
  const { user } = useAuthStore();
  const qc = useQueryClient();

  // Active chat target: null = #general public room, string = recipient user_id for DM
  const [selectedRecipientId, setSelectedRecipientId] = useState<string | null>(null);
  const [memberSearch, setMemberSearch] = useState("");
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Local state for instant optimistic messages & realtime stream
  const [chatMessages, setChatMessages] = useState<Message[]>([]);

  // Local storage key for tracking seen timestamps per conversation
  const storageKey = useMemo(() => {
    if (!currentWorkspace?.id || !user?.id) return null;
    return `orbit_chat_last_seen_${currentWorkspace.id}_${user.id}`;
  }, [currentWorkspace?.id, user?.id]);

  // Load last seen map from localStorage
  const [lastSeenMap, setLastSeenMap] = useState<Record<string, string>>(() => {
    if (typeof window === "undefined" || !storageKey) return {};
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  // Persist last seen map updates
  const markConversationAsSeen = useCallback(
    (targetKey: string, timestamp?: string) => {
      const seenTime = timestamp || new Date().toISOString();
      setLastSeenMap((prev) => {
        const updated = { ...prev, [targetKey]: seenTime };
        if (typeof window !== "undefined" && storageKey) {
          try {
            localStorage.setItem(storageKey, JSON.stringify(updated));
          } catch (e) {
            console.error("Failed to save chat seen state:", e);
          }
        }
        return updated;
      });
    },
    [storageKey]
  );

  // 1. Fetch Workspace Settings (to check settings_allow_dm)
  const { data: settings } = useQuery<WorkspaceSettings>({
    queryKey: ["workspace-settings", currentWorkspace?.id],
    queryFn: () => api.get(`/workspaces/${currentWorkspace?.id}/settings`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
  });

  // 2. Fetch Workspace Members for DM list
  const { data: members = [] } = useQuery<WorkspaceMemberDetail[]>({
    queryKey: ["workspace-members", currentWorkspace?.id],
    queryFn: () => api.get(`/workspaces/${currentWorkspace?.id}/members`).then((r) => r.data),
    enabled: !!currentWorkspace?.id,
    staleTime: 30000,
  });

  // 3. Fetch Workspace Inbox for Unread Calculations & Last Message Metadata
  const { data: inboxMessages = [] } = useQuery<Message[]>({
    queryKey: ["chat-inbox", currentWorkspace?.id],
    queryFn: async () => {
      const res = await api.get(`/chat/${currentWorkspace?.id}/inbox?limit=200`);
      return res.data || [];
    },
    enabled: !!currentWorkspace?.id,
    refetchInterval: 15000,
  });

  // 4. Fetch Initial Messages for Current View (Public or DM)
  const { data: serverMessages = [], isLoading } = useQuery<Message[]>({
    queryKey: ["messages", currentWorkspace?.id, selectedRecipientId],
    queryFn: async () => {
      const endpoint = selectedRecipientId
        ? `/chat/${currentWorkspace?.id}/messages?recipient_id=${selectedRecipientId}&limit=100`
        : `/chat/${currentWorkspace?.id}/messages?limit=100`;
      const res = await api.get(endpoint);
      return res.data || [];
    },
    enabled: !!currentWorkspace?.id,
  });

  // Sync server messages into local chatMessages state with robust deduplication
  useEffect(() => {
    if (!serverMessages) return;
    setChatMessages((prev) => {
      // Keep optimistic messages that are not yet on the server
      const pendingOptimistic = prev.filter(
        (p) =>
          p.id.startsWith("optimistic-") &&
          !serverMessages.some(
            (sm) =>
              sm.content === p.content &&
              sm.sender_id === p.sender_id &&
              Math.abs(new Date(sm.created_at).getTime() - new Date(p.created_at).getTime()) < 10000
          )
      );
      return [...serverMessages, ...pendingOptimistic];
    });
  }, [serverMessages]);

  // Whenever user switches conversation, mark as seen
  useEffect(() => {
    const targetKey = selectedRecipientId || "general";
    markConversationAsSeen(targetKey);
  }, [selectedRecipientId, markConversationAsSeen]);

  // Compute Unread Counts and Last Message info for each member and #general
  const { unreadCounts, lastMessageMap, generalUnreadCount, totalUnreadDMs } = useMemo(() => {
    const counts: Record<string, number> = {};
    const lastMsg: Record<string, LastMessageInfo> = {};
    let genUnread = 0;
    let totalDMs = 0;

    inboxMessages.forEach((m) => {
      if (m.recipient_id) {
        // Direct Message
        if (m.recipient_id === user?.id) {
          const senderId = m.sender_id;
          const lastSeen = lastSeenMap[senderId];
          const isCurrentlyOpen = selectedRecipientId === senderId;

          const isUnread =
            !isCurrentlyOpen &&
            (!lastSeen || new Date(m.created_at).getTime() > new Date(lastSeen).getTime());

          if (isUnread) {
            counts[senderId] = (counts[senderId] || 0) + 1;
          }

          if (
            !lastMsg[senderId] ||
            new Date(m.created_at).getTime() > new Date(lastMsg[senderId].created_at).getTime()
          ) {
            lastMsg[senderId] = {
              content: m.content,
              created_at: m.created_at,
              isMe: false,
            };
          }
        } else if (m.sender_id === user?.id) {
          const recipientId = m.recipient_id;
          if (
            !lastMsg[recipientId] ||
            new Date(m.created_at).getTime() > new Date(lastMsg[recipientId].created_at).getTime()
          ) {
            lastMsg[recipientId] = {
              content: m.content,
              created_at: m.created_at,
              isMe: true,
            };
          }
        }
      } else {
        // Public Channel (#general)
        if (m.sender_id !== user?.id) {
          const lastSeenGen = lastSeenMap["general"];
          const isCurrentlyOpen = selectedRecipientId === null;
          const isUnread =
            !isCurrentlyOpen &&
            (!lastSeenGen || new Date(m.created_at).getTime() > new Date(lastSeenGen).getTime());
          if (isUnread) {
            genUnread += 1;
          }
        }
      }
    });

    Object.values(counts).forEach((cnt) => {
      totalDMs += cnt;
    });

    return {
      unreadCounts: counts,
      lastMessageMap: lastMsg,
      generalUnreadCount: genUnread,
      totalUnreadDMs: totalDMs,
    };
  }, [inboxMessages, user?.id, lastSeenMap, selectedRecipientId]);

  // Realtime Supabase subscription with zero-duplicate reconciliation
  useEffect(() => {
    if (!currentWorkspace?.id) return;

    const channel = supabase
      .channel(`chat-workspace-${currentWorkspace.id}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "messages",
          filter: `workspace_id=eq.${currentWorkspace.id}`,
        },
        (payload) => {
          const newMsg = payload.new as Message;

          if (newMsg.recipient_id) {
            const isForMe = newMsg.recipient_id === user?.id;
            const isFromMe = newMsg.sender_id === user?.id;
            const otherUserId = isFromMe ? newMsg.recipient_id : newMsg.sender_id;

            // Update React Query cache for the conversation
            qc.setQueryData<Message[]>(
              ["messages", currentWorkspace.id, otherUserId],
              (old = []) => {
                if (old.some((m) => m.id === newMsg.id)) return old;
                return [...old, newMsg];
              }
            );

            if (selectedRecipientId) {
              const isCurrentChat =
                (isFromMe && newMsg.recipient_id === selectedRecipientId) ||
                (isForMe && newMsg.sender_id === selectedRecipientId);

              if (isCurrentChat) {
                setChatMessages((prev) => {
                  if (prev.some((m) => m.id === newMsg.id)) return prev;

                  const optIndex = prev.findIndex(
                    (m) =>
                      m.id.startsWith("optimistic-") &&
                      m.content === newMsg.content &&
                      m.sender_id === newMsg.sender_id
                  );

                  if (optIndex !== -1) {
                    const clone = [...prev];
                    clone[optIndex] = newMsg;
                    return clone;
                  }

                  return [...prev, newMsg];
                });

                if (isForMe) {
                  markConversationAsSeen(selectedRecipientId, newMsg.created_at);
                }
              }
            }
          } else {
            // Public Room event
            qc.setQueryData<Message[]>(
              ["messages", currentWorkspace.id, null],
              (old = []) => {
                if (old.some((m) => m.id === newMsg.id)) return old;
                return [...old, newMsg];
              }
            );

            if (selectedRecipientId === null) {
              setChatMessages((prev) => {
                if (prev.some((m) => m.id === newMsg.id)) return prev;

                const optIndex = prev.findIndex(
                  (m) =>
                    m.id.startsWith("optimistic-") &&
                    m.content === newMsg.content &&
                    m.sender_id === newMsg.sender_id
                );

                if (optIndex !== -1) {
                  const clone = [...prev];
                  clone[optIndex] = newMsg;
                  return clone;
                }

                return [...prev, newMsg];
              });

              if (newMsg.sender_id !== user?.id) {
                markConversationAsSeen("general", newMsg.created_at);
              }
            }
          }

          // Refresh inbox summary quietly
          qc.invalidateQueries({ queryKey: ["chat-inbox", currentWorkspace.id] });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [currentWorkspace?.id, selectedRecipientId, user?.id, markConversationAsSeen, qc]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Send Message Mutation with Instant Zero-Lag Optimistic Execution
  const sendMutation = useMutation({
    mutationFn: (msgText: string) =>
      api.post(`/chat/${currentWorkspace?.id}/messages`, {
        content: msgText,
        recipient_id: selectedRecipientId || undefined,
      }),
    onSuccess: (res) => {
      const serverMsg = res.data;
      const targetRecipient = selectedRecipientId;

      // Update React Query cache directly so message persists across conversation switches
      qc.setQueryData<Message[]>(
        ["messages", currentWorkspace?.id, targetRecipient],
        (old = []) => {
          if (old.some((m) => m.id === serverMsg.id)) return old;
          return [...old, serverMsg];
        }
      );

      // Reconcile optimistic placeholder with server response
      setChatMessages((prev) => {
        if (prev.some((m) => m.id === serverMsg.id)) return prev;

        const optIndex = prev.findIndex(
          (m) =>
            m.id.startsWith("optimistic-") &&
            m.content === serverMsg.content &&
            m.sender_id === serverMsg.sender_id
        );

        if (optIndex !== -1) {
          const clone = [...prev];
          clone[optIndex] = serverMsg;
          return clone;
        }

        return [...prev, serverMsg];
      });

      qc.invalidateQueries({
        queryKey: ["messages", currentWorkspace?.id, targetRecipient],
      });
      qc.invalidateQueries({
        queryKey: ["chat-inbox", currentWorkspace?.id],
      });
    },
    onError: (err: unknown, msgText: string) => {
      // Remove optimistic placeholder on failure
      setChatMessages((prev) =>
        prev.filter((m) => !(m.id.startsWith("optimistic-") && m.content === msgText))
      );
      setInput(msgText);
      const error = err as { response?: { data?: { detail?: string } } };
      alert(error.response?.data?.detail || "Failed to send message. Please try again.");
    },
  });

  // Handle Instant Send (0ms perceived latency)
  const handleSend = () => {
    const text = input.trim();
    if (!text || sendMutation.isPending) return;

    // 1. Create optimistic message immediately
    const optimisticId = `optimistic-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const optimisticMessage: Message = {
      id: optimisticId,
      content: text,
      workspace_id: currentWorkspace?.id || "",
      sender_id: user?.id || "",
      sender_email: user?.email || "me",
      recipient_id: selectedRecipientId || null,
      created_at: new Date().toISOString(),
    };

    // 2. Synchronously append to local chat stream
    setChatMessages((prev) => [...prev, optimisticMessage]);

    // 3. Clear input immediately
    setInput("");

    // 4. Trigger server mutation
    sendMutation.mutate(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const otherMembers = useMemo(() => {
    return members.filter((m) => m.user_id !== user?.id);
  }, [members, user?.id]);

  const filteredMembers = useMemo(() => {
    if (!memberSearch.trim()) return otherMembers;
    return otherMembers.filter((m) =>
      m.email.toLowerCase().includes(memberSearch.toLowerCase())
    );
  }, [otherMembers, memberSearch]);

  // Dynamic Auto-Sorting:
  // User with most pending/unseen messages is at the very top!
  const sortedMembers = useMemo(() => {
    return [...filteredMembers].sort((a, b) => {
      const unreadA = unreadCounts[a.user_id] || 0;
      const unreadB = unreadCounts[b.user_id] || 0;

      // 1. Highest pending unread messages first (Descending)
      if (unreadB !== unreadA) {
        return unreadB - unreadA;
      }

      // 2. Most recent message time
      const timeA = lastMessageMap[a.user_id]?.created_at
        ? new Date(lastMessageMap[a.user_id].created_at).getTime()
        : 0;
      const timeB = lastMessageMap[b.user_id]?.created_at
        ? new Date(lastMessageMap[b.user_id].created_at).getTime()
        : 0;
      if (timeB !== timeA) {
        return timeB - timeA;
      }

      // 3. Fallback: Alphabetical
      return a.email.localeCompare(b.email);
    });
  }, [filteredMembers, unreadCounts, lastMessageMap]);

  const selectedMember = useMemo(() => {
    if (!selectedRecipientId) return null;
    return members.find((m) => m.user_id === selectedRecipientId);
  }, [members, selectedRecipientId]);

  const isDMDisabled = settings?.settings_allow_dm === false;

  return (
    <div className="flex h-full overflow-hidden bg-bg text-orbit-text">
      {/* Channels & DMs Sidebar */}
      <aside className="w-72 border-r border-orbit-border bg-surface flex flex-col flex-shrink-0 select-none">
        {/* Workspace Title Header */}
        <div className="p-4 border-b border-orbit-border flex items-center justify-between bg-surface/80 backdrop-blur-md">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-accent/30 to-accent/10 border border-accent/30 flex items-center justify-center flex-shrink-0">
              <MessageSquare className="w-3.5 h-3.5 text-accent" />
            </div>
            <div className="min-w-0">
              <h2 className="font-display font-bold text-xs tracking-tight truncate text-orbit-text">
                {currentWorkspace?.name || "Workspace"}
              </h2>
              <span className="text-[10px] text-orbit-muted font-mono block">
                {members.length} member{members.length === 1 ? "" : "s"}
              </span>
            </div>
          </div>
        </div>

        {/* Channels & Direct Messages List */}
        <div className="flex-1 overflow-y-auto px-3 py-3.5 space-y-5">
          {/* Public Channels */}
          <div>
            <div className="text-[10px] font-mono tracking-wider uppercase text-orbit-muted px-2 mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1.5 font-semibold">
                <Hash className="w-3 h-3" />
                <span>Channels</span>
              </span>
              {generalUnreadCount > 0 && selectedRecipientId !== null && (
                <span className="px-1.5 py-0.5 text-[9px] font-bold font-mono bg-accent/20 border border-accent/40 text-accent rounded-full">
                  {generalUnreadCount} new
                </span>
              )}
            </div>

            <button
              onClick={() => setSelectedRecipientId(null)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.2 rounded-xl text-xs transition-all text-left group ${
                selectedRecipientId === null
                  ? "bg-accent-dim border border-accent-border text-accent font-medium shadow-sm"
                  : generalUnreadCount > 0
                  ? "bg-surface2 text-orbit-text hover:bg-surface border border-accent/25"
                  : "text-orbit-muted hover:bg-surface2 hover:text-orbit-text border border-transparent"
              }`}
            >
              <div
                className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors ${
                  selectedRecipientId === null
                    ? "bg-accent text-black font-bold shadow-sm"
                    : "bg-surface2 text-orbit-muted group-hover:text-orbit-text"
                }`}
              >
                <Hash className="w-3.5 h-3.5" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-xs truncate">general</span>
                  {generalUnreadCount > 0 && selectedRecipientId !== null && (
                    <span className="min-w-[18px] h-[18px] px-1.5 flex items-center justify-center text-[10px] font-bold font-mono text-black bg-accent rounded-full shadow-sm">
                      {generalUnreadCount}
                    </span>
                  )}
                </div>
                <span className="text-[10px] text-orbit-muted block truncate">
                  Public workspace room
                </span>
              </div>
            </button>
          </div>

          {/* Direct Messages Section */}
          <div>
            <div className="text-[10px] font-mono tracking-wider uppercase text-orbit-muted px-2 mb-2 flex items-center justify-between">
              <span className="flex items-center gap-1.5 font-semibold">
                <UserIcon className="w-3 h-3" />
                <span>Direct Messages</span>
              </span>
              {totalUnreadDMs > 0 && (
                <span className="px-1.5 py-0.5 text-[9px] font-bold font-mono bg-[#5b8aff] text-white rounded-full shadow-sm">
                  {totalUnreadDMs}
                </span>
              )}
            </div>

            {otherMembers.length > 4 && (
              <div className="mb-2 px-1">
                <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-surface2 border border-orbit-border focus-within:border-accent/40 text-xs text-orbit-muted">
                  <Search className="w-3.5 h-3.5 text-orbit-muted" />
                  <input
                    type="text"
                    placeholder="Find member..."
                    value={memberSearch}
                    onChange={(e) => setMemberSearch(e.target.value)}
                    className="bg-transparent text-orbit-text placeholder:text-orbit-muted outline-none text-xs w-full"
                  />
                </div>
              </div>
            )}

            {isDMDisabled ? (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-[11px] text-red-400 flex items-start gap-2">
                <Lock className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                <span>Direct messaging is disabled by workspace admin.</span>
              </div>
            ) : sortedMembers.length === 0 ? (
              <div className="text-center py-6 text-[11px] text-orbit-muted">
                {memberSearch ? "No members found" : "Invite members to start private chats"}
              </div>
            ) : (
              <div className="space-y-1">
                {sortedMembers.map((m) => {
                  const isSelected = selectedRecipientId === m.user_id;
                  const unreadCount = unreadCounts[m.user_id] || 0;
                  const lastMsg = lastMessageMap[m.user_id];

                  return (
                    <button
                      key={m.user_id}
                      onClick={() => setSelectedRecipientId(m.user_id)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs transition-all text-left relative group ${
                        isSelected
                          ? "bg-accent-dim border border-accent-border text-accent font-medium shadow-sm"
                          : unreadCount > 0
                          ? "bg-surface2 border border-accent/20 text-orbit-text shadow-sm"
                          : "text-orbit-muted hover:bg-surface2 hover:text-orbit-text border border-transparent"
                      }`}
                    >
                      <div className="relative flex-shrink-0">
                        <Avatar email={m.email} size={28} />
                        {unreadCount > 0 ? (
                          <span className="w-2.5 h-2.5 rounded-full bg-accent absolute -top-0.5 -right-0.5 border-2 border-surface" />
                        ) : (
                          <div className="w-2 h-2 rounded-full bg-emerald-500 absolute -bottom-0.5 -right-0.5 border border-surface" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1 mb-0.5">
                          <span
                            className={`truncate text-xs ${
                              unreadCount > 0 ? "font-bold text-orbit-text" : "font-medium"
                            }`}
                          >
                            {m.email.split("@")[0]}
                          </span>
                          {m.role === "admin" && (
                            <span className="text-[8px] px-1 py-0.2 rounded bg-amber-500/10 text-amber-500 font-mono flex-shrink-0">
                              admin
                            </span>
                          )}
                        </div>

                        <div className="flex items-center justify-between gap-1">
                          <span
                            className={`text-[10px] truncate block ${
                              unreadCount > 0
                                ? "text-accent font-medium"
                                : "text-orbit-muted"
                            }`}
                          >
                            {lastMsg
                              ? (lastMsg.isMe ? "You: " : "") + lastMsg.content
                              : m.email}
                          </span>

                          {lastMsg && !unreadCount && (
                            <span className="text-[9px] text-orbit-muted font-mono flex-shrink-0">
                              {formatRelative(lastMsg.created_at)}
                            </span>
                          )}
                        </div>
                      </div>

                      {unreadCount > 0 && (
                        <div className="flex-shrink-0 pl-1">
                          <span className="min-w-[18px] h-[18px] px-1.5 flex items-center justify-center text-[10px] font-bold font-mono text-white bg-[#5b8aff] rounded-full shadow-sm">
                            {unreadCount > 99 ? "99+" : unreadCount}
                          </span>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* User Info Bar at bottom */}
        <div className="p-3 border-t border-orbit-border bg-surface flex items-center gap-2.5">
          <Avatar email={user?.email || "Me"} size={28} />
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold truncate text-orbit-text">
              {user?.email?.split("@")[0]}
            </div>
            <div className="text-[10px] text-accent flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-orbit-muted">Online</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-bg">
        {/* Chat Window Header */}
        <div className="border-b border-orbit-border px-6 py-3.5 flex items-center justify-between bg-surface/80 backdrop-blur-md flex-shrink-0">
          <div className="flex items-center gap-3">
            {selectedMember ? (
              <>
                <div className="relative">
                  <Avatar email={selectedMember.email} size={34} />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 absolute -bottom-0.5 -right-0.5 border-2 border-surface" />
                </div>
                <div>
                  <div className="text-sm font-bold text-orbit-text flex items-center gap-2">
                    <span>{selectedMember.email}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-surface2 text-orbit-muted border border-orbit-border">
                      Direct Message
                    </span>
                  </div>
                  <div className="text-[10px] text-orbit-muted font-mono">
                    Private conversation • Role: {selectedMember.role}
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="w-9 h-9 rounded-xl bg-accent-dim border border-accent-border flex items-center justify-center text-accent">
                  <Hash className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-bold text-orbit-text flex items-center gap-2">
                    <span>general</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                      Public Room
                    </span>
                  </div>
                  <div className="text-[10px] text-orbit-muted font-mono">
                    All workspace members can view and participate
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <div className="text-[11px] font-mono text-orbit-muted flex items-center gap-1.5 px-3 py-1.2 rounded-lg border border-orbit-border bg-surface">
              <Users className="w-3.5 h-3.5 text-accent" />
              <span>{members.length} members</span>
            </div>
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {isLoading && chatMessages.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <Spinner className="w-5 h-5 text-accent" />
            </div>
          ) : chatMessages.length === 0 ? (
            <div className="text-center py-24 text-orbit-muted animate-fade-up max-w-sm mx-auto">
              <div className="w-14 h-14 rounded-2xl bg-surface2 border border-orbit-border flex items-center justify-center mx-auto mb-3 shadow-md">
                {selectedMember ? (
                  <UserIcon className="w-6 h-6 text-accent" />
                ) : (
                  <Hash className="w-6 h-6 text-accent" />
                )}
              </div>
              <div className="text-sm font-semibold text-orbit-text mb-1">
                {selectedMember
                  ? `Direct message with ${selectedMember.email.split("@")[0]}`
                  : "Welcome to #general"}
              </div>
              <p className="text-xs text-orbit-muted leading-relaxed">
                {selectedMember
                  ? "Send a private message to start collaborating 1-on-1."
                  : "This is the central public channel for team discussions and updates."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-1.5 max-w-3xl mx-auto">
              {chatMessages.map((msg, i) => {
                const isMe = msg.sender_id === user?.id;
                const isOptimistic = msg.id.startsWith("optimistic-");
                const showHeader =
                  i === 0 || chatMessages[i - 1].sender_id !== msg.sender_id;

                return (
                  <div
                    key={msg.id}
                    className={`flex gap-3 pt-1 group transition-opacity ${
                      isOptimistic ? "opacity-75" : "opacity-100"
                    }`}
                  >
                    <div className="w-8 flex-shrink-0 mt-0.5">
                      {showHeader ? (
                        <Avatar email={msg.sender_email} size={30} />
                      ) : (
                        <div className="w-8" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      {showHeader && (
                        <div className="flex items-baseline gap-2 mb-1">
                          <span
                            className={`text-xs font-semibold ${
                              isMe ? "text-accent" : "text-[#5b8aff]"
                            }`}
                          >
                            {msg.sender_email.split("@")[0]}
                          </span>
                          <span className="text-[10px] text-orbit-muted font-mono">
                            {formatTime(msg.created_at)}
                          </span>
                        </div>
                      )}
                      <div
                        className={`text-xs leading-relaxed px-3 py-2 rounded-xl border transition-colors inline-block max-w-[92%] break-words shadow-sm ${
                          isMe
                            ? "bg-accent/15 border-accent/30 text-orbit-text"
                            : "bg-surface border-orbit-border text-orbit-text hover:border-orbit-border2"
                        }`}
                      >
                        {msg.content}
                        {isOptimistic && (
                          <span className="text-[9px] text-orbit-muted font-mono ml-2 inline-flex items-center gap-0.5">
                            <Spinner className="w-2.5 h-2.5 text-accent inline" /> sending...
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input Dock Bar */}
        <div className="p-4 border-t border-orbit-border bg-surface flex-shrink-0">
          {selectedRecipientId && isDMDisabled ? (
            <div className="max-w-3xl mx-auto p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>Direct messaging has been disabled in this workspace by the administrator.</span>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto flex items-center gap-2.5">
              <div className="flex-1 flex items-center gap-2 bg-surface2 border border-orbit-border focus-within:border-accent/60 rounded-2xl px-4 py-2.5 transition-all shadow-inner">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    selectedMember
                      ? `Message @${selectedMember.email.split("@")[0]}...`
                      : "Message #general..."
                  }
                  className="flex-1 bg-transparent text-xs text-orbit-text placeholder:text-orbit-muted outline-none"
                />
              </div>
              <button
                onClick={handleSend}
                disabled={!input.trim() || sendMutation.isPending}
                className={`p-3 rounded-2xl flex-shrink-0 transition-all ${
                  input.trim()
                    ? "bg-accent text-black font-semibold shadow-md hover:brightness-110 active:scale-95 cursor-pointer"
                    : "bg-surface2 text-orbit-muted cursor-not-allowed border border-orbit-border"
                }`}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}