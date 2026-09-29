"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Loader2 } from "lucide-react";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isChecking, setIsChecking] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();

      if (!session && pathname !== "/auth") {
        router.push(`/auth?returnUrl=${encodeURIComponent(pathname)}`);
      } else {
        setIsAuthenticated(!!session);
      }
      setIsChecking(false);
    };

    checkAuth();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT" && pathname !== "/auth") {
        router.push("/auth");
      }
      setIsAuthenticated(!!session);
    });

    return () => subscription.unsubscribe();
  }, [pathname, router]);

  if (isChecking) {
    return (
      <div className="min-h-screen bg-[#f8f9fb] flex flex-col justify-center items-center">
        <Loader2 className="h-8 w-8 text-[#0052cc] animate-spin" />
        <p className="mt-4 text-sm text-[#6b7280]">Verifying secure session...</p>
      </div>
    );
  }

  // If we are on /auth, render normally (let the AuthPage handle itself).
  // If we are elsewhere and not authenticated, we should ideally not render children until redirected,
  // but since router.push is async, returning null briefly is safe.
  if (!isAuthenticated && pathname !== "/auth") {
    return null;
  }

  return <>{children}</>;
}
