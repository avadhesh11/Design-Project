"use client";
import Link from "next/link";
import axios from "axios";
import { useState, useEffect } from "react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { Spinner } from "@/components/app/Spinner";
import { Sparkles, Terminal, Activity, ArrowRight, Database, Orbit } from "lucide-react";

export default function LandingPage() {
  const { user, setUser, logout } = useAuthStore();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const Url = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
     
        await axios.get(`${Url}/api/health`, { timeout: 5000 });
        setApiStatus("online");
      } catch {
        setApiStatus("offline");
      }
    };
    checkStatus();
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      const currentUser = useAuthStore.getState().user;
      if (!currentUser) {
        setCheckingAuth(false);
        return;
      }

      try {
        const { data: me } = await api.get("/auth/me");
        setUser(me);
      } catch {
        logout();
      } finally {
        setCheckingAuth(false);
      }
    };

    checkAuth();
  }, [setUser, logout]);

  if (checkingAuth && user) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <Spinner className="w-6 h-6" />
      </div>
    );
  }

  return (
    <div className="min-h-screen grid-bg flex flex-col relative overflow-x-hidden">
      {/* Decorative Blur Backgrounds */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] rounded-full bg-accent/5 blur-[130px] pointer-events-none -z-10" />
      <div className="absolute top-[60%] left-1/3 w-[350px] h-[350px] rounded-full bg-[#5b8aff]/5 blur-[120px] pointer-events-none -z-10" />

      {/* Nav */}
      <nav className="glass sticky top-0 z-10 border-b border-[#1e1e2e] flex items-center justify-between px-8 h-14">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
              <Orbit className="w-3.5 h-3.5 text-accent" />
            </div>
            <span className="font-display font-bold text-base tracking-tight text-[#e8e8f0]">Orbit</span>
          </div>
          
          {/* Active Server Status Badge */}
          <Link 
            href="/status" 
            className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full border border-[#1e1e2e] bg-[#111118]/60 hover:border-accent/40 hover:bg-[#111118] transition-all duration-150 group"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${
              apiStatus === "online" 
                ? "bg-accent shadow-[0_0_8px_rgba(127,255,178,0.5)] animate-pulse" 
                : apiStatus === "offline"
                ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"
                : "bg-yellow-400 animate-pulse"
            }`} />
            <span className="text-[10px] text-[#8a8a9e] group-hover:text-accent font-mono uppercase tracking-wider transition-colors">
              {apiStatus === "online" ? "API: Online" : apiStatus === "offline" ? "API: Offline" : "Checking System Status"}
            </span>
          </Link>
        </div>

        <div className="flex gap-2.5">
          <Link href="/login" className="orbit-btn-ghost text-xs px-3.5 py-1.5">Sign in</Link>
          <Link href="/register" className="orbit-btn-primary text-xs px-3.5 py-1.5 shadow-[0_4px_12px_rgba(127,255,178,0.15)]">Get started</Link>
        </div>
      </nav>

      {/* Hero & Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center max-w-6xl mx-auto w-full">
        <div className="animate-fade-up inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/5 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
          <span className="font-mono text-[10px] text-accent tracking-widest uppercase">THE UNIFIED AGENTIC WORKSPACE</span>
        </div>

        <h1 className="animate-[fadeUp_0.5s_0.05s_ease_both] font-display font-extrabold text-5xl md:text-7xl leading-[1.05] tracking-[-0.03em] mb-5 max-w-4xl text-[#e8e8f0]">
          Your team&apos;s digital<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-[#b5ffd4]">second brain.</span>
        </h1>

        <p className="animate-[fadeUp_0.5s_0.1s_ease_both] text-[#8a8a9e] text-lg md:text-xl leading-relaxed max-w-xl mb-10 font-light">
          Docs, chat, tasks, and memory — unified. Orbit treats autonomous AI agents as collaborative teammates, not static sidebars.
        </p>

        <div className="animate-[fadeUp_0.5s_0.15s_ease_both] flex gap-3.5 flex-wrap justify-center">
          <Link href="/register" className="orbit-btn-primary px-6 py-3 text-sm shadow-[0_4px_20px_rgba(127,255,178,0.1)]">
            Start building free
          </Link>
          <Link href="/dashboard" className="orbit-btn-ghost px-6 py-3 text-sm flex items-center gap-1 hover:text-accent">
            View live workspace <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Pills */}
        <div className="animate-[fadeUp_0.5s_0.2s_ease_both] flex flex-wrap gap-2.5 mt-14 justify-center">
          {["Realtime collaboration", "Semantic Search", "LangGraph Agents", "Workspace memory", "RAG pipeline", "Supabase DB"].map((f) => (
            <span key={f} className="px-3.5 py-1.5 border border-[#1e1e2e] rounded-full text-xs text-[#8a8a9e] bg-surface/50 backdrop-blur-md">
              {f}
            </span>
          ))}
        </div>

        {/* Dashboard preview mockup */}
        <div className="animate-[fadeUp_0.5s_0.25s_ease_both] mt-20 w-full border border-[#1e1e2e] rounded-2xl overflow-hidden bg-surface shadow-[0_20px_80px_rgba(127,255,178,0.03)] border-t-[#2d2d3f]">
          <div className="h-10 bg-bg border-b border-[#1e1e2e] flex items-center justify-between px-4">
            <div className="flex gap-1.5">
              {["#ff6b6b","#ffd166","#7fffb2"].map(c => (
                <div key={c} className="w-2.5 h-2.5 rounded-full opacity-60" style={{ background: c }} />
              ))}
            </div>
            <div className="font-mono text-[10px] text-[#5a5a7a] bg-[#111118] px-4 py-0.5 rounded border border-[#1e1e2e]/55">orbit.dev/workspace</div>
            <div className="w-14" /> {/* balance layout */}
          </div>
          <div className="flex h-72">
            <div className="w-48 border-r border-[#1e1e2e] p-3.5 flex flex-col gap-1.5 bg-[#0e0e15] text-left">
              <div className="font-mono text-[9px] text-[#5a5a7a] px-2 py-1 mb-1 tracking-widest font-semibold uppercase">Workspace</div>
              {[["📄","Documents",true],["💬","Chat",false],["✅","Tasks",false],["🤖","AI Teammate",false]].map(([ic,name,active]) => (
                <div key={String(name)} className={`px-3 py-2 rounded-lg text-xs flex items-center gap-2.5 font-medium transition-colors ${active ? "bg-accent/10 text-accent border border-accent/10" : "text-[#5a5a7a]"}`}>
                  <span className="text-xs">{ic}</span><span>{name}</span>
                </div>
              ))}
            </div>
            <div className="flex-1 p-5 text-left bg-surface flex flex-col justify-between">
              <div>
                <div className="text-xs font-semibold text-[#8a8a9e] mb-3 uppercase tracking-wider">Active Documents</div>
                {["Database Migration Plan","API Architecture","Sprint Planning"].map(d => (
                  <div key={d} className="flex items-center justify-between p-3 border border-[#1e1e2e] rounded-xl mb-2 bg-[#0e0e15]/40 hover:border-accent/20 transition-all cursor-pointer">
                    <div className="flex items-center gap-3">
                      <span className="text-accent text-xs">📄</span>
                      <div>
                        <div className="text-xs font-medium text-[#e8e8f0]">{d}</div>
                        <div className="text-[9px] text-[#5a5a7a] font-mono">Autosaved to workspace vector DB</div>
                      </div>
                    </div>
                    <span className="text-[10px] text-[#5a5a7a] font-mono">2m ago</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Feature Grid */}
        <section className="mt-32 w-full text-left">
          <div className="text-center mb-16">
            <h2 className="font-display font-extrabold text-3xl md:text-4xl text-[#e8e8f0] mb-3">
              Designed for high-agency teams.
            </h2>
            <p className="text-sm text-[#8a8a9e] max-w-md mx-auto">
              Orbit bridges modern document curation, team sync, and autonomous LLM orchestration in a secure, containerized core.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-6 w-full">
            <div className="p-6 bg-surface border border-[#1e1e2e] rounded-2xl flex gap-4 hover:border-accent/25 transition-all duration-300">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent flex-shrink-0">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold mb-2">LangGraph AI Agent</h3>
                <p className="text-xs text-[#8a8a9e] leading-relaxed">
                  Powered by Gemini 2.5 Flash, the workspace agent executes actions such as creating task boards, reviewing chat context, and broadcasting email alerts based on your commands.
                </p>
              </div>
            </div>

            <div className="p-6 bg-surface border border-[#1e1e2e] rounded-2xl flex gap-4 hover:border-[#5b8aff]/25 transition-all duration-300">
              <div className="w-10 h-10 rounded-xl bg-[#5b8aff]/10 flex items-center justify-center text-[#5b8aff] flex-shrink-0">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold mb-2">pgvector Document Memory</h3>
                <p className="text-xs text-[#8a8a9e] leading-relaxed">
                  Automatic document chunking and vector embeddings generation (`text-embedding-004`). Ask questions and get answers back backed by citations from your uploaded PDFs or Word files.
                </p>
              </div>
            </div>

            <div className="p-6 bg-surface border border-[#1e1e2e] rounded-2xl flex gap-4 hover:border-yellow-400/25 transition-all duration-300">
              <div className="w-10 h-10 rounded-xl bg-yellow-400/10 flex items-center justify-center text-yellow-400 flex-shrink-0">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold mb-2">Supabase Realtime Chat</h3>
                <p className="text-xs text-[#8a8a9e] leading-relaxed">
                  Seamless websocket channel streaming with active online presence badges, ensuring team updates and message logs broadcast instantly.
                </p>
              </div>
            </div>

            <div className="p-6 bg-surface border border-[#1e1e2e] rounded-2xl flex gap-4 hover:border-purple-400/25 transition-all duration-300">
              <div className="w-10 h-10 rounded-xl bg-purple-400/10 flex items-center justify-center text-purple-400 flex-shrink-0">
                <Terminal className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold mb-2">Clean Docker Architecture</h3>
                <p className="text-xs text-[#8a8a9e] leading-relaxed">
                  Deploy or test in a single command. Standard container scripts automate local services mounting, databases replication, and client endpoints linking.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Expanded Modern Footer */}
      <footer className="border-t border-[#1e1e2e] bg-[#09090d] pt-16 pb-10 px-8 w-full mt-24">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-6 mb-12 text-left">
          
          {/* Column 1: Project Identity */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-6 h-6 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
                <Orbit className="w-3 h-3 text-accent" />
              </div>
              <span className="font-display font-bold text-sm tracking-tight">Orbit</span>
            </div>
            <p className="text-xs text-[#5a5a7a] leading-relaxed max-w-xs">
              Unified document workflows, task operations, and context-aware agent workspaces.
            </p>
            
            {/* Live Server Status Button Redirect */}
            <div className="mt-2">
              <Link 
                href="/status" 
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#1e1e2e] bg-[#111118] text-[11px] text-[#8a8a9e] hover:text-accent hover:border-accent/40 hover:bg-[#151522] transition-all duration-150"
              >
                <span className={`w-2 h-2 rounded-full ${
                  apiStatus === "online" 
                    ? "bg-accent shadow-[0_0_8px_rgba(127,255,178,0.6)] animate-pulse" 
                    : apiStatus === "offline"
                    ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]"
                    : "bg-yellow-400 animate-pulse"
                }`} />
                <span>Check Server status</span>
              </Link>
            </div>
          </div>

          {/* Column 2: Capabilities */}
          <div>
            <h3 className="font-mono text-[10px] font-bold tracking-widest text-[#5a5a7a] uppercase mb-4">Capabilities</h3>
            <ul className="flex flex-col gap-2.5 text-xs text-[#8a8a9e]">
              <li><Link href="/dashboard" className="hover:text-accent transition-colors">Workspace Documents</Link></li>
              <li><Link href="/dashboard" className="hover:text-accent transition-colors">Realtime Chat</Link></li>
              <li><Link href="/dashboard" className="hover:text-accent transition-colors">Kanban Tasks Board</Link></li>
              <li><Link href="/dashboard" className="hover:text-accent transition-colors">LangGraph AI assistant</Link></li>
            </ul>
          </div>

          {/* Column 3: Platform Architecture */}
          <div>
            <h3 className="font-mono text-[10px] font-bold tracking-widest text-[#5a5a7a] uppercase mb-4">Architecture</h3>
            <ul className="flex flex-col gap-2.5 text-xs text-[#8a8a9e]">
              <li className="flex items-center gap-1.5">Next.js 14 App Router</li>
              <li className="flex items-center gap-1.5">FastAPI Framework</li>
              <li className="flex items-center gap-1.5">Supabase pgvector</li>
              <li className="flex items-center gap-1.5">Google Gemini API</li>
            </ul>
          </div>

          {/* Column 4: Links */}
          <div>
            <h3 className="font-mono text-[10px] font-bold tracking-widest text-[#5a5a7a] uppercase mb-4">Resources</h3>
            <ul className="flex flex-col gap-2.5 text-xs text-[#8a8a9e]">
              <li>
                <a 
                  href="http://localhost:8000/docs" 
                  target="_blank" 
                  rel="noreferrer" 
                  className="hover:text-accent transition-colors"
                >
                  FastAPI OpenAPI Docs
                </a>
              </li>
              <li>
                <a 
                  href="https://github.com/avadhesh11/Orbit" 
                  target="_blank" 
                  rel="noreferrer" 
                  className="hover:text-accent flex items-center gap-1.5 transition-colors"
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
                    <path d="M9 18c-4.51 2-5-2-7-2" />
                  </svg>
                  Source Repository
                </a>
              </li>
              <li><Link href="/status" className="hover:text-accent transition-colors">Operational Status Page</Link></li>
            </ul>
          </div>
        </div>

        <div className="max-w-6xl mx-auto pt-6 border-t border-[#1e1e2e]/55 flex flex-col sm:flex-row justify-between items-center gap-4">
          <span className="font-mono text-[10px] text-[#5a5a7a]">© 2026 Orbit Platform. Open Source under MIT.</span>
          <span className="font-mono text-[10px] text-[#5a5a7a] flex items-center gap-1">
            Built with <span className="text-accent">❤️</span> for pair programming
          </span>
        </div>
      </footer>
    </div>
  );
}
