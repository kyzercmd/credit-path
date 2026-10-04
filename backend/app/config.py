"""
CreditPath configuration — all tunable thresholds live here.
Loaded once at startup; the admin PUT /config endpoint updates the DB
and reloads this at runtime.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Config:
    # --- Ready rule thresholds (Section 1) ---
    min_history_months: int = 3
    regularity_n: int = 8          # income in at least N of last M weeks
    regularity_m: int = 12
    min_balance_pct_days: float = 0.70   # balance above min in X% of days
    min_balance_threshold: float = 500.0  # the "minimum" balance floor (৳)
    bill_on_time_pct: float = 0.60       # bills paid on time in Y% of cases

    # --- Affordability (F2, F3) ---
    affordability_cap: float = 0.40      # max share of surplus for repayment
    stress_pct: float = 0.30             # income-drop stress test
    illustrative_rate: float = 0.15      # annual interest rate for loan-check

    # --- Model ---
    forecast_weeks: int = 8
    model_version: str = "v1"
    data_as_of: str = ""                 # set after data generation

    # --- Kill switch ---
    kill_safe_range: bool = False
    kill_loan_check: bool = False

    # --- Disclaimer ---
    disclaimer: str = "Built on synthetic data. Guidance only, not a loan offer."

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid})


# Global mutable config — reloaded on admin config change
_config = Config()


def get_config() -> Config:
    return _config


def update_config(new: Config) -> None:
    global _config
    _config = new
