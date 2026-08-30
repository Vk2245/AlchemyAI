"use client";

import { useEffect, useState } from "react";
import { Server, Cloud } from "lucide-react";

export function ExecutionModeToggle() {
  const [isLocal, setIsLocal] = useState(false);

  useEffect(() => {
    // Load preference from localStorage
    const mode = localStorage.getItem("executionMode");
    if (mode === "local") {
      setIsLocal(true);
    } else {
      setIsLocal(false);
      // Ensure default is online if not set
      if (!mode) localStorage.setItem("executionMode", "online");
    }
  }, []);

  const toggleMode = () => {
    const newMode = !isLocal;
    setIsLocal(newMode);
    localStorage.setItem("executionMode", newMode ? "local" : "online");
    // Optionally trigger a reload or event so other components know immediately
    window.dispatchEvent(new Event("executionModeChanged"));
  };

  return (
    <button
      onClick={toggleMode}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors 
        hover:bg-black/5 dark:hover:bg-white/5 
        border-[var(--border)] text-[var(--secondary)]"
      title={`Current mode: ${isLocal ? 'VLLM' : 'Cloud'}`}
    >
      {isLocal ? (
        <>
          <Server size={14} className="text-green-500" />
          <span>VLLM</span>
        </>
      ) : (
        <>
          <Cloud size={14} className="text-blue-500" />
          <span>Cloud</span>
        </>
      )}
    </button>
  );
}
