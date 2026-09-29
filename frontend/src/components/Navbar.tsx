"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldCheck,
  LayoutDashboard,
  FilePlus2,
  MessageCircle,
  Scale,
  Bell,
  Activity,
} from "lucide-react";
import MobileNav from "@/components/MobileNav";
import UserMenu from "@/components/UserMenu";

export default function Navbar() {
  const pathname = usePathname();

  // Hide the navbar completely on the authentication page
  if (pathname === "/auth") {
    return null;
  }

  const navLinks = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/analysis/new", label: "New Analysis", icon: FilePlus2 },
    { href: "/chat", label: "AI Advisor", icon: MessageCircle },
    { href: "/disputes", label: "Disputes", icon: Scale },
    { href: "/audit", label: "Audit", icon: Activity },
  ];

  return (
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
          {navLinks.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 text-[13px] font-medium px-3.5 py-2 rounded-lg transition-all ${
                  isActive
                    ? "text-[#0052cc] bg-[#f0f5ff] font-semibold"
                    : "text-[#6b7280] hover:text-[#1a1d23] hover:bg-[#f3f4f6]"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-[#0052cc]" : ""}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Side */}
        <div className="flex items-center gap-3">
          {/* Notification Bell */}
          <button
            type="button"
            className="relative h-9 w-9 rounded-lg border border-[#e5e7eb] bg-white hover:bg-[#f3f4f6] flex items-center justify-center transition-colors"
            title="Notifications"
          >
            <Bell className="h-4 w-4 text-[#6b7280]" />
            <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-[#0052cc] border-2 border-white" />
          </button>

          <div className="hidden md:flex items-center pl-2 border-l border-[#e5e7eb]">
            <UserMenu />
          </div>

          {/* Mobile Hamburger */}
          <MobileNav />
        </div>
      </div>
    </header>
  );
}
