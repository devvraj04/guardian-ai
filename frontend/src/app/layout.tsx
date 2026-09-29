import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import MainContent from "@/components/MainContent";

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
        <AuthProvider>
          <Navbar />
          <MainContent>{children}</MainContent>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
