"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Shield, ArrowRight, Loader2, Lock, Mail, AlertCircle } from "lucide-react";
import { supabase } from "@/lib/supabase";

function AuthForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get("returnUrl") || "/";

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    // Check if user is already logged in
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace(returnUrl);
      }
    });
  }, [router, returnUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (mode === "register") {
        const { error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        setSuccess("Registration successful! You can now log in.");
        setMode("login");
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        router.push(returnUrl);
      }
    } catch (err: any) {
      setError(err.message || "An error occurred during authentication.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f4f7f9] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="h-14 w-14 bg-gradient-to-br from-[#0052cc] to-[#003d99] rounded-2xl flex items-center justify-center shadow-lg transform transition-transform hover:scale-105">
            <Shield className="h-7 w-7 text-white" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-[#1a1d23] tracking-tight">
          Guardian AI
        </h2>
        <p className="mt-2 text-center text-sm text-[#6b7280]">
          {mode === "login"
            ? "Sign in to access your financial insights"
            : "Create an account to protect your financial interests"}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-xl sm:rounded-2xl sm:px-10 border border-[#e5e7eb] relative overflow-hidden group">
          {/* Subtle background glow effect */}
          <div className="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 rounded-full bg-[#0052cc] opacity-5 blur-3xl transition-opacity group-hover:opacity-10 pointer-events-none"></div>

          <form className="space-y-6 relative z-10" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-[#fef2f2] border border-[#f87171] rounded-lg p-4 flex items-start gap-3 animate-fade-in">
                <AlertCircle className="h-5 w-5 text-[#ef4444] shrink-0 mt-0.5" />
                <p className="text-sm text-[#991b1b]">{error}</p>
              </div>
            )}

            {success && (
              <div className="bg-[#f0fdf4] border border-[#4ade80] rounded-lg p-4 flex items-start gap-3 animate-fade-in">
                <Shield className="h-5 w-5 text-[#22c55e] shrink-0 mt-0.5" />
                <p className="text-sm text-[#166534]">{success}</p>
              </div>
            )}

            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-[#374151]"
              >
                Email address
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-[#9ca3af]" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field pl-10 block w-full transition-shadow focus:ring-2 focus:ring-[#0052cc]/20"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-[#374151]"
              >
                Password
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-[#9ca3af]" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pl-10 block w-full transition-shadow focus:ring-2 focus:ring-[#0052cc]/20"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-[#0052cc] hover:bg-[#003d99] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0052cc] disabled:opacity-70 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02]"
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    {mode === "login" ? "Sign in" : "Create account"}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[#e5e7eb]" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-[#6b7280]">
                  {mode === "login"
                    ? "New to Guardian?"
                    : "Already have an account?"}
                </span>
              </div>
            </div>

            <div className="mt-6">
              <button
                type="button"
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError(null);
                  setSuccess(null);
                }}
                className="w-full flex justify-center py-2.5 px-4 border border-[#d1d5db] rounded-lg shadow-sm bg-white text-sm font-medium text-[#4b5563] hover:bg-[#f9fafb] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0052cc] transition-colors"
              >
                {mode === "login"
                  ? "Create a new account"
                  : "Sign in to existing account"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#f4f7f9] flex flex-col justify-center py-12 sm:px-6 lg:px-8 items-center">
        <Loader2 className="h-8 w-8 text-[#0052cc] animate-spin" />
      </div>
    }>
      <AuthForm />
    </Suspense>
  );
}
