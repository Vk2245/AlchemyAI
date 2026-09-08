"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import AnimatedPipeline from "@/components/AnimatedPipeline";

interface LogEntry {
  id: string;
  message: string;
  timestamp: string;
}

export default function ProcessPage({ params }: { params: { slug: string } }) {
  const documentId = params.slug.split("-").pop();
  const searchParams = useSearchParams();
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<"connecting" | "processing" | "completed" | "error">("connecting");
  const [errorMsg, setErrorMsg] = useState("");
  const [isExcel, setIsExcel] = useState(false);
  
  const router = useRouter();
  const logsContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (searchParams.get("type") === "excel") {
      setIsExcel(true);
    }
  }, [searchParams]);

  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTo({
        top: logsContainerRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [logs]);

  useEffect(() => {
    if (!documentId) return;

    setStatus("processing");
    
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:6104";
    const token = localStorage.getItem("token") || "";
    const mode = searchParams.get("mode") || "online";
    const sseUrl = `${API_URL}/api/process/${documentId}?token=${token}&mode=${mode}`;
    console.log("CONNECTING TO SSE:", sseUrl);
    const eventSource = new EventSource(sseUrl);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("SSE EVENT RECEIVED:", data);
        
        if (data.is_excel !== undefined) {
          setIsExcel(data.is_excel);
        }

        if (data.progress !== undefined) {
          setProgress(data.progress);
        }
        
        if (data.message) {
          setLogs(prev => [...prev, {
            id: Date.now().toString() + Math.random().toString(),
            message: data.message,
            timestamp: new Date().toLocaleTimeString()
          }]);
        }
        
        if (data.status === "completed") {
          eventSource.close();
          setStatus("completed");
          setTimeout(() => {
            router.push(`/record/${documentId}`);
          }, 1500);
        } else if (data.status === "error") {
          eventSource.close();
          setStatus("error");
          setErrorMsg(data.message || "An error occurred during processing.");
        }
      } catch (err) {
        console.error("Failed to parse SSE data", err);
      }
    };
    
    eventSource.onerror = (err) => {
      console.error("SSE Error:", err);
      eventSource.close();
      setStatus("error");
      setErrorMsg("Connection to server lost. Please check if backend is running.");
    };
    
    return () => {
      console.log("Cleaning up EventSource");
      eventSource.close();
    };
  }, [documentId, router]);

  return (
    <div className="w-full max-w-5xl mx-auto flex flex-col relative z-10 h-[calc(100vh-160px)] justify-center py-2">
      <div className="text-center mb-4 shrink-0">
        <h1 className="text-2xl font-bold tracking-tight text-[var(--foreground)] mb-1">
          Analyzing Product Data
        </h1>
        <p className="text-[var(--secondary)] text-sm">
          Our AI pipeline is extracting, validating, and scoring the document.
        </p>
      </div>

      <div className="w-full glass-panel rounded-3xl p-5 md:p-6 flex flex-col flex-1 min-h-0 border border-[var(--border)] shadow-[0_0_40px_rgba(0,0,0,0.1)]">
        {/* Progress Bar Container */}
        <div className="mb-4 shrink-0">
          <div className="flex justify-between items-end mb-4">
            <span className="text-sm font-semibold text-[var(--secondary)] uppercase tracking-widest">
              {status === "completed" ? "Finished" : "Processing"}
            </span>
            <span className="text-4xl font-extrabold tracking-tighter text-gradient-accent">
              {progress}%
            </span>
          </div>
          
          <div className="h-3 w-full bg-black/40 rounded-full overflow-hidden relative border border-white/5">
            <motion.div 
              className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 rounded-full shadow-[0_0_15px_rgba(99,102,241,0.5)]"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ type: "spring", stiffness: 50, damping: 15 }}
            />
          </div>
        </div>

        {/* Pipeline Animation */}
        <div className="mb-4 shrink-0">
          <AnimatedPipeline progress={progress} isExcel={isExcel} />
        </div>

        {/* Live Logs */}
        <div 
          ref={logsContainerRef}
          className="flex-1 min-h-0 bg-black/5 dark:bg-black/40 rounded-2xl p-6 overflow-y-auto border border-black/5 dark:border-white/5 shadow-inner"
        >
          <div className="flex flex-col gap-4 font-mono text-sm">
            <AnimatePresence initial={false}>
              {logs.map((log) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-start gap-4 text-[var(--foreground)]"
                >
                  <span className="text-[var(--secondary)] whitespace-nowrap shrink-0">
                    [{log.timestamp}]
                  </span>
                  <span className="leading-relaxed text-[var(--foreground)]">{log.message}</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>
      
      {/* Status Indicators */}
      <AnimatePresence mode="wait">
        {status === "processing" && (
          <motion.div 
            key="processing"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex items-center self-center gap-4 mt-6 text-[var(--secondary)] bg-[var(--surface-dim)] pl-6 pr-3 py-2 rounded-full border border-[var(--border)]"
          >
            <Loader2 size={18} className="animate-spin text-blue-400" />
            <span className="text-sm font-medium tracking-wide">Pipeline running in the cloud...</span>
            <div className="w-px h-6 bg-[var(--border)] ml-2"></div>
            <button 
              onClick={() => router.push("/")}
              className="px-4 py-1.5 hover:bg-black/10 dark:hover:bg-white/10 text-[var(--foreground)] rounded-full text-xs font-semibold uppercase tracking-wider transition-colors"
            >
              Cancel
            </button>
          </motion.div>
        )}
        
        {status === "completed" && (
          <motion.div 
            key="completed"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 text-green-400 bg-green-950/30 px-6 py-3 rounded-full border border-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.1)] mt-6"
          >
            <CheckCircle2 size={18} />
            <span className="text-sm font-medium tracking-wide">Redirecting to results dashboard...</span>
          </motion.div>
        )}

        {status === "error" && (
          <motion.div 
            key="error"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-4 text-red-400 bg-red-950/50 border border-red-500/20 px-6 py-3 rounded-full shadow-[0_0_15px_rgba(239,68,68,0.1)] mt-6"
          >
            <div className="flex items-center gap-3">
              <AlertCircle size={18} />
              <span className="text-sm font-medium tracking-wide">{errorMsg}</span>
            </div>
            <button 
              onClick={() => window.location.reload()}
              className="px-3 py-1 bg-red-500/20 hover:bg-red-500/40 text-red-200 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors"
            >
              Retry
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
