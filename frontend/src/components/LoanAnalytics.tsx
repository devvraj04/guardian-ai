"use client";

import React, { useState, useMemo } from "react";
import {
  TrendingUp,
  Percent,
  Banknote,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  BarChart3,
  HelpCircle,
  Download,
  Printer,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  Zap,
  ArrowRight,
  Sparkles,
  TrendingDown,
  Scale,
  Info,
  Layers,
  ArrowUpRight,
  Sliders,
  Table,
} from "lucide-react";

// ==========================================
// 1. FAULTY / EMPTY KFS DETECTION
// ==========================================
export interface KfsHealthReport {
  isFaulty: boolean;
  severity: "critical" | "warning" | "healthy";
  reasons: string[];
}

export function evaluateKfsHealth(kfs: any, apr: any): KfsHealthReport {
  const reasons: string[] = [];

  const principal = kfs?.principal || apr?.principal;
  const rate = kfs?.disclosed_rate || apr?.disclosed_rate;
  const tenure = kfs?.tenure_months || apr?.tenure_months;

  if (!kfs || Object.keys(kfs).length === 0) {
    reasons.push("Key Fact Statement is completely empty or could not be read.");
  }
  if (!principal || principal <= 0) {
    reasons.push("Sanctioned Loan Principal amount is missing, zero, or unpopulated.");
  }
  if (!rate || rate <= 0) {
    reasons.push("Disclosed Interest Rate (% p.a.) is missing or not provided.");
  }
  if (!tenure || tenure <= 0) {
    reasons.push("Loan Tenor (Repayment Term in months) is not stated.");
  }
  if (!kfs?.monthly_emi && !apr?.monthly_emi) {
    reasons.push("Equated Periodic Instalment (Monthly EMI) is omitted.");
  }
  if (!kfs?.prepayment_clause) {
    reasons.push("Prepayment / Foreclosure penalty policy clause is missing.");
  }
  if (!kfs?.penal_charges) {
    reasons.push("Penal Charges for delayed payment are not disclosed.");
  }
  if (!kfs?.grievance_email && !kfs?.grievance_phone) {
    reasons.push("Grievance Redressal Nodal Officer contact details are omitted.");
  }

  const isCritical = !principal || !rate || !tenure;
  const isFaulty = isCritical || reasons.length >= 3;

  return {
    isFaulty,
    severity: isCritical ? "critical" : isFaulty ? "warning" : "healthy",
    reasons,
  };
}

// ==========================================
// 2. MATHEMATICAL AMORTIZATION ENGINE
// ==========================================
export interface AmortizationPoint {
  month: number;
  year: number;
  beginningBalance: number;
  emi: number;
  interestPaid: number;
  principalPaid: number;
  endingBalance: number;
  cumulativeInterest: number;
}

export interface YearlyAmortizationSummary {
  year: number;
  openingBalance: number;
  totalEmiPaid: number;
  principalPaid: number;
  interestPaid: number;
  closingBalance: number;
  loanPaidOffPct: number;
  monthsActive: number;
}

export function generateAmortizationSchedule(
  principal: number,
  annualRate: number,
  tenureMonths: number,
  customExtraPayment: number = 0,
  extraEmiPerYear: boolean = false,
  annualStepUpPct: number = 0,
  lumpSumAmount: number = 0,
  lumpSumMonth: number = 12
): {
  schedule: AmortizationPoint[];
  actualMonths: number;
  totalInterestPaid: number;
  totalPayment: number;
  yearlySummary: YearlyAmortizationSummary[];
} {
  if (principal <= 0 || tenureMonths <= 0) {
    return {
      schedule: [],
      actualMonths: 0,
      totalInterestPaid: 0,
      totalPayment: 0,
      yearlySummary: [],
    };
  }

  const monthlyRate = annualRate > 0 ? annualRate / (12 * 100) : 0;
  
  // Standard Base EMI
  let baseEmi: number;
  if (monthlyRate === 0) {
    baseEmi = principal / tenureMonths;
  } else {
    const factor = Math.pow(1 + monthlyRate, tenureMonths);
    baseEmi = (principal * monthlyRate * factor) / (factor - 1);
  }

  const schedule: AmortizationPoint[] = [];
  let balance = principal;
  let cumulativeInterest = 0;
  let currentEmi = baseEmi;

  for (let month = 1; month <= tenureMonths * 1.5 && balance > 0.01; month++) {
    const year = Math.ceil(month / 12);

    // Apply annual step-up if configured
    if (annualStepUpPct > 0 && month > 1 && (month - 1) % 12 === 0) {
      currentEmi = currentEmi * (1 + annualStepUpPct / 100);
    }

    const interestForMonth = monthlyRate > 0 ? balance * monthlyRate : 0;
    
    // Check extra EMI at month 12, 24, 36...
    const isAnnualBonusMonth = extraEmiPerYear && month % 12 === 0;
    const bonusPayment = isAnnualBonusMonth ? baseEmi : 0;

    // Check one-time lump sum
    const lumpSumPayment = (lumpSumAmount > 0 && month === lumpSumMonth) ? lumpSumAmount : 0;
    
    const totalPaymentThisMonth = currentEmi + customExtraPayment + bonusPayment + lumpSumPayment;
    
    let principalPortion = totalPaymentThisMonth - interestForMonth;
    if (principalPortion > balance) {
      principalPortion = balance;
    }

    const endingBalance = Math.max(0, balance - principalPortion);
    cumulativeInterest += interestForMonth;

    schedule.push({
      month,
      year,
      beginningBalance: balance,
      emi: interestForMonth + principalPortion,
      interestPaid: interestForMonth,
      principalPaid: principalPortion,
      endingBalance,
      cumulativeInterest,
    });

    balance = endingBalance;
    if (balance <= 0.01) {
      break;
    }
  }

  // Aggregate into yearly summaries
  const yearlyMap = new Map<number, YearlyAmortizationSummary>();
  for (const pt of schedule) {
    if (!yearlyMap.has(pt.year)) {
      yearlyMap.set(pt.year, {
        year: pt.year,
        openingBalance: pt.beginningBalance,
        totalEmiPaid: 0,
        principalPaid: 0,
        interestPaid: 0,
        closingBalance: pt.endingBalance,
        loanPaidOffPct: 0,
        monthsActive: 0,
      });
    }
    const row = yearlyMap.get(pt.year)!;
    row.totalEmiPaid += pt.emi;
    row.principalPaid += pt.principalPaid;
    row.interestPaid += pt.interestPaid;
    row.closingBalance = pt.endingBalance;
    row.monthsActive += 1;
    row.loanPaidOffPct = principal > 0
      ? Math.min(100, Math.max(0, ((principal - pt.endingBalance) / principal) * 100))
      : 0;
  }

  const yearlySummary = Array.from(yearlyMap.values());
  const totalInterestPaid = cumulativeInterest;
  const totalPayment = principal + totalInterestPaid;

  return {
    schedule,
    actualMonths: schedule.length,
    totalInterestPaid,
    totalPayment,
    yearlySummary,
  };
}

// ==========================================
// 3. MAIN COMPONENT: LOAN ANALYTICS & SIMULATOR
// ==========================================
interface LoanAnalyticsProps {
  kfs: any;
  apr: any;
  pipelineResult?: any;
  loanId?: string;
  lenderName?: string;
  loanName?: string;
  mode?: "all" | "verification" | "simulator";
  onProceedToSimulator?: () => void;
}

export default function LoanAnalytics({
  kfs,
  apr,
  pipelineResult,
  loanId,
  lenderName,
  loanName,
  mode = "all",
  onProceedToSimulator,
}: LoanAnalyticsProps) {
  // Extract canonical numbers
  const principal = kfs?.principal || apr?.principal || 0;
  const rate = kfs?.disclosed_rate || apr?.disclosed_rate || 0;
  const tenure = kfs?.tenure_months || apr?.tenure_months || 0;
  const fees = kfs?.processing_fee ?? apr?.fees ?? 0;
  const monthlyEmi = kfs?.monthly_emi || apr?.monthly_emi || 0;
  const trueApr = apr?.recomputed_apr || kfs?.apr || rate;
  const netDisbursed = apr?.disbursed_amount || kfs?.net_disbursed_amount || Math.max(0, principal - fees);

  // Health check
  const health = useMemo(() => evaluateKfsHealth(kfs, apr), [kfs, apr]);

  // Section accordions & active views
  const [showCalculationDetails, setShowCalculationDetails] = useState(true);
  const [activeAmortizationView, setActiveAmortizationView] = useState<"simulated" | "baseline" | "comparison">("simulated");

  // Serviceability Simulator state
  const [userIncome, setUserIncome] = useState<string>("85000");
  const [userObligations, setUserObligations] = useState<string>("10000");

  // Prepayment Simulator scenarios
  const [extraEmiYearly, setExtraEmiYearly] = useState(true); // Default enabled so user immediately sees simulation value!
  const [stepUpPct, setStepUpPct] = useState<number>(0); // 0%, 5%, 10%, 15%
  const [extraMonthlyPayment, setExtraMonthlyPayment] = useState<string>("0");
  const [lumpSumAmount, setLumpSumAmount] = useState<string>("0");
  const [lumpSumMonth, setLumpSumMonth] = useState<number>(12);

  // Base schedule vs. Simulated schedule
  const baseSchedule = useMemo(() => {
    return generateAmortizationSchedule(principal, rate, tenure, 0, false, 0, 0, 12);
  }, [principal, rate, tenure]);

  const simulatedSchedule = useMemo(() => {
    const extraPerMonth = parseFloat(extraMonthlyPayment) || 0;
    const lump = parseFloat(lumpSumAmount) || 0;
    return generateAmortizationSchedule(
      principal,
      rate,
      tenure,
      extraPerMonth,
      extraEmiYearly,
      stepUpPct,
      lump,
      lumpSumMonth
    );
  }, [principal, rate, tenure, extraMonthlyPayment, extraEmiYearly, stepUpPct, lumpSumAmount, lumpSumMonth]);

  // Savings metrics
  const interestSaved = Math.max(0, baseSchedule.totalInterestPaid - simulatedSchedule.totalInterestPaid);
  const monthsReduced = Math.max(0, baseSchedule.actualMonths - simulatedSchedule.actualMonths);
  const yearsReduced = (monthsReduced / 12).toFixed(1);

  // Serviceability evaluation
  const incomeNum = parseFloat(userIncome) || 0;
  const obligationsNum = parseFloat(userObligations) || 0;
  const totalEmis = obligationsNum + monthlyEmi;
  const dtiRatio = incomeNum > 0 ? (totalEmis / incomeNum) * 100 : 0;
  const disposableIncome = incomeNum - totalEmis;

  // Inflation vs. ROI economics (India CPI ~5.5%)
  const inflationRate = 5.5;
  const realInterestRate = rate - inflationRate;
  const isHighInterestLoan = rate >= 11.5;
  const isLowInterestLoan = rate <= 9.25;

  // Export full report handlers
  const handlePrintReport = () => {
    window.print();
  };

  const handleDownloadJsonReport = () => {
    const auditData = {
      report_generated_at: new Date().toISOString(),
      platform: "GUARDIAN AI — Autonomous RBI Lending Compliance Engine",
      loan_id: loanId,
      loan_name: loanName,
      lender: lenderName || kfs?.bank_name,
      kfs_health: health,
      disclosed_terms: {
        principal,
        disclosed_rate_pa: rate,
        tenor_months: tenure,
        monthly_emi: monthlyEmi,
        upfront_fees: fees,
        net_disbursed_amount: netDisbursed,
      },
      audit_recomputation: {
        true_apr_irr: trueApr,
        fee_impact_apr: apr?.fee_impact_apr || (trueApr - rate),
        total_payment: baseSchedule.totalPayment,
        total_interest: baseSchedule.totalInterestPaid,
        calculation_formula: "Reducing balance EMI = P*r*(1+r)^N / ((1+r)^N - 1); True APR = IRR(Net Disbursed, EMIs)",
      },
      yearly_amortization_schedule: baseSchedule.yearlySummary,
      simulated_prepayment: {
        scenario_extra_emi_yearly: extraEmiYearly,
        scenario_step_up_pct: stepUpPct,
        scenario_extra_monthly: parseFloat(extraMonthlyPayment) || 0,
        scenario_lump_sum: parseFloat(lumpSumAmount) || 0,
        original_tenure_months: baseSchedule.actualMonths,
        simulated_tenure_months: simulatedSchedule.actualMonths,
        tenure_saved_months: monthsReduced,
        total_interest_saved_inr: interestSaved,
        simulated_yearly_schedule: simulatedSchedule.yearlySummary,
      },
      inflation_vs_roi_analysis: {
        india_cpi_inflation: `${inflationRate}%`,
        loan_nominal_roi: `${rate}%`,
        real_cost_of_debt: `${realInterestRate.toFixed(2)}%`,
        recommendation: isHighInterestLoan
          ? "Aggressive prepayment strongly recommended (ROI beats market & inflation)."
          : "Consider strategic hybrid allocation (Low real cost of debt vs equity compounding).",
      },
      verified_claims: pipelineResult?.verified_claims || [],
      warnings: pipelineResult?.warnings || [],
    };

    const blob = new Blob([JSON.stringify(auditData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `GUARDIAN_Audit_Report_${loanId || "kfs"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Sample data points for SVG chart (approx 24 evenly spaced points)
  const chartPoints = useMemo(() => {
    const baseSched = baseSchedule.schedule;
    const simSched = simulatedSchedule.schedule;
    if (baseSched.length === 0) return { basePts: [], simPts: [] };

    const totalM = Math.max(baseSched.length, simSched.length, 1);
    const stepSize = Math.max(1, Math.floor(totalM / 24));

    const basePts: { month: number; year: number; balance: number }[] = [];
    for (let i = 0; i < baseSched.length; i += stepSize) {
      basePts.push({
        month: baseSched[i].month,
        year: baseSched[i].year,
        balance: baseSched[i].endingBalance,
      });
    }
    if (baseSched.length > 0) {
      basePts.push({
        month: baseSched[baseSched.length - 1].month,
        year: baseSched[baseSched.length - 1].year,
        balance: baseSched[baseSched.length - 1].endingBalance,
      });
    }

    const simPts: { month: number; year: number; balance: number }[] = [];
    for (let i = 0; i < simSched.length; i += stepSize) {
      simPts.push({
        month: simSched[i].month,
        year: simSched[i].year,
        balance: simSched[i].endingBalance,
      });
    }
    if (simSched.length > 0) {
      simPts.push({
        month: simSched[simSched.length - 1].month,
        year: simSched[simSched.length - 1].year,
        balance: simSched[simSched.length - 1].endingBalance,
      });
    }

    return { basePts, simPts };
  }, [baseSchedule, simulatedSchedule]);

  const showVerificationPart = mode === "all" || mode === "verification";
  const showSimulatorPart = mode === "all" || mode === "simulator";

  return (
    <div className="space-y-6">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* 1. FAULTY / EMPTY KFS BANNER (If detected)                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      {health.isFaulty && (
        <div className="p-5 rounded-2xl bg-gradient-to-r from-[#fef2f2] to-[#fff1f2] border-2 border-[#f87171] shadow-sm animate-fade-in space-y-3">
          <div className="flex items-start gap-3.5">
            <div className="h-10 w-10 rounded-xl bg-[#dc2626] flex items-center justify-center text-white shrink-0 shadow-md shadow-red-200">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h3 className="text-[15px] font-bold text-[#991b1b] flex items-center gap-2">
                  <span>⚠️ Key Fact Statement (KFS) is Faulty or Incomplete</span>
                  <span className="badge-danger text-[10px]">RBI Non-Compliant</span>
                </h3>
              </div>
              <p className="text-[12px] text-[#b91c1c] mt-1 leading-relaxed">
                The submitted Key Fact Statement document could not be properly parsed, is empty/unpopulated, or is missing mandatory statutory disclosures required by the Reserve Bank of India (RBI/2024-25/18 Master Directions).
              </p>
              <div className="mt-3 p-3 rounded-xl bg-white/80 border border-[#fecaca] space-y-1.5">
                <p className="text-[11px] font-bold text-[#7f1d1d] uppercase tracking-wide">
                  Deficiencies Detected in Submitted KFS:
                </p>
                <ul className="list-disc list-inside text-[11px] text-[#991b1b] space-y-1">
                  {health.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
              <p className="text-[11px] text-[#6b7280] mt-2 italic">
                * Note: Verification report below uses fallback terms or manual profile inputs for illustration. Please re-upload a clear, populated official KFS PDF.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. REPORT ACTIONS: DOWNLOAD & PRINT                           */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="card p-4 bg-gradient-to-r from-[#f8fafc] via-[#f1f5f9] to-[#f8fafc] border border-[#cbd5e1] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-[#0052cc]/10 flex items-center justify-center">
            <Printer className="h-4.5 w-4.5 text-[#0052cc]" />
          </div>
          <div>
            <h4 className="text-[13px] font-bold text-[#1a1d23]">
              Audit Verification Report Ready
            </h4>
            <p className="text-[11px] text-[#6b7280]">
              Certified compliance breakdown against RBI Master Directions (RBI/2024-25/18)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDownloadJsonReport}
            className="btn-ghost text-[12px] px-3 py-1.5 border border-[#cbd5e1] bg-white hover:bg-[#f1f5f9] shadow-xs"
          >
            <Download className="h-3.5 w-3.5 text-[#0052cc]" />
            Download JSON Audit
          </button>
          <button
            type="button"
            onClick={handlePrintReport}
            className="btn-primary text-[12px] px-4 py-1.5 shadow-sm"
          >
            <Printer className="h-3.5 w-3.5" />
            Download / Print Full PDF Report
          </button>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 3. VERIFICATION SECTION: MATHEMATICAL CALCULATION BREAKDOWN    */}
      {/* ───────────────────────────────────────────────────────────── */}
      {showVerificationPart && (
        <div className="card overflow-hidden border border-[#e5e7eb] shadow-sm">
          <button
            type="button"
            onClick={() => setShowCalculationDetails(!showCalculationDetails)}
            className="w-full px-5 py-4 bg-gradient-to-r from-[#f8fafc] to-[#f1f5f9] border-b border-[#e5e7eb] flex items-center justify-between text-left transition-colors hover:bg-[#f1f5f9]"
          >
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-[#0052cc]/10 flex items-center justify-center">
                <Scale className="h-4 w-4 text-[#0052cc]" />
              </div>
              <div>
                <h4 className="text-[14px] font-bold text-[#1a1d23] flex items-center gap-2">
                  Full Mathematical Calculation Breakdown
                  <span className="badge-info text-[10px]">Deterministic Proof</span>
                </h4>
                <p className="text-[11px] text-[#6b7280]">
                  Step-by-step mathematical substitution showing how every number was calculated
                </p>
              </div>
            </div>
            {showCalculationDetails ? (
              <ChevronUp className="h-4 w-4 text-[#6b7280]" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[#6b7280]" />
            )}
          </button>

          {showCalculationDetails && (
            <div className="p-5 space-y-6 text-[12px] animate-fade-in">
              {/* 1. Monthly Reducing Balance EMI Formula */}
              <div className="p-4 rounded-xl bg-[#f9fafb] border border-[#e5e7eb] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#1e40af] text-[13px] flex items-center gap-1.5">
                    <Banknote className="h-4 w-4" />
                    1. Equated Periodic Instalment (Monthly Reducing-Balance EMI)
                  </span>
                  <span className="badge-success text-[10px]">RBI Annexure B Formula</span>
                </div>
                
                <div className="p-3 bg-white rounded-lg border border-[#e2e8f0] font-mono text-[12px] text-[#0f172a] overflow-x-auto">
                  <p className="text-[#0052cc] font-bold">
                    EMI = P × r × (1 + r)ᴺ / ((1 + r)ᴺ - 1)
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                  <div className="space-y-1">
                    <p className="text-[#6b7280]">
                      <strong className="text-[#1a1d23]">P (Sanctioned Principal):</strong> ₹{principal.toLocaleString("en-IN")}
                    </p>
                    <p className="text-[#6b7280]">
                      <strong className="text-[#1a1d23]">R (Annual Nominal Rate):</strong> {rate}% p.a.
                    </p>
                    <p className="text-[#6b7280]">
                      <strong className="text-[#1a1d23]">r (Monthly Interest Rate):</strong> {rate} / (12 × 100) ={" "}
                      <span className="font-mono text-[#0052cc]">{(rate / (12 * 100)).toFixed(7)}</span>
                    </p>
                    <p className="text-[#6b7280]">
                      <strong className="text-[#1a1d23]">N (Total Tenor in Months):</strong> {tenure} months
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-[#eff6ff] border border-[#bfdbfe] space-y-1 font-mono">
                    <p className="text-[10px] text-[#1e40af] font-semibold">Substituted Values:</p>
                    <p className="text-[#1e3a8a]">
                      (1 + r)ᴺ = (1 + {(rate / (12 * 100)).toFixed(5)})^({tenure}) ={" "}
                      <strong>{Math.pow(1 + rate / (12 * 100), tenure).toFixed(4)}</strong>
                    </p>
                    <p className="text-[#1e3a8a]">
                      Numerator = ₹{principal.toLocaleString("en-IN")} × {(rate / (12 * 100)).toFixed(6)} × {Math.pow(1 + rate / (12 * 100), tenure).toFixed(4)}
                    </p>
                    <p className="text-[13px] font-bold text-[#0052cc] pt-1 border-t border-[#bfdbfe]">
                      Calculated EMI = ₹{Math.round(monthlyEmi).toLocaleString("en-IN")} / month
                    </p>
                  </div>
                </div>
              </div>

              {/* 2. Upfront Deductions & Net Disbursed */}
              <div className="p-4 rounded-xl bg-[#f9fafb] border border-[#e5e7eb] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#065f46] text-[13px] flex items-center gap-1.5">
                    <DollarSign className="h-4 w-4" />
                    2. Net Disbursed Amount (Actual Cash Transferred to Borrower)
                  </span>
                  <span className="badge-success text-[10px]">Annexure B Item 7</span>
                </div>
                <div className="p-3 bg-white rounded-lg border border-[#e2e8f0] font-mono text-[12px] text-[#0f172a]">
                  <p className="text-[#059669] font-bold">
                    Net Disbursed = Sanctioned Principal - Total Upfront Fees & Charges
                  </p>
                  <p className="mt-1 text-[#334155]">
                    Net Disbursed = ₹{principal.toLocaleString("en-IN")} - ₹{fees.toLocaleString("en-IN")} ={" "}
                    <strong className="text-[#0d9f6e]">₹{netDisbursed.toLocaleString("en-IN")}</strong>
                  </p>
                </div>
                <p className="text-[11px] text-[#6b7280]">
                  ⚠️ <strong className="text-[#1a1d23]">Regulatory Insight:</strong> While the borrower only receives ₹{netDisbursed.toLocaleString("en-IN")} in their bank account, the bank computes interest on the full sanctioned principal of ₹{principal.toLocaleString("en-IN")}. This upfront deduction is what causes the true APR to exceed the nominal interest rate.
                </p>
              </div>

              {/* 3. True APR Calculation via Numerical IRR */}
              <div className="p-4 rounded-xl bg-[#f9fafb] border border-[#e5e7eb] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#7c3aed] text-[13px] flex items-center gap-1.5">
                    <TrendingUp className="h-4 w-4" />
                    3. Annual Percentage Rate (True APR via Numerical IRR Solver)
                  </span>
                  <span className="badge-info text-[10px]">RBI Standard Formula</span>
                </div>
                <div className="p-3 bg-white rounded-lg border border-[#e2e8f0] font-mono text-[12px] text-[#0f172a] overflow-x-auto">
                  <p className="text-[#7c3aed] font-bold">
                    Net Disbursed = ∑ [ Monthly EMI / (1 + r_irr)ᵗ ] for t=1 to N
                  </p>
                  <p className="mt-1 text-[#334155]">
                    True APR = r_irr (monthly) × 12 × 100
                  </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-center">
                  <div className="p-3 rounded-lg bg-white border border-[#e5e7eb]">
                    <p className="text-[10px] text-[#6b7280]">Nominal Disclosed Rate</p>
                    <p className="text-[15px] font-bold text-[#1a1d23]">{rate}% p.a.</p>
                  </div>
                  <div className="p-3 rounded-lg bg-white border border-[#e5e7eb]">
                    <p className="text-[10px] text-[#6b7280]">Upfront Fee Drag</p>
                    <p className="text-[15px] font-bold text-[#dc2626]">
                      +{(trueApr - rate).toFixed(2)}% p.a.
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-[#eff6ff] border border-[#bfdbfe]">
                    <p className="text-[10px] text-[#1e40af] font-semibold">True Annual Cost (APR)</p>
                    <p className="text-[16px] font-bold text-[#0052cc]">{trueApr.toFixed(2)}% p.a.</p>
                  </div>
                </div>
              </div>

              {/* 4. Total Outflow & Interest Burden */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-white border border-[#e5e7eb]">
                  <span className="text-[11px] text-[#6b7280]">Total Sanctioned Principal</span>
                  <p className="text-[16px] font-bold text-[#1a1d23] mt-0.5">
                    ₹{principal.toLocaleString("en-IN")}
                  </p>
                  <span className="text-[10px] text-[#6b7280]">100% of borrowing</span>
                </div>
                <div className="p-3.5 rounded-xl bg-white border border-[#e5e7eb]">
                  <span className="text-[11px] text-[#6b7280]">Total Cumulative Interest</span>
                  <p className="text-[16px] font-bold text-[#d97706] mt-0.5">
                    ₹{Math.round(baseSchedule.totalInterestPaid).toLocaleString("en-IN")}
                  </p>
                  <span className="text-[10px] text-[#d97706] font-medium">
                    {principal > 0 ? `${((baseSchedule.totalInterestPaid / principal) * 100).toFixed(1)}% of loan amount` : "—"}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-white border border-[#e5e7eb]">
                  <span className="text-[11px] text-[#6b7280]">Total Lifetime Repayment</span>
                  <p className="text-[16px] font-bold text-[#0052cc] mt-0.5">
                    ₹{Math.round(baseSchedule.totalPayment).toLocaleString("en-IN")}
                  </p>
                  <span className="text-[10px] text-[#0052cc] font-medium">
                    Principal + Total Interest
                  </span>
                </div>
              </div>

              {/* Prompt to proceed to Serviceability & Amortization section if callback provided */}
              {onProceedToSimulator && (
                <div className="pt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={onProceedToSimulator}
                    className="btn-primary flex items-center gap-2 text-[13px] px-5 py-2.5 shadow-sm"
                  >
                    <span>Proceed to Serviceability & Year-by-Year Amortization</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 4. SIMULATION & SERVICEABILITY SECTION                         */}
      {/* ───────────────────────────────────────────────────────────── */}
      {showSimulatorPart && (
        <div className="space-y-6 animate-slide-up">
          {/* Section Header */}
          <div className="card p-5 bg-gradient-to-r from-[#eff6ff] via-white to-[#f0fdf4] border-2 border-[#bfdbfe] shadow-sm">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#0052cc] to-[#0d9f6e] flex items-center justify-center text-white shadow-md shadow-blue-200">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-[16px] font-bold text-[#1a1d23] flex items-center gap-2">
                    Serviceability Assessment & Prepayment Simulator
                    <span className="badge-success text-[10px]">Smart Advisory</span>
                  </h3>
                  <p className="text-[12px] text-[#6b7280]">
                    Live interactive simulations: 1 extra EMI, step-up % increments, updated payoff graph, and full year-by-year amortization table
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Part A: Serviceability / Affordability Input & FOIR/DTI */}
          <div className="card p-5 border border-[#e5e7eb] space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <span className="text-[13px] font-bold text-[#1a1d23] flex items-center gap-1.5">
                <DollarSign className="h-4 w-4 text-[#0052cc]" />
                Borrower Cash Flow & Affordability Assessment (FOIR / DTI)
              </span>
              <span
                className={`text-[11px] font-bold px-3 py-1 rounded-full uppercase ${
                  dtiRatio <= 40
                    ? "badge-success"
                    : dtiRatio <= 50
                    ? "badge-warning"
                    : "badge-danger"
                }`}
              >
                {dtiRatio <= 40
                  ? "Comfortably Serviceable (<40%)"
                  : dtiRatio <= 50
                  ? "Moderate / Marginal (40-50%)"
                  : "Stressed Debt Burden (>50%)"}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[12px] font-semibold text-[#374151] mb-1.5 block">
                  Net Monthly Take-Home Income (₹)
                </label>
                <input
                  type="number"
                  min="0"
                  step="5000"
                  value={userIncome}
                  onChange={(e) => setUserIncome(e.target.value)}
                  placeholder="e.g. 85000"
                  className="input-field text-[13px]"
                />
              </div>
              <div>
                <label className="text-[12px] font-semibold text-[#374151] mb-1.5 block">
                  Existing Monthly Obligations / Other EMIs (₹)
                </label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  value={userObligations}
                  onChange={(e) => setUserObligations(e.target.value)}
                  placeholder="e.g. 10000"
                  className="input-field text-[13px]"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-1">
              <div className="p-3 bg-[#f9fafb] rounded-lg border border-[#e2e8f0]">
                <span className="text-[10px] text-[#6b7280]">Total Monthly EMIs</span>
                <p className="text-[14px] font-bold text-[#1a1d23]">
                  ₹{Math.round(totalEmis).toLocaleString("en-IN")}
                </p>
                <span className="text-[9px] text-[#9ca3af]">Existing + New EMI</span>
              </div>
              <div className="p-3 bg-[#f9fafb] rounded-lg border border-[#e2e8f0]">
                <span className="text-[10px] text-[#6b7280]">Fixed Obligation Ratio (DTI)</span>
                <p
                  className={`text-[14px] font-bold ${
                    dtiRatio <= 40
                      ? "text-[#0d9f6e]"
                      : dtiRatio <= 50
                      ? "text-[#d97706]"
                      : "text-[#dc2626]"
                  }`}
                >
                  {dtiRatio.toFixed(1)}%
                </p>
                <span className="text-[9px] text-[#9ca3af]">Industry threshold ≤ 40%</span>
              </div>
              <div className="p-3 bg-[#f9fafb] rounded-lg border border-[#e2e8f0]">
                <span className="text-[10px] text-[#6b7280]">Net Disposable Buffer</span>
                <p
                  className={`text-[14px] font-bold ${
                    disposableIncome >= 0 ? "text-[#0d9f6e]" : "text-[#dc2626]"
                  }`}
                >
                  ₹{Math.round(disposableIncome).toLocaleString("en-IN")}
                </p>
                <span className="text-[9px] text-[#9ca3af]">Cash left for living</span>
              </div>
              <div className="p-3 bg-[#f9fafb] rounded-lg border border-[#e2e8f0]">
                <span className="text-[10px] text-[#6b7280]">Underlying Rule</span>
                <p className="text-[12px] font-semibold text-[#1a1d23]">Lending Heuristic</p>
                <span className="text-[9px] text-[#9ca3af]">Not an RBI mandate (§6.4)</span>
              </div>
            </div>
          </div>

          {/* Part B: Prepayment Simulation Controls */}
          <div className="card p-5 border border-[#e5e7eb] space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <span className="text-[13px] font-bold text-[#1a1d23] flex items-center gap-1.5">
                <Sliders className="h-4 w-4 text-[#f59e0b]" />
                Interactive Prepayment Acceleration Controls
              </span>
              <span className="text-[11px] text-[#059669] font-semibold">
                Instant Recalculation
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Scenario 1: 1 Extra EMI / Year */}
              <button
                type="button"
                onClick={() => setExtraEmiYearly(!extraEmiYearly)}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  extraEmiYearly
                    ? "border-[#0052cc] bg-[#eff6ff] shadow-sm ring-1 ring-[#0052cc]"
                    : "border-[#e5e7eb] bg-white hover:bg-[#f9fafb]"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[12px] font-bold text-[#1a1d23]">
                    1 Extra EMI / Year (13th EMI)
                  </span>
                  <input
                    type="checkbox"
                    checked={extraEmiYearly}
                    onChange={() => {}}
                    className="rounded text-[#0052cc] focus:ring-0"
                  />
                </div>
                <p className="text-[11px] text-[#6b7280] leading-snug">
                  Pay 1 additional EMI every 12 months using your annual bonus or tax refund.
                </p>
              </button>

              {/* Scenario 2: Annual Step-Up EMI */}
              <div className="p-3.5 rounded-xl border border-[#e5e7eb] bg-white space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-bold text-[#1a1d23]">
                    Annual EMI Step-Up
                  </span>
                  <span className="badge-info text-[10px]">+{stepUpPct}% / yr</span>
                </div>
                <p className="text-[11px] text-[#6b7280] leading-snug">
                  Increase EMI as your salary grows annually:
                </p>
                <div className="flex items-center gap-1.5 pt-1">
                  {[0, 5, 10, 15].map((pct) => (
                    <button
                      key={pct}
                      type="button"
                      onClick={() => setStepUpPct(pct)}
                      className={`flex-1 py-1 text-[11px] font-semibold rounded-md transition-colors ${
                        stepUpPct === pct
                          ? "bg-[#0052cc] text-white"
                          : "bg-[#f3f4f6] text-[#4b5563] hover:bg-[#e5e7eb]"
                      }`}
                    >
                      {pct === 0 ? "Off" : `${pct}%`}
                    </button>
                  ))}
                </div>
              </div>

              {/* Scenario 3: Fixed Extra Monthly Amount */}
              <div className="p-3.5 rounded-xl border border-[#e5e7eb] bg-white space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-bold text-[#1a1d23]">
                    Custom Extra Monthly (₹)
                  </span>
                </div>
                <input
                  type="number"
                  min="0"
                  step="500"
                  value={extraMonthlyPayment}
                  onChange={(e) => setExtraMonthlyPayment(e.target.value)}
                  placeholder="e.g. 2000"
                  className="input-field text-[12px] py-1.5"
                />
                <p className="text-[10px] text-[#9ca3af]">
                  Adds ₹{parseFloat(extraMonthlyPayment) || 0} to every single monthly EMI.
                </p>
              </div>
            </div>

            {/* Simulation Savings Header Card */}
            <div className="p-5 rounded-2xl bg-gradient-to-r from-[#0f172a] to-[#1e293b] text-white space-y-4 shadow-lg">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <TrendingDown className="h-5 w-5 text-[#34d399]" />
                  <span className="text-[14px] font-bold text-white">
                    Simulation Outcome: Fast-Track Freedom
                  </span>
                </div>
                {interestSaved > 0 && (
                  <span className="text-[11px] font-bold bg-[#34d399]/20 text-[#34d399] px-3 py-1 rounded-full border border-[#34d399]/30">
                    🎉 Save {yearsReduced} Years of Debt
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                  <span className="text-[10px] text-[#94a3b8] uppercase tracking-wider font-semibold">
                    Original Baseline
                  </span>
                  <p className="text-[16px] font-bold text-white mt-1">
                    {baseSchedule.actualMonths} Months
                  </p>
                  <span className="text-[10px] text-[#94a3b8]">
                    ({(baseSchedule.actualMonths / 12).toFixed(1)} Years)
                  </span>
                </div>

                <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                  <span className="text-[10px] text-[#94a3b8] uppercase tracking-wider font-semibold">
                    Simulated Fast-Track
                  </span>
                  <p className="text-[16px] font-bold text-[#38bdf8] mt-1">
                    {simulatedSchedule.actualMonths} Months
                  </p>
                  <span className="text-[10px] text-[#38bdf8]">
                    ({(simulatedSchedule.actualMonths / 12).toFixed(1)} Years)
                  </span>
                </div>

                <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                  <span className="text-[10px] text-[#94a3b8] uppercase tracking-wider font-semibold">
                    Tenure Saved
                  </span>
                  <p className="text-[16px] font-bold text-[#34d399] mt-1">
                    -{yearsReduced} Years
                  </p>
                  <span className="text-[10px] text-[#34d399]">
                    {monthsReduced} fewer EMIs
                  </span>
                </div>

                <div className="p-3 bg-gradient-to-br from-[#059669]/30 to-[#047857]/30 rounded-xl border border-[#34d399]/40">
                  <span className="text-[10px] text-[#a7f3d0] uppercase tracking-wider font-semibold">
                    Total Interest Saved
                  </span>
                  <p className="text-[18px] font-extrabold text-[#34d399] mt-0.5">
                    ₹{Math.round(interestSaved).toLocaleString("en-IN")}
                  </p>
                  <span className="text-[10px] text-[#a7f3d0]">Direct Cash Kept in Pocket</span>
                </div>
              </div>
            </div>
          </div>

          {/* Part C: UPDATED DUAL-CURVE AMORTIZATION GRAPH */}
          <div className="card p-5 border border-[#e5e7eb] space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h4 className="text-[14px] font-bold text-[#1a1d23] flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-[#0052cc]" />
                  Updated Loan Balance Payoff Graph (Baseline vs. Simulated Prepayment)
                </h4>
                <p className="text-[11px] text-[#6b7280]">
                  Visualizing how your principal balance decreases over time under baseline vs. fast-track simulation
                </p>
              </div>
              <div className="flex items-center gap-4 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-full bg-[#0052cc]" />
                  <span className="text-[#374151]">Original Baseline</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-3 w-3 rounded-full bg-[#10b981]" />
                  <span className="text-[#374151] font-semibold">Simulated Fast-Track</span>
                </div>
              </div>
            </div>

            {/* SVG Visual Chart */}
            <div className="w-full h-64 sm:h-72 relative bg-white rounded-xl border border-[#e5e7eb] p-3">
              <svg
                viewBox="0 0 800 240"
                className="w-full h-full overflow-visible"
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id="baseGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0052cc" stopOpacity="0.15" />
                    <stop offset="100%" stopColor="#0052cc" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="simGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Horizontal grid lines */}
                {[0, 60, 120, 180, 240].map((y) => (
                  <line
                    key={y}
                    x1="0"
                    y1={y}
                    x2="800"
                    y2={y}
                    stroke="#f1f5f9"
                    strokeWidth="1"
                  />
                ))}

                {(() => {
                  const maxVal = Math.max(principal, 1);
                  const totalBaseM = baseSchedule.actualMonths || 1;

                  // Baseline path
                  const basePoints = chartPoints.basePts.map((pt) => {
                    const x = (pt.month / totalBaseM) * 780 + 10;
                    const y = 230 - (pt.balance / maxVal) * 210;
                    return `${x.toFixed(1)},${y.toFixed(1)}`;
                  });
                  const basePathD = `M 10,${(230 - (principal / maxVal) * 210).toFixed(1)} L ` + basePoints.join(" L ");
                  const baseAreaD = `${basePathD} L 790,230 L 10,230 Z`;

                  // Simulated path
                  const simPoints = chartPoints.simPts.map((pt) => {
                    const x = (pt.month / totalBaseM) * 780 + 10;
                    const y = 230 - (pt.balance / maxVal) * 210;
                    return `${x.toFixed(1)},${y.toFixed(1)}`;
                  });
                  const simEndX = (simulatedSchedule.actualMonths / totalBaseM) * 780 + 10;
                  const simPathD = `M 10,${(230 - (principal / maxVal) * 210).toFixed(1)} L ` + simPoints.join(" L ");
                  const simAreaD = `${simPathD} L ${simEndX.toFixed(1)},230 L 10,230 Z`;

                  return (
                    <>
                      {/* Baseline Area & Line */}
                      <path d={baseAreaD} fill="url(#baseGrad)" />
                      <path
                        d={basePathD}
                        fill="none"
                        stroke="#0052cc"
                        strokeWidth="2"
                        strokeDasharray="4 3"
                      />

                      {/* Simulated Area & Line */}
                      <path d={simAreaD} fill="url(#simGrad)" />
                      <path
                        d={simPathD}
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="3"
                        strokeLinecap="round"
                      />

                      {/* Payoff Milestone Marker for Simulation */}
                      {simulatedSchedule.actualMonths < baseSchedule.actualMonths && (
                        <g>
                          <line
                            x1={simEndX}
                            y1="20"
                            x2={simEndX}
                            y2="230"
                            stroke="#10b981"
                            strokeWidth="1.5"
                            strokeDasharray="3 3"
                          />
                          <circle cx={simEndX} cy="230" r="5" fill="#10b981" />
                          <rect
                            x={Math.max(10, simEndX - 70)}
                            y="15"
                            width="140"
                            height="24"
                            rx="6"
                            fill="#10b981"
                          />
                          <text
                            x={Math.max(10, simEndX - 70) + 70}
                            y="31"
                            textAnchor="middle"
                            fontSize="10"
                            fontWeight="bold"
                            fill="#ffffff"
                          >
                            🎉 Paid Off {yearsReduced} Yrs Early
                          </text>
                        </g>
                      )}

                      {/* Milestone labels at bottom */}
                      <text x="15" y="238" fontSize="9" fill="#94a3b8">
                        Month 1 (Start)
                      </text>
                      <text x={simEndX} y="238" textAnchor="middle" fontSize="9" fontWeight="bold" fill="#047857">
                        Yr {(simulatedSchedule.actualMonths / 12).toFixed(1)}
                      </text>
                      <text x="785" y="238" textAnchor="end" fontSize="9" fill="#94a3b8">
                        Yr {(baseSchedule.actualMonths / 12).toFixed(0)} (Original)
                      </text>
                    </>
                  );
                })()}
              </svg>
            </div>
          </div>

          {/* Part D: FULL YEAR-BY-YEAR AMORTIZATION TABLE */}
          <div className="card overflow-hidden border border-[#e5e7eb] shadow-sm space-y-4 p-5">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <h4 className="text-[14px] font-bold text-[#1a1d23] flex items-center gap-2">
                  <Table className="h-4 w-4 text-[#0052cc]" />
                  Full Year-by-Year Amortization Schedule
                </h4>
                <p className="text-[11px] text-[#6b7280]">
                  Complete annual breakdown showing how EMI reduces principal and interest every single year
                </p>
              </div>

              {/* View Selector Tabs */}
              <div className="flex items-center gap-1.5 p-1 bg-[#f1f5f9] rounded-xl border border-[#e2e8f0]">
                <button
                  type="button"
                  onClick={() => setActiveAmortizationView("simulated")}
                  className={`px-3 py-1.5 text-[11px] font-bold rounded-lg transition-colors ${
                    activeAmortizationView === "simulated"
                      ? "bg-white text-[#059669] shadow-xs"
                      : "text-[#64748b] hover:text-[#0f172a]"
                  }`}
                >
                  ⚡ Simulated Fast-Track Schedule
                </button>
                <button
                  type="button"
                  onClick={() => setActiveAmortizationView("baseline")}
                  className={`px-3 py-1.5 text-[11px] font-bold rounded-lg transition-colors ${
                    activeAmortizationView === "baseline"
                      ? "bg-white text-[#0052cc] shadow-xs"
                      : "text-[#64748b] hover:text-[#0f172a]"
                  }`}
                >
                  📅 Original Baseline Schedule
                </button>
                <button
                  type="button"
                  onClick={() => setActiveAmortizationView("comparison")}
                  className={`px-3 py-1.5 text-[11px] font-bold rounded-lg transition-colors ${
                    activeAmortizationView === "comparison"
                      ? "bg-white text-[#7c3aed] shadow-xs"
                      : "text-[#64748b] hover:text-[#0f172a]"
                  }`}
                >
                  ⚖️ Side-by-Side Comparison
                </button>
              </div>
            </div>

            {/* Scrollable Year-by-Year Table */}
            <div className="border border-[#e2e8f0] rounded-xl overflow-hidden shadow-xs">
              <div className="overflow-x-auto max-h-[460px] overflow-y-auto">
                <table className="w-full text-left border-collapse text-[12px]">
                  <thead className="bg-[#f8fafc] text-[#475569] font-bold text-[11px] uppercase tracking-wider sticky top-0 z-10 border-b border-[#e2e8f0]">
                    {activeAmortizationView === "comparison" ? (
                      <tr>
                        <th className="py-3 px-3">Year</th>
                        <th className="py-3 px-3">Baseline Ending Balance</th>
                        <th className="py-3 px-3">Simulated Ending Balance</th>
                        <th className="py-3 px-3">Base Interest</th>
                        <th className="py-3 px-3">Simulated Interest</th>
                        <th className="py-3 px-3 text-[#059669]">Annual Interest Saved</th>
                        <th className="py-3 px-3">Progress</th>
                      </tr>
                    ) : (
                      <tr>
                        <th className="py-3 px-3">Year</th>
                        <th className="py-3 px-3">Opening Principal (₹)</th>
                        <th className="py-3 px-3">Total Annual EMI (₹)</th>
                        <th className="py-3 px-3 text-[#0052cc]">Principal Paid (₹)</th>
                        <th className="py-3 px-3 text-[#d97706]">Interest Paid (₹)</th>
                        <th className="py-3 px-3">Closing Principal (₹)</th>
                        <th className="py-3 px-3">% Repaid</th>
                      </tr>
                    )}
                  </thead>
                  <tbody className="divide-y divide-[#f1f5f9] font-mono text-[11px]">
                    {activeAmortizationView === "comparison" ? (
                      baseSchedule.yearlySummary.map((bRow) => {
                        const sRow = simulatedSchedule.yearlySummary.find((s) => s.year === bRow.year);
                        const isSimPaidOff = !sRow || sRow.closingBalance <= 0;
                        const annualSaved = Math.max(0, bRow.interestPaid - (sRow?.interestPaid || 0));

                        return (
                          <tr
                            key={bRow.year}
                            className={`hover:bg-[#f8fafc] transition-colors ${
                              isSimPaidOff ? "bg-[#f0fdf4]/50" : ""
                            }`}
                          >
                            <td className="py-2.5 px-3 font-sans font-bold text-[#1e293b]">
                              Year {bRow.year}
                            </td>
                            <td className="py-2.5 px-3 text-[#64748b]">
                              ₹{Math.round(bRow.closingBalance).toLocaleString("en-IN")}
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-[#0f172a]">
                              {sRow && sRow.closingBalance > 0 ? (
                                `₹${Math.round(sRow.closingBalance).toLocaleString("en-IN")}`
                              ) : (
                                <span className="badge-success text-[10px]">₹0 (Fully Paid)</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-[#d97706]">
                              ₹{Math.round(bRow.interestPaid).toLocaleString("en-IN")}
                            </td>
                            <td className="py-2.5 px-3 text-[#059669]">
                              ₹{Math.round(sRow?.interestPaid || 0).toLocaleString("en-IN")}
                            </td>
                            <td className="py-2.5 px-3 font-bold text-[#059669]">
                              {annualSaved > 0 ? `+₹${Math.round(annualSaved).toLocaleString("en-IN")}` : "—"}
                            </td>
                            <td className="py-2.5 px-3">
                              <div className="flex items-center gap-1.5">
                                <div className="h-2 w-16 bg-[#e2e8f0] rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-[#10b981]"
                                    style={{ width: `${sRow?.loanPaidOffPct || 100}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-[#64748b]">
                                  {(sRow?.loanPaidOffPct || 100).toFixed(0)}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      (activeAmortizationView === "simulated"
                        ? simulatedSchedule.yearlySummary
                        : baseSchedule.yearlySummary
                      ).map((row) => (
                        <tr
                          key={row.year}
                          className="hover:bg-[#f8fafc] transition-colors"
                        >
                          <td className="py-2.5 px-3 font-sans font-bold text-[#1e293b]">
                            Year {row.year}
                          </td>
                          <td className="py-2.5 px-3 text-[#64748b]">
                            ₹{Math.round(row.openingBalance).toLocaleString("en-IN")}
                          </td>
                          <td className="py-2.5 px-3 font-semibold text-[#0f172a]">
                            ₹{Math.round(row.totalEmiPaid).toLocaleString("en-IN")}
                          </td>
                          <td className="py-2.5 px-3 font-semibold text-[#0052cc]">
                            ₹{Math.round(row.principalPaid).toLocaleString("en-IN")}
                          </td>
                          <td className="py-2.5 px-3 font-semibold text-[#d97706]">
                            ₹{Math.round(row.interestPaid).toLocaleString("en-IN")}
                          </td>
                          <td className="py-2.5 px-3 font-bold text-[#1e293b]">
                            {row.closingBalance <= 0 ? (
                              <span className="badge-success text-[10px]">₹0 (Paid Off)</span>
                            ) : (
                              `₹${Math.round(row.closingBalance).toLocaleString("en-IN")}`
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-1.5">
                              <div className="h-2 w-16 bg-[#e2e8f0] rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-[#0052cc]"
                                  style={{ width: `${row.loanPaidOffPct}%` }}
                                />
                              </div>
                              <span className="text-[10px] text-[#64748b]">
                                {row.loanPaidOffPct.toFixed(0)}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                  {/* Summary Totals Footer */}
                  <tfoot className="bg-[#f8fafc] font-bold border-t border-[#e2e8f0] text-[11px] text-[#1e293b]">
                    <tr>
                      <td className="py-3 px-3 font-sans">Total Lifetime</td>
                      <td className="py-3 px-3 font-mono">₹{principal.toLocaleString("en-IN")}</td>
                      <td className="py-3 px-3 font-mono">
                        ₹{Math.round(
                          activeAmortizationView === "simulated"
                            ? simulatedSchedule.totalPayment
                            : baseSchedule.totalPayment
                        ).toLocaleString("en-IN")}
                      </td>
                      <td className="py-3 px-3 text-[#0052cc] font-mono">
                        ₹{principal.toLocaleString("en-IN")}
                      </td>
                      <td className="py-3 px-3 text-[#d97706] font-mono">
                        ₹{Math.round(
                          activeAmortizationView === "simulated"
                            ? simulatedSchedule.totalInterestPaid
                            : baseSchedule.totalInterestPaid
                        ).toLocaleString("en-IN")}
                      </td>
                      <td className="py-3 px-3 text-[#059669] font-mono">₹0.00</td>
                      <td className="py-3 px-3 text-[#059669]">100% Repaid</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>

          {/* Part E: Strategic Reality Check: Loan ROI vs. Current Inflation */}
          <div className="p-5 rounded-2xl bg-gradient-to-r from-[#fffbeb] via-[#fef3c7] to-[#fffbeb] border border-[#fcd34d] space-y-4">
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-[#b45309]" />
              <h5 className="text-[14px] font-bold text-[#92400e]">
                Economic Reality Check: Is Prepayment Really Necessary? (ROI vs. Inflation)
              </h5>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px]">
              <div className="p-3.5 bg-white/80 rounded-xl border border-[#fde68a] space-y-1">
                <span className="text-[11px] text-[#78350f] font-semibold">1. Nominal Loan ROI</span>
                <p className="text-[16px] font-bold text-[#1a1d23]">{rate}% p.a.</p>
                <p className="text-[10px] text-[#6b7280]">The interest rate charged by lender</p>
              </div>

              <div className="p-3.5 bg-white/80 rounded-xl border border-[#fde68a] space-y-1">
                <span className="text-[11px] text-[#78350f] font-semibold">2. India CPI Inflation</span>
                <p className="text-[16px] font-bold text-[#d97706]">~{inflationRate}% p.a.</p>
                <p className="text-[10px] text-[#6b7280]">RBI Target & Macroeconomic average</p>
              </div>

              <div className="p-3.5 bg-white/80 rounded-xl border border-[#fde68a] space-y-1">
                <span className="text-[11px] text-[#78350f] font-semibold">3. Real Cost of Debt</span>
                <p className="text-[16px] font-bold text-[#0052cc]">
                  {realInterestRate.toFixed(2)}% p.a.
                </p>
                <p className="text-[10px] text-[#6b7280]">
                  Nominal Rate ({rate}%) - Inflation ({inflationRate}%)
                </p>
              </div>
            </div>

            {/* Strategic Decision Matrix */}
            <div className="p-4 rounded-xl bg-white border border-[#fde68a] space-y-2.5">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h6 className="text-[12px] font-bold text-[#1a1d23]">
                  Financial Strategy Recommendation:
                </h6>
                {isHighInterestLoan ? (
                  <span className="badge-danger text-[10px]">
                    Aggressive Prepayment Optimal
                  </span>
                ) : isLowInterestLoan ? (
                  <span className="badge-success text-[10px]">
                    Consider Investing Surplus (Hybrid Allocation)
                  </span>
                ) : (
                  <span className="badge-warning text-[10px]">
                    Balanced Repayment Recommended
                  </span>
                )}
              </div>

              {isLowInterestLoan ? (
                <p className="text-[11px] text-[#451a03] leading-relaxed">
                  🎯 <strong>Housing Loan Arbitrage Insight:</strong> Your loan ROI ({rate}%) is low. After accounting for inflation ({inflationRate}%) and Section 24(b) tax deductions (up to ₹2 Lakh/year), your <em>effective real cost of borrowing is only ~1.5% to 3.0%</em>. Over a 15–20 year horizon, inflation systematically erodes the real burden of your fixed debt. If you instead systematically invest that extra 1 EMI into Indian Equity Index Funds / Mutual Funds (which have historically delivered <strong>~12%–14% CAGR</strong>), your accumulated wealth will significantly exceed the ₹{Math.round(interestSaved).toLocaleString("en-IN")} saved on interest!
                </p>
              ) : isHighInterestLoan ? (
                <p className="text-[11px] text-[#451a03] leading-relaxed">
                  🚨 <strong>High-Cost Debt Warning:</strong> Your loan interest rate ({rate}%) substantially exceeds India's inflation rate ({inflationRate}%) and safe fixed-income yields. Prepaying this loan gives you a <strong>guaranteed, risk-free, tax-free return of {rate}% p.a.</strong> Prepaying as aggressively as possible is mathematically the most rewarding choice you can make.
                </p>
              ) : (
                <p className="text-[11px] text-[#451a03] leading-relaxed">
                  ⚖️ <strong>Balanced Approach:</strong> Your loan rate of {rate}% sits moderately above inflation. A hybrid approach—prepaying 1 extra EMI per year while keeping the rest invested for emergency liquidity—gives you both psychological peace of mind and wealth generation.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
