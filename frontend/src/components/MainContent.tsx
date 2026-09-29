"use client";

import { usePathname } from "next/navigation";

export default function MainContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuth = pathname === "/auth";

  return (
    <main className={isAuth ? "flex-1 w-full" : "flex-1 max-w-[1360px] w-full mx-auto px-6 py-8"}>
      {children}
    </main>
  );
}
