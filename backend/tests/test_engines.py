import pytest
import re
import pandas as pd
from app.config import Config, get_config
from app.data.loader import get_customer_ids, load_data
from app.engines.reasons import ReasonCatalog, get_reason_text
from app.engines.ready import ReadyEngine, ReadyResult
from app.engines.affordability import AffordabilityEngine, SafeRangeResult, LoanCheckResult
from app.engines.timing import TimingEngine, CalendarResult
from app.engines.recourse import RecourseEngine, PathStepResult


@pytest.fixture(scope="module")
def sample_customer_id():
    """Pick a training customer with valid history."""
    cids = get_customer_ids("train")
    return cids[0]


def test_reason_catalog_no_jargon():
    """Assert Reason Catalog contains no prohibited words (EMI, surplus, PD, default, credit score)."""
    # Prohibited jargon words/tokens
    forbidden_terms = ["emi", "surplus", "pd", "credit score", "default"]

    for code, template in ReasonCatalog.TEMPLATES.items():
        text_lower = template.lower()
        for term in forbidden_terms:
            pattern = rf"\b{re.escape(term)}\b"
            assert not re.search(pattern, text_lower), (
                f"Prohibited term '{term}' found in template for code '{code}': {template}"
            )

    # Test sample formatting
    formatted = get_reason_text("AFFORDABILITY_COMFORTABLE", pct=35)
    assert "spare money" in formatted.lower() or "payment" in formatted.lower()
    for term in forbidden_terms:
        assert not re.search(rf"\b{re.escape(term)}\b", formatted.lower())


def test_ready_rule_evaluation(sample_customer_id):
    """Test Ready Rule Engine evaluates 3 checks and flips on config change."""
    engine = ReadyEngine()
    config = Config()

    result = engine.evaluate(sample_customer_id, config=config)
    assert isinstance(result, ReadyResult)
    assert isinstance(result.ready, bool)
    assert result.status_label in ("Ready", "Not yet")
    assert len(result.checks) == 3

    check_names = {c.name for c in result.checks}
    assert "Wallet History" in check_names
    assert "Steady Money In" in check_names
    assert "Cushion & Bills" in check_names

    for chk in result.checks:
        assert chk.reason_code != ""
        assert len(chk.reason) > 0
        assert chk.current_value is not None
        assert chk.target_value is not None

    # Test config changes: impossible history threshold must flip check 1 to failed
    strict_config = Config(min_history_months=120)  # 10 years of history required
    strict_result = engine.evaluate(sample_customer_id, config=strict_config)
    assert strict_result.ready is False
    assert strict_result.status_label == "Not yet"
    history_chk = next(c for c in strict_result.checks if c.name == "Wallet History")
    assert history_chk.passed is False
    assert history_chk.reason_code == "HISTORY_INSUFFICIENT"


def test_affordability_safe_range(sample_customer_id):
    """Test Affordability Engine computes safe range respecting policy cap and stress test."""
    engine = AffordabilityEngine()
    config = Config(affordability_cap=0.40, stress_pct=0.30)

    result = engine.safe_range(sample_customer_id, config=config)
    assert isinstance(result, SafeRangeResult)
    assert result.monthly_low >= 0.0
    assert result.monthly_high >= result.monthly_low

    # Stressed range must not exceed baseline range
    assert result.stressed_high <= result.monthly_high + 1e-5
    assert result.stressed_low <= result.monthly_low + 1e-5

    assert result.basis_months >= 1
    assert "wallet activity" in result.basis_sentence.lower()


def test_loan_check_verdicts(sample_customer_id):
    """Test loan check amortization, verdict boundaries, and nearest-comfortable suggestions."""
    engine = AffordabilityEngine()
    config = Config(affordability_cap=0.40, illustrative_rate=0.15)

    # 1. Tiny loan with long tenor should be Comfortable
    res_comfortable = engine.loan_check(
        sample_customer_id, amount=1000.0, tenor_months=24, config=config
    )
    assert isinstance(res_comfortable, LoanCheckResult)
    assert res_comfortable.monthly_payment > 0
    assert res_comfortable.total_repayment >= res_comfortable.amount

    # Test exact standard amortization formula
    r = config.illustrative_rate / 12.0
    n = 24
    expected_pmt = round(1000.0 * (r * (1 + r) ** n) / ((1 + r) ** n - 1), 2)
    assert abs(res_comfortable.monthly_payment - expected_pmt) <= 0.05

    # 2. Huge loan should be Too much
    res_too_much = engine.loan_check(
        sample_customer_id, amount=500000.0, tenor_months=3, config=config
    )
    assert res_too_much.verdict == "Too much"
    assert res_too_much.surplus_share > 0.60 or res_too_much.surplus_share == 0.0

    # 3. Nearest-comfortable search for a tight or too much loan
    if res_too_much.nearest_comfortable is not None:
        nc = res_too_much.nearest_comfortable
        assert nc.monthly_payment > 0
        assert nc.amount > 0
        assert nc.tenor_months <= 36
        # Re-check candidate with loan_check
        re_check = engine.loan_check(
            sample_customer_id, amount=nc.amount, tenor_months=nc.tenor_months, config=config
        )
        assert re_check.verdict == "Comfortable"


def test_timing_calendar(sample_customer_id):
    """Test Timing Engine weekly predictions, safe vs tight weeks, and recommended window."""
    engine = TimingEngine()
    config = Config(forecast_weeks=8)

    calendar = engine.calendar(sample_customer_id, config=config)
    assert isinstance(calendar, CalendarResult)
    assert len(calendar.weeks) == 8

    for wf in calendar.weeks:
        assert wf.status in ("safe", "tight")
        assert wf.money_in >= 0.0
        assert wf.money_out >= 0.0
        assert wf.expected_balance >= 0.0
        assert len(wf.reason) > 0

    assert isinstance(calendar.recommended_window, str)
    assert len(calendar.recommended_window) > 0
    assert isinstance(calendar.avoid_weeks, list)

    # Avoid weeks must match tight weeks
    tight_indices = [
        f"Week {i+1}" for i, w in enumerate(calendar.weeks) if w.status == "tight"
    ]
    assert calendar.avoid_weeks == tight_indices


def test_recourse_actionable_only(sample_customer_id):
    """Test Recourse Engine only suggests actionable steps that flip failed checks."""
    ready_engine = ReadyEngine()
    recourse_engine = RecourseEngine()

    # Find or induce a configuration where customer has missing checks
    strict_config = Config(
        min_history_months=120,
        regularity_n=12,
        min_balance_pct_days=0.99,
        bill_on_time_pct=0.99,
    )
    ready_res = ready_engine.evaluate(sample_customer_id, config=strict_config)
    assert not ready_res.ready

    path_steps = recourse_engine.path(sample_customer_id, config=strict_config)
    assert len(path_steps) > 0

    for step in path_steps:
        assert isinstance(step, PathStepResult)
        assert step.estimated_weeks > 0
        assert len(step.action) > 0
        assert len(step.reason) > 0
        # Check action belongs to legitimate recourse categories
        allowed_items = {"Wallet History", "Steady Money In", "Wallet Cushion", "Utility Bills"}
        assert step.item in allowed_items
