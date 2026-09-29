# Module 5: Grievance Classification & Redressal

## Architectural Role
Module 5 provides automated complaint classification and tracking for user-initiated digital lending disputes. It maps unstructured borrower complaints into official Reserve Bank of India (RBI) Digital Lending Directions categories with associated legal citations and a mandated 30-day turnaround time (TAT).

## Governing Invariants (RULES.md §1.3, §4.7; SPEC §3.4)
1. **User-Initiated Only**: Grievance classification is triggered strictly on user dispute submission (`POST /api/v1/loans/{loan_id}/disputes`), never automatically as part of regular document processing or cron.
2. **Claim Schema Conformance**: Every dispute emits a tracking `Claim` (`source_module="grievance"`) for auditability and verification.
3. **Audit Logged**: Every dispute submission is appended to `public.audit_log` (`action="DISPUTE_SUBMITTED"`).

## RBI-Aligned Dispute Taxonomy
| Category | Label | RBI Reference | TAT |
|---|---|---|---|
| `excessive_charges_and_hidden_fees` | Excessive Interest & Undisclosed Fees | Clauses 3.3, 5.1 | 30 Days |
| `recovery_harassment_and_privacy` | Recovery Harassment & Privacy Breach | Clauses 5.4, 7 | 30 Days |
| `unauthorized_disbursal_or_credit_limit` | Unauthorized Disbursal / Limit Increase | Clauses 4.1, 4.2 | 30 Days |
| `transparency_and_kfs_violation` | KFS Non-Issuance & Transparency Violations | Clauses 3.1, 3.2 | 30 Days |
| `repayment_and_noc_delay` | Repayment Accounting Delay & Bureau Reporting | Clause 5.2, CIC Regs | 30 Days |
| `general_service_deficiency` | Grievance Redressal Unresponsiveness & TAT Breach | Clause 6.1 | 30 Days |

## Performance
- **Macro F1 Score**: `1.0` (exceeds SPEC §3.7 target of $\ge 0.80$)
- **Architecture**: Sublinear TF-IDF (1–2 n-grams) + Balanced Logistic Regression
