"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

import { Spinner } from "@/components/app/Spinner";
import { Orbit } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();

  const { setUser, logout } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const urlError = params.get("error");
      if (urlError) {
        setError(decodeURIComponent(urlError));
      }
    }

    const checkAuth = async () => {
      try {
        const { data: me } = await api.get("/auth/me");
        setUser(me);
        router.push("/dashboard");
      } catch {
        logout();
        setCheckingAuth(false);
      }
    };

    checkAuth();
  }, [setUser, logout, router]);

  const handleSubmit = async (
    e: React.FormEvent
  ) => {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      // Login -> backend sets cookies
      await api.post("/auth/login", {
        email,
        password,
      });
 
      
      // Fetch current user
      const { data: me } = await api.get(
        "/auth/me"
      );

      // Store user only
      setUser(me);

      router.push("/dashboard");

    } catch (err: unknown) {
      const error = err as {
        response?: {
          data?: {
            detail?: string | Array<{ msg?: string }>;
          };
        };
      };

      const detail = error.response?.data?.detail;
      let message = "Invalid credentials";

      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        message = detail
          .map((d) => d.msg?.replace(/^Value error, /i, "") || "")
          .filter(Boolean)
          .join(". ") || message;
      }

      setError(message);

    } finally {
      setLoading(false);
    }
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <Spinner className="w-6 h-6" />
      </div>
    );
  }

  const githubAuthUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/github`;

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-6">
      <div className="w-full max-w-sm animate-fade-up">

        <Link
          href="/"
          className="flex items-center gap-2 mb-10"
        >
          <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            <Orbit className="w-3.5 h-3.5 text-accent" />
          </div>

          <span className="font-display font-bold">
            Orbit AI
          </span>
        </Link>

        <h1 className="font-display font-extrabold text-2xl mb-1">
          Welcome back
        </h1>

        <p className="text-orbit-muted text-sm mb-6">
          Sign in to your workspace
        </p>

        {/* GitHub OAuth Button */}
        <a
          href={githubAuthUrl}
          className="w-full flex items-center justify-center gap-2.5 px-4 py-2.5 rounded-lg border border-orbit-border bg-surface hover:bg-surface2 hover:border-orbit-border2 text-sm font-medium text-orbit-text transition-all cursor-pointer mb-4"
        >
          <svg className="w-4 h-4 fill-current text-orbit-text" viewBox="0 0 24 24">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            />
          </svg>
          Continue with GitHub
        </a>

        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-orbit-border" />
          <span className="text-[11px] uppercase tracking-wider text-orbit-muted font-mono">or</span>
          <div className="flex-1 h-px bg-orbit-border" />
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4"
        >
          <div>
            <label className="block text-xs text-orbit-muted mb-1.5 font-medium">
              Email
            </label>

            <input
              className="orbit-input"
              type="email"
              value={email}
              onChange={(e) =>
                setEmail(e.target.value)
              }
              placeholder="you@example.com"
              required
            />
          </div>

          <div>
            <label className="block text-xs text-orbit-muted mb-1.5 font-medium">
              Password
            </label>

            <input
              className="orbit-input"
              type="password"
              value={password}
              onChange={(e) =>
                setPassword(e.target.value)
              }
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="px-3 py-2.5 bg-red-500/8 border border-red-500/20 rounded-md text-xs text-red-500">
              {error}
            </div>
          )}

          <button
            className="orbit-btn-primary justify-center py-2.5 mt-1"
            type="submit"
            disabled={loading}
          >
            {loading ? (
              <Spinner />
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        <div className="h-px bg-orbit-border my-5" />

        <p className="text-center text-sm text-orbit-muted">
          Don&apos;t have an account?{" "}

          <Link
            href="/register"
            className="text-accent font-medium hover:underline"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}