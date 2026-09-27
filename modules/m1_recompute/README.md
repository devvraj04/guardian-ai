# Module 1: APR Recompute Engine

## 1. Overview
Module 1 provides the deterministic mathematical foundation for loan interest rate verification. It computes the reducing-balance Equated Monthly Installment (EMI) and solves for the true Effective Annual Percentage Rate (APR) by accounting for all upfront fees, processing charges, and documentation costs.

## 2. Invariants & Rules
- **RULES.md §1.7**: `apr_recompute.py` is a single function, imported everywhere its number is needed — Module 3's numeric check, Module 2's consistency comparisons, and the Serviceability engine. There are no duplicate copies anywhere in the repository.
- **RULES.md §4.4**: Unit-tested against hand-computed ground truth examples in `data/test_cases/hand_computed_apr.json`.
- **Pure Python**: Zero ML, zero stochastic behavior, pure numerical methods.

## 3. Mathematical Specification
1. **Reducing-Balance EMI**:
   $$r = \frac{\text{disclosed\_rate}}{12 \times 100}$$
   $$\text{EMI} = P \times \frac{r(1+r)^N}{(1+r)^N - 1}$$
2. **Effective APR (Cash-flow IRR)**:
   Net disbursed amount $= P - \text{fees}$.
   Solves for monthly rate $r_{\text{irr}}$:
   $$P - \text{fees} = \sum_{t=1}^{N} \frac{\text{EMI}}{(1 + r_{\text{irr}})^t}$$
   $$\text{Effective APR} = r_{\text{irr}} \times 12 \times 100$$

## 4. Running Unit Tests
```powershell
pytest modules/m1_recompute/tests -v
```
