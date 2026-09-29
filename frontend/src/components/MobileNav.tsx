"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Menu,
  X,
  LayoutDashboard,
  FilePlus2,
  MessageCircle,
  Scale,
  Activity,
  ShieldCheck,
  LogOut,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function MobileNav() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user?.email) {
        setEmail(session.user.email);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setEmail(session?.user?.email || null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setOpen(false);
    router.push("/auth");
  };

  const navLinks = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/analysis/new", label: "New Analysis", icon: FilePlus2 },
    { href: "/chat", label: "AI Advisor", icon: MessageCircle },
    { href: "/disputes", label: "Disputes", icon: Scale },
    { href: "/audit", label: "Audit Trail", icon: Activity },
  ];

  return (
    <>
      {/* Hamburger button — mobile only */}
      <button
        onClick={() => setOpen(true)}
        className="md:hidden h-9 w-9 rounded-lg border border-[#e5e7eb] bg-white hover:bg-[#f3f4f6] flex items-center justify-center transition-colors"
        aria-label="Open menu"
      >
        <Menu className="h-4 w-4 text-[#6b7280]" />
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-[100] bg-black/30 backdrop-blur-sm md:hidden animate-fade-in"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 z-[110] h-full w-72 bg-white shadow-2xl transform transition-transform duration-300 md:hidden ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#e5e7eb]">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-[#0052cc] flex items-center justify-center">
              <ShieldCheck className="h-4 w-4 text-white" />
            </div>
            <span className="text-[14px] font-bold text-[#1a1d23]">GUARDIAN</span>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="h-8 w-8 rounded-lg hover:bg-[#f3f4f6] flex items-center justify-center transition-colors"
            aria-label="Close menu"
          >
            <X className="h-4 w-4 text-[#6b7280]" />
          </button>
        </div>

        {/* Nav Links */}
        <nav className="px-3 py-4 space-y-1">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium text-[#374151] hover:bg-[#f3f4f6] hover:text-[#0052cc] transition-all"
            >
              <link.icon className="h-5 w-5 text-[#6b7280]" />
              {link.label}
            </Link>
          ))}
        </nav>

        {/* User Info */}
        <div className="absolute bottom-0 left-0 right-0 p-5 border-t border-[#e5e7eb] bg-white">
          {email ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-[#0052cc] to-[#0078d4] flex items-center justify-center text-white text-sm font-bold shadow-sm">
                  {email.split("@")[0].substring(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="text-[13px] font-semibold text-[#1a1d23] truncate w-32">
                    {email.split("@")[0]}
                  </p>
                  <p className="text-[11px] text-[#9ca3af] truncate w-32">
                    {email}
                  </p>
                </div>
              </div>
              <button
                onClick={handleSignOut}
                className="h-9 w-9 rounded-lg border border-[#e5e7eb] bg-white hover:bg-[#fef2f2] hover:text-[#ef4444] hover:border-[#fca5a5] flex items-center justify-center transition-colors group"
                title="Sign Out"
              >
                <LogOut className="h-4 w-4 text-[#6b7280] group-hover:text-[#ef4444]" />
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <Link
                href="/auth"
                onClick={() => setOpen(false)}
                className="w-full flex justify-center py-2 px-4 border border-[#0052cc] rounded-lg text-sm font-semibold text-[#0052cc] hover:bg-[#e8f0fe] transition-colors"
              >
                Sign In
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
