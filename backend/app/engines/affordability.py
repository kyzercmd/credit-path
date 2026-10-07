"""
CreditPath Affordability Engine (B5).

Computes policy-capped repayment capacity and amortized loan check verdicts:
- Monthly spare money (surplus) projected over 4 weeks using CashFlowForecaster.
- Safe repayment range capped at policy limit (config.affordability_cap, default 40%).
- Stress test assuming income drop (config.stress_pct, default 30%).
- Amortized loan check with verdicts: "Comfortable", "Tight", "Too much".
- Nearest-comfortable parameter search when requested loan exceeds capacity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd

from app.config import Config, get_config
from app.engines.reasons import get_reason_text
from app.features.builder import build_customer_features
from app.ml.model_store import load_model, get_model_version, get_data_as_of
from app.schemas import Meta, NearestComfortable


@dataclass
class SafeRangeResult:
    customer_id: str
    monthly_low: float
    monthly_high: float
    stressed_low: float
    stressed_high: float
    basis_months: int
    basis_sentence: str
    meta: Meta
    low_confidence: bool = False


@dataclass
class LoanCheckResult:
    customer_id: str
    amount: float
    tenor_months: int
    monthly_payment: float
    total_repayment: float
    surplus_share: float
    verdict: str
    verdict_reason: str
    stress_verdict: str
    stress_reason: str
    nearest_comfortable: NearestComfortable | None
    meta: Meta


def calculate_amortization(amount: float, tenor_months: int, annual_rate: float) -> float:
    """Calculate monthly payment using standard annuity formula."""
    if tenor_months <= 0:
        raise ValueError("tenor_months must be positive.")
    if amount <= 0:
        return 0.0

    r = annual_rate / 12.0
    if r > 0:
        factor = (1.0 + r) ** tenor_months
        pmt = amount * (r * factor) / (factor - 1.0)
    else:
        pmt = amount / float(tenor_months)

    return round(float(pmt), 2)


class AffordabilityEngine:
    """Computes sustainable borrowing capacity and loan-level guidance."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or get_config()

    def _get_forecaster_projections(
        self,
        customer_id: str,
        cutoff_date: str = "2025-12-31",
        customer_features: pd.DataFrame | None = None,
    ) -> tuple[float, float]:
        """Project next 4 weeks of inflow and outflow."""
        if customer_features is None:
            customer_features = build_customer_features(customer_id, cutoff_date=cutoff_date)

        forecaster, _ = load_model("forecaster")
        projections = forecaster.predict_future_weeks(
            customer_features,
            weeks=4,
            base_date=cutoff_date,
        )

        monthly_inflow = float(projections["predicted_inflow"].sum())
        monthly_outflow = float(projections["predicted_outflow"].sum())
        return monthly_inflow, monthly_outflow

    def safe_range(
        self,
        customer_id: str,
        config: Config | None = None,
        cutoff_date: str = "2025-12-31",
        customer_features: pd.DataFrame | None = None,
    ) -> SafeRangeResult:
        """Calculate recommended safe monthly payment ranges, including stress test."""
        cfg = config or self.config
        if cfg.kill_safe_range:
            raise RuntimeError("Safe range calculation is temporarily disabled by admin kill-switch.")

        monthly_inflow, monthly_outflow = self._get_forecaster_projections(
            customer_id, cutoff_date=cutoff_date, customer_features=customer_features
        )

        surplus = max(0.0, monthly_inflow - monthly_outflow)
        max_safe = surplus * cfg.affordability_cap

        monthly_high = max(0.0, round(max_safe, -1))
        monthly_low = max(0.0, round(max_safe * 0.5, -1))

        # Stressed capacity calculation
        stressed_inflow = monthly_inflow * (1.0 - cfg.stress_pct)
        stressed_surplus = max(0.0, stressed_inflow - monthly_outflow)
        stressed_max_safe = stressed_surplus * cfg.affordability_cap

        stressed_high = max(0.0, round(stressed_max_safe, -1))
        stressed_low = max(0.0, round(stressed_max_safe * 0.5, -1))

        # Ensure stressed bounds do not exceed baseline bounds
        stressed_high = min(stressed_high, monthly_high)
        stressed_low = min(stressed_low, monthly_low)

        meta = Meta(
            model_version=get_model_version("forecaster"),
            data_as_of=get_data_as_of(),
            disclaimer=cfg.disclaimer,
        )
        # Determine if customer belongs to a low-confidence forecasting persona cohort
        low_confidence = False
        try:
            from app.data.loader import load_data
            from app.api.admin import get_forecast_quality
            d_data = load_data()
            cust_df = d_data.get("customers")
            if cust_df is not None:
                row = cust_df[cust_df["customer_id"] == customer_id]
                if len(row) > 0:
                    persona = str(row["persona"].iloc[0])
                    fq = get_forecast_quality()
                    low_confidence = bool(fq.by_persona.get(persona, {}).get("low_confidence", False))
        except Exception:
            low_confidence = False

        return SafeRangeResult(
            customer_id=customer_id,
            monthly_low=monthly_low,
            monthly_high=monthly_high,
            stressed_low=stressed_low,
            stressed_high=stressed_high,
            basis_months=3,
            basis_sentence="Based on your last 3 months of wallet activity.",
            low_confidence=low_confidence,
            meta=meta,
        )

    def loan_check(
        self,
        customer_id: str,
        amount: float,
        tenor_months: int,
        config: Config | None = None,
        cutoff_date: str = "2025-12-31",
        customer_features: pd.DataFrame | None = None,
    ) -> LoanCheckResult:
        """Evaluate a specific loan proposal against cash-flow spare money and stress bounds."""
        cfg = config or self.config
        if cfg.kill_loan_check:
            raise RuntimeError("Loan check calculation is temporarily disabled by admin kill-switch.")

        monthly_inflow, monthly_outflow = self._get_forecaster_projections(
            customer_id, cutoff_date=cutoff_date, customer_features=customer_features
        )

        surplus = max(0.0, monthly_inflow - monthly_outflow)
        pmt = calculate_amortization(amount, tenor_months, cfg.illustrative_rate)
        total_repayment = round(pmt * tenor_months, 2)

        if surplus > 0:
            surplus_share = round(pmt / surplus, 4)
        else:
            surplus_share = 999.0

        # Baseline verdict
        if surplus_share <= cfg.affordability_cap:
            verdict = "Comfortable"
        elif surplus_share <= 0.60:
            verdict = "Tight"
        else:
            verdict = "Too much"

        if surplus > 0:
            verdict_reason = get_reason_text(
                f"AFFORDABILITY_{verdict.upper().replace(' ', '_')}",
                pct=round(surplus_share * 100.0, 1),
            )
        else:
            verdict_reason = get_reason_text("AFFORDABILITY_NO_SPARE")

        # Stress test evaluation
        stressed_inflow = monthly_inflow * (1.0 - cfg.stress_pct)
        stressed_surplus = max(0.0, stressed_inflow - monthly_outflow)
        if stressed_surplus > 0:
            stressed_share = round(pmt / stressed_surplus, 4)
        else:
            stressed_share = 999.0

        if stressed_share <= cfg.affordability_cap:
            stress_verdict = "Comfortable"
        elif stressed_share <= 0.60:
            stress_verdict = "Tight"
        else:
            stress_verdict = "Too much"

        if stressed_surplus > 0:
            stress_reason = get_reason_text(
                f"STRESS_{stress_verdict.upper().replace(' ', '_')}",
                stress_pct=round(cfg.stress_pct * 100.0, 0),
                pct=round(stressed_share * 100.0, 1),
            )
        else:
            stress_reason = get_reason_text(
                "STRESS_TOO_MUCH",
                stress_pct=round(cfg.stress_pct * 100.0, 0),
                pct=100.0,
            )

        # Nearest comfortable search if proposal is Tight or Too much
        nearest_comfortable: NearestComfortable | None = None
        if verdict in ("Tight", "Too much"):
            nearest_comfortable = self._find_nearest_comfortable(
                amount=amount,
                tenor_months=tenor_months,
                surplus=surplus,
                affordability_cap=cfg.affordability_cap,
                rate=cfg.illustrative_rate,
            )

        meta = Meta(
            model_version=get_model_version("forecaster"),
            data_as_of=get_data_as_of(),
            disclaimer=cfg.disclaimer,
        )

        return LoanCheckResult(
            customer_id=customer_id,
            amount=amount,
            tenor_months=tenor_months,
            monthly_payment=pmt,
            total_repayment=total_repayment,
            surplus_share=surplus_share,
            verdict=verdict,
            verdict_reason=verdict_reason,
            stress_verdict=stress_verdict,
            stress_reason=stress_reason,
            nearest_comfortable=nearest_comfortable,
            meta=meta,
        )

    def _find_nearest_comfortable(
        self,
        amount: float,
        tenor_months: int,
        surplus: float,
        affordability_cap: float,
        rate: float,
    ) -> NearestComfortable | None:
        """Search for closest comfortable amount and tenor configuration."""
        max_safe_pmt = surplus * affordability_cap
        if max_safe_pmt <= 0:
            return None

        # 1. First attempt: keep requested amount, extend tenor up to 36 months
        for t in range(tenor_months + 1, 37):
            cand_pmt = calculate_amortization(amount, t, rate)
            if cand_pmt <= max_safe_pmt:
                return NearestComfortable(
                    amount=amount,
                    tenor_months=t,
                    monthly_payment=cand_pmt,
                )

        # 2. Second attempt: reduce amount in steps of 500 down to 1000
        start_amt = float(int(amount // 500) * 500)
        if start_amt == amount:
            start_amt -= 500.0

        amt_candidates = np.arange(start_amt, 999.0, -500.0)
        for cand_amt in amt_candidates:
            cand_amt = float(cand_amt)
            # Try from requested tenor up to 36
            for t in range(tenor_months, 37):
                cand_pmt = calculate_amortization(cand_amt, t, rate)
                if cand_pmt <= max_safe_pmt:
                    return NearestComfortable(
                        amount=cand_amt,
                        tenor_months=t,
                        monthly_payment=cand_pmt,
                    )

        # 3. Last fallback: test at 1000 with max tenor 36
        cand_pmt = calculate_amortization(1000.0, 36, rate)
        if cand_pmt <= max_safe_pmt:
            return NearestComfortable(
                amount=1000.0,
                tenor_months=36,
                monthly_payment=cand_pmt,
            )

        return None


def calculate_safe_range(
    customer_id: str,
    config: Config | None = None,
    cutoff_date: str = "2025-12-31",
) -> SafeRangeResult:
    """Convenience function to calculate safe repayment range."""
    engine = AffordabilityEngine(config=config)
    return engine.safe_range(customer_id, config=config, cutoff_date=cutoff_date)


def evaluate_loan_check(
    customer_id: str,
    amount: float,
    tenor_months: int,
    config: Config | None = None,
    cutoff_date: str = "2025-12-31",
) -> LoanCheckResult:
    """Convenience function to evaluate loan check."""
    engine = AffordabilityEngine(config=config)
    return engine.loan_check(
        customer_id=customer_id,
        amount=amount,
        tenor_months=tenor_months,
        config=config,
        cutoff_date=cutoff_date,
    )

