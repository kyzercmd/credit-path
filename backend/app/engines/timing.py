"""
CreditPath Repayment Timing Engine (B6).

Projects multi-week cash flow and identifies safe vs tight repayment periods:
- Generates 4-8 week projections with CashFlowForecaster.
- Flags each week as 'safe' or 'tight' based on expected balance cushion and net flow.
- Recommends an optimal monthly repayment window immediately following typical income days.
- Surfaces specific weeks to avoid when cash is strained.
"""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from app.config import Config, get_config
from app.data.loader import load_data
from app.engines.reasons import get_reason_text
from app.features.builder import build_customer_features
from app.ml.model_store import load_model, get_model_version, get_data_as_of
from app.schemas import Meta, WeekForecast


@dataclass
class CalendarResult:
    customer_id: str
    weeks: list[WeekForecast]
    recommended_window: str
    avoid_weeks: list[str]
    meta: Meta
    low_confidence: bool = False


class TimingEngine:
    """Repayment calendar planning and timing engine."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or get_config()

    def calendar(
        self,
        customer_id: str,
        config: Config | None = None,
        cutoff_date: str = "2025-12-31",
        customer_features: pd.DataFrame | None = None,
        data: dict[str, pd.DataFrame] | None = None,
    ) -> CalendarResult:
        """Generate weekly repayment cash-flow calendar."""
        cfg = config or self.config

        if customer_features is None:
            customer_features = build_customer_features(customer_id, cutoff_date=cutoff_date)
        if data is None:
            data = load_data()

        forecaster, _ = load_model("forecaster")
        weeks_count = cfg.forecast_weeks

        projections = forecaster.predict_future_weeks(
            customer_features,
            weeks=weeks_count,
            base_date=cutoff_date,
        )

        base_dt = pd.to_datetime(cutoff_date)
        week_forecasts: list[WeekForecast] = []
        avoid_weeks: list[str] = []

        for idx, row in projections.iterrows():
            w_idx = int(row["week_index"])
            week_date = base_dt + pd.Timedelta(days=7 * (w_idx - 1) + 1)
            week_str = week_date.strftime("%Y-%m-%d")

            money_in = float(row["predicted_inflow"])
            money_out = float(row["predicted_outflow"])
            exp_bal = float(row["expected_balance"])

            # Classification rule: safe if balance cushion meets floor and inflow covers outflow adequately
            is_safe = (exp_bal >= cfg.min_balance_threshold) and (money_in >= money_out * 0.5)
            status = "safe" if is_safe else "tight"

            if is_safe:
                reason = get_reason_text("TIMING_SAFE")
            else:
                reason = get_reason_text("TIMING_TIGHT", w=w_idx)
                avoid_weeks.append(f"Week {w_idx}")

            week_forecasts.append(
                WeekForecast(
                    week_start=week_str,
                    money_in=money_in,
                    money_out=money_out,
                    expected_balance=exp_bal,
                    status=status,
                    reason=reason,
                )
            )

        # Determine recommended repayment window from historical income timing
        recommended_window = self._compute_recommended_window(customer_id, data, cutoff_date)

        meta = Meta(
            model_version=get_model_version("forecaster"),
            data_as_of=get_data_as_of(),
            disclaimer=cfg.disclaimer,
        )

        # Determine if customer belongs to a low-confidence forecasting persona cohort
        low_confidence = False
        try:
            from app.api.admin import get_forecast_quality
            cust_df = data.get("customers")
            if cust_df is not None:
                row = cust_df[cust_df["customer_id"] == customer_id]
                if len(row) > 0:
                    persona = str(row["persona"].iloc[0])
                    fq = get_forecast_quality()
                    low_confidence = bool(fq.by_persona.get(persona, {}).get("low_confidence", False))
        except Exception:
            low_confidence = False

        return CalendarResult(
            customer_id=customer_id,
            weeks=week_forecasts,
            recommended_window=recommended_window,
            avoid_weeks=avoid_weeks,
            low_confidence=low_confidence,
            meta=meta,
        )

    def _compute_recommended_window(
        self,
        customer_id: str,
        data: dict[str, pd.DataFrame],
        cutoff_date: str,
    ) -> str:
        """Find the optimal monthly calendar days aligned with historical inflow days."""
        tx = data["transactions"]
        cutoff_dt = pd.to_datetime(cutoff_date)
        c_tx = tx[
            (tx["customer_id"] == customer_id)
            & (pd.to_datetime(tx["date"]) <= cutoff_dt)
            & (tx["type"].isin(["cash_in", "p2p_in"]))
        ]

        if len(c_tx) > 0:
            days = pd.to_datetime(c_tx["date"]).dt.day
            median_day = int(days.median())
        else:
            median_day = 5

        if median_day <= 5:
            return "Days 5 to 10 of each month (just after your typical income days)."
        elif median_day <= 15:
            return "Days 15 to 20 of each month (just after your typical income days)."
        elif median_day <= 25:
            return "Days 25 to 30 of each month (just after your typical income days)."
        else:
            return "Days 1 to 5 of each month (just after your typical income days)."


def generate_calendar_forecast(
    customer_id: str,
    config: Config | None = None,
    cutoff_date: str = "2025-12-31",
) -> CalendarResult:
    """Convenience function to generate calendar forecast."""
    engine = TimingEngine(config=config)
    return engine.calendar(customer_id, config=config, cutoff_date=cutoff_date)

