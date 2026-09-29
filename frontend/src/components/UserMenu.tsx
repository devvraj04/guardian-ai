"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function UserMenu() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);

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
    router.push("/auth");
  };

  if (!email) {
    return null;
  }

  // Generate initials
  const initials = email
    .split("@")[0]
    .substring(0, 2)
    .toUpperCase();

  return (
    <div className="flex items-center gap-4">
      <div className="hidden md:flex flex-col items-end">
        <span className="text-[13px] font-semibold text-[#1a1d23] leading-none">
          {email.split("@")[0]}
        </span>
        <span className="text-[11px] text-[#9ca3af] leading-none mt-0.5">
          {email}
        </span>
      </div>
      <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[#0052cc] to-[#0078d4] flex items-center justify-center text-white text-xs font-bold shadow-sm">
        {initials}
      </div>
      <button
        onClick={handleSignOut}
        className="h-8 w-8 rounded-lg border border-[#e5e7eb] bg-white hover:bg-[#fef2f2] hover:text-[#ef4444] hover:border-[#fca5a5] flex items-center justify-center transition-colors group"
        title="Sign Out"
      >
        <LogOut className="h-4 w-4 text-[#6b7280] group-hover:text-[#ef4444]" />
      </button>
    </div>
  );
}
