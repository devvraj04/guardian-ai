"use client";

import { usePathname } from "next/navigation";

export default function Footer() {
  const pathname = usePathname();

  // Hide the footer on the authentication page
  if (pathname === "/auth") {
    return null;
  }

  return (
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
  );
}
