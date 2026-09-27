# Module 1b: Serviceability / Affordability Engine

## 1. Overview
Module 1b deterministically computes a borrower's debt-to-income (DTI) ratio and net disposable income buffer to evaluate whether a specific loan offer is affordable.

## 2. Invariants & Rules
- **RULES.md §1.7**: `serviceability.py` is a single function, imported everywhere its number is needed. There are no duplicate copies anywhere in the repository.
- **RULES.md §1.8**: The DTI/serviceability arithmetic is deterministic ground truth and does not need re-verification. However, the natural language explanation describing the verdict is a `Claim` (`source_module="serviceability"`) that must pass through Module 3 before being presented to the user.
- **RULES.md §4.4**: Unit-tested against hand-computed ground truth examples in `data/test_cases/hand_computed_dti.json`.
- **RULES.md §6.4**: The thresholds below are an **industry lending heuristic, NOT an RBI mandate**. This distinction must be prominently stated in all code comments, API outputs, and user-facing reports.

## 3. Mathematical Formulas & Classification Bands
$$\text{total\_obligations} = \text{existing\_emis} + \text{new\_emi}$$
$$\text{DTI} = \frac{\text{total\_obligations}}{\text{monthly\_income}}$$
$$\text{disposable\_income} = \text{monthly\_income} - \text{monthly\_expenses} - \text{total\_obligations}$$

### Heuristic Verdicts:
1. `serviceable`: $\text{DTI} \le 40\%$ AND $\text{disposable\_income} > 0$
2. `marginal`: $40\% < \text{DTI} \le 50\%$ AND $\text{disposable\_income} \ge 0$
3. `not-serviceable`: $\text{DTI} > 50\%$ OR $\text{disposable\_income} < 0$

## 4. Running Unit Tests
```powershell
pytest modules/m1b_serviceability/tests -v
```
