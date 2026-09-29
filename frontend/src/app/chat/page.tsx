"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import {
  Send,
  Loader2,
  Bot,
  User,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

interface Message {
  role: "user" | "assistant";
  content: string;
  claim_id?: string;
  verification_status?: "grounded" | "flagged" | "unverified";
  warning_message?: string;
  source_module?: string;
}

function ChatContent() {
  const searchParams = useSearchParams();
  const initialLoanId = searchParams.get("loan_id") || "";

  const [loanId, setLoanId] = useState(initialLoanId);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const initChatSession = async (targetLoanId: string) => {
    try {
      setInitializing(true);
      setError(null);
      const res = await api.createChatSession(targetLoanId);
      setSessionId(res.id);
      setMessages([
        {
          role: "assistant",
          content:
            "Hello! I'm your GUARDIAN Financial Advisor. All my responses are grounded in RBI Master Directions and verified through our dual verification gate before display. Ask me anything about your loan terms, APR calculations, or hidden charges.",
          verification_status: "grounded",
        },
      ]);
    } catch (e: any) {
      setError(e.message || "Failed to start chat session.");
    } finally {
      setInitializing(false);
    }
  };

  useEffect(() => {
    if (initialLoanId) {
      initChatSession(initialLoanId);
    }
  }, [initialLoanId]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !loanId || !sessionId || loading) return;

    const userText = inputMessage.trim();
    setInputMessage("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);

    try {
      setLoading(true);
      setError(null);
      const response = await api.sendChatMessage(loanId, sessionId, userText);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.content || response.answer,
          claim_id: response.claim_id,
          verification_status:
            response.verification_status ||
            (response.is_grounded ? "grounded" : "flagged"),
          warning_message: response.warning_message,
          source_module: "m6_chatbot",
        },
      ]);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve verified response.");
    } finally {
      setLoading(false);
    }
  };

  const quickPrompts = [
    "Is my APR consistent with the KFS?",
    "Are prepayment penalties allowed on floating rate loans?",
    "What grievance mechanisms exist under RBI Ombudsman?",
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="section-label">AI Advisor</span>
          </div>
          <h1 className="text-xl font-bold text-[#1a1d23] flex items-center gap-2">
            Verified Financial Chatbot
          </h1>
          <p className="text-[13px] text-[#6b7280] mt-0.5">
            RAG-powered consultation with mandatory groundedness verification
          </p>
        </div>
        {sessionId && (
          <span className="badge-success text-[11px]">
            <span className="status-dot status-dot-success mr-1" />
            Active Session
          </span>
        )}
      </div>

      {/* Session Init Card */}
      {!sessionId && (
        <div className="card p-6 space-y-4 animate-slide-up">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-[#e8f0fe] flex items-center justify-center">
              <Bot className="h-5 w-5 text-[#0052cc]" />
            </div>
            <div>
              <h3 className="text-[14px] font-semibold text-[#1a1d23]">
                Start a Verified Consultation
              </h3>
              <p className="text-[12px] text-[#6b7280]">
                Enter a Loan ID to begin. All responses are verified before display.
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Enter loan session ID..."
              value={loanId}
              onChange={(e) => setLoanId(e.target.value)}
              className="input-field flex-1 font-mono text-[13px]"
            />
            <button
              onClick={() => initChatSession(loanId)}
              disabled={!loanId.trim() || initializing}
              className="btn-primary text-[13px]"
            >
              {initializing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Start Chat"
              )}
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-[#fef2f2] border border-[#fecaca] text-[12px] text-[#991b1b]">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Chat Window */}
      {sessionId && (
        <div className="card flex flex-col h-[560px] overflow-hidden">
          {/* Messages */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4">
            {messages.map((msg, index) => {
              const isAssistant = msg.role === "assistant";
              return (
                <div
                  key={index}
                  className={`flex gap-3 ${
                    isAssistant ? "justify-start" : "justify-end"
                  } animate-fade-in`}
                >
                  {isAssistant && (
                    <div className="h-8 w-8 rounded-lg bg-[#e8f0fe] flex items-center justify-center shrink-0">
                      <Bot className="h-4 w-4 text-[#0052cc]" />
                    </div>
                  )}

                  <div
                    className={`max-w-[75%] rounded-2xl p-4 text-[13px] leading-relaxed space-y-2 ${
                      isAssistant
                        ? "bg-[#f9fafb] border border-[#e5e7eb] text-[#374151]"
                        : "bg-[#0052cc] text-white"
                    }`}
                  >
                    <p>{msg.content}</p>

                    {/* Verification Badge */}
                    {isAssistant && msg.verification_status && (
                      <div className="pt-2 border-t border-[#e5e7eb] flex items-center justify-between">
                        <span
                          className={`flex items-center gap-1 text-[11px] font-semibold ${
                            msg.verification_status === "grounded"
                              ? "text-[#0d9f6e]"
                              : "text-[#dc2626]"
                          }`}
                        >
                          {msg.verification_status === "grounded" ? (
                            <ShieldCheck className="h-3.5 w-3.5" />
                          ) : (
                            <ShieldAlert className="h-3.5 w-3.5" />
                          )}
                          {msg.verification_status === "grounded"
                            ? "Verified & Grounded"
                            : "Flagged — Unverified"}
                        </span>
                        {msg.claim_id && (
                          <span className="font-mono text-[10px] text-[#9ca3af]">
                            {msg.claim_id.slice(0, 8)}
                          </span>
                        )}
                      </div>
                    )}

                    {msg.warning_message && (
                      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-[#fef2f2] border border-[#fecaca] text-[11px] text-[#991b1b]">
                        <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
                        {msg.warning_message}
                      </div>
                    )}
                  </div>

                  {!isAssistant && (
                    <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-[#0052cc] to-[#0078d4] flex items-center justify-center shrink-0">
                      <User className="h-4 w-4 text-white" />
                    </div>
                  )}
                </div>
              );
            })}

            {/* Loading indicator */}
            {loading && (
              <div className="flex gap-3 items-center animate-fade-in">
                <div className="h-8 w-8 rounded-lg bg-[#e8f0fe] flex items-center justify-center">
                  <Bot className="h-4 w-4 text-[#0052cc]" />
                </div>
                <div className="bg-[#f9fafb] border border-[#e5e7eb] rounded-2xl px-4 py-3 flex items-center gap-2 text-[13px] text-[#6b7280]">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-[#0052cc]" />
                  Retrieving context & verifying response...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="px-5 py-2.5 border-t border-[#e5e7eb] bg-[#f9fafb] flex gap-2 overflow-x-auto">
            {quickPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => setInputMessage(prompt)}
                className="shrink-0 text-[11px] font-medium text-[#6b7280] bg-white border border-[#e5e7eb] hover:border-[#0052cc] hover:text-[#0052cc] px-3 py-1.5 rounded-full transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Input */}
          <form
            onSubmit={handleSendMessage}
            className="p-4 border-t border-[#e5e7eb] flex gap-2 bg-white"
          >
            <input
              type="text"
              placeholder="Ask about loan terms, RBI compliance, or hidden charges..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              className="input-field flex-1 text-[13px]"
            />
            <button
              type="submit"
              disabled={loading || !inputMessage.trim()}
              className="btn-primary px-4"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-5 w-5 animate-spin text-[#0052cc]" />
        </div>
      }
    >
      <ChatContent />
    </Suspense>
  );
}
