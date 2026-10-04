"""
CreditPath Reason Catalog (B9).

Fixed catalog mapping reason codes to plain-language, jargon-free explanation templates.
Strictly avoids forbidden words (EMI, surplus, PD, default, credit score).
Plain vocabulary used: "monthly payment", "spare money", "regular income", "cushion".
"""
from __future__ import annotations
import re
from typing import Any

FORBIDDEN_WORDS = ["emi", "surplus", "pd", "credit score", "default"]


class ReasonCatalog:
    """Fixed catalog of plain-language templates and formatting helpers."""

    TEMPLATES: dict[str, str] = {
        # Check 1: History
        "HISTORY_ENOUGH": "You have {months} months of wallet activity (minimum {min_months} needed).",
        "HISTORY_INSUFFICIENT": "You have {months} months of wallet activity (minimum {min_months} needed).",

        # Check 2: Steady Money In
        "INCOME_REGULAR": "Your income arrived in {n} of the last {m} weeks (needed at least {req_n}).",
        "INCOME_IRREGULAR": "Your income arrived in {n} of the last {m} weeks (needed at least {req_n}).",

        # Check 3: Cushion & Bills
        "CUSHION_OK": "Your balance stayed above ৳{threshold:.0f} on {pct:.0f}% of days (minimum {req_pct:.0f}% required).",
        "CUSHION_LOW": "Your balance stayed above ৳{threshold:.0f} on {pct:.0f}% of days (minimum {req_pct:.0f}% required).",
        "BILLS_ON_TIME": "Utility bills were paid on time in {pct:.0f}% of cases (minimum {req_pct:.0f}% required).",
        "BILLS_LATE": "Utility bills were paid on time in {pct:.0f}% of cases (minimum {req_pct:.0f}% required).",

        # Affordability
        "AFFORDABILITY_COMFORTABLE": "This payment is {pct:.0f}% of your usual spare money.",
        "AFFORDABILITY_TIGHT": "This payment is {pct:.0f}% of your usual spare money.",
        "AFFORDABILITY_TOO_MUCH": "This payment is {pct:.0f}% of your usual spare money.",
        "AFFORDABILITY_NO_SPARE": "This payment exceeds your usual spare money.",

        # Stress test
        "STRESS_COMFORTABLE": "Under a {stress_pct:.0f}% drop in income, this payment would be {pct:.0f}% of your spare money.",
        "STRESS_TIGHT": "Under a {stress_pct:.0f}% drop in income, this payment would be {pct:.0f}% of your spare money.",
        "STRESS_TOO_MUCH": "Under a {stress_pct:.0f}% drop in income, this payment would exceed your spare money.",

        # Timing
        "TIMING_SAFE": "Expected wallet balance is healthy after regular income.",
        "TIMING_TIGHT": "Your wallet usually runs low in week {w}.",

        # Recourse actions
        "RECOURSE_HISTORY": "Maintain active wallet transactions for one more month",
        "RECOURSE_REGULARITY": "Receive at least one regular top-up or cash-in every week",
        "RECOURSE_CUSHION": "Keep at least ৳{threshold:.0f} balance in your wallet for 3 consecutive weeks",
        "RECOURSE_BILLS": "Pay your utility bills on time next month",
    }

    @classmethod
    def get(cls, code: str, **kwargs: Any) -> str:
        """Retrieve and format a plain-language explanation by code."""
        template = cls.TEMPLATES.get(code)
        if template is None:
            return f"Condition {code} evaluated."
        try:
            formatted = template.format(**kwargs)
        except (KeyError, ValueError):
            return template

        # Safety check: guarantee no forbidden jargon is emitted
        lower_text = formatted.lower()
        for word in FORBIDDEN_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", lower_text):
                raise ValueError(f"Prohibited jargon term '{word}' found in formatted reason: {formatted}")

        return formatted

    @classmethod
    def format(cls, code: str, **kwargs: Any) -> str:
        return cls.get(code, **kwargs)


def get_reason_text(code: str, **kwargs: Any) -> str:
    """Convenience functional access to the Reason Catalog."""
    return ReasonCatalog.get(code, **kwargs)
