"use client";

import UploadZone from "@/components/UploadZone";
import BulkExcelUpload from "@/components/BulkExcelUpload";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Zap,
  ShieldCheck,
  Search,
  ArrowRight,
  FileText,
  BarChart3,
  Globe2,
  Layers,
  ChevronRight,
  Bot,
  LayoutDashboard,
  MessageSquare,
  ClipboardList,
  FileSearch,
  Brain,
  ScanLine,
  Tags,
  AlertTriangle,
  FileOutput,
  FileSpreadsheet,
} from "lucide-react";
import BranchedPipeline from "@/components/BranchedPipeline";
import { useState } from "react";

const stats = [
  { label: "Industries Supported", value: "8+", icon: Globe2 },
  { label: "Attributes Extracted", value: "50+", icon: Layers },
  { label: "Inference Speed", value: "<50ms", icon: Zap },
  { label: "Accuracy Rate", value: "94%", icon: BarChart3 },
];

const features = [
  {
    icon: Bot,
    color: "text-blue-400",
    bg: "bg-blue-500/10 border-blue-500/20",
    title: "Autonomous AI Agents",
    desc: "When your PDF is missing specs, our agents autonomously search the web, scrape data, and judge quality before filling gaps.",
  },
  {
    icon: ShieldCheck,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    title: "Tamper-Proof Records",
    desc: "Every extraction is cryptographically signed with HMAC-SHA256. Modify a single byte and the hash breaks — verifiable live.",
  },
  {
    icon: Zap,
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    title: "Hybrid Fast Path",
    desc: "DistilBERT ONNX models deliver <50ms CPU inference for industry classification. No GPU required.",
  },
  {
    icon: Search,
    color: "text-violet-400",
    bg: "bg-violet-500/10 border-violet-500/20",
    title: "3-Tier Web Research",
    desc: "DuckDuckGo → Playwright/Jina → Firecrawl OSS → Gemini fallback. Each tier is scored by an LLM-as-Judge.",
  },
  {
    icon: Globe2,
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
    title: "Industry Agnostic",
    desc: "Zero-shot classification adapts to electrical, pharma, food, agri, software, and more. No retraining needed.",
  },
  {
    icon: FileText,
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
    title: "PDF Product Intelligence",
    desc: "Automatic executive one-pager and full pipeline intelligence rendered as downloadable PDF with WeasyPrint.",
  },
];

const steps = [
  { num: "01", title: "Upload PDF", desc: "Drag-and-drop any product catalog, datasheet, or spec sheet." },
  { num: "02", title: "AI Extraction", desc: "8-stage pipeline extracts, validates, scores, and classifies data." },
  { num: "03", title: "Agent Research", desc: "Autonomous agents fill missing gaps by searching the web." },
  { num: "04", title: "Verified Product Intelligence", desc: "Download a tamper-proof, HMAC-signed product intelligence." },
];

const quickAccess = [
  {
    icon: LayoutDashboard,
    title: "Dashboard",
    desc: "View all analyzed catalogs, confidence scores, and processing history.",
    href: "/dashboard",
    color: "from-blue-500/20 to-blue-600/5",
    borderColor: "hover:border-blue-500/30",
    iconColor: "text-blue-400",
  },
  {
    icon: MessageSquare,
    title: "AI Chat",
    desc: "Ask questions about your uploaded documents using RAG-powered chat.",
    href: "/chat",
    color: "from-violet-500/20 to-violet-600/5",
    borderColor: "hover:border-violet-500/30",
    iconColor: "text-violet-400",
  },
  {
    icon: ClipboardList,
    title: "Sample Report",
    desc: "See what a finished intelligence report looks like.",
    href: "/record/demo",
    color: "from-emerald-500/20 to-emerald-600/5",
    borderColor: "hover:border-emerald-500/30",
    iconColor: "text-emerald-400",
  },
];

const pipelineStages = [
  { icon: FileSearch, label: "PDF Ingestion", color: "#3b82f6" },
  { icon: ScanLine, label: "OCR", color: "#8b5cf6" },
  { icon: Globe2, label: "Industry Detection", color: "#10b981" },
  { icon: Layers, label: "Attribute Extraction", color: "#f59e0b" },
  { icon: Tags, label: "Taxonomy", color: "#ef4444" },
  { icon: Brain, label: "AI Agent Research", color: "#ec4899" },
  { icon: AlertTriangle, label: "Risk Radar", color: "#f97316" },
  { icon: FileOutput, label: "Intelligence Gen", color: "#06b6d4" },
];

export default function Home() {
  const [activeUpload, setActiveUpload] = useState<"none" | "pdf" | "excel">("none");

  return (
    <div className="flex flex-col relative z-10">
      {/* ─── Hero ─── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-12 pb-8 flex flex-col items-center text-center">

        {/* Heading */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-3xl sm:text-4xl md:text-6xl font-extrabold tracking-tighter mb-2 text-balance leading-[1.1] relative z-10"
        >
          <span className="text-gradient-hero">Document Intelligence </span>
          <br className="hidden md:block" />
          <span className="text-gradient-accent">for SMEs.</span>
        </motion.h1>

        {/* Video Animation Overlay */}
        <div className="w-screen relative left-1/2 -translate-x-1/2 pointer-events-none mix-blend-screen -my-6 md:-my-12 flex justify-center items-center">
          <video 
            src="/video.mp4" 
            autoPlay 
            loop 
            muted 
            playsInline
            className="w-full h-[40vh] md:h-[55vh] object-cover opacity-90"
            style={{
              maskImage: "radial-gradient(ellipse at center, black 40%, transparent 80%)",
              WebkitMaskImage: "radial-gradient(ellipse at center, black 40%, transparent 80%)"
            }}
          />
        </div>

        {/* ALCHEMY AI text below jar - animated glow */}
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.8, ease: "easeOut" }}
          className="relative z-10 mb-6"
        >
          <motion.span
            className="text-2xl md:text-3xl font-extrabold tracking-[0.3em] uppercase bg-clip-text text-transparent bg-gradient-to-r from-violet-400 via-blue-400 to-violet-400 drop-shadow-lg"
            animate={{
              backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "linear",
            }}
            style={{
              backgroundSize: "200% 200%",
            }}
          >
           
          </motion.span>
        </motion.div>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="text-base md:text-lg text-[var(--secondary)] max-w-xl mx-auto text-balance leading-relaxed mb-8 relative z-10"
        >
          Upload any invoice, contract, or business document. Our AI agents extract, classify, and summarize critical information into structured data — all in seconds.
        </motion.p>

        {/* Upload Container */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch mx-auto"
        >
          {/* 1. PDF Upload */}
          <div className={activeUpload === "excel" ? "opacity-50 pointer-events-none transition-opacity" : "transition-opacity"}>
            <UploadZone 
              disabled={activeUpload === "excel"}
              onUploadStart={() => setActiveUpload("pdf")}
              onUploadEnd={() => setActiveUpload("none")}
            />
          </div>
          
          {/* 2. Excel/CSV Bulk Upload Section */}
          <div className={activeUpload === "pdf" ? "opacity-50 pointer-events-none transition-opacity" : "transition-opacity"}>
            <BulkExcelUpload 
              onComplete={() => window.location.href = '/dashboard'} 
              disabled={activeUpload === "pdf"}
              onUploadStart={() => setActiveUpload("excel")}
              onUploadEnd={() => setActiveUpload("none")}
            />
          </div>
        </motion.div>

        {/* Try demo link */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-4 flex items-center gap-4 text-sm"
        >
          <span className="text-gray-400">No PDF?</span>
          <Link
            href="/record/demo"
            className="text-[var(--accent-blue)] font-medium flex items-center gap-1 hover:underline underline-offset-4"
          >
            View sample report <ArrowRight size={13} />
          </Link>
        </motion.div>
      </section>

      {/* ─── Stats Strip ─── */}
      <section className="border-t border-b border-[var(--border)] bg-white/[0.01]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="flex flex-col items-center text-center"
            >
              <s.icon size={16} className="text-[var(--accent-blue)] mb-1.5" />
              <span className="text-2xl font-extrabold text-[var(--foreground)] tracking-tight stat-glow">
                {s.value}
              </span>
              <span className="text-[11px] text-[var(--secondary)] mt-1 font-medium">
                {s.label}
              </span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ─── Quick Access Cards ─── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
        <div className="text-center mb-8">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--foreground)] mb-2">
            Explore Your Workspace
          </h2>
          <p className="text-sm text-[var(--secondary)] max-w-md mx-auto">
            Jump into any module — analyze documents, chat with your data, or browse product intelligence.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {quickAccess.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <Link
                href={item.href}
                className={`block glass-panel rounded-xl p-5 group ${item.borderColor} border border-[var(--glass-border)] transition-all duration-300 hover:scale-[1.02]`}
              >
                <div className={`absolute inset-0 rounded-xl bg-gradient-to-br ${item.color} opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none`} />
                <div className="relative z-10">
                  <item.icon size={22} className={`${item.iconColor} mb-3`} />
                  <h3 className="text-base font-semibold text-[var(--foreground)] mb-1 flex items-center gap-1.5">
                    {item.title}
                    <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                  </h3>
                  <p className="text-xs text-[var(--secondary)] leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ─── Pipeline Visualization ─── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
        <div className="text-center mb-8">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--foreground)] mb-2">
            9-Stage Intelligence Pipeline
          </h2>
          <p className="text-sm text-[var(--secondary)] max-w-md mx-auto">
            Every document passes through our end-to-end AI pipeline.
          </p>
        </div>

        <BranchedPipeline />
      </section>

      {/* ─── How It Works ─── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
        <div className="text-center mb-10">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--foreground)] mb-3">
            How It Works
          </h2>
          <p className="text-sm text-[var(--secondary)] max-w-lg mx-auto">
            Four steps from raw PDF to verified, tamper-proof product intelligence.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {steps.map((step, i) => (
            <motion.div
              key={step.num}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.12 }}
              className="relative glass-panel rounded-xl p-5 group hover:border-black/10 dark:hover:border-white/10 transition-colors"
            >
              <span className="text-3xl font-extrabold text-[var(--foreground)] opacity-10 absolute top-3 right-3">
                {step.num}
              </span>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-bold text-[var(--accent-blue)] uppercase tracking-widest">
                  Step {step.num}
                </span>
                {i < steps.length - 1 && (
                  <ChevronRight
                    size={11}
                    className="text-[var(--muted)] hidden md:block"
                  />
                )}
              </div>
              <h3 className="text-sm font-semibold text-[var(--foreground)] mb-1">
                {step.title}
              </h3>
              <p className="text-xs text-[var(--secondary)] leading-relaxed">
                {step.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ─── Features Grid ─── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
        <div className="text-center mb-10">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--foreground)] mb-3">
            Built for Production
          </h2>
          <p className="text-sm text-[var(--secondary)] max-w-lg mx-auto">
            Enterprise-grade security, agentic AI, and zero cloud dependency.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="glass-panel rounded-xl p-5 group hover:border-white/10 transition-colors"
            >
              <div
                className={`w-9 h-9 rounded-lg border flex items-center justify-center mb-3 ${f.bg} ${f.color} group-hover:scale-110 transition-transform duration-300`}
              >
                <f.icon size={17} />
              </div>
              <h3 className="text-sm font-semibold text-[var(--foreground)] mb-1.5">
                {f.title}
              </h3>
              <p className="text-xs text-[var(--secondary)] leading-relaxed">
                {f.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ─── CTA Banner ─── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
        <div className="glass-panel-strong rounded-2xl p-8 text-center relative overflow-hidden dot-pattern">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-violet-500/5 pointer-events-none" />
          <h2 className="text-2xl font-bold text-[var(--foreground)] mb-3 relative z-10">
            Ready to extract intelligence?
          </h2>
          <p className="text-sm text-[var(--secondary)] mb-6 max-w-md mx-auto relative z-10">
            Create an account and start analyzing your first product catalog in under 60 seconds.
          </p>
          <div className="flex items-center justify-center gap-3 relative z-10">
            <Link
              href="/register"
              className="btn-primary text-xs px-6 py-2.5 flex items-center gap-2"
            >
              Get Started Free <ArrowRight size={13} />
            </Link>
            <Link
              href="/record/demo"
              className="btn-ghost text-xs px-5 py-2.5"
            >
              View Demo
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
