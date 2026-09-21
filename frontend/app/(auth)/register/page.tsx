"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { Spinner } from "@/components/app/Spinner";
import { Orbit } from "lucide-react";

export default function RegisterPage() {
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
      // Backend sets cookies
      await api.post("/auth/register", {
        email,
        password,
      });

      // Fetch logged in user
      const { data: me } = await api.get(
        "/auth/me"
      );

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
      let message = "Registration failed";

      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        // Pydantic validation errors return an array of objects
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
    <div className="min-h-screen grid-bg flex items-center justify-center px-6">
      <div className="w-full max-w-sm animate-fade-up">
        <Link href="/" className="flex items-center gap-2 mb-10">
          <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            <Orbit className="w-3.5 h-3.5 text-accent" />
          </div>
          <span className="font-display font-bold">Orbit AI</span>
        </Link>

        <h1 className="font-display font-extrabold text-2xl mb-1">Create account</h1>
        <p className="text-[#5a5a7a] text-sm mb-6">Start building with Orbit AI</p>

        {/* GitHub OAuth Button */}
        <a
          href={githubAuthUrl}
          className="w-full flex items-center justify-center gap-2.5 px-4 py-2.5 rounded-lg border border-[#2a2a3e] bg-[#14141e] hover:bg-[#1a1a28] hover:border-[#3a3a52] text-sm font-medium text-[#e8e8f0] transition-all cursor-pointer mb-4"
        >
          <svg className="w-4 h-4 fill-current text-white" viewBox="0 0 24 24">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            />
          </svg>
          Continue with GitHub
        </a>

        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-[#1e1e2e]" />
          <span className="text-[11px] uppercase tracking-wider text-[#5a5a7a] font-mono">or continue with email</span>
          <div className="flex-1 h-px bg-[#1e1e2e]" />
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs text-[#5a5a7a] mb-1.5 font-medium">Email</label>
            <input className="orbit-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
          </div>
          <div>
            <label className="block text-xs text-[#5a5a7a] mb-1.5 font-medium">Password</label>
            <input className="orbit-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="MIN 8 characters, at least one uppercase and one digit" required minLength={8} />
          </div>

          {error && (
            <div className="px-3 py-2.5 bg-[#ff6b6b]/10 border border-[#ff6b6b]/20 rounded-lg text-xs text-[#ff6b6b]">{error}</div>
          )}

          <button className="orbit-btn-primary justify-center py-2.5 mt-1" type="submit" disabled={loading}>
            {loading ? <Spinner /> : "Create account"}
          </button>
        </form>

        <div className="h-px bg-[#1e1e2e] my-5" />
        <p className="text-center text-sm text-[#5a5a7a]">
          Already have an account?{" "}
          <Link href="/login" className="text-accent font-medium hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}

