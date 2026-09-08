"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LogIn,
  Eye,
  EyeOff,
  Box,
  ArrowRight,
  Building2,
  ShieldCheck,
} from "lucide-react";

const INDUSTRIES = [
  "Electrical Engineering",
  "Software / SaaS",
  "Pharmaceuticals",
  "Food & Beverage",
  "Agriculture",
  "Automotive",
  "Construction",
  "General / Other",
];

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const API = "http://127.0.0.1:6104";
      const res = await fetch(`${API}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Invalid credentials");
      }

      const data = await res.json();
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user || { email }));
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Login failed");
      setIsLoading(false);
    }
  };

  const handleDemoLogin = async (role: "admin" | "user") => {
    setIsLoading(true);
    setError("");
    try {
      const API = "http://127.0.0.1:6104";
      const res = await fetch(`${API}/api/auth/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });

      if (!res.ok) {
        throw new Error("Demo login failed");
      }

      const data = await res.json();
      localStorage.setItem("token", data.access_token);
      localStorage.setItem(
        "user",
        JSON.stringify({
          email: role === "admin" ? "admin@Alchemy AI.io" : "demo@Alchemy AI.io",
          role,
          username: data.username,
        })
      );
      router.push(role === "admin" ? "/admin" : "/dashboard");
    } catch (err: any) {
      setError(err.message || "Demo login failed");
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-white text-black rounded-2xl mb-6 shadow-[0_0_20px_rgba(255,255,255,0.1)]">
            <Box size={24} strokeWidth={2} />
          </div>
          <h1 className="text-3xl font-bold text-[var(--foreground)] tracking-tight mb-2">
            Welcome back
          </h1>
          <p className="text-[var(--secondary)]">
            Sign in to access your document intelligence dashboard.
          </p>
        </div>

        {/* Form Card */}
        <div className="glass-panel-strong rounded-3xl p-8">
          <form onSubmit={handleLogin} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-[var(--secondary)] mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@company.com"
                className="w-full px-4 py-3 bg-black/5 dark:bg-white/5 border border-[var(--border)] rounded-xl text-[var(--foreground)] text-sm placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]/50 focus:border-[var(--accent-blue)]/50 transition-all"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-[var(--secondary)] mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full px-4 py-3 bg-black/5 dark:bg-white/5 border border-[var(--border)] rounded-xl text-[var(--foreground)] text-sm placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]/50 focus:border-[var(--accent-blue)]/50 transition-all pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2.5"
              >
                {error}
              </motion.p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-primary py-3 text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:hover:scale-100"
            >
              {isLoading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                  className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full"
                />
              ) : (
                <>
                  <LogIn size={16} /> Sign In
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-6">
            <div className="flex-1 h-px bg-[var(--border)]" />
            <span className="text-xs text-[var(--muted)] uppercase tracking-wider">
              or
            </span>
            <div className="flex-1 h-px bg-[var(--border)]" />
          </div>

          {/* Quick Role Access */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleDemoLogin("admin")}
              disabled={isLoading}
              className="flex items-center gap-2 justify-center btn-ghost text-xs px-4 py-2.5 rounded-xl disabled:opacity-50"
            >
              <ShieldCheck size={14} className="text-emerald-400" /> Admin Demo
            </button>
            <button
              type="button"
              onClick={() => handleDemoLogin("user")}
              disabled={isLoading}
              className="flex items-center gap-2 justify-center btn-ghost text-xs px-4 py-2.5 rounded-xl disabled:opacity-50"
            >
              <Building2 size={14} className="text-blue-400" /> User Demo
            </button>
          </div>

        </div>

        {/* Register Link */}
        <p className="text-center mt-8 text-sm text-[var(--secondary)]">
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="text-[var(--accent-blue)] font-medium hover:underline underline-offset-4"
          >
            Create one <ArrowRight size={12} className="inline" />
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
