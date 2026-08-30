"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Box, LogIn, LogOut, LayoutDashboard, User, MessageSquare } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { ExecutionModeToggle } from "./ExecutionModeToggle";

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const isAuthPage = pathname?.startsWith("/login") || pathname?.startsWith("/register");

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userName, setUserName] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");
    if (token && token.length > 10) {
      setIsLoggedIn(true);
      try {
        const user = JSON.parse(userStr || "{}");
        setUserName(user.username || user.email || "User");
      } catch {
        setUserName("User");
      }
    } else {
      setIsLoggedIn(false);
    }
  }, [pathname]); // Re-check on route change

  const handleSignOut = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setIsLoggedIn(false);
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-50 w-full glass-panel border-b border-[var(--border)]">
      <div className="mx-auto max-w-[1600px] px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-3 text-[var(--foreground)] font-semibold text-lg tracking-tight hover:opacity-80 transition-opacity"
        >
          <img 
            src="/logo_circular_transparent.png" 
            alt="Alchemy AI Logo" 
            className="w-10 h-10 object-contain drop-shadow-[0_0_8px_rgba(139,92,246,0.5)]" 
          />
          <span>Alchemy AI</span>
        </Link>

        {/* Right Nav */}
        <div className="flex items-center gap-4">
          <ExecutionModeToggle />
          <ThemeToggle />
          {!isAuthPage && (
            <nav className="flex items-center gap-2">
              <Link
                href="/dashboard"
                className="flex items-center gap-1.5 text-[var(--secondary)] text-sm font-medium px-3.5 py-2 rounded-lg hover:text-[var(--foreground)] hover:bg-black/5 dark:hover:bg-white/5 transition-all"
              >
              <LayoutDashboard size={15} />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>

            {isLoggedIn && (
              <Link
                href="/chat"
                className="flex items-center gap-1.5 text-[var(--secondary)] text-sm font-medium px-3.5 py-2 rounded-lg hover:text-[var(--foreground)] hover:bg-black/5 dark:hover:bg-white/5 transition-all"
              >
                <MessageSquare size={15} />
                <span className="hidden sm:inline">Chat</span>
              </Link>
            )}

            {isLoggedIn ? (
              <div className="flex items-center gap-2">
                <span className="hidden sm:flex items-center gap-1.5 text-[var(--secondary)] text-xs px-3 py-2">
                  <User size={13} />
                  {userName}
                </span>
                <button
                  onClick={handleSignOut}
                  className="flex items-center gap-1.5 btn-ghost text-xs px-4 py-2 rounded-lg text-red-400 hover:bg-red-500/10 transition-all"
                >
                  <LogOut size={14} />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="flex items-center gap-1.5 btn-primary text-xs px-4 py-2"
              >
                <LogIn size={14} />
                <span className="hidden sm:inline">Sign In</span>
              </Link>
            )}
          </nav>
          )}
        </div>
      </div>
    </header>
  );
}
