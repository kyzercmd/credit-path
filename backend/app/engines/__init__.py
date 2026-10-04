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
from app.engines.ready import ReadyEngine, ReadyResult, evaluate
from app.engines.affordability import (
    AffordabilityEngine,
    SafeRangeResult,
    LoanCheckResult,
    calculate_amortization,
)
from app.engines.timing import TimingEngine, CalendarResult
from app.engines.recourse import RecourseEngine, PathStepResult

__all__ = [
    "ReasonCatalog",
    "get_reason_text",
    "ReadyEngine",
    "ReadyResult",
    "evaluate",
    "AffordabilityEngine",
    "SafeRangeResult",
    "LoanCheckResult",
    "calculate_amortization",
    "TimingEngine",
    "CalendarResult",
    "RecourseEngine",
    "PathStepResult",
]
