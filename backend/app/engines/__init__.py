"""
CreditPath Core Engines (B4-B7, B9).

Modules:
- reasons: Plain-language Reason Catalog without forbidden jargon
- ready: B4 Ready Rule Engine (3 policy checks)
- affordability: B5 Affordability & Safe Range Engine
- timing: B6 Repayment Timing & Calendar Engine
- recourse: B7 Recourse & Path to Readiness Engine
"""

from app.engines.reasons import ReasonCatalog, get_reason_text
from app.engines.ready import ReadyEngine, ReadyResult, evaluate, evaluate_customer
from app.engines.affordability import (
    AffordabilityEngine,
    SafeRangeResult,
    LoanCheckResult,
    calculate_amortization,
    calculate_safe_range,
    evaluate_loan_check,
)
from app.engines.timing import TimingEngine, CalendarResult, generate_calendar_forecast
from app.engines.recourse import RecourseEngine, PathStepResult, compute_recourse_path

__all__ = [
    "ReasonCatalog",
    "get_reason_text",
    "ReadyEngine",
    "ReadyResult",
    "evaluate",
    "evaluate_customer",
    "AffordabilityEngine",
    "SafeRangeResult",
    "LoanCheckResult",
    "calculate_amortization",
    "calculate_safe_range",
    "evaluate_loan_check",
    "TimingEngine",
    "CalendarResult",
    "generate_calendar_forecast",
    "RecourseEngine",
    "PathStepResult",
    "compute_recourse_path",
]

