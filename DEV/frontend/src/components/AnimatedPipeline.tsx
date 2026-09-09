"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  FileSearch,
  ScanLine,
  Globe2,
  Layers,
  Tags,
  Brain,
  AlertTriangle,
  FileOutput,
} from "lucide-react";

export const pipelineStages = [
  { icon: FileSearch, label: "PDF Ingestion", color: "#3b82f6" },
  { icon: ScanLine, label: "OCR", color: "#8b5cf6" },
  { icon: Globe2, label: "Industry Detection", color: "#10b981" },
  { icon: Layers, label: "Attribute Extraction", color: "#f59e0b" },
  { icon: Tags, label: "Taxonomy", color: "#ef4444" },
  { icon: Brain, label: "AI Agent Research", color: "#ec4899" },
  { icon: AlertTriangle, label: "Risk Radar", color: "#f97316" },
  { icon: FileOutput, label: "Intelligence Gen", color: "#06b6d4" },
];

export default function AnimatedPipeline({ progress, isExcel = false }: { progress: number, isExcel?: boolean }) {
  // Determine how many stages should be active based on progress (0-100)
  // There are 8 stages.
  const activeStagesCount = Math.min(
    8,
    progress === 100 ? 8 : Math.floor((progress / 100) * 8) + 1
  );

  const displayStages = isExcel ? [
    { icon: FileSearch, label: "Excel Ingestion", color: "#3b82f6" },
    { icon: ScanLine, label: "Data Structuring", color: "#8b5cf6" },
    { icon: Globe2, label: "Categorization", color: "#10b981" },
    { icon: Layers, label: "Bulk Enrichment", color: "#f59e0b" },
    { icon: Tags, label: "Taxonomy", color: "#ef4444" },
    { icon: Brain, label: "AI Processing", color: "#ec4899" },
    { icon: AlertTriangle, label: "Risk Radar", color: "#f97316" },
    { icon: FileOutput, label: "Report Gen", color: "#06b6d4" },
  ] : pipelineStages;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      className="glass-panel rounded-2xl p-6 overflow-x-auto"
    >
      <div className="flex items-center justify-between min-w-[700px] gap-1">
        {displayStages.map((stage, i) => {
          const isActive = i < activeStagesCount;

          return (
            <motion.div
              key={stage.label}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.08 }}
              className="flex items-center gap-1"
            >
              <div className="flex flex-col items-center group cursor-default">
                <motion.div
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-2 transition-all duration-300 group-hover:scale-110"
                  animate={{
                    background: isActive ? `${stage.color}15` : "transparent",
                    borderColor: isActive ? `${stage.color}30` : "var(--border)",
                    boxShadow: isActive ? `0 0 20px ${stage.color}20` : "none",
                  }}
                  style={{
                    border: `1px solid var(--border)`,
                  }}
                >
                  <stage.icon
                    size={18}
                    style={{ color: isActive ? stage.color : "var(--muted)" }}
                    className={`transition-colors duration-300 ${isActive ? "opacity-100" : "opacity-40"}`}
                  />
                </motion.div>
                <span
                  className={`text-[10px] font-medium max-w-[70px] text-center leading-tight transition-colors duration-300 ${isActive ? "text-[var(--foreground)]" : "text-[var(--muted)]"
                    }`}
                >
                  {stage.label}
                </span>
              </div>
              {i < displayStages.length - 1 && (
                <div className="flex-1 min-w-[24px] h-[1px] bg-[var(--border)] relative overflow-hidden -mt-6">
                  {i < activeStagesCount - 1 && (
                    <motion.div
                      className="absolute inset-0 h-full w-full"
                      initial={{ x: "-100%" }}
                      animate={{ x: "0%" }}
                      transition={{ duration: 0.5 }}
                      style={{
                        background: `linear-gradient(90deg, transparent, ${stage.color}80, ${displayStages[i + 1].color})`,
                      }}
                    />
                  )}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
