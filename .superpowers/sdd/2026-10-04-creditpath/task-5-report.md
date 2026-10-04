# Task 5 Report: Core Engines — Ready, Affordability, Timing, Recourse (B4-B7, B9)

**Execution Status**: DONE

## Overview
Implemented the complete suite of CreditPath core calculation and decision engines along with the plain-language Reason Catalog. All outputs are computed dynamically at request time from real models and rules without any hardcoded outputs, mock stubs, or prohibited jargon.

## Components Implemented

1. **Reason Catalog (`backend/app/engines/reasons.py`, B9)**
   - Fixed mapping of reason codes to plain-language explanation templates.
   - Strictly enforces no-jargon policy (no "EMI", "surplus", "PD", "credit score", or "default").
   - Uses plain concepts: "monthly payment", "spare money", "regular income", "cushion".
   - Codes implemented: `HISTORY_ENOUGH`, `HISTORY_INSUFFICIENT`, `INCOME_REGULAR`, `INCOME_IRREGULAR`, `CUSHION_OK`, `CUSHION_LOW`, `BILLS_ON_TIME`, `BILLS_LATE`, `AFFORDABILITY_COMFORTABLE`, `AFFORDABILITY_TIGHT`, `AFFORDABILITY_TOO_MUCH`, `AFFORDABILITY_NO_SPARE`, `STRESS_COMFORTABLE`, `STRESS_TIGHT`, `STRESS_TOO_MUCH`, `TIMING_SAFE`, `TIMING_TIGHT`, `RECOURSE_HISTORY`, `RECOURSE_REGULARITY`, `RECOURSE_CUSHION`, `RECOURSE_BILLS`.

2. **Ready Rule Engine (`backend/app/engines/ready.py`, B4)**
   - Evaluates the three core policy checks:
     - Check 1 (History): `months_active >= config.min_history_months`
     - Check 2 (Steady money in): income in `>= config.regularity_n` of last `config.regularity_m` weeks
     - Check 3 (Cushion & bills): balance stays above `config.min_balance_threshold` on `>= config.min_balance_pct_days` proportion of days, and bills paid on time in `>= config.bill_on_time_pct` proportion of cases (or balance only if no bills).
   - Binary readiness state: "Ready" iff all three checks pass; else "Not yet".
   - Ranks missing checks dynamically using the calibrated risk model feature importances.

3. **Affordability Engine (`backend/app/engines/affordability.py`, B5)**
   - Surplus forecast: computed from Forecaster 4-week projections (`monthly_inflow - monthly_outflow`).
   - Safe range: policy-capped share of monthly surplus (`surplus * config.affordability_cap`), with half-cap lower bound.
   - Stressed capacity: re-evaluates surplus under a 30% drop in income (`config.stress_pct`).
   - Amortized loan check: evaluates annuity monthly payment at `config.illustrative_rate` against surplus share.
   - Verdicts: "Comfortable" (<=40%), "Tight" (40-60%), "Too much" (>60%).
   - Nearest-comfortable search: searches loan parameters (tenor extension up to 36 months, amount reductions down to 1000৳) to find the closest comfortable configuration.
   - Honors admin kill-switches (`kill_safe_range`, `kill_loan_check`).

4. **Repayment Timing Engine (`backend/app/engines/timing.py`, B6)**
   - Uses multi-week Forecaster projections (default 8 weeks).
   - Classifies each week as `safe` (balance >= floor and inflow covers outflow adequately) or `tight`.
   - Identifies safe repayment windows aligned with historical income days (e.g. Days 5-10).
   - Generates list of tight weeks to avoid.

5. **Recourse Engine (`backend/app/engines/recourse.py`, B7)**
   - Generates actionable, behavioral steps for customers in "Not yet" status.
   - Constrained search strictly over controllable behaviors: utility bills on time, minimum balance cushion, regular cash-ins, account maturity.
   - Rescores simulated changes against policy rules to ensure each recommended action genuinely flips a missing check.
   - Ranked by risk impact and provides realistic time-to-readiness in weeks.

6. **Engines Package Init (`backend/app/engines/__init__.py`)**
   - Cleanly exports all engines, results, and utility functions.

## Test Verification
- Test file: `backend/tests/test_engines.py`
  - `test_reason_catalog_no_jargon`: PASS
  - `test_ready_rule_evaluation`: PASS
  - `test_affordability_safe_range`: PASS
  - `test_loan_check_verdicts`: PASS
  - `test_timing_calendar`: PASS
  - `test_recourse_actionable_only`: PASS
- Full backend suite: 32 passed in 27.71s (including data generator, features, ML, and engines).
