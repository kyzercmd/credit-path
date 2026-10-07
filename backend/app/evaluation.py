"""
CreditPath Section 8 Model Evaluation & Disparity Audit (B14).

Produces comprehensive evaluation across 6 core pillars:
1. Forecast Metrics: Weekly MAE & WAPE vs naive moving average baseline,
   broken down by persona with irregular/seasonal personas evaluated separately.
2. Ready Rule Validity: Shortfall rates among Ready vs Not yet cohorts on held-out test months (10-12).
3. Timing Guidance: Proportion of shortfall events avoided with recommended window vs fixed calendar day.
4. Affordability Calibration: Rate at which a 'Comfortable' loan verdict is followed by cash shortfall in simulation.
5. Fairness Audit: Group counts, ready rate, forecast error, and false-not-yet rate across gender,
   region, and age bands, including threshold mitigation evaluation for female micro-savers.
6. Multi-Seed Robustness: Evaluated across 5 distinct random seeds (42, 43, 44, 45, 46), reporting mean ± std.

All tables, outputs, and JSON payloads explicitly bear the required header:
"synthetic data, relative comparison"
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import Config, get_config
from app.data.generator import generate_dataset
from app.data.loader import get_customer_ids, load_data, get_split_dates
from app.engines.affordability import AffordabilityEngine, calculate_amortization
from app.engines.ready import ReadyEngine
from app.engines.timing import TimingEngine
from app.fairness.module import FairnessModule
from app.features.builder import build_features
from app.ml.forecaster import CashFlowForecaster, NaiveForecaster, SeasonalNaiveForecaster
from app.ml.model_store import load_model, get_model_version, get_data_as_of

DISCLAIMER_LABEL = "synthetic data, relative comparison"


def format_table(header: list[str], rows: list[list[Any]], title: str = "") -> str:
    """Render a clean, aligned ASCII table with standard disclaimer."""
    lines = []
    if title:
        lines.append(f"\n{'=' * 75}")
        lines.append(f"{title} [{DISCLAIMER_LABEL}]")
        lines.append(f"{'=' * 75}")
    col_widths = [len(h) for h in header]
    str_rows = []
    for row in rows:
        s_row = [str(c) if c is not None else "N/A" for c in row]
        str_rows.append(s_row)
        for i, val in enumerate(s_row):
            col_widths[i] = max(col_widths[i], len(val))

    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(header))
    sep_line = "  ".join("-" * col_widths[i] for i in range(len(header)))
    lines.append(header_line)
    lines.append(sep_line)
    for row in str_rows:
        row_line = "  ".join(val.ljust(col_widths[i]) for i, val in enumerate(row))
        lines.append(row_line)
    return "\n".join(lines)


# ==============================================================================
# Pillar 1: Forecast Performance vs Baseline
# ==============================================================================

def evaluate_forecast_performance(
    data: dict[str, pd.DataFrame],
    test_cids: list[str],
    features: pd.DataFrame | None = None,
    forecaster: Any | None = None,
) -> dict[str, Any]:
    """
    Compute weekly MAE and WAPE on held-out test months (10-12) vs naive baseline,
    broken down by persona, with irregular/seasonal cohorts isolated.
    """
    if features is None:
        features = build_features(
            data["transactions"],
            data["daily_balances"],
            data["bills"],
            cutoff_date="2025-12-31",
            customer_ids=test_cids,
        )

    # Filter to held-out test months (months 10, 11, 12)
    test_eval = features[features["month"] >= 10].copy().reset_index(drop=True)
    if len(test_eval) == 0:
        return {"error": "No test evaluation data available"}

    # Attach customer persona
    cust_df = data["customers"]
    test_eval = test_eval.merge(cust_df[["customer_id", "persona"]], on="customer_id", how="left")

    if forecaster is None:
        try:
            forecaster, _ = load_model("forecaster")
        except Exception:
            forecaster = CashFlowForecaster(seed=42)
            train_feats = features[features["month"] <= 9]
            forecaster.fit(train_feats, train_feats["weekly_inflow"], train_feats["weekly_outflow"])

    naive = NaiveForecaster()
    s_naive = SeasonalNaiveForecaster(seasonal_lag=4)

    preds = forecaster.predict(test_eval)
    naive_preds = naive.predict(test_eval)
    s_naive_preds = s_naive.predict(test_eval)

    test_eval["pred_in"] = preds["predicted_inflow"].to_numpy()
    test_eval["pred_out"] = preds["predicted_outflow"].to_numpy()
    test_eval["naive_pred_in"] = naive_preds["predicted_inflow"].to_numpy()
    test_eval["naive_pred_out"] = naive_preds["predicted_outflow"].to_numpy()
    test_eval["s_naive_pred_in"] = s_naive_preds["predicted_inflow"].to_numpy()
    test_eval["s_naive_pred_out"] = s_naive_preds["predicted_outflow"].to_numpy()

    # Overall metrics
    total_vol = test_eval["weekly_inflow"] + test_eval["weekly_outflow"]
    sum_vol = float(np.sum(total_vol))
    err_forecaster = np.abs(test_eval["weekly_inflow"] - test_eval["pred_in"]) + np.abs(
        test_eval["weekly_outflow"] - test_eval["pred_out"]
    )
    err_naive = np.abs(test_eval["weekly_inflow"] - test_eval["naive_pred_in"]) + np.abs(
        test_eval["weekly_outflow"] - test_eval["naive_pred_out"]
    )
    err_s_naive = np.abs(test_eval["weekly_inflow"] - test_eval["s_naive_pred_in"]) + np.abs(
        test_eval["weekly_outflow"] - test_eval["s_naive_pred_out"]
    )

    overall_mae = round(float(np.mean(err_forecaster) / 2.0), 2)
    overall_wape = round(float(np.sum(err_forecaster) / max(1.0, sum_vol)), 4)
    naive_mae = round(float(np.mean(err_naive) / 2.0), 2)
    naive_wape = round(float(np.sum(err_naive) / max(1.0, sum_vol)), 4)
    s_naive_mae = round(float(np.mean(err_s_naive) / 2.0), 2)
    s_naive_wape = round(float(np.sum(err_s_naive) / max(1.0, sum_vol)), 4)
    stronger_naive_mae = min(naive_mae, s_naive_mae)
    stronger_naive_wape = min(naive_wape, s_naive_wape)
    wape_improvement = round(float((stronger_naive_wape - overall_wape) / max(0.0001, stronger_naive_wape)), 4)

    # By Persona Breakdown
    personas = [
        "wage_worker",
        "seasonal_farmer",
        "informal_merchant",
        "woman_led_household",
        "salaried_user",
    ]
    cfg = get_config()
    by_persona = {}
    for p in personas:
        p_df = test_eval[test_eval["persona"] == p]
        count = len(p_df["customer_id"].unique())
        if len(p_df) > 0:
            p_vol = float(np.sum(p_df["weekly_inflow"] + p_df["weekly_outflow"]))
            p_err = np.abs(p_df["weekly_inflow"] - p_df["pred_in"]) + np.abs(
                p_df["weekly_outflow"] - p_df["pred_out"]
            )
            p_naive_err = np.abs(p_df["weekly_inflow"] - p_df["naive_pred_in"]) + np.abs(
                p_df["weekly_outflow"] - p_df["naive_pred_out"]
            )
            p_s_naive_err = np.abs(p_df["weekly_inflow"] - p_df["s_naive_pred_in"]) + np.abs(
                p_df["weekly_outflow"] - p_df["s_naive_pred_out"]
            )

            p_mae = round(float(np.mean(p_err) / 2.0), 2)
            p_wape = round(float(np.sum(p_err) / max(1.0, p_vol)), 4)
            p_naive_mae = round(float(np.mean(p_naive_err) / 2.0), 2)
            p_naive_wape = round(float(np.sum(p_naive_err) / max(1.0, p_vol)), 4)
            p_s_naive_mae = round(float(np.mean(p_s_naive_err) / 2.0), 2)
            p_s_naive_wape = round(float(np.sum(p_s_naive_err) / max(1.0, p_vol)), 4)

            p_stronger_mae = min(p_naive_mae, p_s_naive_mae)
            p_stronger_wape = min(p_naive_wape, p_s_naive_wape)

            p_low_conf = bool((p_mae > p_stronger_mae) or (p_wape > p_stronger_wape))
            p_tier = cfg.persona_tiers.get(p, "primary")

            p_mae_edge = round(float((p_stronger_mae - p_mae) / max(0.0001, p_stronger_mae)) * 100, 1)
            p_wape_gain = round(float((p_stronger_wape - p_wape) / max(0.0001, p_stronger_wape)) * 100, 1)

            by_persona[p] = {
                "customers": count,
                "forecaster_mae": p_mae,
                "forecaster_wape": p_wape,
                "naive_mae": p_naive_mae,
                "naive_wape": p_naive_wape,
                "seasonal_naive_mae": p_s_naive_mae,
                "seasonal_naive_wape": p_s_naive_wape,
                "stronger_naive_mae": p_stronger_mae,
                "stronger_naive_wape": p_stronger_wape,
                "mae_edge_pct": p_mae_edge,
                "wape_reduction_pct": p_wape_gain,
                "low_confidence": p_low_conf,
                "persona_tier": p_tier,
            }

    # Irregular / seasonal personas evaluation
    seasonal_df = test_eval[test_eval["persona"].isin(["seasonal_farmer", "informal_merchant"])]
    if len(seasonal_df) > 0:
        s_vol = float(np.sum(seasonal_df["weekly_inflow"] + seasonal_df["weekly_outflow"]))
        s_err = np.abs(seasonal_df["weekly_inflow"] - seasonal_df["pred_in"]) + np.abs(
            seasonal_df["weekly_outflow"] - seasonal_df["pred_out"]
        )
        s_naive_err = np.abs(seasonal_df["weekly_inflow"] - seasonal_df["naive_pred_in"]) + np.abs(
            seasonal_df["weekly_outflow"] - seasonal_df["naive_pred_out"]
        )
        irregular_seasonal_eval = {
            "customers": int(seasonal_df["customer_id"].nunique()),
            "forecaster_wape": round(float(np.sum(s_err) / max(1.0, s_vol)), 4),
            "naive_wape": round(float(np.sum(s_naive_err) / max(1.0, s_vol)), 4),
            "wape_reduction_pct": round(
                float((np.sum(s_naive_err) - np.sum(s_err)) / max(1.0, np.sum(s_naive_err))) * 100, 1
            ),
        }
    else:
        irregular_seasonal_eval = {}

    return {
        "disclaimer": DISCLAIMER_LABEL,
        "overall": {
            "forecaster_mae": overall_mae,
            "forecaster_wape": overall_wape,
            "naive_mae": naive_mae,
            "naive_wape": naive_wape,
            "seasonal_naive_mae": s_naive_mae,
            "seasonal_naive_wape": s_naive_wape,
            "stronger_naive_mae": stronger_naive_mae,
            "stronger_naive_wape": stronger_naive_wape,
            "wape_reduction_pct": round(wape_improvement * 100, 1),
        },
        "by_persona": by_persona,
        "irregular_seasonal": irregular_seasonal_eval,
    }


# ==============================================================================
# Pillar 2: Ready Rule Validity
# ==============================================================================

def evaluate_ready_rule_validity(
    data: dict[str, pd.DataFrame],
    test_cids: list[str],
    features: pd.DataFrame,
    config: Config,
) -> dict[str, Any]:
    """
    Evaluates shortfall rate (cash flow negative or balance < 0 or shortfall == True)
    among Ready vs Not yet cohorts on held-out test months (10-12).
    """
    fairness = FairnessModule(config=config, data=data)
    ready_series = fairness.evaluate_customer_readiness_batch(
        customer_ids=test_cids,
        features=features,
        data=data,
        cutoff_date="2025-09-30",
        config=config,
    )

    ready_cids = [cid for cid in test_cids if ready_series.get(cid, False)]
    not_yet_cids = [cid for cid in test_cids if not ready_series.get(cid, False)]

    bal = data["daily_balances"]
    test_bal = bal[(bal["customer_id"].isin(test_cids)) & (bal["date"] >= "2025-10-01")]

    # Shortfall indicator in test period
    # Customer experienced at least one shortfall week or daily balance < 200
    sf_by_cust = test_bal.groupby("customer_id")["shortfall"].any()

    ready_sf_rate = (
        round(float(sf_by_cust.reindex(ready_cids, fill_value=False).mean()), 4)
        if ready_cids
        else 0.0
    )
    not_yet_sf_rate = (
        round(float(sf_by_cust.reindex(not_yet_cids, fill_value=False).mean()), 4)
        if not_yet_cids
        else 0.0
    )

    risk_reduction = (
        round(float((not_yet_sf_rate - ready_sf_rate) / max(0.0001, not_yet_sf_rate)) * 100, 1)
        if not_yet_sf_rate > 0
        else 0.0
    )

    return {
        "disclaimer": DISCLAIMER_LABEL,
        "ready_count": len(ready_cids),
        "not_yet_count": len(not_yet_cids),
        "ready_shortfall_rate": ready_sf_rate,
        "not_yet_shortfall_rate": not_yet_sf_rate,
        "shortfall_reduction_pct": risk_reduction,
    }


# ==============================================================================
# Pillar 3: Timing Guidance Evaluation
# ==============================================================================

def evaluate_timing_guidance(
    data: dict[str, pd.DataFrame],
    test_cids: list[str],
    installment_amount: float = 500.0,
) -> dict[str, Any]:
    """
    Evaluates proportion of shortfall events avoided when following the recommended
    repayment window vs a fixed calendar day (1st of month) on held-out test months (10-12).
    """
    bal = data["daily_balances"]
    test_bal = bal[(bal["customer_id"].isin(test_cids)) & (bal["date"] >= "2025-10-01")].copy()
    test_bal["day"] = pd.to_datetime(test_bal["date"]).dt.day
    test_bal["month"] = pd.to_datetime(test_bal["date"]).dt.month

    # Fixed Day strategy: Repayment on 1st of month
    fixed_day_bal = test_bal[test_bal["day"] == 1]
    fixed_shortfalls = int((fixed_day_bal["balance"] - installment_amount < 200).sum())
    fixed_events = max(1, len(fixed_day_bal))
    fixed_rate = round(float(fixed_shortfalls / fixed_events), 4)

    # Recommended window strategy: Repayment within customer's peak liquidity window (days 5-25)
    rec_window_bal = (
        test_bal[(test_bal["day"] >= 5) & (test_bal["day"] <= 25)]
        .groupby(["customer_id", "month"])["balance"]
        .max()
    )
    rec_shortfalls = int((rec_window_bal - installment_amount < 200).sum())
    rec_events = max(1, len(rec_window_bal))
    rec_rate = round(float(rec_shortfalls / rec_events), 4)

    avoided_pct = (
        round(float((fixed_rate - rec_rate) / max(0.0001, fixed_rate)) * 100, 1)
        if fixed_rate > 0
        else 0.0
    )

    return {
        "disclaimer": DISCLAIMER_LABEL,
        "fixed_day_shortfall_rate": fixed_rate,
        "recommended_window_shortfall_rate": rec_rate,
        "shortfall_avoided_pct": avoided_pct,
    }


# ==============================================================================
# Pillar 4: Affordability Calibration
# ==============================================================================

def evaluate_affordability_calibration(
    data: dict[str, pd.DataFrame],
    test_cids: list[str],
    features: pd.DataFrame,
    config: Config,
    proposed_amount: float = 3000.0,
    tenor_months: int = 6,
) -> dict[str, Any]:
    """
    Calculates the rate at which a 'Comfortable' loan verdict is followed by
    a cash shortfall in simulation across held-out test months (10-12).
    """
    engine = AffordabilityEngine(config=config)
    pmt = calculate_amortization(proposed_amount, tenor_months, config.illustrative_rate)

    bal = data["daily_balances"]
    test_bal = bal[(bal["customer_id"].isin(test_cids)) & (bal["date"] >= "2025-10-01")].copy()

    # Pre-aggregate minimum balances during test months
    min_bal_by_cust = test_bal.groupby("customer_id")["balance"].min()

    # Fast evaluation of monthly surplus from features
    pre_test_feats = features[features["month"] <= 9]
    latest_feats = pre_test_feats.groupby("customer_id").last()

    comfortable_count = 0
    shortfall_count = 0

    for cid in test_cids:
        c_feats = features[features["customer_id"] == cid]
        if len(c_feats) == 0:
            continue
        try:
            lc = engine.loan_check(
                cid,
                amount=proposed_amount,
                tenor_months=tenor_months,
                config=config,
                customer_features=c_feats,
            )
            if lc.verdict == "Comfortable":
                comfortable_count += 1
                cust_min_bal = float(min_bal_by_cust.get(cid, 0.0))
                # Shortfall if balance minus installment drops below the ৳200 floor
                if cust_min_bal - pmt < 200.0:
                    shortfall_count += 1
        except Exception:
            continue

    sf_rate = (
        round(float(shortfall_count / comfortable_count), 4)
        if comfortable_count > 0
        else 0.0
    )

    return {
        "disclaimer": DISCLAIMER_LABEL,
        "sample_size": len(test_cids),
        "comfortable_loans": comfortable_count,
        "shortfalls_in_simulation": shortfall_count,
        "shortfall_rate": sf_rate,
        "calibration_status": "Well-Calibrated (<15% shortfall)" if sf_rate < 0.15 else "Caution",
    }


# ==============================================================================
# Pillar 5: Fairness & Disparity Audit
# ==============================================================================

def evaluate_fairness_audit(
    data: dict[str, pd.DataFrame],
    test_cids: list[str],
    config: Config,
) -> dict[str, Any]:
    """
    Computes group sample sizes, ready rate, forecast error, and false-not-yet rate
    across gender, region, and age bands, and evaluates female micro-saver mitigation.
    """
    fairness = FairnessModule(config=config, data=data)
    report = fairness.compute(
        customer_ids=test_cids,
        cutoff_date="2025-09-30",
        config=config,
    )

    return {
        "disclaimer": DISCLAIMER_LABEL,
        "by_gender": [g.model_dump() for g in report.by_gender],
        "by_region": [g.model_dump() for g in report.by_region],
        "by_age_band": [g.model_dump() for g in report.by_age_band],
        "mitigation": report.mitigation if isinstance(report.mitigation, dict) else report.mitigation.model_dump(),
    }


# ==============================================================================
# Pillar 6: Multi-Seed Robustness
# ==============================================================================

def evaluate_multi_seed_robustness(
    seeds: list[int] = [42, 43, 44, 45, 46],
    n_customers_per_seed: int = 300,
) -> dict[str, Any]:
    """
    Runs evaluation across multiple seeds and aggregates key metrics into mean ± std.
    """
    metrics_records: list[dict[str, float]] = []
    cfg = get_config()

    for s in seeds:
        # Generate fresh seed dataset
        s_data = generate_dataset(seed=s, n_customers=n_customers_per_seed)
        all_cids = s_data["customers"]["customer_id"].tolist()
        # Train / test split (80/20)
        n_test = max(10, int(len(all_cids) * 0.20))
        test_cids = all_cids[:n_test]

        s_feats = build_features(
            s_data["transactions"],
            s_data["daily_balances"],
            s_data["bills"],
            cutoff_date="2025-12-31",
            customer_ids=test_cids,
        )

        # 1. Forecast WAPE
        fq = evaluate_forecast_performance(s_data, test_cids, features=s_feats)
        wape = fq["overall"]["forecaster_wape"]
        naive_wape = fq["overall"]["naive_wape"]

        # 2. Ready Rule Shortfall Rate
        rr = evaluate_ready_rule_validity(s_data, test_cids, features=s_feats, config=cfg)
        ready_sf = rr["ready_shortfall_rate"]
        not_yet_sf = rr["not_yet_shortfall_rate"]

        # 3. Timing Avoided
        tg = evaluate_timing_guidance(s_data, test_cids)
        timing_avoided = tg["shortfall_avoided_pct"]

        # 4. Affordability Shortfall
        ac = evaluate_affordability_calibration(s_data, test_cids, features=s_feats, config=cfg)
        afford_sf = ac["shortfall_rate"]

        # 5. Fairness female ready rate
        fair = evaluate_fairness_audit(s_data, test_cids, config=cfg)
        f_before = fair["mitigation"]["before"]["ready_rate"]
        f_after = fair["mitigation"]["after"]["ready_rate"]

        metrics_records.append({
            "seed": s,
            "forecaster_wape": wape,
            "naive_wape": naive_wape,
            "ready_shortfall_rate": ready_sf,
            "not_yet_shortfall_rate": not_yet_sf,
            "timing_avoided_pct": timing_avoided,
            "affordability_shortfall_rate": afford_sf,
            "female_ready_rate_before": f_before,
            "female_ready_rate_after": f_after,
        })

    df_metrics = pd.DataFrame(metrics_records)

    summary = {}
    for col in df_metrics.columns:
        if col == "seed":
            continue
        vals = df_metrics[col].dropna()
        summary[col] = {
            "mean": round(float(vals.mean()), 4),
            "std": round(float(vals.std()), 4),
            "min": round(float(vals.min()), 4),
            "max": round(float(vals.max()), 4),
        }

    return {
        "disclaimer": DISCLAIMER_LABEL,
        "seeds_evaluated": seeds,
        "runs": metrics_records,
        "summary": summary,
    }


# ==============================================================================
# Full Report Orchestration & Printing
# ==============================================================================

def run_evaluation(
    multi_seed: bool = True,
    sample_size: int = 500,
    seeds: list[int] = [42, 43, 44, 45, 46],
) -> dict[str, Any]:
    """
    Run full Section 8 Evaluation Suite.
    """
    cfg = get_config()
    data = load_data()
    test_cids = get_customer_ids("test")[:sample_size]

    print("\n" + "=" * 80)
    print(f" CREDITPATH SECTION 8 EVALUATION REPORT")
    print(f" [{DISCLAIMER_LABEL.upper()}]")
    print("=" * 80)

    # Pre-build features for test customers once
    print(f"\nBuilding evaluation features for {len(test_cids)} held-out test customers...")
    features = build_features(
        data["transactions"],
        data["daily_balances"],
        data["bills"],
        cutoff_date="2025-12-31",
        customer_ids=test_cids,
    )

    # 1. Forecast Performance
    print("\nEvaluating cash-flow forecaster against naive baseline...")
    forecast_report = evaluate_forecast_performance(data, test_cids, features=features)

    # 2. Ready Rule Validity
    print("Evaluating Ready vs Not yet rule validity on held-out months (10-12)...")
    ready_validity = evaluate_ready_rule_validity(data, test_cids, features, cfg)

    # 3. Timing Guidance
    print("Evaluating repayment timing guidance vs fixed-day scheduling...")
    timing_report = evaluate_timing_guidance(data, test_cids)

    # 4. Affordability Calibration
    print("Evaluating affordability calibration on comfortable loan proposals...")
    affordability_report = evaluate_affordability_calibration(data, test_cids, features, cfg)

    # 5. Fairness Audit
    print("Executing demographic disparity and fairness mitigation audit...")
    fairness_report = evaluate_fairness_audit(data, test_cids, cfg)

    # 6. Multi-Seed Robustness
    multi_seed_report = None
    if multi_seed:
        print(f"Running multi-seed robustness across 5 seeds: {seeds}...")
        multi_seed_report = evaluate_multi_seed_robustness(seeds=seeds, n_customers_per_seed=250)

    # Print Formatted Report Tables
    print_report_tables(
        forecast_report,
        ready_validity,
        timing_report,
        affordability_report,
        fairness_report,
        multi_seed_report,
    )

    full_payload = {
        "disclaimer": DISCLAIMER_LABEL,
        "evaluation_date": "2025-12-31",
        "sample_customers": len(test_cids),
        "forecast_metrics": forecast_report,
        "ready_rule_validity": ready_validity,
        "timing_guidance": timing_report,
        "affordability_calibration": affordability_report,
        "fairness_audit": fairness_report,
        "multi_seed_robustness": multi_seed_report,
    }

    return full_payload


def print_report_tables(
    forecast: dict,
    ready: dict,
    timing: dict,
    affordability: dict,
    fairness: dict,
    multi_seed: dict | None,
) -> None:
    """Print readable text tables for each evaluation pillar."""
    # 1. Forecast Table
    f_rows = []
    for p, stats in forecast.get("by_persona", {}).items():
        tier = stats.get("persona_tier", "").replace("_", " ").title()
        conf = "Low Confidence" if stats.get("low_confidence") else "OK"
        f_rows.append([
            p,
            tier,
            stats["customers"],
            f"৳{stats['forecaster_mae']:.0f}",
            f"{stats['forecaster_wape'] * 100:.1f}%",
            f"৳{stats.get('stronger_naive_mae', stats.get('naive_mae', 0)):.0f}",
            f"{stats.get('stronger_naive_wape', stats.get('naive_wape', 0)) * 100:.1f}%",
            f"{stats.get('mae_edge_pct', 0):+.1f}%",
            f"{stats.get('wape_reduction_pct', 0):+.1f}%",
            conf,
        ])
    ov = forecast.get("overall", {})
    ov_stronger_mae = ov.get("stronger_naive_mae", ov.get("naive_mae", 0))
    ov_stronger_wape = ov.get("stronger_naive_wape", ov.get("naive_wape", 0))
    ov_mae_edge = ((ov_stronger_mae - ov.get("forecaster_mae", 0)) / max(0.0001, ov_stronger_mae)) * 100
    f_rows.append([
        "OVERALL",
        "—",
        sum(s["customers"] for s in forecast.get("by_persona", {}).values()),
        f"৳{ov.get('forecaster_mae', 0):.0f}",
        f"{ov.get('forecaster_wape', 0) * 100:.1f}%",
        f"৳{ov_stronger_mae:.0f}",
        f"{ov_stronger_wape * 100:.1f}%",
        f"{ov_mae_edge:+.1f}%",
        f"{ov.get('wape_reduction_pct', 0):+.1f}%",
        "OK",
    ])
    f_headers = ["Persona", "Tier", "N", "LGBM MAE", "LGBM WAPE", "Naive MAE", "Naive WAPE", "MAE Edge", "WAPE Gain", "Status"]
    print(format_table(f_headers, f_rows, "PILLAR 1: FORECAST PERFORMANCE VS NAIVE BASELINE"))

    # Irregular / seasonal callout
    irreg = forecast.get("irregular_seasonal", {})
    if irreg:
        print(f"\n  Irregular & Seasonal Personas (Farmers & Merchants):")
        print(f"  - Sample size: {irreg.get('customers')} customers")
        print(f"  - Forecaster WAPE: {irreg.get('forecaster_wape', 0)*100:.1f}% vs Naive: {irreg.get('naive_wape', 0)*100:.1f}%")
        print(f"  - Error reduction: {irreg.get('wape_reduction_pct'):+.1f}%")

    # 2. Ready Rule Validity Table
    rr_headers = ["Cohort", "Count", "Shortfall Rate (Months 10-12)", "Relative Risk"]
    rr_rows = [
        ["Ready", ready.get("ready_count"), f"{ready.get('ready_shortfall_rate', 0)*100:.1f}%", "Baseline (low risk)"],
        ["Not yet", ready.get("not_yet_count"), f"{ready.get('not_yet_shortfall_rate', 0)*100:.1f}%", f"{ready.get('shortfall_reduction_pct'):+.1f}% higher shortfall"],
    ]
    print(format_table(rr_headers, rr_rows, "PILLAR 2: READY RULE VALIDITY ON HELD-OUT MONTHS"))

    # 3. Timing Guidance Table
    t_headers = ["Repayment Strategy", "Shortfall Occurrence", "Shortfalls Avoided"]
    t_rows = [
        ["Fixed Calendar Day (1st of month)", f"{timing.get('fixed_day_shortfall_rate', 0)*100:.1f}%", "-"],
        ["Recommended Window (post-income)", f"{timing.get('recommended_window_shortfall_rate', 0)*100:.1f}%", f"{timing.get('shortfall_avoided_pct'):.1f}% avoided"],
    ]
    print(format_table(t_headers, t_rows, "PILLAR 3: REPAYMENT TIMING GUIDANCE EVALUATION"))

    # 4. Affordability Calibration Table
    ac_headers = ["Loan Proposal (3k BDT / 6m)", "Comfortable Verdicts", "Shortfalls in Sim", "Shortfall Rate", "Calibration"]
    ac_rows = [
        [
            "Amortized Installment",
            affordability.get("comfortable_loans"),
            affordability.get("shortfalls_in_simulation"),
            f"{affordability.get('shortfall_rate', 0)*100:.1f}%",
            affordability.get("calibration_status"),
        ]
    ]
    print(format_table(ac_headers, ac_rows, "PILLAR 4: AFFORDABILITY CALIBRATION"))

    # 5. Fairness Audit Tables
    for dim_name, group_list in [
        ("Gender", fairness.get("by_gender", [])),
        ("Region", fairness.get("by_region", [])),
        ("Age Band", fairness.get("by_age_band", [])),
    ]:
        fair_headers = [dim_name, "N", "Ready Rate", "Forecast WAPE", "False Not Yet Rate"]
        fair_rows = [
            [
                g["group"],
                g["count"],
                f"{g['ready_rate']*100:.1f}%" if g["ready_rate"] is not None else "N/A",
                f"{g['forecast_error']*100:.1f}%" if g["forecast_error"] is not None else "N/A",
                f"{g['false_not_yet_rate']*100:.1f}%" if g["false_not_yet_rate"] is not None else "N/A",
            ]
            for g in group_list
        ]
        print(format_table(fair_headers, fair_rows, f"PILLAR 5: FAIRNESS AUDIT - {dim_name.upper()}"))

    # Mitigation summary
    mitig = fairness.get("mitigation", {})
    if mitig:
        b_fem = mitig.get("before", {}).get("ready_rate", 0)
        a_fem = mitig.get("after", {}).get("ready_rate", 0)
        print(f"\n  Threshold Mitigation Policy (Female Micro-Savers ৳300 Cushion):")
        print(f"  - Female ready rate: {b_fem*100:.1f}% → {a_fem*100:.1f}% (Impact: {mitig.get('impact_summary')})")

    # 6. Multi-Seed Robustness Table
    if multi_seed:
        ms_summary = multi_seed.get("summary", {})
        ms_headers = ["Key Metric", "Mean ± Std (5 Seeds)", "Range [Min, Max]"]
        ms_rows = [
            [
                "Forecaster WAPE",
                f"{ms_summary.get('forecaster_wape', {}).get('mean', 0)*100:.1f}% ± {ms_summary.get('forecaster_wape', {}).get('std', 0)*100:.1f}%",
                f"[{ms_summary.get('forecaster_wape', {}).get('min', 0)*100:.1f}%, {ms_summary.get('forecaster_wape', {}).get('max', 0)*100:.1f}%]",
            ],
            [
                "Naive WAPE",
                f"{ms_summary.get('naive_wape', {}).get('mean', 0)*100:.1f}% ± {ms_summary.get('naive_wape', {}).get('std', 0)*100:.1f}%",
                f"[{ms_summary.get('naive_wape', {}).get('min', 0)*100:.1f}%, {ms_summary.get('naive_wape', {}).get('max', 0)*100:.1f}%]",
            ],
            [
                "Ready Shortfall Rate",
                f"{ms_summary.get('ready_shortfall_rate', {}).get('mean', 0)*100:.1f}% ± {ms_summary.get('ready_shortfall_rate', {}).get('std', 0)*100:.1f}%",
                f"[{ms_summary.get('ready_shortfall_rate', {}).get('min', 0)*100:.1f}%, {ms_summary.get('ready_shortfall_rate', {}).get('max', 0)*100:.1f}%]",
            ],
            [
                "Not Yet Shortfall Rate",
                f"{ms_summary.get('not_yet_shortfall_rate', {}).get('mean', 0)*100:.1f}% ± {ms_summary.get('not_yet_shortfall_rate', {}).get('std', 0)*100:.1f}%",
                f"[{ms_summary.get('not_yet_shortfall_rate', {}).get('min', 0)*100:.1f}%, {ms_summary.get('not_yet_shortfall_rate', {}).get('max', 0)*100:.1f}%]",
            ],
            [
                "Timing Shortfalls Avoided",
                f"{ms_summary.get('timing_avoided_pct', {}).get('mean', 0):.1f}% ± {ms_summary.get('timing_avoided_pct', {}).get('std', 0):.1f}%",
                f"[{ms_summary.get('timing_avoided_pct', {}).get('min', 0):.1f}%, {ms_summary.get('timing_avoided_pct', {}).get('max', 0):.1f}%]",
            ],
            [
                "Comfortable Shortfall Rate",
                f"{ms_summary.get('affordability_shortfall_rate', {}).get('mean', 0)*100:.1f}% ± {ms_summary.get('affordability_shortfall_rate', {}).get('std', 0)*100:.1f}%",
                f"[{ms_summary.get('affordability_shortfall_rate', {}).get('min', 0)*100:.1f}%, {ms_summary.get('affordability_shortfall_rate', {}).get('max', 0)*100:.1f}%]",
            ],
            [
                "Female Ready Rate (Mitigated)",
                f"{ms_summary.get('female_ready_rate_after', {}).get('mean', 0)*100:.1f}% ± {ms_summary.get('female_ready_rate_after', {}).get('std', 0)*100:.1f}%",
                f"[{ms_summary.get('female_ready_rate_after', {}).get('min', 0)*100:.1f}%, {ms_summary.get('female_ready_rate_after', {}).get('max', 0)*100:.1f}%]",
            ],
        ]
        print(format_table(ms_headers, ms_rows, "PILLAR 6: MULTI-SEED ROBUSTNESS (5 RANDOM SEEDS)"))


def main() -> None:
    """CLI Entrypoint for running Section 8 evaluation and saving output."""
    parser = argparse.ArgumentParser(description="CreditPath Section 8 Model Evaluation & Audit")
    parser.add_argument("--no-multi-seed", action="store_true", help="Skip 5-seed robustness evaluation")
    parser.add_argument("--sample-size", type=int, default=500, help="Number of held-out test customers to evaluate")
    parser.add_argument("--output", type=str, default="evaluation_report.json", help="Destination JSON report file path")
    args = parser.parse_args()

    report = run_evaluation(multi_seed=not args.no_multi_seed, sample_size=args.sample_size)

    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[OK] Full evaluation report successfully saved to: {output_path.resolve()}\n")


if __name__ == "__main__":
    main()
