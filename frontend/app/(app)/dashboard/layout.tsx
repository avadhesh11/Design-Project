"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/authStore";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useThemeStore } from "@/store/themeStore";
import { Avatar } from "@/components/app/Avatar";
import { Spinner } from "@/components/app/Spinner";
import api from "@/lib/api";
import { Workspace } from "@/types";
import {
  FileText,
  CheckSquare,
  Bot,
  LogOut,
  Copy,
  Check,
  ChevronDown,
  Plus,
  LayoutDashboard,
  PanelLeft,
  Sun,
  Moon,
  ChevronLeft,
  ChevronRight,
  X,
  AlertCircle,
  Users,
  MessageSquare,
  Workflow,
  GitBranch,
  Settings,
} from "lucide-react";

const NAV = [
  { path: "/dashboard", href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/documents", href: "/dashboard/documents", label: "Documents", icon: FileText },
  { path: "/tasks", href: "/dashboard/tasks", label: "Tasks", icon: CheckSquare },
  { path: "/chat", href: "/dashboard/chat", label: "Chat", icon: MessageSquare },
  { path: "/flows", href: "/dashboard/flows", label: "Flows", icon: Workflow },
  { path: "/ai", href: "/dashboard/ai", label: "AI Assistant", icon: Bot },
  { path: "/integrations", href: "/dashboard/integrations", label: "Integrations", icon: GitBranch },
  { path: "/settings", href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, setUser, logout } = useAuthStore();
  const { currentWorkspace, setCurrentWorkspace, setWorkspaces } = useWorkspaceStore();
  const { theme, toggleTheme } = useThemeStore();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [loading, setLoading] = useState(!user || !currentWorkspace);
  const [copied, setCopied] = useState(false);
  const [showWsMenu, setShowWsMenu] = useState(false);
  const [workspaces, setWsList] = useState<Workspace[]>([]);

  // Create Workspace Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [newWsDesc, setNewWsDesc] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState("");

  // Join Workspace Modal
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [joinCode, setJoinCode] = useState("");
  const [joinLoading, setJoinLoading] = useState(false);
  const [joinError, setJoinError] = useState("");

  // Fallback screen join
  const [emptyJoinCode, setEmptyJoinCode] = useState("");
  const [emptyJoinLoading, setEmptyJoinLoading] = useState(false);
  const [emptyJoinError, setEmptyJoinError] = useState("");

  useEffect(() => {
    try {
      const stored = localStorage.getItem("orbit-sidebar-collapsed");
      if (stored === "true") setIsCollapsed(true);
    } catch {}
  }, []);

  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem("orbit-sidebar-collapsed", String(next)); } catch {}
      return next;
    });
  };

  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      try {
        const [mePromise, wsPromise] = [
          !user ? api.get("/auth/me") : Promise.resolve({ data: user }),
          api.get("/workspaces/"),
        ];
        const [meRes, wsRes] = await Promise.all([mePromise, wsPromise]);
        if (!isMounted) return;

        if (meRes?.data && !user) setUser(meRes.data);

        const ws = wsRes.data || [];
        setWsList(ws);
        setWorkspaces(ws);

        const belongsToUser = currentWorkspace && ws.some((w: Workspace) => w.id === currentWorkspace.id);
        if (!belongsToUser && ws.length > 0) {
          setCurrentWorkspace(ws[0]);
        } else if (ws.length === 0) {
          setCurrentWorkspace(null as unknown as Workspace);
        }
      } catch (err: unknown) {
        const error = err as { response?: { status?: number } };
        if (error?.response?.status === 401) {
          logout();
          router.push("/login");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    init();
    return () => { isMounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const copyInvite = () => {
    if (currentWorkspace) {
      navigator.clipboard.writeText(currentWorkspace.invite_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCreateWorkspace = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!newWsName.trim()) { setCreateError("Workspace name is required"); return; }
    setCreateLoading(true);
    setCreateError("");
    try {
      const { data } = await api.post("/workspaces/", {
        name: newWsName.trim(),
        description: newWsDesc.trim() || undefined,
      });
      const updated = [...workspaces, data];
      setWsList(updated);
      setWorkspaces(updated);
      setCurrentWorkspace(data);
      setNewWsName("");
      setNewWsDesc("");
      setShowCreateModal(false);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string; message?: string } } };
      setCreateError(
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Failed to create workspace. Please try again."
      );
    } finally {
      setCreateLoading(false);
    }
  };

  const handleJoinWorkspace = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const codeToUse = joinCode.trim();
    if (!codeToUse) { setJoinError("Please enter an invite code"); return; }
    setJoinLoading(true);
    setJoinError("");
    try {
      const { data } = await api.post(`/workspaces/join/${codeToUse}`);
      const exists = workspaces.some((w) => w.id === data.id);
      const updatedWorkspaces = exists ? workspaces : [...workspaces, data];
      setWsList(updatedWorkspaces);
      setWorkspaces(updatedWorkspaces);
      setCurrentWorkspace(data);
      setJoinCode("");
      setShowJoinModal(false);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string; message?: string } } };
      setJoinError(
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Failed to join workspace. Please verify the invite code."
      );
    } finally {
      setJoinLoading(false);
    }
  };

  const handleEmptyScreenJoin = async () => {
    const codeToUse = emptyJoinCode.trim();
    if (!codeToUse) { setEmptyJoinError("Please enter an invite code"); return; }
    setEmptyJoinLoading(true);
    setEmptyJoinError("");
    try {
      const { data } = await api.post(`/workspaces/join/${codeToUse}`);
      setWsList([data]);
      setWorkspaces([data]);
      setCurrentWorkspace(data);
      setEmptyJoinCode("");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string; message?: string } } };
      setEmptyJoinError(
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Failed to join workspace. Please verify the invite code."
      );
    } finally {
      setEmptyJoinLoading(false);
    }
  };

  const handleLogout = () => { logout(); router.push("/"); };

  /* ─── Loading ─────────────────────────────────────────────────── */
  if (loading) return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <Spinner className="w-5 h-5" />
    </div>
  );

  /* ─── No Workspace Fallback ───────────────────────────────────── */
  if (!currentWorkspace) return (
    <div className="min-h-screen bg-bg flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-6">
        <div>
          <div className="text-xs text-orbit-muted font-mono tracking-widest mb-2">ORBIT AI</div>
          <h1 className="font-display font-bold text-xl text-orbit-text">No workspaces</h1>
          <p className="text-sm text-orbit-muted mt-1">Create or join a workspace to get started.</p>
        </div>

        <div className="orbit-card p-4 space-y-3">
          <p className="text-xs font-semibold text-orbit-text">Create a workspace</p>
          <CreateWorkspaceInline onCreated={(ws) => {
            setCurrentWorkspace(ws);
            setWsList([ws]);
            setWorkspaces([ws]);
          }} />
        </div>

        <div className="orbit-card p-4 space-y-3">
          <p className="text-xs font-semibold text-orbit-text">Join an existing workspace</p>
          {emptyJoinError && (
            <div className="p-2.5 rounded-md bg-red-500/8 border border-red-500/20 text-red-500 text-xs flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              <span>{emptyJoinError}</span>
            </div>
          )}
          <div className="flex gap-2">
            <input
              className="orbit-input flex-1 font-mono uppercase tracking-widest text-xs"
              value={emptyJoinCode}
              onChange={(e) => setEmptyJoinCode(e.target.value)}
              placeholder="Invite code"
              onKeyDown={(e) => e.key === "Enter" && handleEmptyScreenJoin()}
            />
            <button
              className="orbit-btn-primary text-xs"
              onClick={handleEmptyScreenJoin}
              disabled={emptyJoinLoading || !emptyJoinCode.trim()}
            >
              {emptyJoinLoading ? <Spinner className="w-3.5 h-3.5" /> : "Join"}
            </button>
          </div>
        </div>

        <button onClick={handleLogout} className="text-xs text-orbit-muted hover:text-orbit-text transition-colors">
          ← Sign out
        </button>
      </div>
    </div>
  );

  /* ─── Current page label ─────────────────────────────────────── */
  const currentNavItem = NAV.find((n) =>
    n.href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(n.href)
  );

  /* ─── Main Layout ─────────────────────────────────────────────── */
  return (
    <div className="flex h-screen overflow-hidden bg-bg">

      {/* ── Sidebar ───────────────────────────────────────────────── */}
      <aside
        className={`${isCollapsed ? "w-14" : "w-56"
          } border-r border-orbit-border flex flex-col bg-surface flex-shrink-0 transition-all duration-200 ease-in-out relative z-40`}
      >
        {/* Workspace switcher */}
        <div className={`px-2 py-2.5 border-b border-orbit-border relative ${isCollapsed ? "flex justify-center" : ""}`}>
          <button
            onClick={() => setShowWsMenu(!showWsMenu)}
            className={`w-full flex items-center gap-2 px-1.5 py-1.5 rounded-md hover:bg-surface2 transition-colors ${isCollapsed ? "justify-center" : ""}`}
            title={isCollapsed ? `${currentWorkspace.name}` : undefined}
          >
            <div className="w-6 h-6 rounded bg-accent-dim border border-accent-border flex items-center justify-center flex-shrink-0">
              <span className="text-accent text-[10px] font-bold font-display leading-none">
                {currentWorkspace.name[0]?.toUpperCase()}
              </span>
            </div>
            {!isCollapsed && (
              <>
                <div className="flex-1 text-left overflow-hidden">
                  <div className="text-xs font-semibold text-orbit-text truncate leading-tight">{currentWorkspace.name}</div>
                  <div className="text-[10px] text-orbit-muted leading-tight">Workspace</div>
                </div>
                <ChevronDown className="w-3 h-3 text-orbit-muted flex-shrink-0" />
              </>
            )}
          </button>

          {/* Workspace dropdown */}
          {showWsMenu && (
            <div
              className={`absolute mt-1 bg-surface border border-orbit-border rounded-lg shadow-xl z-50 overflow-hidden animate-fade-in ${isCollapsed ? "top-2 left-14 w-52" : "top-full left-2 right-2"
                }`}
            >
              {workspaces.length > 0 && (
                <div className="py-1">
                  {workspaces.map((ws) => (
                    <button
                      key={ws.id}
                      onClick={() => { setCurrentWorkspace(ws); setShowWsMenu(false); }}
                      className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-surface2 text-left transition-colors text-xs text-orbit-text"
                    >
                      <div className="w-5 h-5 rounded bg-accent-dim flex items-center justify-center text-[9px] font-bold text-accent flex-shrink-0">
                        {ws.name[0]?.toUpperCase()}
                      </div>
                      <span className="truncate flex-1">{ws.name}</span>
                      {ws.id === currentWorkspace.id && <Check className="w-3 h-3 text-accent flex-shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
              <div className="border-t border-orbit-border py-1">
                <button
                  onClick={() => { setShowWsMenu(false); setCreateError(""); setNewWsName(""); setNewWsDesc(""); setShowCreateModal(true); }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-surface2 text-left transition-colors text-xs text-orbit-muted hover:text-orbit-text"
                >
                  <Plus className="w-3 h-3 flex-shrink-0" />
                  New workspace
                </button>
                <button
                  onClick={() => { setShowWsMenu(false); setJoinError(""); setJoinCode(""); setShowJoinModal(true); }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-surface2 text-left transition-colors text-xs text-orbit-muted hover:text-orbit-text"
                >
                  <Users className="w-3 h-3 flex-shrink-0" />
                  Join workspace
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto overflow-x-hidden">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`sidebar-nav-item group ${active ? "active" : ""} ${isCollapsed ? "justify-center px-0 h-8 w-8 mx-auto" : ""}`}
                title={isCollapsed ? label : undefined}
              >
                <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${active ? "text-accent" : "text-orbit-muted group-hover:text-orbit-text"}`} />
                {!isCollapsed && <span className="truncate text-xs">{label}</span>}

                {isCollapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-surface border border-orbit-border text-[11px] rounded shadow-lg pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap text-orbit-text">
                    {label}
                  </div>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom controls */}
        <div className="px-2 py-2 border-t border-orbit-border space-y-0.5">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className={`sidebar-nav-item group ${isCollapsed ? "justify-center px-0 h-8 w-8 mx-auto" : ""}`}
            title={theme === "dark" ? "Light mode" : "Dark mode"}
          >
            {theme === "dark"
              ? <Sun className="w-3.5 h-3.5 text-orbit-muted group-hover:text-orbit-text flex-shrink-0" />
              : <Moon className="w-3.5 h-3.5 text-orbit-muted group-hover:text-orbit-text flex-shrink-0" />}
            {!isCollapsed && <span className="text-xs truncate">{theme === "dark" ? "Light mode" : "Dark mode"}</span>}

            {isCollapsed && (
              <div className="absolute left-full ml-2 px-2 py-1 bg-surface border border-orbit-border text-[11px] rounded shadow-lg pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap text-orbit-text">
                {theme === "dark" ? "Light mode" : "Dark mode"}
              </div>
            )}
          </button>

          {/* Collapse toggle */}
          <button
            onClick={handleToggleCollapse}
            className={`sidebar-nav-item group ${isCollapsed ? "justify-center px-0 h-8 w-8 mx-auto" : ""}`}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed
              ? <ChevronRight className="w-3.5 h-3.5 text-orbit-muted group-hover:text-orbit-text flex-shrink-0" />
              : <ChevronLeft className="w-3.5 h-3.5 text-orbit-muted group-hover:text-orbit-text flex-shrink-0" />}
            {!isCollapsed && <span className="text-xs truncate">Collapse</span>}
          </button>

          <div className="h-px bg-orbit-border my-1" />

          {/* User row */}
          <div className={`flex items-center gap-2 px-1 py-1 rounded-md ${isCollapsed ? "justify-center" : ""}`}>
            <div title={user?.email || ""} className="flex-shrink-0">
              <Avatar email={user?.email || ""} size={22} />
            </div>
            {!isCollapsed && (
              <div className="flex-1 min-w-0">
                <div className="text-[11px] text-orbit-muted truncate leading-tight">{user?.email}</div>
              </div>
            )}
            <button
              onClick={handleLogout}
              className="text-orbit-muted hover:text-red-500 transition-colors p-1 rounded hover:bg-surface2 flex-shrink-0"
              title="Sign out"
            >
              <LogOut className="w-3 h-3" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main content area ─────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-bg">

        {/* Header */}
        <header
          className="border-b border-orbit-border bg-surface flex items-center justify-between px-4 flex-shrink-0 z-20"
          style={{ height: 48 }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={handleToggleCollapse}
              className="p-1 rounded text-orbit-muted hover:text-orbit-text hover:bg-surface2 transition-colors"
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <PanelLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2 text-sm">
              <span className="text-orbit-muted">Orbit</span>
              {currentNavItem && (
                <>
                  <span className="text-orbit-border2">/</span>
                  <span className="text-orbit-text font-medium">{currentNavItem.label}</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Theme toggle in header */}
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded border border-orbit-border text-orbit-muted hover:text-orbit-text hover:bg-surface2 transition-colors"
              title={theme === "dark" ? "Light mode" : "Dark mode"}
            >
              {theme === "dark"
                ? <Sun className="w-3.5 h-3.5 text-orbit-muted" />
                : <Moon className="w-3.5 h-3.5 text-orbit-muted" />}
            </button>

            {/* Invite code */}
            {(!currentWorkspace.settings_restrict_invites || currentWorkspace.owner_id === user?.id) && (
              <button
                onClick={copyInvite}
                className="flex items-center gap-1.5 px-2.5 py-1 border border-orbit-border rounded text-[11px] font-mono text-orbit-muted hover:border-orbit-border2 hover:text-orbit-text transition-colors bg-surface"
              >
                <span>Invite:</span>
                <span className="text-orbit-text font-semibold">{currentWorkspace.invite_code}</span>
                {copied ? <Check className="w-2.5 h-2.5 text-accent" /> : <Copy className="w-2.5 h-2.5" />}
              </button>
            )}
          </div>
        </header>

        <main className="flex-1 overflow-auto bg-bg">{children}</main>
      </div>

      {/* Workspace menu backdrop */}
      {showWsMenu && <div className="fixed inset-0 z-30" onClick={() => setShowWsMenu(false)} />}

      {/* ── Create Workspace Modal ────────────────────────────────── */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in">
          <div
            className="w-full max-w-sm bg-surface border border-orbit-border rounded-xl shadow-2xl p-5 relative"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4 pb-3.5 border-b border-orbit-border">
              <div>
                <h3 className="text-sm font-semibold text-orbit-text">New workspace</h3>
                <p className="text-[11px] text-orbit-muted mt-0.5">Create a collaborative space for your team</p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1.5 rounded text-orbit-muted hover:text-orbit-text hover:bg-surface2 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {createError && (
              <div className="mb-4 p-2.5 rounded-md bg-red-500/8 border border-red-500/20 text-red-500 text-xs flex items-center gap-2">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreateWorkspace} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-orbit-text mb-1.5">
                  Name <span className="text-accent">*</span>
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  placeholder="e.g. Acme Engineering"
                  value={newWsName}
                  onChange={(e) => setNewWsName(e.target.value)}
                  className="orbit-input text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-orbit-text mb-1.5">
                  Description <span className="text-orbit-muted font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Core product roadmap"
                  value={newWsDesc}
                  onChange={(e) => setNewWsDesc(e.target.value)}
                  className="orbit-input text-sm"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-orbit-border">
                <button type="button" onClick={() => setShowCreateModal(false)} className="orbit-btn-ghost text-xs">
                  Cancel
                </button>
                <button type="submit" disabled={createLoading || !newWsName.trim()} className="orbit-btn-primary text-xs">
                  {createLoading ? <Spinner className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Join Workspace Modal ──────────────────────────────────── */}
      {showJoinModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in">
          <div
            className="w-full max-w-sm bg-surface border border-orbit-border rounded-xl shadow-2xl p-5 relative"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4 pb-3.5 border-b border-orbit-border">
              <div>
                <h3 className="text-sm font-semibold text-orbit-text">Join workspace</h3>
                <p className="text-[11px] text-orbit-muted mt-0.5">Enter an invite code to join a team workspace</p>
              </div>
              <button
                onClick={() => setShowJoinModal(false)}
                className="p-1.5 rounded text-orbit-muted hover:text-orbit-text hover:bg-surface2 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {joinError && (
              <div className="mb-4 p-2.5 rounded-md bg-red-500/8 border border-red-500/20 text-red-500 text-xs flex items-center gap-2">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{joinError}</span>
              </div>
            )}

            <form onSubmit={handleJoinWorkspace} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-orbit-text mb-1.5">
                  Invite code <span className="text-accent">*</span>
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  placeholder="e.g. 6A45812"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value)}
                  className="orbit-input text-sm font-mono uppercase tracking-widest"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-orbit-border">
                <button type="button" onClick={() => setShowJoinModal(false)} className="orbit-btn-ghost text-xs">
                  Cancel
                </button>
                <button type="submit" disabled={joinLoading || !joinCode.trim()} className="orbit-btn-primary text-xs">
                  {joinLoading ? <Spinner className="w-3.5 h-3.5" /> : <Users className="w-3.5 h-3.5" />}
                  Join
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Inline workspace creation (no-workspace fallback) ─────────── */
function CreateWorkspaceInline({ onCreated }: { onCreated: (ws: Workspace) => void }) {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const create = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/workspaces/", { name: name.trim() });
      onCreated(data);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string; message?: string } } };
      setError(
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Failed to create workspace"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={create} className="w-full space-y-2">
      {error && (
        <div className="p-2.5 rounded-md bg-red-500/8 border border-red-500/20 text-red-500 text-xs flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      <div className="flex gap-2">
        <input
          className="orbit-input flex-1 text-sm"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Workspace name"
          autoFocus
        />
        <button className="orbit-btn-primary text-xs" type="submit" disabled={loading || !name.trim()}>
          {loading ? <Spinner className="w-3.5 h-3.5" /> : "Create"}
        </button>
      </div>
    </form>
  );
}