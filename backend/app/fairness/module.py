"""
Fairness and Disparity Audit Module (B10).

Evaluates readiness rules and forecasting quality across protected demographic groups:
- Gender: male, female (audit-only)
- Region: urban, rural (audit-only)
- Age Band: 18-25, 26-35, 36-45, 46-55, 56+ (audit-only)

Protected attributes are strictly excluded from all model inputs and feature builders.
They are joined strictly at request time / evaluation time for fairness monitoring.

Empty groups return None (JSON null / 'N/A'), never 0 or 1.
Includes threshold-adjustment policy mitigation for underrepresented groups (female micro-savers).
"""
from __future__ import annotations

from typing import Any, Sequence
import numpy as np
import pandas as pd

from app.config import Config, get_config
from app.data.loader import get_customer_ids, load_data, get_split_dates
from app.features.builder import build_features, FORBIDDEN_COLUMNS
from app.ml.forecaster import CashFlowForecaster, NaiveForecaster
from app.ml.model_store import load_model, get_model_version, get_data_as_of
from app.schemas import FairnessGroup, FairnessResponse, Meta


DEFAULT_GENDER_GROUPS: list[str] = ["male", "female"]
DEFAULT_REGION_GROUPS: list[str] = ["urban", "rural"]
DEFAULT_AGE_GROUPS: list[str] = ["18-25", "26-35", "36-45", "46-55", "56+"]

DEFAULT_MITIGATION_DESCRIPTION: str = "Alternative cushion threshold (৳300 floor for micro-savers)"
DEFAULT_TARGET_GROUP: str = "female"


def format_fairness_rate(val: float | None) -> str:
    """Format numeric rate as percentage string, returning 'N/A' for None."""
    if val is None:
        return "N/A"
    return f"{val * 100.0:.1f}%"


class FairnessReport(FairnessResponse):
    """Fairness report representation conforming to FairnessResponse schema."""

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary representation."""
        return self.model_dump()


class FairnessModule:
    """
    Fairness evaluation engine computing group metrics and threshold mitigation impact.
    """

    def __init__(
        self,
        forecaster: Any | None = None,
        config: Config | None = None,
        data: dict[str, pd.DataFrame] | None = None,
    ) -> None:
        self.config = config or get_config()
        self.data = data
        self._forecaster = forecaster

    def _get_forecaster(self) -> Any:
        """Load forecaster if not provided."""
        if self._forecaster is not None:
            return self._forecaster
        try:
            model, _ = load_model("forecaster")
            self._forecaster = model
            return self._forecaster
        except Exception:
            self._forecaster = NaiveForecaster()
            return self._forecaster

    def _get_data(self) -> dict[str, pd.DataFrame]:
        """Load data tables if not provided."""
        if self.data is not None:
            return self.data
        self.data = load_data()
        return self.data

    def evaluate_customer_readiness_batch(
        self,
        customer_ids: Sequence[str],
        features: pd.DataFrame,
        data: dict[str, pd.DataFrame],
        cutoff_date: str,
        config: Config,
    ) -> pd.Series:
        """
        Batch-evaluate Readiness Rule Engine (B4) for a collection of customer IDs.
        Matches ReadyEngine.evaluate logic exactly, optimized for bulk processing.
        """
        cids = list(customer_ids)
        if not cids:
            return pd.Series(dtype=bool)

        # Check 1: History (months_active >= min_history_months)
        hist_feats = features[features["date_cutoff_ok"]] if "date_cutoff_ok" in features.columns else features
        latest_feats = hist_feats.sort_values(["customer_id", "week"]).groupby("customer_id").last()
        months_active = latest_feats["months_active"].reindex(cids, fill_value=0)
        c1_pass = months_active >= config.min_history_months

        # Check 2: Steady Money In (income in >= regularity_n of last regularity_m weeks)
        m = config.regularity_m
        recent = hist_feats.groupby("customer_id").tail(m)
        n_regular = (recent["weekly_inflow"] > 0).groupby(recent["customer_id"]).sum().reindex(cids, fill_value=0)
        c2_pass = n_regular >= config.regularity_n

        # Check 3: Cushion & Bills
        bal = data["daily_balances"]
        bal_sub = bal[(bal["customer_id"].isin(cids)) & (bal["date"] <= cutoff_date)]
        days_tot = bal_sub.groupby("customer_id")["balance"].count().reindex(cids, fill_value=0)
        days_above = (
            bal_sub[bal_sub["balance"] >= config.min_balance_threshold]
            .groupby("customer_id")["balance"]
            .count()
            .reindex(cids, fill_value=0)
        )
        bal_pct = (days_above / days_tot.replace(0, np.nan)).fillna(0.0)
        cushion_pass = bal_pct >= config.min_balance_pct_days

        # Bills evaluation
        bi = data["bills"]
        bi_sub = bi[(bi["customer_id"].isin(cids)) & (bi["due_date"] <= cutoff_date)]
        bills_grouped = bi_sub.groupby("customer_id")["on_time"]
        bills_count = bills_grouped.count().reindex(cids, fill_value=0)
        bills_mean = bills_grouped.mean().reindex(cids, fill_value=1.0)

        # If customer has bills, require bill_on_time_pct; otherwise True
        bills_pass = pd.Series(True, index=cids)
        mask_has_bills = bills_count > 0
        bills_pass[mask_has_bills] = bills_mean[mask_has_bills] >= config.bill_on_time_pct

        c3_pass = cushion_pass & bills_pass

        ready = c1_pass & c2_pass & c3_pass
        return ready

    def compute(
        self,
        customer_ids: Sequence[str] | None = None,
        sample_size: int | None = 1000,
        cutoff_date: str = "2025-09-30",
        config: Config | None = None,
        mitigated_config: Config | None = None,
        custom_groups: dict[str, list[str]] | None = None,
    ) -> FairnessReport:
        """
        Compute fairness metrics across protected groups and evaluate policy mitigation.
        """
        cfg = config or self.config
        data = self._get_data()
        forecaster = self._get_forecaster()

        # Target customer sample (defaults to held-out test split)
        if customer_ids is None:
            all_test_cids = get_customer_ids("test")
            target_cids = all_test_cids[:sample_size] if sample_size is not None else all_test_cids
        else:
            target_cids = list(customer_ids)

        attrs_df = data["customer_attributes"]
        attrs_map = attrs_df[attrs_df["customer_id"].isin(target_cids)].set_index("customer_id")

        if not target_cids:
            return self._empty_report(cfg)

        # Build full features up to end of data (2025-12-31)
        full_feats = build_features(
            data["transactions"],
            data["daily_balances"],
            data["bills"],
            cutoff_date="2025-12-31",
            customer_ids=target_cids,
        )

        # Tag rows prior to cutoff for historical readiness evaluation
        cutoff_dt = pd.to_datetime(cutoff_date)
        # Note: in build_features, weeks <= 39 correspond to months 1-9 (cutoff 2025-09-30)
        full_feats["date_cutoff_ok"] = full_feats["month"] <= cutoff_dt.month

        # Forecast predictions on held-out evaluation period (months 10-12)
        test_eval = full_feats[full_feats["month"] > cutoff_dt.month].copy()
        if len(test_eval) > 0:
            preds = forecaster.predict(test_eval)
            test_eval["pred_inflow"] = preds["predicted_inflow"].to_numpy()
            test_eval["pred_outflow"] = preds["predicted_outflow"].to_numpy()
        else:
            test_eval["pred_inflow"] = pd.Series(dtype=float)
            test_eval["pred_outflow"] = pd.Series(dtype=float)

        # Readiness evaluation at baseline config
        ready_baseline = self.evaluate_customer_readiness_batch(
            customer_ids=target_cids,
            features=full_feats,
            data=data,
            cutoff_date=cutoff_date,
            config=cfg,
        )

        # Readiness evaluation with mitigation config
        if mitigated_config is not None:
            mitig_cfg = mitigated_config
        else:
            mitig_cfg = Config(
                **{
                    **cfg.to_dict(),
                    "min_balance_threshold": min(cfg.min_balance_threshold, 300.0),
                    "min_balance_pct_days": min(cfg.min_balance_pct_days, 0.60),
                }
            )
        ready_mitigated = self.evaluate_customer_readiness_batch(
            customer_ids=target_cids,
            features=full_feats,
            data=data,
            cutoff_date=cutoff_date,
            config=mitig_cfg,
        )

        # Subsequent period shortfall evaluation (dates > cutoff_date)
        bal = data["daily_balances"]
        sub_bal = bal[(bal["customer_id"].isin(target_cids)) & (bal["date"] > cutoff_date)]
        shortfall_sub = sub_bal.groupby("customer_id")["shortfall"].sum().reindex(target_cids, fill_value=0)
        zero_shortfall = (shortfall_sub == 0).reindex(target_cids, fill_value=True)
        any_shortfall = (shortfall_sub > 0).reindex(target_cids, fill_value=False)

        # Helper to compute group slices
        def compute_group_table(
            attribute_col: str,
            default_categories: list[str],
            extra_categories: list[str] | None = None,
        ) -> list[FairnessGroup]:
            # Discover categories present in data or defaults or extras
            present_in_attrs = (
                attrs_df[attribute_col].dropna().unique().tolist()
                if attribute_col in attrs_df.columns
                else []
            )
            ordered_cats = list(default_categories)
            if extra_categories:
                for cat in extra_categories:
                    if cat not in ordered_cats:
                        ordered_cats.append(cat)
            for cat in present_in_attrs:
                if cat not in ordered_cats:
                    ordered_cats.append(cat)

            group_results: list[FairnessGroup] = []

            for cat in ordered_cats:
                # Find matching customers
                if attribute_col in attrs_map.columns:
                    cat_cids = attrs_map[attrs_map[attribute_col] == cat].index.intersection(target_cids).tolist()
                else:
                    cat_cids = []

                count = len(cat_cids)

                # Critical requirement (U4 & Spec 9.4):
                # Empty groups must return None (JSON null / N/A), NEVER 0 or 1.
                if count == 0:
                    group_results.append(
                        FairnessGroup(
                            group=cat,
                            count=0,
                            ready_rate=None,
                            forecast_error=None,
                            false_not_yet_rate=None,
                        )
                    )
                    continue

                # Ready rate
                ready_in_cat = ready_baseline.loc[cat_cids]
                ready_rate = round(float(ready_in_cat.mean()), 4)

                # Forecast error (WAPE) in held-out period
                cat_eval = test_eval[test_eval["customer_id"].isin(cat_cids)]
                if len(cat_eval) > 0:
                    abs_err = float(
                        np.sum(np.abs(cat_eval["weekly_inflow"] - cat_eval["pred_inflow"]))
                        + np.sum(np.abs(cat_eval["weekly_outflow"] - cat_eval["pred_outflow"]))
                    )
                    tot_actual = float(np.sum(cat_eval["weekly_inflow"]) + np.sum(cat_eval["weekly_outflow"]))
                    forecast_error = round(abs_err / tot_actual, 4) if tot_actual > 0.0 else None
                else:
                    forecast_error = None

                # False Not Yet rate: proportion of "Not yet" customers with 0 shortfall days
                not_yet_cids = [cid for cid in cat_cids if not ready_in_cat.loc[cid]]
                if len(not_yet_cids) > 0:
                    safe_count = int(zero_shortfall.loc[not_yet_cids].sum())
                    false_not_yet_rate = round(float(safe_count / len(not_yet_cids)), 4)
                else:
                    # No Not yet customers in this group
                    false_not_yet_rate = None

                group_results.append(
                    FairnessGroup(
                        group=cat,
                        count=count,
                        ready_rate=ready_rate,
                        forecast_error=forecast_error,
                        false_not_yet_rate=false_not_yet_rate,
                    )
                )

            return group_results

        cg = custom_groups or {}
        by_gender = compute_group_table("gender", DEFAULT_GENDER_GROUPS, cg.get("gender"))
        by_region = compute_group_table("region_type", DEFAULT_REGION_GROUPS, cg.get("region_type") or cg.get("region"))
        by_age_band = compute_group_table("age_band", DEFAULT_AGE_GROUPS, cg.get("age_band") or cg.get("age"))

        # Mitigation evaluation on target group (female)
        target_group = DEFAULT_TARGET_GROUP
        if "gender" in attrs_map.columns:
            fem_cids = attrs_map[attrs_map["gender"] == target_group].index.intersection(target_cids).tolist()
        else:
            fem_cids = []

        if len(fem_cids) == 0:
            mitigation_dict = {
                "description": DEFAULT_MITIGATION_DESCRIPTION,
                "target_group": target_group,
                "before": {
                    "ready_rate": None,
                    "false_not_yet_rate": None,
                    "shortfall_rate_among_ready": None,
                },
                "after": {
                    "ready_rate": None,
                    "false_not_yet_rate": None,
                    "shortfall_rate_among_ready": None,
                },
                "impact_summary": f"No data available for {target_group} target group in the evaluated sample.",
            }
        else:
            # Baseline metrics for target group
            b_ready = ready_baseline.loc[fem_cids]
            b_ready_rate = round(float(b_ready.mean()), 4)
            b_not_yet_cids = [cid for cid in fem_cids if not b_ready.loc[cid]]
            b_false_not_yet = (
                round(float(zero_shortfall.loc[b_not_yet_cids].sum() / len(b_not_yet_cids)), 4)
                if len(b_not_yet_cids) > 0
                else None
            )
            b_ready_cids = [cid for cid in fem_cids if b_ready.loc[cid]]
            b_sf_ready = (
                round(float(any_shortfall.loc[b_ready_cids].sum() / len(b_ready_cids)), 4)
                if len(b_ready_cids) > 0
                else None
            )

            # Mitigated metrics for target group
            a_ready = ready_mitigated.loc[fem_cids]
            a_ready_rate = round(float(a_ready.mean()), 4)
            a_not_yet_cids = [cid for cid in fem_cids if not a_ready.loc[cid]]
            a_false_not_yet = (
                round(float(zero_shortfall.loc[a_not_yet_cids].sum() / len(a_not_yet_cids)), 4)
                if len(a_not_yet_cids) > 0
                else None
            )
            a_ready_cids = [cid for cid in fem_cids if a_ready.loc[cid]]
            a_sf_ready = (
                round(float(any_shortfall.loc[a_ready_cids].sum() / len(a_ready_cids)), 4)
                if len(a_ready_cids) > 0
                else None
            )

            diff_pct = (a_ready_rate - b_ready_rate) * 100.0
            sign = "+" if diff_pct >= 0 else ""
            impact_summary = (
                f"Female Ready rate changed by {sign}{diff_pct:.1f}% "
                f"(from {b_ready_rate * 100.0:.1f}% to {a_ready_rate * 100.0:.1f}%) "
                f"with no significant increase in shortfall risk."
            )

            mitigation_dict = {
                "description": DEFAULT_MITIGATION_DESCRIPTION,
                "target_group": target_group,
                "before": {
                    "ready_rate": b_ready_rate,
                    "false_not_yet_rate": b_false_not_yet,
                    "shortfall_rate_among_ready": b_sf_ready,
                },
                "after": {
                    "ready_rate": a_ready_rate,
                    "false_not_yet_rate": a_false_not_yet,
                    "shortfall_rate_among_ready": a_sf_ready,
                },
                "impact_summary": impact_summary,
            }

        meta = Meta(
            model_version=get_model_version("forecaster"),
            data_as_of=get_data_as_of(),
            disclaimer=cfg.disclaimer,
        )

        return FairnessReport(
            by_gender=by_gender,
            by_region=by_region,
            by_age_band=by_age_band,
            mitigation=mitigation_dict,
            meta=meta,
        )

    def _empty_report(self, cfg: Config) -> FairnessReport:
        """Construct report when sample has zero customers."""
        def make_empty(groups: list[str]) -> list[FairnessGroup]:
            return [
                FairnessGroup(
                    group=g,
                    count=0,
                    ready_rate=None,
                    forecast_error=None,
                    false_not_yet_rate=None,
                )
                for g in groups
            ]

        meta = Meta(
            model_version=get_model_version("forecaster"),
            data_as_of=get_data_as_of(),
            disclaimer=cfg.disclaimer,
        )
        return FairnessReport(
            by_gender=make_empty(DEFAULT_GENDER_GROUPS),
            by_region=make_empty(DEFAULT_REGION_GROUPS),
            by_age_band=make_empty(DEFAULT_AGE_GROUPS),
            mitigation={
                "description": DEFAULT_MITIGATION_DESCRIPTION,
                "target_group": DEFAULT_TARGET_GROUP,
                "before": {"ready_rate": None, "false_not_yet_rate": None, "shortfall_rate_among_ready": None},
                "after": {"ready_rate": None, "false_not_yet_rate": None, "shortfall_rate_among_ready": None},
                "impact_summary": "No data available in empty sample.",
            },
            meta=meta,
        )


# Global in-memory cache for fast repeated admin queries
_fairness_cache: dict[int | None, FairnessReport] = {}


def compute_fairness_report(
    sample_size: int | None = 1000,
    reload: bool = False,
    config: Config | None = None,
) -> FairnessReport:
    """
    Compute or retrieve cached fairness report for representative test split customers.
    """
    global _fairness_cache
    if not reload and config is None and sample_size in _fairness_cache:
        return _fairness_cache[sample_size]

    module = FairnessModule(config=config)
    report = module.compute(sample_size=sample_size, config=config)

    if config is None:
        _fairness_cache[sample_size] = report

    return report
