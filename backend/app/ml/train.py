"""
ML Training Pipeline (B3, B8, B12).

Orchestrates training and evaluation of:
1. NaiveForecaster (baseline)
2. CashFlowForecaster (LightGBM on lag and calendar features)
3. LogisticRiskBaseline (baseline)
4. CalibratedRiskModel (Calibrated LightGBM classifier)

Evaluates on held-out customer test period (months 10-12) and persists models
and metadata JSON to `backend/trained_models/`.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from app.data.loader import get_customer_ids, load_data
from app.features.builder import build_features, build_training_features
from app.ml.forecaster import CashFlowForecaster, NaiveForecaster
from app.ml.model_store import ModelStore
from app.ml.risk_model import CalibratedRiskModel, LogisticRiskBaseline


def train_all(
    seed: int = 42,
    sample_customers: int = 2000,
    test_sample_size: int = 500,
    model_dir: Path | str | None = None,
) -> dict[str, Any]:
    """
    Train cash flow forecasters and risk models, evaluate on held-out test data,
    and save artifacts to disk.

    Parameters
    ----------
    seed : int
        Fixed random seed for determinism.
    sample_customers : int
        Number of training customers to sample (default 2000).
    test_sample_size : int
        Number of held-out test customers for evaluation (default 500).
    model_dir : Path | str | None
        Directory where models are saved. Defaults to backend/trained_models.

    Returns
    -------
    dict[str, Any]
        Dictionary of training run metrics, model paths, and evaluation summaries.
    """
    print("=" * 60)
    print("CreditPath ML Training Pipeline")
    print(f"Seed: {seed} | Train customers: {sample_customers} | Test customers: {test_sample_size}")
    print("=" * 60)

    # 1. Build training features (up to 2025-09-30 cutoff)
    print("\n[1/5] Building training features up to 2025-09-30...")
    train_df = build_training_features(
        cutoff_date="2025-09-30",
        sample_size=sample_customers,
    )
    print(f"  Training feature matrix: {train_df.shape[0]} rows, {train_df.shape[1]} columns.")

    y_inflow = train_df["weekly_inflow"]
    y_outflow = train_df["weekly_outflow"]
    y_shortfall = train_df["shortfall_next_week"]

    # 2. Fit Forecasters
    print("\n[2/5] Training Cash-Flow Forecasters...")
    naive_forecaster = NaiveForecaster()
    naive_forecaster.fit(train_df, y_inflow, y_outflow)

    forecaster = CashFlowForecaster(
        seed=seed,
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
    )
    forecaster.fit(train_df, y_inflow, y_outflow)
    print("  CashFlowForecaster (LightGBM) trained successfully.")

    # 3. Fit Risk Models
    print("\n[3/5] Training Repayment Risk Models...")
    logistic_baseline = LogisticRiskBaseline(seed=seed)
    logistic_baseline.fit(train_df, y_shortfall)

    calibrated_risk = CalibratedRiskModel(
        seed=seed,
        n_estimators=60,
        max_depth=4,
        learning_rate=0.05,
        cv=3,
    )
    calibrated_risk.fit(train_df, y_shortfall)
    print("  CalibratedRiskModel (LightGBM + Platt Scaling) trained successfully.")

    # 4. Evaluate on held-out test customers over test period (months 10-12)
    print("\n[4/5] Evaluating on held-out customers (2025-10-01 to 2025-12-31)...")
    data = load_data()
    test_cids = get_customer_ids("test")[:test_sample_size]

    test_full_df = build_features(
        data["transactions"],
        data["daily_balances"],
        data["bills"],
        cutoff_date="2025-12-31",
        customer_ids=test_cids,
    )

    # Filter to test period (months 10, 11, 12)
    test_eval = test_full_df[test_full_df["month"] >= 10].copy().reset_index(drop=True)
    print(f"  Test evaluation rows: {len(test_eval)}")

    # Evaluate Forecaster
    lgb_preds = forecaster.predict(test_eval)
    naive_preds = naive_forecaster.predict(test_eval)

    mae_in = float(np.mean(np.abs(test_eval["weekly_inflow"] - lgb_preds["predicted_inflow"])))
    naive_mae_in = float(np.mean(np.abs(test_eval["weekly_inflow"] - naive_preds["predicted_inflow"])))

    sum_in = float(np.sum(test_eval["weekly_inflow"]))
    wape_in = float(np.sum(np.abs(test_eval["weekly_inflow"] - lgb_preds["predicted_inflow"])) / max(1.0, sum_in))
    naive_wape_in = float(np.sum(np.abs(test_eval["weekly_inflow"] - naive_preds["predicted_inflow"])) / max(1.0, sum_in))

    mae_out = float(np.mean(np.abs(test_eval["weekly_outflow"] - lgb_preds["predicted_outflow"])))
    naive_mae_out = float(np.mean(np.abs(test_eval["weekly_outflow"] - naive_preds["predicted_outflow"])))

    sum_out = float(np.sum(test_eval["weekly_outflow"]))
    wape_out = float(np.sum(np.abs(test_eval["weekly_outflow"] - lgb_preds["predicted_outflow"])) / max(1.0, sum_out))
    naive_wape_out = float(np.sum(np.abs(test_eval["weekly_outflow"] - naive_preds["predicted_outflow"])) / max(1.0, sum_out))

    # Evaluate Risk Model (exclude boundary week where future target is cutoff)
    eval_risk_rows = test_eval[test_eval["week"] < test_eval["week"].max()].copy()
    y_test_risk = eval_risk_rows["shortfall_next_week"].to_numpy()

    risk_probas = calibrated_risk.predict_proba(eval_risk_rows)[:, 1]
    baseline_probas = logistic_baseline.predict_proba(eval_risk_rows)[:, 1]

    roc_auc = float(roc_auc_score(y_test_risk, risk_probas))
    brier = float(brier_score_loss(y_test_risk, risk_probas))

    base_roc_auc = float(roc_auc_score(y_test_risk, baseline_probas))
    base_brier = float(brier_score_loss(y_test_risk, baseline_probas))

    # 5. Persist models to trained_models/
    print("\n[5/5] Saving model artifacts to ModelStore...")
    store = ModelStore(model_dir=model_dir)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    forecaster_meta = {
        "name": "forecaster",
        "version": "v1.0.0",
        "data_as_of": "2025-12-31",
        "trained_at": now_iso,
        "seed": seed,
        "sample_customers": sample_customers,
        "features": forecaster.feature_names,
        "metrics": {
            "forecaster_mae_inflow": round(mae_in, 2),
            "forecaster_mae_outflow": round(mae_out, 2),
            "forecaster_wape_inflow": round(wape_in, 4),
            "forecaster_wape_outflow": round(wape_out, 4),
            "naive_mae_inflow": round(naive_mae_in, 2),
            "naive_mae_outflow": round(naive_mae_out, 2),
            "naive_wape_inflow": round(naive_wape_in, 4),
            "naive_wape_outflow": round(naive_wape_out, 4),
        },
    }
    p_forecaster = store.save(forecaster, "forecaster", forecaster_meta)

    risk_meta = {
        "name": "risk_model",
        "version": "v1.0.0",
        "data_as_of": "2025-12-31",
        "trained_at": now_iso,
        "seed": seed,
        "sample_customers": sample_customers,
        "features": calibrated_risk.feature_names,
        "feature_importances": calibrated_risk.get_feature_importances(),
        "metrics": {
            "roc_auc": round(roc_auc, 4),
            "brier_score": round(brier, 4),
            "baseline_roc_auc": round(base_roc_auc, 4),
            "baseline_brier_score": round(base_brier, 4),
        },
    }
    p_risk = store.save(calibrated_risk, "risk_model", risk_meta)

    # Also persist baseline models for benchmark comparisons
    store.save(naive_forecaster, "naive_forecaster", {"name": "naive_forecaster", "version": "v1.0.0"})
    store.save(logistic_baseline, "logistic_risk_baseline", {"name": "logistic_risk_baseline", "version": "v1.0.0"})

    print("\nTraining complete! Artifacts saved:")
    print(f"  Forecaster: {p_forecaster}")
    print(f"  Risk Model: {p_risk}")
    print("\nMetrics Summary:")
    print(f"  Inflow MAE : LightGBM = ৳{mae_in:.2f} vs Naive = ৳{naive_mae_in:.2f}")
    print(f"  Inflow WAPE: LightGBM = {wape_in:.2%} vs Naive = {naive_wape_in:.2%}")
    print(f"  Outflow MAE: LightGBM = ৳{mae_out:.2f} vs Naive = ৳{naive_mae_out:.2f}")
    print(f"  Outflow WAPE: LightGBM = {wape_out:.2%} vs Naive = {naive_wape_out:.2%}")
    print(f"  Risk ROC-AUC: Calibrated LGBM = {roc_auc:.4f} vs Logistic = {base_roc_auc:.4f}")
    print(f"  Risk Brier  : Calibrated LGBM = {brier:.4f} vs Logistic = {base_brier:.4f}")

    return {
        "forecaster_path": str(p_forecaster),
        "risk_model_path": str(p_risk),
        "forecaster_metrics": forecaster_meta["metrics"],
        "risk_metrics": risk_meta["metrics"],
        "feature_importances": risk_meta["feature_importances"],
    }


if __name__ == "__main__":
    train_all()
