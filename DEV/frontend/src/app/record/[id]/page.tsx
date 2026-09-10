"use client";

import React, { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  ShieldCheck,
  Zap,
  ChevronRight,
  Download,
  FileJson2,
  ShieldAlert,
  CheckCircle2,
  BarChart3,
  Globe2,
  ArrowLeft,
  Copy,
  Check,
  ExternalLink,
  Bot,
} from "lucide-react";

// Lazy-load BulkDashboard (uses recharts which is heavy)
const BulkDashboard = dynamic(() => import("./BulkDashboard"), { ssr: false });

interface Attribute {
  name?: string;
  type?: string;
  entity_type?: string;
  value: string | number;
  unit?: string;
  confidence: number;
  source_text?: string;
}

interface DocumentRecord {
  document_title: string;
  primary_party: string;
  part_number: string;
  document_type: string;
  category: string;
  record_confidence: number;
  validation_passed: boolean;
  risk_level: string;
  content_hash: string;
  record_data: {
    entities: Attribute[];
    categories?: Record<string, any[]>;
    stats?: any;
    excel_path?: string;
    [key: string]: any;
  };
  risks: { rule: string; status: string }[];
}


export default function RecordPage({ params }: { params: { id: string } }) {
  const [record, setRecord] = useState<DocumentRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedHash, setCopiedHash] = useState(false);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"attributes" | "risks">("attributes");

  useEffect(() => {
    async function fetchRecord() {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          window.location.href = "/login";
          return;
        }

        const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:6104";
        const res = await fetch(`${API}/api/records/${params.id}`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });

        if (!res.ok) throw new Error("Failed to fetch record");

        const data = await res.json();

        if (data.document_record) {
          // Map backend data to frontend interface
          setRecord({
            document_title: data.document_record.document_title || "Unknown Document",
            primary_party: data.document_record.primary_party || "Unknown Party",
            part_number: data.document_record.part_number || "N/A",
            document_type: data.document_record.document_type || "General",
            category: data.document_record.category || "Uncategorized",
            record_confidence: data.document_record.record_confidence || 0,
            validation_passed: data.document_record.validation_passed || false,
            risk_level: data.document_record.risk_level || "Unknown",
            content_hash: data.document_record.content_hash || "",
            record_data: { entities: [], ...(data.document_record.record_data || {}) },
            risks: data.document_record.risks_summary?.detected_risks || [],
          });
        }
      } catch (err) {
        console.error("Error fetching record:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchRecord();
  }, [params.id]);

  // ── Export JSON (working) ──
  const handleExportJSON = useCallback(() => {
    if (!record) return;
    const blob = new Blob([JSON.stringify(record, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${record.document_title.replace(/\s+/g, "_")}_report.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [record]);

  // ── Export PDF (Download fixed template from backend) ──
  const handleExportPDF = useCallback(async () => {
    if (!record) return;
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:6104";
      const timestamp = new Date().getTime();
      const res = await fetch(`${API}/api/records/${params.id}/pdf?t=${timestamp}`, {
        headers: { "Authorization": `Bearer ${token}` },
        cache: "no-store"
      });

      if (!res.ok) throw new Error("Failed to download PDF");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Report_${record.document_title.replace(/\s+/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading PDF:", err);
      alert("Failed to download PDF report. It might still be generating.");
    }
  }, [record, params.id]);

  // ── Export CSV (Download Enriched CSV for Bulk Excel) ──
  const handleExportCSV = useCallback(async () => {
    if (!record) return;
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:6104";
      const timestamp = new Date().getTime();
      const res = await fetch(`${API}/api/records/${params.id}/csv?t=${timestamp}`, {
        headers: { "Authorization": `Bearer ${token}` },
        cache: "no-store"
      });

      if (!res.ok) throw new Error("Failed to download CSV");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Enriched_${record.document_title.replace(/\s+/g, "_")}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading CSV:", err);
      alert("Failed to download Enriched CSV. It might not be available for this document.");
    }
  }, [record, params.id]);

  const copyHash = () => {
    if (!record) return;
    navigator.clipboard.writeText(record.content_hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin w-7 h-7 border-2 border-white/20 border-t-white rounded-full" />
      </div>
    );
  }

  if (!record) return null;

  const confPct = (record.record_confidence * 100).toFixed(0);
  const isBulk = !!record.record_data.categories;

  return (
    <div className={`mx-auto px-6 py-8 space-y-6 relative z-10 ${isBulk ? 'max-w-[1400px]' : 'max-w-5xl'}`}>
      {/* Back + Breadcrumb */}
      <div className="flex items-center gap-3 text-sm text-[var(--secondary)]">
        <Link
          href="/dashboard"
          className="flex items-center gap-1 hover:text-[var(--foreground)] transition-colors"
        >
          <ArrowLeft size={14} /> Dashboard
        </Link>
        <ChevronRight size={12} />
        <span className="text-[var(--accent-blue)]">{record.document_type}</span>
        <ChevronRight size={12} />
        <span className="text-[var(--foreground)]">{record.document_title}</span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b border-[var(--border)] pb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tighter text-[var(--foreground)] mb-2">
            {record.document_title}
          </h1>
          <p className="text-base text-[var(--secondary)]">
            {record.primary_party}
          </p>
        </div>

        <div className="flex gap-3 shrink-0">
          {record.record_data.excel_path && (
            <button
              onClick={handleExportCSV}
              className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold text-xs px-5 py-2.5 flex items-center gap-2 rounded-xl shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all"
            >
              <Download size={14} /> Download Enriched CSV
            </button>
          )}
          {!record.record_data.excel_path && (
            <button
              onClick={handleExportJSON}
              className="btn-ghost text-xs px-4 py-2.5 flex items-center gap-2 rounded-xl"
            >
              <FileJson2 size={14} /> Export JSON
            </button>
          )}
          <button
            onClick={handleExportPDF}
            className="btn-primary text-xs px-5 py-2.5 flex items-center gap-2 rounded-xl shadow-[0_0_15px_rgba(255,255,255,0.08)]"
          >
            <Download size={14} /> {record.record_data.excel_path ? "Summary PDF" : "Download PDF Report"}
          </button>
          <button
            onClick={() => window.location.href = `/review/${params.id}`}
            className="bg-[var(--accent-primary)] hover:opacity-90 text-white font-semibold text-xs px-5 py-2.5 flex items-center gap-2 rounded-xl transition-all"
          >
            <ShieldCheck size={14} /> Human Review
          </button>
        </div>
      </div>

      {/* Conditional: Bulk Dashboard vs Single Product View */}
      {isBulk ? (
        <BulkDashboard recordData={record.record_data} />
      ) : (
        <>
          {/* Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="glass-panel rounded-2xl p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-3xl -mr-8 -mt-8" />
              <p className="text-xs text-[var(--secondary)] uppercase tracking-wider mb-1">
                AI Confidence
              </p>
              <p className="text-3xl font-extrabold text-[var(--foreground)] stat-glow">
                {confPct}%
              </p>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden mt-3">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-indigo-400 rounded-full"
                  style={{ width: `${confPct}%` }}
                />
              </div>
            </div>

            <div className="glass-panel rounded-2xl p-5">
              <p className="text-xs text-[var(--secondary)] uppercase tracking-wider mb-1">
                Risk Level
              </p>
              <p
                className={`text-3xl font-extrabold ${record.risk_level === "Low"
                    ? "text-emerald-400"
                    : record.risk_level === "Medium"
                      ? "text-amber-400"
                      : "text-red-400"
                  }`}
              >
                {record.risk_level}
              </p>
              <p className="text-xs text-[var(--muted)] mt-2">
                {record.risks.filter((r) => r.status === "pass").length}/
                {record.risks.length} checks passed
              </p>
            </div>

            <div className="glass-panel rounded-2xl p-5">
              <p className="text-xs text-[var(--secondary)] uppercase tracking-wider mb-1">
                Document Type
              </p>
              <p className="text-lg font-bold text-[var(--foreground)] flex items-center gap-2">
                <Globe2 size={16} className="text-[var(--accent-blue)]" />
                {record.document_type.split(" ")[0]}
              </p>
              <p className="text-xs text-[var(--muted)] mt-2 truncate">
                {record.category}
              </p>
            </div>

            <div className="glass-panel rounded-2xl p-5">
              <p className="text-xs text-[var(--secondary)] uppercase tracking-wider mb-1">
                Entities
              </p>
              <p className="text-3xl font-extrabold text-[var(--foreground)]">
                {record.record_data.entities?.length || 0}
              </p>
              <p className="text-xs text-[var(--muted)] mt-2">
                {
                  record.record_data.entities?.filter(
                    (a) => a.confidence >= 0.9
                  ).length || 0
                }{" "}
                high-confidence
              </p>
            </div>
          </div>

          {/* Main Content */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Table */}
            <div className="lg:col-span-2 glass-panel-strong rounded-2xl p-6">
              {/* Tab Bar */}
              <div className="flex items-center gap-1 mb-6 bg-white/[0.02] rounded-xl p-1 border border-[var(--border)]">
                <button
                  onClick={() => setActiveTab("attributes")}
                  className={`flex-1 text-sm font-medium py-2 rounded-lg transition-all ${activeTab === "attributes"
                      ? "bg-black/10 dark:bg-white/10 text-[var(--foreground)]"
                      : "text-[var(--muted)] hover:text-[var(--secondary)]"
                    }`}
                >
                  <BarChart3 size={14} className="inline mr-2 -mt-0.5" />
                  Entities ({record.record_data.entities?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("risks")}
                  className={`flex-1 text-sm font-medium py-2 rounded-lg transition-all ${activeTab === "risks"
                      ? "bg-black/10 dark:bg-white/10 text-[var(--foreground)]"
                      : "text-[var(--muted)] hover:text-[var(--secondary)]"
                    }`}
                >
                  <ShieldAlert size={14} className="inline mr-2 -mt-0.5" />
                  Safety Checks ({record.risks.length})
                </button>
                <button
                  onClick={() => setActiveTab("dynamic")}
                  className={`flex-1 text-sm font-medium py-2 rounded-lg transition-all ${activeTab === "dynamic"
                      ? "bg-black/10 dark:bg-white/10 text-[var(--foreground)]"
                      : "text-[var(--muted)] hover:text-[var(--secondary)]"
                    }`}
                >
                  <Globe2 size={14} className="inline mr-2 -mt-0.5" />
                  Dynamic Data
                </button>
              </div>

              <AnimatePresence mode="wait">
                {activeTab === "attributes" ? (
                  <motion.div
                    key="attrs"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                  >
                    <table className="w-full text-left">
                      <thead>
                        <tr className="border-b border-white/10">
                          <th className="pb-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">
                            Entity
                          </th>
                          <th className="pb-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">
                            Value
                          </th>
                          <th className="pb-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider text-right">
                            Confidence
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {record.record_data.entities?.map((attr, idx) => (
                          <React.Fragment key={idx}>
                            <motion.tr
                              initial={{ opacity: 0, y: 6 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: idx * 0.04 }}
                              className="border-b border-white/[0.03] hover:bg-white/[0.02] cursor-pointer transition-colors"
                              onClick={() =>
                                setExpandedRow(expandedRow === idx ? null : idx)
                              }
                            >
                              <td className="py-3.5 text-sm font-medium text-gray-200">
                                {attr.type || attr.entity_type || attr.name}
                              </td>
                              <td className="py-3.5 text-sm font-mono text-[var(--foreground)]">
                                {attr.value}{" "}
                                {attr.unit && (
                                  <span className="text-[var(--accent-blue)]">
                                    {attr.unit}
                                  </span>
                                )}
                              </td>
                              <td className="py-3.5 text-right">
                                <div className="flex items-center justify-end gap-2.5">
                                  <div className="w-14 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${attr.confidence >= 0.9
                                          ? "bg-emerald-400"
                                          : attr.confidence >= 0.75
                                            ? "bg-amber-400"
                                            : "bg-red-400"
                                        }`}
                                      style={{
                                        width: `${attr.confidence * 100}%`,
                                      }}
                                    />
                                  </div>
                                  <span className="text-xs font-mono text-[var(--secondary)] w-7">
                                    {(attr.confidence * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </td>
                            </motion.tr>
                            {/* Expanded Source */}
                            <AnimatePresence>
                              {expandedRow === idx && attr.source_text && (
                                <motion.tr
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: "auto" }}
                                  exit={{ opacity: 0, height: 0 }}
                                >
                                  <td
                                    colSpan={3}
                                    className="pb-3 pt-0 px-0"
                                  >
                                    <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 text-xs text-[var(--secondary)] italic leading-relaxed flex items-start gap-3">
                                      <ExternalLink
                                        size={12}
                                        className="shrink-0 mt-0.5 text-[var(--accent-blue)]"
                                      />
                                      {attr.source_text}
                                    </div>
                                  </td>
                                </motion.tr>
                              )}
                            </AnimatePresence>
                          </React.Fragment>
                        ))}
                      </tbody>
                    </table>
                  </motion.div>
                ) : activeTab === "dynamic" ? (
                  <motion.div
                    key="dynamic"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="space-y-4"
                  >
                    {Object.entries(record.record_data).filter(([k]) => k !== "entities" && k !== "excel_path").map(([key, val], i) => (
                      <div key={i} className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
                        <h4 className="text-xs font-semibold text-[var(--secondary)] uppercase tracking-wider mb-2">
                          {key.replace(/_/g, " ")}
                        </h4>
                        {typeof val === "object" ? (
                          <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">{JSON.stringify(val, null, 2)}</pre>
                        ) : (
                          <p className="text-sm text-gray-200">{String(val)}</p>
                        )}
                      </div>
                    ))}
                  </motion.div>
                ) : (
                  <motion.div
                    key="risks"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="space-y-2"
                  >
                    {record.risks?.map((r, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="flex items-center justify-between py-3 px-4 bg-white/[0.02] rounded-xl border border-white/5"
                      >
                        <span className="text-sm text-gray-300">{r.rule}</span>
                        <span
                          className={`flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider ${r.status === "pass"
                              ? "text-emerald-400"
                              : "text-red-400"
                            }`}
                        >
                          {r.status === "pass" ? (
                            <CheckCircle2 size={14} />
                          ) : (
                            <ShieldAlert size={14} />
                          )}
                          {r.status}
                        </span>
                      </motion.div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Right Sidebar */}
            <div className="space-y-5">
              {/* Tamper Proof */}
              <div className="glass-panel rounded-2xl p-5">
                <h3 className="text-xs font-semibold text-[var(--secondary)] uppercase tracking-wider mb-3 flex items-center gap-2">
                  <ShieldCheck size={14} className="text-emerald-400" /> Tamper Proof
                </h3>
                <p className="text-[10px] text-[var(--muted)] mb-2 uppercase tracking-wider">
                  HMAC-SHA256 Signature
                </p>
                <div className="bg-black/40 border border-white/5 p-3 rounded-xl relative group">
                  <code className="text-[11px] text-emerald-400 break-all font-mono leading-relaxed">
                    {record.content_hash}
                  </code>
                  <button
                    onClick={copyHash}
                    className="absolute top-2 right-2 text-[var(--muted)] hover:text-[var(--foreground)] transition-colors opacity-0 group-hover:opacity-100"
                  >
                    {copiedHash ? (
                      <Check size={14} className="text-emerald-400" />
                    ) : (
                      <Copy size={14} />
                    )}
                  </button>
                </div>
                <p className="text-[10px] text-[var(--muted)] mt-3 leading-relaxed">
                  Modify any field and the hash will break. Verify anytime via{" "}
                  <code className="text-[var(--accent-blue)]">/api/verify/{'{'}{params.id}{'}'}</code>
                </p>
              </div>

              {/* Validation Status */}
              <div className="glass-panel rounded-2xl p-5">
                <h3 className="text-xs font-semibold text-[var(--secondary)] uppercase tracking-wider mb-3">
                  Validation
                </h3>
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--secondary)]">Data validation passed</span>
                    {record.validation_passed ? (
                      <CheckCircle2 size={14} className="text-emerald-400" />
                    ) : (
                      <ShieldAlert size={14} className="text-red-400" />
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
