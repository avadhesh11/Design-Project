"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle, AlertTriangle, Activity, Server, Database, Brain, RefreshCw, Orbit } from "lucide-react";
import api from "@/lib/api";
interface ServiceStatus {
  name: string;
  status: "operational" | "degraded" | "offline" |"checking";
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

export default function StatusPage() {
  const [loading, setLoading] = useState(true);
  const [ping, setPing] = useState<number | null>(null);
  const [systemStatus, setSystemStatus] = useState<"all_good" | "issues" | "offline">("all_good");
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "Frontend Server", status: "checking", description: "Vercel edge hosting & Next.js rendering", icon: Server },
    { name: "Backend API", status: "checking", description: "FastAPI request handlers & JWT Auth security", icon: Activity },
    { name: "Database (Supabase)", status: "checking", description: "PostgreSQL core data engine & pgvector store", icon: Database },
    { name: "Agent Engine", status: "checking", description: "LangGraph agent & Gemini orchestration service", icon: Brain },
  ]);

  const checkHealth = async () => {
    setLoading(true);
    const start = Date.now();

    
    try {
      // Fetch health endpoint
      const res = await api.get("/health");
      const duration = Date.now() - start;
      setPing(duration);

      const isOk = res.data?.status === "ok";
      console.log(isOk);
      

      
      setServices([
        { name: "Frontend Server", status: "operational", description: "Vercel edge hosting & Next.js rendering", icon: Server },
        { 
          name: "Backend API", 
          status: isOk ? "operational" : "offline", 
          description: "FastAPI request handlers & JWT Auth security", 
          icon: Activity 
        },
        { 
          name: "Database (Supabase)", 
          status: isOk ? "operational" : "offline", 
          description: "PostgreSQL core data engine & pgvector store", 
          icon: Database 
        },
        { 
          name: "Agent Engine", 
          status: isOk ? "operational" : "offline", 
          description: "LangGraph agent & Gemini orchestration service", 
          icon: Brain 
        },
      ]);
      
      setSystemStatus(isOk ? "all_good" : "issues");
    } catch {
      setPing(null);
      setSystemStatus("offline");
      setServices([
        { name: "Frontend Server", status: "operational", description: "Vercel edge hosting & Next.js rendering", icon: Server },
        { name: "Backend API", status: "offline", description: "FastAPI request handlers & JWT Auth security", icon: Activity },
        { name: "Database (Supabase)", status: "offline", description: "PostgreSQL core data engine & pgvector store", icon: Database },
        { name: "Agent Engine", status: "offline", description: "LangGraph agent & Gemini orchestration service", icon: Brain },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen grid-bg flex flex-col items-center justify-between text-[#e8e8f0]">
      {/* Navbar */}
      <nav className="w-full glass border-b border-[#1e1e2e] flex items-center justify-between px-8 h-14">
        <Link href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
          <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            <Orbit className="w-3.5 h-3.5 text-accent" />
          </div>
          <span className="font-display font-bold text-base">Orbit Status</span>
        </Link>
        <Link href="/" className="orbit-btn-ghost text-xs px-3.5 py-1.5 flex items-center gap-1.5">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Home
        </Link>
      </nav>

      {/* Main content */}
      <main className="flex-1 w-full max-w-3xl px-6 py-16 flex flex-col gap-8">
        
        {/* Overall Status Banner */}
        <div className={`p-6 rounded-2xl border transition-all duration-300 ${
          systemStatus === "all_good" 
            ? "bg-[rgba(127,255,178,0.03)] border-[rgba(127,255,178,0.15)] shadow-[0_0_40px_rgba(127,255,178,0.02)]" 
            : "bg-red-950/10 border-red-500/20 shadow-[0_0_40px_rgba(239,68,68,0.02)]"
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {systemStatus === "all_good" ? (
                <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-accent" />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-red-400" />
                </div>
              )}
              <div>
                <h1 className="font-display font-bold text-xl md:text-2xl">
                  {systemStatus === "all_good" ? "All Services Operational" : "Service Disruptions Detected"}
                </h1>
                <p className="text-xs text-[#5a5a7a] mt-0.5">
                  {systemStatus === "all_good" 
                    ? "Everything is running smoothly. Last check just now." 
                    : "Some backend services are currently unreachable. Retrying..."}
                </p>
              </div>
            </div>
            
            <button 
              onClick={checkHealth}
              disabled={loading}
              className="w-9 h-9 rounded-lg bg-surface border border-[#1e1e2e] flex items-center justify-center text-[#5a5a7a] hover:text-accent hover:border-accent/40 disabled:opacity-40 transition-all duration-150"
              title="Refresh status"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-accent" : ""}`} />
            </button>
          </div>
          
          {/* Latency Info */}
          {systemStatus === "all_good" && ping !== null && (
            <div className="mt-5 pt-4 border-t border-[#1e1e2e]/60 flex items-center justify-between text-xs text-[#5a5a7a] font-mono">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                API Connection Status: Excellent
              </span>
              <span>Response Latency: {ping}ms</span>
            </div>
          )}
        </div>

        {/* Services List */}
        <div className="flex flex-col gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-[#5a5a7a] px-1">Individual Services</h2>
          <div className="grid gap-3">
            {services.map((svc) => {
              const Icon = svc.icon;
              return (
                <div key={svc.name} className="p-4 bg-surface border border-[#1e1e2e] rounded-xl flex items-center justify-between hover:border-[#2a2a3e] transition-all duration-150">
                  <div className="flex items-center gap-3.5">
                    <div className="w-9 h-9 rounded-lg bg-surface2 border border-[#1e1e2e] flex items-center justify-center text-[#5a5a7a]">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-medium">{svc.name}</div>
                      <div className="text-[11px] text-[#5a5a7a]">{svc.description}</div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      svc.status === "operational" 
                        ? "bg-accent shadow-[0_0_8px_rgba(127,255,178,0.4)]" 
                        : svc.status === "degraded"
                        ? "bg-yellow-400 shadow-[0_0_8px_rgba(250,204,21,0.4)]"
                        : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]"
                    }`} />
                    <span className="text-xs font-mono font-medium capitalize text-[#8a8a9e]">
                      {svc.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* System Logs Mock Timeline */}
        <div className="flex flex-col gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-[#5a5a7a] px-1">System Uptime (90 Days)</h2>
          <div className="p-5 bg-surface border border-[#1e1e2e] rounded-xl font-mono text-xs">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[#8a8a9e]">Orbit API Cluster</span>
              <span className="text-accent">100% Uptime</span>
            </div>
            {/* Uptime bars mock visual */}
            <div className="flex gap-[2px] h-6 items-end mb-4">
              {Array.from({ length: 45 }).map((_, i) => (
                <div 
                  key={i} 
                  className="flex-1 h-4 bg-accent/40 rounded-[1px] hover:bg-accent hover:h-6 transition-all duration-100 cursor-pointer"
                  title={`Uptime: 100% — June ${i + 1}, 2026`}
                />
              ))}
            </div>
            
            <div className="flex justify-between items-center text-[10px] text-[#5a5a7a]">
              <span>90 days ago</span>
              <span>Today</span>
            </div>
          </div>
        </div>

      </main>

      {/* Footer */}
      <footer className="w-full border-t border-[#1e1e2e] py-6 px-8 flex justify-between items-center">
        <span className="font-mono text-[10px] text-[#5a5a7a]">© 2026 Orbit System Operations</span>
        <div className="flex gap-4">
          <Link href="/" className="font-mono text-[10px] text-[#5a5a7a] hover:text-[#e8e8f0]">Home</Link>
          <a href="/api/docs" className="font-mono text-[10px] text-[#5a5a7a] hover:text-[#e8e8f0]">API Reference</a>
        </div>
      </footer>
    </div>
  );
}
