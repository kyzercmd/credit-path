# Task 4 Report: ML Models — Forecaster & Risk Model (B3, B8, B12)

## Status
DONE

## Commits
5b629ad

## Test Summary
6 ML tests passed (26 total backend tests passing): verification of CashFlowForecaster training, non-negative predictions, multi-week iterative roll-forward forecasting with wallet balance update, LightGBM MAE/WAPE beating NaiveForecaster baseline on held-out seasonal test period, CalibratedRiskModel probability calibration strictly in [0, 1] with feature importances extraction, LogisticRiskBaseline comparison, deterministic reproducibility across identical seeds, joblib persistence and metadata deserialization via ModelStore, and strict absence of protected attributes and latent traits.

## Concerns
None. Training across 2,000 customers (80,000+ weekly feature records) and evaluating against 500 held-out test customers runs in under 10 seconds. Inflow MAE improves from ৳4,399.71 (naive) to ৳3,296.59 (LightGBM), with 0.8770 ROC-AUC for shortfall prediction.
