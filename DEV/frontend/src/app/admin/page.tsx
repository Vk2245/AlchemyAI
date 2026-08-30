"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  Users,
  FileText,
  BarChart3,
  AlertTriangle,
  ShieldCheck,
  Activity,
  ArrowRight,
  TrendingUp,
} from "lucide-react";

const adminStats = [
  { label: "Total Users", value: "142", change: "+12%", icon: Users, color: "text-blue-400" },
  { label: "Documents Processed", value: "1,847", change: "+23%", icon: FileText, color: "text-emerald-400" },
  { label: "Avg Confidence", value: "91.4%", change: "+2.1%", icon: BarChart3, color: "text-violet-400" },
  { label: "Risk Flags", value: "23", change: "-8%", icon: AlertTriangle, color: "text-amber-400" },
];

const recentActivity = [
  { user: "alice@acme.com", action: "Processed", doc: "Circuit_Breaker_X400.pdf", industry: "Electrical", time: "2m ago", confidence: 96 },
  { user: "bob@pharma.io", action: "Uploaded", doc: "Drug_Safety_Sheet_B12.pdf", industry: "Pharma", time: "5m ago", confidence: null },
  { user: "carol@foods.co", action: "Processed", doc: "Organic_Label_2026.pdf", industry: "Food", time: "12m ago", confidence: 88 },
  { user: "dave@agri.net", action: "Verified", doc: "Fertilizer_Spec_NPK.pdf", industry: "Agriculture", time: "18m ago", confidence: 92 },
  { user: "eve@auto.com", action: "Processed", doc: "Brake_Pad_Datasheet.pdf", industry: "Automotive", time: "25m ago", confidence: 79 },
];

export default function AdminPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12 space-y-10 relative z-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Admin Console</h1>
          <p className="text-[var(--secondary)] mt-1">System-wide monitoring and user management.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
            <Activity size={12} /> All systems operational
          </div>
          <Link href="/" className="btn-ghost text-xs px-4 py-2">Back to App</Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {adminStats.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="glass-panel-strong rounded-2xl p-6 group hover:border-white/10 transition-colors"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center ${s.color}`}>
                <s.icon size={18} />
              </div>
              <span className="flex items-center gap-1 text-xs font-medium text-emerald-400">
                <TrendingUp size={12} /> {s.change}
              </span>
            </div>
            <span className="text-3xl font-extrabold text-white tracking-tight">{s.value}</span>
            <p className="text-xs text-[var(--secondary)] mt-1">{s.label}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-2 glass-panel-strong rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white">Recent Activity</h2>
            <span className="text-xs text-[var(--muted)]">Live feed</span>
          </div>
          <div className="space-y-3">
            {recentActivity.map((act, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className="flex items-center justify-between py-3 border-b border-white/5 last:border-0"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-xs font-bold text-white shrink-0">
                    {act.user.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm text-white font-medium truncate">
                      {act.user}{" "}
                      <span className="text-[var(--secondary)] font-normal">{act.action}</span>{" "}
                      <span className="text-[var(--accent-blue)] font-mono text-xs">{act.doc}</span>
                    </p>
                    <p className="text-xs text-[var(--muted)]">{act.industry} • {act.time}</p>
                  </div>
                </div>
                {act.confidence && (
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full shrink-0 ${
                    act.confidence >= 90 ? 'bg-emerald-500/10 text-emerald-400' :
                    act.confidence >= 80 ? 'bg-amber-500/10 text-amber-400' :
                    'bg-red-500/10 text-red-400'
                  }`}>
                    {act.confidence}%
                  </span>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Security Panel */}
        <div className="glass-panel-strong rounded-2xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <ShieldCheck size={18} className="text-emerald-400" /> Security
          </h2>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-[var(--secondary)]">Tamper Checks</span>
              <span className="text-sm font-semibold text-emerald-400">All Passed</span>
            </div>
            <div className="h-px bg-white/5" />
            <div className="flex justify-between items-center">
              <span className="text-sm text-[var(--secondary)]">Failed Logins (24h)</span>
              <span className="text-sm font-semibold text-amber-400">3</span>
            </div>
            <div className="h-px bg-white/5" />
            <div className="flex justify-between items-center">
              <span className="text-sm text-[var(--secondary)]">Rate-Limited IPs</span>
              <span className="text-sm font-semibold text-white">7</span>
            </div>
            <div className="h-px bg-white/5" />
            <div className="flex justify-between items-center">
              <span className="text-sm text-[var(--secondary)]">Audit Log Size</span>
              <span className="text-sm font-semibold text-white">4,291 entries</span>
            </div>
          </div>

          <Link
            href="#"
            className="flex items-center justify-center gap-2 btn-ghost text-xs w-full py-2.5 rounded-xl mt-4"
          >
            View Full Audit Log <ArrowRight size={12} />
          </Link>
        </div>
      </div>
    </div>
  );
}
