export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";

// Auth token management — uses demo JWT by default, swappable for real Supabase Auth
let authToken: string | null = null;

// Valid JWT for test_borrower@guardian.local registered in Supabase
const DEMO_JWT = process.env.NEXT_PUBLIC_DEMO_JWT || "";

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function getAuthToken(): string {
  return authToken || DEMO_JWT;
}

export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE}${endpoint}`;

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${getAuthToken()}`);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorMsg = `API request failed (${res.status})`;
    try {
      const data = await res.json();
      errorMsg = data.message || data.detail || errorMsg;
      if (typeof errorMsg === "object") {
        errorMsg = JSON.stringify(errorMsg);
      }
    } catch (e) {
      // Ignored
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export const api = {
  // Health
  health: () => fetchApi("/health"),

  // Loans
  getLoans: () => fetchApi("/loans"),
  getLoan: (loanId: string) => fetchApi(`/loans/${loanId}`),
  createLoan: (data: { loan_name: string; lender_name: string }) =>
    fetchApi("/loans", { method: "POST", body: JSON.stringify(data) }),
  getLoanTerms: (loanId: string) => fetchApi(`/loans/${loanId}/terms`),
  saveTerms: (loanId: string, terms: { principal: number; disclosed_rate: number; tenure_months: number; fees?: number }) =>
    fetchApi(`/loans/${loanId}/terms`, { method: "POST", body: JSON.stringify(terms) }),

  // Documents
  uploadDocument: (loanId: string, docType: "tnc" | "kfs", file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", docType);
    return fetchApi(`/loans/${loanId}/documents/upload`, {
      method: "POST",
      body: formData,
    });
  },

  // Pipeline
  runPipeline: (loanId: string, data: { target_language?: string; monthly_income?: number; existing_obligations?: number } = {}) =>
    fetchApi(`/loans/${loanId}/pipeline/analyze`, { method: "POST", body: JSON.stringify(data) }),

  // Individual module endpoints
  runRecompute: (loanId: string) =>
    fetchApi(`/loans/${loanId}/recompute`, { method: "POST" }),
  runServiceability: (loanId: string, data: { monthly_income: number; existing_emis?: number; monthly_expenses?: number }) =>
    fetchApi(`/loans/${loanId}/serviceability`, { method: "POST", body: JSON.stringify(data) }),
  runConsistency: (loanId: string) =>
    fetchApi(`/loans/${loanId}/consistency`, { method: "POST" }),

  // Verification
  verifyClaim: (loanId: string, claimId: string) =>
    fetchApi(`/loans/${loanId}/claims/${claimId}/verify`, { method: "POST" }),
  getClaimVerification: (loanId: string, claimId: string) =>
    fetchApi(`/loans/${loanId}/claims/${claimId}/verification`),

  // Disputes
  getDisputes: (loanId: string) => fetchApi(`/loans/${loanId}/disputes`),
  getDispute: (loanId: string, disputeId: string) => fetchApi(`/loans/${loanId}/disputes/${disputeId}`),
  createDispute: (loanId: string, data: { free_text: string; category_override?: string }) =>
    fetchApi(`/loans/${loanId}/disputes`, { method: "POST", body: JSON.stringify(data) }),

  // Chat
  createChatSession: (loanId: string) =>
    fetchApi(`/loans/${loanId}/chat/sessions`, { method: "POST", body: JSON.stringify({}) }),
  getChatSessions: (loanId: string) =>
    fetchApi(`/loans/${loanId}/chat/sessions`),
  sendChatMessage: (loanId: string, sessionId: string, message: string) =>
    fetchApi(`/loans/${loanId}/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getChatHistory: (loanId: string, sessionId: string) =>
    fetchApi(`/loans/${loanId}/chat/sessions/${sessionId}/messages`),

  // Vernacular
  translateClaim: (loanId: string, claimId: string, targetLanguage: string) =>
    fetchApi(`/loans/${loanId}/claims/${claimId}/vernacular`, {
      method: "POST",
      body: JSON.stringify({ target_language: targetLanguage }),
    }),

  // Audit
  getAuditLogs: (loanId?: string, limit: number = 50) => {
    const params = new URLSearchParams();
    if (loanId) params.set("loan_id", loanId);
    params.set("limit", String(limit));
    return fetchApi(`/audit?${params.toString()}`);
  },
};
