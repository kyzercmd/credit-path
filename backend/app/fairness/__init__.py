"""Fairness and Disparity Module (B10)."""
from app.fairness.module import (
    FairnessModule,
    FairnessReport,
    compute_fairness_report,
    format_fairness_rate,
)

__all__ = [
    "FairnessModule",
    "FairnessReport",
    "compute_fairness_report",
    "format_fairness_rate",
]
