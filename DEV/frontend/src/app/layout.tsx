import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

import { ThemeProvider } from "@/components/providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Alchemy AI | AI-Powered Product Intelligence",
  description:
    "Transform product PDFs into structured, validated, tamper-proof data using autonomous AI agents.",
  icons: {
    icon: "/logo_square.png",
    apple: "/logo_square.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.className} min-h-screen hero-bg bg-[var(--background)] text-[var(--foreground)] flex flex-col`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <Navbar />
          <main className="flex-1 w-full relative z-10 flex flex-col min-h-0">{children}</main>
          <footer className="w-full text-center py-8 text-[var(--muted)] text-sm relative z-10 border-t border-[var(--border)] flex flex-col items-center gap-2">
            <div className="flex items-center gap-2 font-semibold">
              <img src="/logo_circular_transparent.png" alt="Alchemy AI Logo" className="w-6 h-6 object-contain" />
              <span>Alchemy AI</span>
            </div>
            <p>© {new Date().getFullYear()} Alchemy AI. Built for the future of Document Intelligence.</p>
          </footer>
        </ThemeProvider>
      </body>
    </html>
  );
}
