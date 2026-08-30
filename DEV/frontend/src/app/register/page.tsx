"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  UserPlus,
  Eye,
  EyeOff,
  Box,
  ArrowRight,
  Building2,
  Check,
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

export default function RegisterPage() {
  const [step, setStep] = useState<1 | 2>(1);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [industry, setIndustry] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleStep1 = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setStep(2);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!industry) {
      setError("Please select your industry.");
      return;
    }
    setIsLoading(true);
    setError("");

    try {
      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          email,
          password,
          industry,
          company_name: companyName,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Registration failed");
      }
      const data = await res.json();
      
      // Auto-login after registration
      localStorage.setItem("token", data.access_token);
      localStorage.setItem(
        "user",
        JSON.stringify({ email, username, industry, role: "user" })
      );
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Registration failed");
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
            Create your account
          </h1>
          <p className="text-[var(--secondary)]">
            {step === 1
              ? "Set up your credentials to get started."
              : "Tell us about your industry for tailored analysis."}
          </p>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center gap-2 mb-8 max-w-[200px] mx-auto">
          <div className={`flex-1 h-1 rounded-full transition-colors ${step >= 1 ? 'bg-[var(--accent-blue)]' : 'bg-white/10'}`} />
          <div className={`flex-1 h-1 rounded-full transition-colors ${step >= 2 ? 'bg-[var(--accent-blue)]' : 'bg-white/10'}`} />
        </div>

        {/* Form Card */}
        <div className="glass-panel-strong rounded-3xl p-8">
          <AnimatePresence mode="wait">
            {step === 1 ? (
              <motion.form
                key="step1"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                onSubmit={handleStep1}
                className="space-y-5"
              >
                <div>
                  <label className="block text-sm font-medium text-[var(--secondary)] mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    placeholder="johndoe"
                    className="w-full px-4 py-3 bg-black/5 dark:bg-white/5 border border-[var(--border)] rounded-xl text-[var(--foreground)] text-sm placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]/50 focus:border-[var(--accent-blue)]/50 transition-all"
                  />
                </div>

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
                      placeholder="Min 6 characters"
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

                <div>
                  <label className="block text-sm font-medium text-[var(--secondary)] mb-2">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    placeholder="Repeat password"
                    className="w-full px-4 py-3 bg-black/5 dark:bg-white/5 border border-[var(--border)] rounded-xl text-[var(--foreground)] text-sm placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]/50 focus:border-[var(--accent-blue)]/50 transition-all"
                  />
                </div>

                {error && (
                  <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2.5">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  className="w-full btn-primary py-3 text-sm flex items-center justify-center gap-2"
                >
                  Continue <ArrowRight size={15} />
                </button>
              </motion.form>
            ) : (
              <motion.form
                key="step2"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onSubmit={handleRegister}
                className="space-y-5"
              >
                <div>
                  <label className="block text-sm font-medium text-[var(--secondary)] mb-2">
                    Company Name <span className="text-[var(--muted)]">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Acme Corp"
                    className="w-full px-4 py-3 bg-white/5 border border-[var(--border)] rounded-xl text-white text-sm placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]/50 focus:border-[var(--accent-blue)]/50 transition-all"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-[var(--secondary)] mb-3">
                    Your Industry
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {INDUSTRIES.map((ind) => (
                      <button
                        key={ind}
                        type="button"
                        onClick={() => setIndustry(ind)}
                        className={`flex items-center gap-2 text-xs font-medium px-3 py-2.5 rounded-xl border transition-all text-left ${
                          industry === ind
                            ? "bg-[var(--accent-blue)]/10 border-[var(--accent-blue)]/40 text-[var(--accent-blue)]"
                            : "bg-black/[0.02] dark:bg-white/[0.02] border-[var(--border)] text-[var(--secondary)] hover:border-black/15 dark:hover:border-white/15 hover:text-[var(--foreground)]"
                        }`}
                      >
                        {industry === ind && (
                          <Check size={12} className="shrink-0" />
                        )}
                        <Building2
                          size={12}
                          className={`shrink-0 ${
                            industry === ind ? "hidden" : ""
                          }`}
                        />
                        {ind}
                      </button>
                    ))}
                  </div>
                </div>

                {error && (
                  <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2.5">
                    {error}
                  </p>
                )}

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="flex-1 btn-ghost py-3 text-sm rounded-xl"
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="flex-[2] btn-primary py-3 text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {isLoading ? (
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                        className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full"
                      />
                    ) : (
                      <>
                        <UserPlus size={15} /> Create Account
                      </>
                    )}
                  </button>
                </div>
              </motion.form>
            )}
          </AnimatePresence>
        </div>

        <p className="text-center mt-8 text-sm text-[var(--secondary)]">
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-[var(--accent-blue)] font-medium hover:underline underline-offset-4"
          >
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
