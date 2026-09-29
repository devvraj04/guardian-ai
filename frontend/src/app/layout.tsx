import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import {
  ShieldCheck,
  LayoutDashboard,
  FilePlus2,
  MessageCircle,
  Scale,
  Bell,
  Menu,
  Activity,
} from "lucide-react";
import MobileNav from "@/components/MobileNav";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "GUARDIAN — Loan Verification Platform",
  description:
    "Groundedness-Verified Agentic Financial Advocate for Digital Lending Compliance",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light">
      <body
        className={`${inter.variable} font-sans min-h-screen bg-[#f8f9fb] text-[#1a1d23] flex flex-col`}
      >
        {/* ─── Top Navigation Bar ─── */}
        <header className="sticky top-0 z-50 w-full bg-white border-b border-[#e5e7eb]">
          <div className="max-w-[1360px] mx-auto flex h-16 items-center justify-between px-6">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="h-9 w-9 rounded-lg bg-[#0052cc] flex items-center justify-center shadow-sm shadow-blue-200">
                <ShieldCheck className="h-5 w-5 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-[15px] font-bold tracking-tight text-[#1a1d23] leading-none">
                  GUARDIAN
                </span>
                <span className="text-[10px] font-medium text-[#9ca3af] leading-none mt-0.5">
                  Loan Verification
                </span>
              </div>
            </Link>

            {/* Center Navigation (Desktop) */}
            <nav className="hidden md:flex items-center gap-1">
              <Link
                href="/"
                className="flex items-center gap-2 text-[13px] font-medium text-[#6b7280] hover:text-[#1a1d23] hover:bg-[#f3f4f6] px-3.5 py-2 rounded-lg transition-all"
              >
                <LayoutDashboard className="h-4 w-4" />
                Dashboard
              </Link>
              <Link
                href="/analysis/new"
                className="flex items-center gap-2 text-[13px] font-medium text-[#6b7280] hover:text-[#1a1d23] hover:bg-[#f3f4f6] px-3.5 py-2 rounded-lg transition-all"
              >
                <FilePlus2 className="h-4 w-4" />
                New Analysis
              </Link>
              <Link
                href="/chat"
                className="flex items-center gap-2 text-[13px] font-medium text-[#6b7280] hover:text-[#1a1d23] hover:bg-[#f3f4f6] px-3.5 py-2 rounded-lg transition-all"
              >
                <MessageCircle className="h-4 w-4" />
                AI Advisor
              </Link>
              <Link
                href="/disputes"
                className="flex items-center gap-2 text-[13px] font-medium text-[#6b7280] hover:text-[#1a1d23] hover:bg-[#f3f4f6] px-3.5 py-2 rounded-lg transition-all"
              >
                <Scale className="h-4 w-4" />
                Disputes
              </Link>
              <Link
                href="/audit"
                className="flex items-center gap-2 text-[13px] font-medium text-[#6b7280] hover:text-[#1a1d23] hover:bg-[#f3f4f6] px-3.5 py-2 rounded-lg transition-all"
              >
                <Activity className="h-4 w-4" />
                Audit
              </Link>
            </nav>

            {/* Right Side */}
            <div className="flex items-center gap-3">
              {/* Notification Bell */}
              <button className="relative h-9 w-9 rounded-lg border border-[#e5e7eb] bg-white hover:bg-[#f3f4f6] flex items-center justify-center transition-colors">
                <Bell className="h-4 w-4 text-[#6b7280]" />
                <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-[#0052cc] border-2 border-white" />
              </button>

              {/* User Avatar (Desktop) */}
              <div className="hidden md:flex items-center gap-2 pl-2 border-l border-[#e5e7eb]">
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[#0052cc] to-[#0078d4] flex items-center justify-center text-white text-xs font-bold shadow-sm">
                  TB
                </div>
                <div className="flex flex-col">
                  <span className="text-[13px] font-semibold text-[#1a1d23] leading-none">
                    Test Borrower
                  </span>
                  <span className="text-[11px] text-[#9ca3af] leading-none mt-0.5">
                    test_borrower@guardian.local
                  </span>
                </div>
              </div>

              {/* Mobile Hamburger */}
              <MobileNav />
            </div>
          </div>
        </header>

        {/* ─── Main Content ─── */}
        <main className="flex-1 max-w-[1360px] w-full mx-auto px-6 py-8">
          {children}
        </main>

        {/* ─── Footer ─── */}
        <footer className="border-t border-[#e5e7eb] bg-white py-5">
          <div className="max-w-[1360px] mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-3 text-[12px] text-[#9ca3af]">
            <div className="flex items-center gap-4">
              <span>© 2026 GUARDIAN AI Platform</span>
              <span className="hidden md:inline">·</span>
              <span className="hidden md:inline">
                Not an RBI-mandated or DPDP-certified application
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="badge-info text-[10px] py-1 px-2.5">
                Powered by RoBERTa-MNLI + ChromaDB
              </span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
