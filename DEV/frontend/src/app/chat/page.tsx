"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Bot,
  User,
  Sparkles,
  MessageSquare,
  Trash2,
  Plus,
} from "lucide-react";

interface ConversationSummary {
  conversation_id: string;
  last_message: string;
  last_role: string;
  last_at: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [historyList, setHistoryList] = useState<ConversationSummary[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    setIsLoggedIn(!!token && token.length > 10);

    // Restore conversation ID from localStorage
    const savedConvId = localStorage.getItem("chatConversationId");
    if (savedConvId) {
      setConversationId(savedConvId);
      loadHistory(savedConvId);
    }
    loadHistoryList();
  }, []);

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [messages]);

  
  const loadHistoryList = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;
    try {
      const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:6104";
      const res = await fetch(`${API}/api/chat/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data.conversations || []);
      }
    } catch (e) {}
  };

  const loadHistory = async (convId: string) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:6104";
      const res = await fetch(
        `${API}/api/chat/history?conversation_id=${convId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
        }
      }
    } catch (e) {
      // Silently fail — fresh conversation
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const userMessage: Message = { role: "user", content: text.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const executionMode = localStorage.getItem("executionMode") || "online";
      const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:6104";
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "X-Execution-Mode": executionMode,
        },
        body: JSON.stringify({
          message: text.trim(),
          conversation_id: conversationId,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Chat request failed");
      }

      // Save conversation ID from headers (for new conversations)
      const convIdHeader = res.headers.get("X-Conversation-ID");
      if (convIdHeader && !conversationId) {
        setConversationId(convIdHeader);
        localStorage.setItem("chatConversationId", convIdHeader);
        loadHistoryList();
      }

      // Add placeholder for assistant message
      const assistantMessage: Message = { role: "assistant", content: "" };
      setMessages((prev) => [...prev, assistantMessage]);

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No readable stream");
      const decoder = new TextDecoder();
      let accumulatedResponse = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        accumulatedResponse += decoder.decode(value, { stream: true });
        
        // Dynamic regex to strip <think> blocks in real-time
        // Matches from <think> up to </think> or end of string if still generating
        const displayResponse = accumulatedResponse.replace(/<think>[\s\S]*?(<\/think>|$)/g, "").trimStart();

        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            content: displayResponse,
          };
          return newMessages;
        });
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry, something went wrong: ${err.message}`,
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSend = () => sendMessage(input);

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    localStorage.removeItem("chatConversationId");
    loadHistoryList();
  };

  const handleClearHistory = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:6104";
      // Clear specific conversation if active, else clear all
      const url = conversationId 
        ? `${API}/api/chat/history?conversation_id=${conversationId}`
        : `${API}/api/chat/history`;
        
      await fetch(url, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      handleNewConversation();
      loadHistoryList();
    } catch (e) {
      console.error("Failed to clear history", e);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
        <div className="glass-panel-strong rounded-3xl p-12 text-center max-w-md">
          <MessageSquare
            size={48}
            className="text-[var(--accent-blue)] mx-auto mb-6"
          />
          <h2 className="text-2xl font-bold text-[var(--foreground)] mb-3">
            Sign in to Chat
          </h2>
          <p className="text-[var(--secondary)] mb-6">
            Sign in to ask questions about your product scan history.
          </p>
          <a
            href="/login"
            className="btn-primary text-sm px-8 py-3 inline-block"
          >
            Sign In
          </a>
        </div>
      </div>
    );
  }

  
  return (
    <div className="flex h-[calc(100dvh-130px)] w-full max-w-5xl mx-auto relative z-10 pt-4 pb-6 px-4 md:px-6 gap-4">
      {/* Sidebar */}
      <div className="w-56 flex-shrink-0 flex-col gap-4 hidden md:flex border border-[var(--border)] rounded-2xl glass-panel p-4 overflow-hidden">
        <h2 className="text-[10px] font-semibold text-[var(--secondary)] uppercase tracking-widest px-1 mb-2">Past Conversations</h2>
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
          {historyList.length === 0 ? (
            <p className="text-xs text-[var(--muted)] px-1">No past conversations.</p>
          ) : (
            historyList.map(conv => (
              <button
                key={conv.conversation_id}
                onClick={() => {
                  setConversationId(conv.conversation_id);
                  localStorage.setItem("chatConversationId", conv.conversation_id);
                  loadHistory(conv.conversation_id);
                }}
                className={`w-full text-left p-3 rounded-xl transition-all ${conversationId === conv.conversation_id ? "bg-[var(--accent-blue)]/10 border border-[var(--accent-blue)]/20 text-[var(--accent-blue)]" : "bg-black/[0.02] dark:bg-white/[0.02] border border-transparent hover:border-[var(--border)] text-[var(--foreground)]"}`}
              >
                <p className="text-sm font-medium truncate mb-1">{conv.last_message}</p>
                <p className="text-[10px] text-[var(--muted)]">{new Date(conv.last_at).toLocaleDateString()}</p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col border border-[var(--border)] rounded-2xl overflow-hidden glass-panel">

      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between border-b border-[var(--border)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 border border-blue-500/20 flex items-center justify-center">
            <Sparkles size={18} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[var(--foreground)]">
              Alchemy AI Assistant
            </h1>
            <p className="text-xs text-[var(--muted)]">
              Ask about your product scans
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleClearHistory}
            className="btn-ghost text-xs px-3 py-2 rounded-lg flex items-center gap-1.5 text-red-400 hover:bg-red-500/10 hover:text-red-300"
            title="Clear chat history"
          >
            <Trash2 size={14} />
            Clear
          </button>
          <button
            onClick={handleNewConversation}
            className="btn-ghost text-xs px-3 py-2 rounded-lg flex items-center gap-1.5"
            title="New conversation"
          >
            <Plus size={14} />
            New Chat
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div 
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto px-6 py-6 space-y-4"
      >
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-full text-center"
          >
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/10 to-violet-500/10 border border-black/5 dark:border-white/5 flex items-center justify-center mb-6">
              <Bot size={28} className="text-blue-400" />
            </div>
            <h2 className="text-lg font-semibold text-[var(--foreground)] mb-2">
              How can I help?
            </h2>
            <p className="text-[var(--secondary)] max-w-xs text-xs mb-6">
              Ask me anything about your product scans — confidence scores,
              risk levels, comparisons, and more.
            </p>

            {/* Suggestion chips */}
            <div className="flex flex-wrap justify-center gap-2 max-w-lg">
              {[
                "What products have I scanned?",
                "Which scan has the highest risk?",
                "Show me a summary of all analyses",
                "Compare my products by confidence",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => sendMessage(suggestion)}
                  className="text-xs px-4 py-2 rounded-full border border-[var(--border)] bg-black/[0.02] dark:bg-white/[0.02] text-[var(--secondary)] hover:text-[var(--foreground)] hover:bg-black/5 dark:hover:bg-white/5 hover:border-black/10 dark:hover:border-white/10 transition-all"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex items-start gap-3 ${
                msg.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                  msg.role === "user"
                    ? "bg-blue-500/15 border border-blue-500/20 text-blue-950 dark:text-white"
                    : "bg-white/5 text-violet-400"
                }`}
              >
                {msg.role === "user" ? (
                  <User size={14} />
                ) : (
                  <Bot size={14} />
                )}
              </div>

              {/* Bubble */}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-500/15 border border-blue-500/20 text-black dark:text-white"
                    : "glass-panel text-[var(--secondary)]"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-xl bg-white/5 flex items-center justify-center text-violet-400">
              <Bot size={14} />
            </div>
            <div className="glass-panel rounded-2xl px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full bg-violet-400/60 animate-bounce"
                  style={{ animationDelay: "0ms" }}
                />
                <span
                  className="w-2 h-2 rounded-full bg-violet-400/60 animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <span
                  className="w-2 h-2 rounded-full bg-violet-400/60 animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Input Bar */}
      <div className="border-t border-[var(--border)] px-6 py-4">
        <div className="flex items-center gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask about your product scans..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 bg-black/[0.03] dark:bg-white/[0.03] border border-[var(--border)] rounded-xl text-[var(--foreground)] text-sm placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]/30 transition-all disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="btn-primary px-4 py-3 rounded-xl disabled:opacity-30 disabled:hover:scale-100 transition-all"
          >
            <Send size={16} />
          </button>
        </div>
        
        <p className="text-[10px] text-[var(--muted)] mt-2 text-center">
          Responses are grounded in your scan data. The assistant cannot access
          other users&apos; records.
        </p>
      </div>
    </div>
  </div>
  );
}
