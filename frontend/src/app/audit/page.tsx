"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import {
  Loader2,
  Clock,
  FileText,
  ShieldCheck,
  AlertTriangle,
  ArrowLeft,
  Search,
  Activity,
  ChevronDown,
} from "lucide-react";
import Link from "next/link";

interface AuditEntry {
  id: string;
  user_id?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  metadata: Record<string, any>;
  timestamp: string;
}

const ACTION_ICONS: Record<string, any> = {
  LOAN_CREATED: FileText,
  MANUAL_TERMS_ENTERED: FileText,
  DOCUMENT_UPLOADED: FileText,
  CLAIM_VERIFIED: ShieldCheck,
  PIPELINE_STARTED: Activity,
  PIPELINE_COMPLETED: Activity,
  DISPUTE_CREATED: AlertTriangle,
};

const ACTION_COLORS: Record<string, string> = {
  LOAN_CREATED: "bg-[#e8f0fe] text-[#0052cc]",
  MANUAL_TERMS_ENTERED: "bg-[#ecfdf5] text-[#0d9f6e]",
  DOCUMENT_UPLOADED: "bg-[#fffbeb] text-[#d97706]",
  CLAIM_VERIFIED: "bg-[#ecfdf5] text-[#0d9f6e]",
  PIPELINE_STARTED: "bg-[#e8f0fe] text-[#0052cc]",
  PIPELINE_COMPLETED: "bg-[#ecfdf5] text-[#0d9f6e]",
  DISPUTE_CREATED: "bg-[#fef2f2] text-[#dc2626]",
};

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loanIdFilter, setLoanIdFilter] = useState("");
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);

  const loadAuditLog = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getAuditLogs(loanIdFilter || undefined, 50);
      setEntries(res.entries || []);
    } catch (e: any) {
      setError(e.message || "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditLog();
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="section-label">Security</span>
        </div>
        <h1 className="text-xl font-bold text-[#1a1d23]">
          Audit Trail
        </h1>
        <p className="text-[13px] text-[#6b7280] mt-0.5">
          Append-only event log (RULES.md §S-21 — no UPDATE or DELETE permitted)
        </p>
      </div>

      {/* Filter Bar */}
      <div className="card p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-[#e8f0fe] flex items-center justify-center">
            <Search className="h-4 w-4 text-[#0052cc]" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-[#1a1d23]">
              Filter by Loan
            </p>
            <p className="text-[11px] text-[#9ca3af]">
              Leave blank to view all events
            </p>
          </div>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <input
            type="text"
            placeholder="Loan session ID..."
            value={loanIdFilter}
            onChange={(e) => setLoanIdFilter(e.target.value)}
            className="input-field flex-1 md:w-72 font-mono text-[13px]"
          />
          <button
            onClick={loadAuditLog}
            disabled={loading}
            className="btn-primary text-[13px]"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-[#fef2f2] border border-[#fecaca] text-[12px] text-[#991b1b] animate-fade-in">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Audit Entries */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#e5e7eb] bg-[#f9fafb] flex items-center justify-between">
          <h3 className="text-[14px] font-semibold text-[#1a1d23]">
            Event Log
          </h3>
          <span className="badge-neutral text-[11px]">
            {entries.length} {entries.length === 1 ? "Event" : "Events"}
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-14">
            <Loader2 className="h-5 w-5 animate-spin text-[#0052cc]" />
            <span className="ml-3 text-[13px] text-[#6b7280]">Loading audit trail...</span>
          </div>
        ) : entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-center">
            <div className="h-12 w-12 rounded-2xl bg-[#f3f4f6] flex items-center justify-center mb-3">
              <Activity className="h-6 w-6 text-[#9ca3af]" />
            </div>
            <p className="text-[13px] font-medium text-[#6b7280]">
              No audit events found
            </p>
            <p className="text-[12px] text-[#9ca3af] mt-0.5">
              Events will appear here as you use the platform
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[#f0f0f0]">
            {entries.map((entry) => {
              const IconComponent = ACTION_ICONS[entry.action] || Activity;
              const colorClass = ACTION_COLORS[entry.action] || "bg-[#f3f4f6] text-[#6b7280]";
              const isExpanded = expandedEntry === entry.id;

              return (
                <div
                  key={entry.id}
                  className="px-5 py-4 hover:bg-[#f9fafb] transition-colors cursor-pointer"
                  onClick={() => setExpandedEntry(isExpanded ? null : entry.id)}
                >
                  <div className="flex items-start gap-3.5">
                    <div className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${colorClass}`}>
                      <IconComponent className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-semibold text-[#1a1d23]">
                            {entry.action.replace(/_/g, " ")}
                          </span>
                          <span className="badge-neutral text-[10px] font-mono">
                            {entry.entity_type}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-[#9ca3af] flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(entry.timestamp).toLocaleString("en-IN", {
                              day: "2-digit",
                              month: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          <ChevronDown
                            className={`h-3.5 w-3.5 text-[#9ca3af] transition-transform ${
                              isExpanded ? "rotate-180" : ""
                            }`}
                          />
                        </div>
                      </div>
                      {entry.entity_id && (
                        <p className="text-[11px] text-[#9ca3af] font-mono mt-0.5 truncate">
                          Entity: {entry.entity_id}
                        </p>
                      )}
                      {/* Expanded metadata */}
                      {isExpanded && entry.metadata && Object.keys(entry.metadata).length > 0 && (
                        <div className="mt-3 bg-[#f9fafb] border border-[#e5e7eb] rounded-lg p-3 space-y-1.5 animate-fade-in">
                          {Object.entries(entry.metadata).map(([key, value]) => (
                            <div key={key} className="flex items-start gap-2 text-[12px]">
                              <span className="text-[#6b7280] font-medium min-w-[120px]">
                                {key}:
                              </span>
                              <span className="text-[#374151] font-mono break-all">
                                {typeof value === "object" ? JSON.stringify(value) : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
