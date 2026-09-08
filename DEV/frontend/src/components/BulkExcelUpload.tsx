"use client";

import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileSpreadsheet, CheckCircle2, ArrowRight, AlertCircle, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";

export default function BulkExcelUpload({
  onComplete,
  disabled = false,
  onUploadStart,
  onUploadEnd,
}: {
  onComplete?: () => void;
  disabled?: boolean;
  onUploadStart?: () => void;
  onUploadEnd?: () => void;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const router = useRouter();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    if (e.dataTransfer.files?.[0]) handleFileSelection(e.dataTransfer.files[0]);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (disabled) return;
    if (e.target.files?.[0]) handleFileSelection(e.target.files[0]);
  };

  const handleFileSelection = (selectedFile: File) => {
    setError(null);
    if (!selectedFile.name.endsWith(".xlsx") && !selectedFile.name.endsWith(".csv")) {
      setError("Only .xlsx or .csv files are accepted.");
      return;
    }
    setFile(selectedFile);
  };

  const startUploadAndProcess = async () => {
    if (!file || disabled) return;
    setIsUploading(true);
    setError(null);
    if (onUploadStart) onUploadStart();

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setError("You must be logged in.");
        setTimeout(() => router.push("/login"), 1500);
        if (onUploadEnd) onUploadEnd();
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      const API = "http://127.0.0.1:6104";

      const executionMode = localStorage.getItem("executionMode") || "online";
      const res = await fetch(`${API}/api/upload`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "X-Execution-Mode": executionMode
        },
        body: formData,
        signal: abortController.signal,
      });

      if (!res.ok) throw new Error(`Upload failed (${res.status})`);
      const data = await res.json();

      // Clean up the name for the URL slug
      const safeName = file.name.replace(/[^a-zA-Z0-9.-]/g, "_").replace(/\.(xlsx|csv)$/i, "");
      router.push(`/process/${safeName}-${data.document_id}?type=excel`);
      if (onUploadEnd) onUploadEnd();

    } catch (err: any) {
      if (err.name === "AbortError") {
        setError("Upload cancelled.");
      } else {
        setError(err.message || "Unexpected error.");
      }
      setIsUploading(false);
      if (onUploadEnd) onUploadEnd();
    }
  };

  return (
    <div className="w-full h-full max-w-xl mx-auto relative z-10 flex flex-col">
      <motion.div
        className={`relative overflow-hidden flex-1 flex flex-col glass-panel-strong rounded-3xl transition-all duration-500 ${isDragging
            ? "border-emerald-500/40 shadow-[0_0_60px_rgba(16,185,129,0.12)]"
            : "border border-black/5 dark:border-white/5 hover:border-black/10 dark:hover:border-white/10"
          }`}
        animate={{ scale: isDragging ? 0.98 : 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="p-6 sm:p-10 text-center flex-1 flex flex-col items-center justify-center min-h-[280px]">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".xlsx,.csv"
            className="hidden"
          />

          <AnimatePresence mode="wait">
            {!file ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.25 }}
                className="flex flex-col items-center"
              >
                <div
                  className={`p-4 rounded-2xl mb-5 transition-colors duration-300 ${isDragging
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-black/5 dark:bg-white/5 text-[var(--muted)]"
                    }`}
                >
                  <FileSpreadsheet size={36} strokeWidth={1.2} />
                </div>
                <h3 className="text-lg font-semibold text-[var(--foreground)] mb-2">
                  Bulk Process Documents
                </h3>
                <p className="text-[var(--secondary)] text-sm mb-7 max-w-xs leading-relaxed">
                  Upload an Excel or CSV file to extract many items at once.
                </p>
                <button
                  onClick={() => !disabled && fileInputRef.current?.click()}
                  disabled={disabled}
                  className="btn-primary text-sm px-7 py-3 w-full sm:w-auto disabled:opacity-50"
                >
                  Choose File
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="selected"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center w-full"
              >
                <div className="bg-black/5 dark:bg-white/5 p-4 rounded-2xl mb-4 relative border border-black/5 dark:border-white/5">
                  <FileSpreadsheet
                    size={36}
                    className="text-[var(--foreground)] opacity-80"
                    strokeWidth={1.2}
                  />
                  <div className="absolute -bottom-1.5 -right-1.5 bg-emerald-500 text-black p-1 rounded-full shadow-[0_0_12px_rgba(16,185,129,0.3)]">
                    <CheckCircle2 size={14} strokeWidth={2.5} />
                  </div>
                </div>

                <h3 className="text-base font-semibold text-[var(--foreground)] truncate max-w-[260px] mb-1">
                  {file.name}
                </h3>
                <p className="text-[var(--secondary)] text-xs mb-7">
                  {(file.size / 1024).toFixed(1)} KB
                </p>

                {isUploading ? (
                  <div className="flex flex-col sm:flex-row items-center justify-center gap-3 w-full max-w-xs mx-auto">
                    <button
                      onClick={() => {
                        if (isUploading && abortControllerRef.current) {
                          abortControllerRef.current.abort();
                        }
                        setFile(null);
                        setError(null);
                      }}
                      disabled={isUploading}
                      className="w-full sm:w-auto px-5 py-2.5 rounded-xl font-medium text-[var(--secondary)] hover:bg-black/5 dark:hover:bg-white/5 transition-colors disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      disabled={true}
                      className="w-full sm:w-auto btn-primary px-5 py-2.5 flex items-center justify-center gap-2"
                    >
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{
                          repeat: Infinity,
                          duration: 0.8,
                          ease: "linear",
                        }}
                        className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full"
                      />
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-3 w-full max-w-xs">
                    <button
                      onClick={() => {
                        setFile(null);
                        setError(null);
                      }}
                      disabled={isUploading || disabled}
                      className="flex-1 btn-ghost text-sm px-4 py-2.5 rounded-xl disabled:opacity-40"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={startUploadAndProcess}
                      disabled={isUploading || disabled}
                      className="flex-[2] btn-primary text-sm px-4 py-2.5 rounded-xl flex items-center justify-center gap-2 disabled:opacity-40 disabled:hover:scale-100"
                    >
                      Start <ArrowRight size={14} />
                    </button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Error toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="absolute top-[105%] left-0 w-full flex items-center gap-2.5 text-red-400 bg-red-950/60 border border-red-500/20 p-3.5 rounded-2xl text-sm font-medium backdrop-blur-xl"
          >
            <AlertCircle size={16} /> {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
