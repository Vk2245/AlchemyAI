"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  FileText,
  TableProperties,
  ScanLine,
  Globe2,
  Layers,
  Tags,
  Brain,
  AlertTriangle,
  FileOutput,
  FileBox,
  Binary,
  Database,
  Network
} from "lucide-react";

export default function BranchedPipeline() {
  const commonTail = [
    { icon: Tags, label: "Taxonomy", color: "#ef4444" },
    { icon: Brain, label: "AI Agent Research", color: "#ec4899" },
    { icon: AlertTriangle, label: "Risk Radar", color: "#f97316" },
    { icon: FileOutput, label: "Intelligence Gen", color: "#06b6d4" },
  ];

  const pdfBranch = [
    { icon: FileText, label: "PDF Document", color: "#3b82f6" },
    { icon: ScanLine, label: "OCR Vision", color: "#8b5cf6" },
    { icon: Globe2, label: "Industry Detection", color: "#10b981" },
    { icon: Layers, label: "Attribute Extraction", color: "#f59e0b" },
  ];

  const excelBranch = [
    { icon: TableProperties, label: "Excel Catalog", color: "#22c55e" },
    { icon: Binary, label: "Data Structuring", color: "#6366f1" },
    { icon: Database, label: "Categorization", color: "#14b8a6" },
    { icon: Network, label: "Bulk Enrichment", color: "#eab308" },
  ];

  const StageNode = ({ stage, index, delayOffset = 0 }: { stage: any, index: number, delayOffset?: number }) => (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ delay: delayOffset + index * 0.1, duration: 0.4 }}
      className="flex flex-col items-center group cursor-default relative z-10"
    >
      <motion.div
        className="w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center mb-2 transition-all duration-300 group-hover:scale-110 bg-white/90 dark:bg-slate-900/80 backdrop-blur-md shadow-sm"
        style={{
          border: `1px solid ${stage.color}60`,
          boxShadow: `0 0 20px ${stage.color}25`,
        }}
        whileHover={{
          boxShadow: `0 0 30px ${stage.color}50`,
          borderColor: `${stage.color}`,
        }}
      >
        <stage.icon
          size={20}
          style={{ color: stage.color }}
          className="transition-colors duration-300"
        />
      </motion.div>
      <span className="text-[10px] md:text-[11px] font-medium max-w-[70px] text-center leading-tight text-[var(--foreground)]">
        {stage.label}
      </span>
    </motion.div>
  );

  const HorizontalLine = ({ color, delay }: { color: string, delay: number }) => (
    <div className="flex-1 h-[2px] bg-[var(--border)] relative overflow-hidden -mt-6 min-w-[20px] md:min-w-[40px]">
      <motion.div
        className="absolute inset-0 h-full w-full"
        initial={{ x: "-100%" }}
        whileInView={{ x: "0%" }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay, ease: "easeInOut" }}
        style={{
          background: `linear-gradient(90deg, transparent, ${color}80, ${color})`,
        }}
      />
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="glass-panel rounded-2xl p-4 md:p-8 overflow-hidden relative border border-white/10"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 pointer-events-none" />
      
      <div className="flex flex-col md:flex-row items-center justify-start md:justify-center gap-6 md:gap-0 max-w-full overflow-x-auto pb-4 custom-scrollbar">
        
        {/* Entry Node */}
        <div className="flex items-center self-start md:self-auto ml-4 md:ml-0">
          <StageNode stage={{ icon: FileBox, label: "Upload", color: "#94a3b8" }} index={0} />
        </div>

        {/* Branching SVG (Desktop) */}
        <div className="hidden md:block w-[60px] h-[120px] relative -mt-6">
          <svg className="w-full h-full absolute inset-0" preserveAspectRatio="none">
            <path
              d="M 0 60 C 30 60, 30 20, 60 20"
              fill="none"
              stroke="var(--border)"
              strokeWidth="2"
            />
            <path
              d="M 0 60 C 30 60, 30 100, 60 100"
              fill="none"
              stroke="var(--border)"
              strokeWidth="2"
            />
            <motion.path
              d="M 0 60 C 30 60, 30 20, 60 20"
              fill="none"
              stroke="#3b82f6"
              strokeWidth="2"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.2 }}
            />
            <motion.path
              d="M 0 60 C 30 60, 30 100, 60 100"
              fill="none"
              stroke="#22c55e"
              strokeWidth="2"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.2 }}
            />
          </svg>
        </div>

        {/* Parallel Branches */}
        <div className="flex flex-col gap-6 md:gap-10 relative mt-2 md:mt-0 ml-4 md:ml-0">
          {/* PDF Branch */}
          <div className="flex items-center bg-blue-500/5 dark:bg-blue-500/10 rounded-xl p-2 md:p-3 border border-blue-500/10 dark:border-blue-500/20 backdrop-blur-sm">
            {pdfBranch.map((stage, i) => (
              <React.Fragment key={stage.label}>
                <StageNode stage={stage} index={i} delayOffset={0.4} />
                {i < pdfBranch.length - 1 && <HorizontalLine color={stage.color} delay={0.4 + i * 0.1} />}
              </React.Fragment>
            ))}
          </div>

          {/* Excel Branch */}
          <div className="flex items-center bg-green-500/5 dark:bg-green-500/10 rounded-xl p-2 md:p-3 border border-green-500/10 dark:border-green-500/20 backdrop-blur-sm">
            {excelBranch.map((stage, i) => (
              <React.Fragment key={stage.label}>
                <StageNode stage={stage} index={i} delayOffset={0.4} />
                {i < excelBranch.length - 1 && <HorizontalLine color={stage.color} delay={0.4 + i * 0.1} />}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Merging SVG (Desktop) */}
        <div className="hidden md:block w-[60px] h-[120px] relative -mt-6">
          <svg className="w-full h-full absolute inset-0" preserveAspectRatio="none">
            <path
              d="M 0 20 C 30 20, 30 60, 60 60"
              fill="none"
              stroke="var(--border)"
              strokeWidth="2"
            />
            <path
              d="M 0 100 C 30 100, 30 60, 60 60"
              fill="none"
              stroke="var(--border)"
              strokeWidth="2"
            />
            <motion.path
              d="M 0 20 C 30 20, 30 60, 60 60"
              fill="none"
              stroke="#ef4444"
              strokeWidth="2"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 1.0 }}
            />
            <motion.path
              d="M 0 100 C 30 100, 30 60, 60 60"
              fill="none"
              stroke="#ef4444"
              strokeWidth="2"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 1.0 }}
            />
          </svg>
        </div>

        {/* Merged Tail */}
        <div className="flex items-center mt-6 md:mt-0 ml-4 md:ml-0 bg-red-500/5 dark:bg-red-500/10 rounded-xl p-2 md:p-3 border border-red-500/10 dark:border-red-500/20 backdrop-blur-sm">
          {commonTail.map((stage, i) => (
            <React.Fragment key={stage.label}>
              {i > 0 && <HorizontalLine color={commonTail[i-1].color} delay={1.2 + i * 0.1} />}
              <StageNode stage={stage} index={i} delayOffset={1.2} />
            </React.Fragment>
          ))}
        </div>

      </div>
    </motion.div>
  );
}
