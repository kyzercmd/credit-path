"""
CreditPath Ready Rule Engine (B4).

Evaluates the three core readiness checks against current Config thresholds:
1. Check 1 (Wallet History): months_active >= config.min_history_months (default 3)
2. Check 2 (Steady Money In): income in >= config.regularity_n of last config.regularity_m weeks (default 8 of 12)
3. Check 3 (Cushion & Bills): balance stays above config.min_balance_threshold on
   >= config.min_balance_pct_days proportion of days (default 70%), AND utility bills paid on time
   in >= config.bill_on_time_pct proportion of cases (default 60%). If customer has no bills, check balance only.

Overall readiness requires passing ALL THREE checks.
Missing checks are ranked by risk model importance / shortfall probability impact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import pandas as pd

from app.config import Config, get_config
from app.data.loader import load_data
from app.engines.reasons import get_reason_text
from app.features.builder import build_customer_features
from app.ml.model_store import load_model
from app.schemas import CheckResult


@dataclass
class ReadyResult:
    ready: bool
    status_label: str
    status_sentence: str
    checks: list[CheckResult]
    missing_checks: list[CheckResult] = field(default_factory=list)


class ReadyEngine:
    """Evaluates customer readiness against policy rules."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or get_config()

    def evaluate(
        self,
        customer_id: str,
        config: Config | None = None,
        cutoff_date: str = "2025-12-31",
        customer_features: pd.DataFrame | None = None,
        data: dict[str, pd.DataFrame] | None = None,
    ) -> ReadyResult:
        """
        Evaluate customer against the three policy readiness checks.
        """
        cfg = config or self.config

        # 1. Obtain features and base data
        if customer_features is None:
            customer_features = build_customer_features(customer_id, cutoff_date=cutoff_date)
        if data is None:
            data = load_data()

        # Check 1: History (months_active)
        if len(customer_features) > 0 and "months_active" in customer_features.columns:
            months_active = int(customer_features.iloc[-1]["months_active"])
        else:
            tx = data["transactions"]
            c_tx = tx[(tx["customer_id"] == customer_id) & (pd.to_datetime(tx["date"]) <= pd.to_datetime(cutoff_date))]
            months_active = int(pd.to_datetime(c_tx["date"]).dt.to_period("M").nunique()) if len(c_tx) > 0 else 0

        c1_passed = months_active >= cfg.min_history_months
        c1_code = "HISTORY_ENOUGH" if c1_passed else "HISTORY_INSUFFICIENT"
        c1_reason = get_reason_text(
            c1_code,
            months=months_active,
            min_months=cfg.min_history_months,
        )
        chk1 = CheckResult(
            name="Wallet History",
            passed=c1_passed,
            reason=c1_reason,
            reason_code=c1_code,
            current_value=months_active,
            target_value=cfg.min_history_months,
        )

        # Check 2: Steady Money In (income in >= regularity_n of last regularity_m weeks)
        m = cfg.regularity_m
        if len(customer_features) >= m:
            recent_inflows = customer_features.iloc[-m:]["weekly_inflow"]
            n_regular = int((recent_inflows > 0).sum())
        elif len(customer_features) > 0:
            recent_inflows = customer_features["weekly_inflow"]
            n_regular = int((recent_inflows > 0).sum())
        else:
            n_regular = 0

        c2_passed = n_regular >= cfg.regularity_n
        c2_code = "INCOME_REGULAR" if c2_passed else "INCOME_IRREGULAR"
        c2_reason = get_reason_text(
            c2_code,
            n=n_regular,
            m=cfg.regularity_m,
            req_n=cfg.regularity_n,
        )
        chk2 = CheckResult(
            name="Steady Money In",
            passed=c2_passed,
            reason=c2_reason,
            reason_code=c2_code,
            current_value=n_regular,
            target_value=cfg.regularity_n,
        )

        # Check 3: Cushion & Bills
        bal = data["daily_balances"]
        c_bal = bal[(bal["customer_id"] == customer_id) & (pd.to_datetime(bal["date"]) <= pd.to_datetime(cutoff_date))]
        if len(c_bal) > 0:
            days_above = (c_bal["balance"] >= cfg.min_balance_threshold).sum()
            balance_pct = float(days_above / len(c_bal))
        else:
            balance_pct = 0.0

        cushion_passed = balance_pct >= cfg.min_balance_pct_days

        # Bills evaluation
        bi = data["bills"]
        c_bi = bi[(bi["customer_id"] == customer_id) & (pd.to_datetime(bi["due_date"]) <= pd.to_datetime(cutoff_date))]
        has_bills = len(c_bi) > 0
        if has_bills:
            bill_pct = float(c_bi["on_time"].astype(bool).mean())
            bills_passed = bill_pct >= cfg.bill_on_time_pct
        else:
            bill_pct = 1.0
            bills_passed = True

        c3_passed = cushion_passed and bills_passed

        # Select appropriate reason code and message for Check 3
        if not cushion_passed:
            c3_code = "CUSHION_LOW"
            c3_reason = get_reason_text(
                c3_code,
                threshold=cfg.min_balance_threshold,
                pct=balance_pct * 100.0,
                req_pct=cfg.min_balance_pct_days * 100.0,
            )
        elif has_bills and not bills_passed:
            c3_code = "BILLS_LATE"
            c3_reason = get_reason_text(
                c3_code,
                pct=bill_pct * 100.0,
                req_pct=cfg.bill_on_time_pct * 100.0,
            )
        else:
            c3_code = "CUSHION_OK"
            c3_reason = get_reason_text(
                c3_code,
                threshold=cfg.min_balance_threshold,
                pct=balance_pct * 100.0,
                req_pct=cfg.min_balance_pct_days * 100.0,
            )

        chk3 = CheckResult(
            name="Cushion & Bills",
            passed=c3_passed,
            reason=c3_reason,
            reason_code=c3_code,
            current_value=round(balance_pct * 100.0, 1),
            target_value=round(cfg.min_balance_pct_days * 100.0, 1),
        )

        all_checks = [chk1, chk2, chk3]
        ready = c1_passed and c2_passed and c3_passed
        status_label = "Ready" if ready else "Not yet"

        if ready:
            status_sentence = (
                "Your wallet history shows steady income and healthy savings to support small repayments."
            )
        else:
            status_sentence = (
                "A few areas in your wallet activity need a bit more time or steady pattern."
            )

        unpassed_checks = [c for c in all_checks if not c.passed]
        ranked_missing = self._rank_missing_checks(unpassed_checks)

        return ReadyResult(
            ready=ready,
            status_label=status_label,
            status_sentence=status_sentence,
            checks=all_checks,
            missing_checks=ranked_missing,
        )

    def _rank_missing_checks(self, missing_checks: list[CheckResult]) -> list[CheckResult]:
        """Rank missing checks using risk model feature importances."""
        if not missing_checks:
            return []

        try:
            risk_model, _ = load_model("risk_model")
            importances = risk_model.get_feature_importances()
        except Exception:
            importances = {}

        # Aggregate importance corresponding to each check's domain
        check_weights = {
            "Wallet History": importances.get("months_active", 0.1),
            "Steady Money In": (
                importances.get("income_regularity_ratio", 0.2)
                + importances.get("lag_1_inflow", 0.05)
            ),
            "Cushion & Bills": (
                importances.get("balance_mean", 0.25)
                + importances.get("balance_min", 0.2)
                + importances.get("bill_on_time_ratio", 0.1)
            ),
        }

        return sorted(
            missing_checks,
            key=lambda chk: check_weights.get(chk.name, 0.0),
            reverse=True,
        )


def evaluate(
    customer_id: str,
    config: Config | None = None,
    cutoff_date: str = "2025-12-31",
) -> ReadyResult:
    """Convenience function to evaluate customer readiness."""
    engine = ReadyEngine(config=config)
    return engine.evaluate(customer_id, config=config, cutoff_date=cutoff_date)


evaluate_customer = evaluate

