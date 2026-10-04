"""
Fairness and Disparity Module Tests (B10, U4, Spec 9.4).

Verifies:
- Empty groups and groups with 0 counts return None (N/A), never 0 or 1.
- Counts accurately match demographic distributions in customer_attributes.
- Protected attributes (gender, region, age, religion) are never used in model features.
- Policy mitigation produces measurable before/after improvement for target groups.
- Response payload strictly validates against FairnessResponse schema.
"""
from __future__ import annotations

import re
import pytest
import pandas as pd

from app.config import Config
from app.data.loader import get_customer_ids, load_data
from app.features.builder import FEATURE_COLUMNS, FORBIDDEN_COLUMNS, build_features
from app.fairness.module import (
    FairnessModule,
    FairnessReport,
    compute_fairness_report,
    format_fairness_rate,
)
from app.ml.forecaster import CashFlowForecaster, FORECASTER_FEATURES
from app.ml.risk_model import CalibratedRiskModel, RISK_FEATURES
from app.schemas import FairnessGroup, FairnessResponse


@pytest.fixture(scope="module")
def fairness_data():
    """Load data tables once for test suite."""
    return load_data()


@pytest.fixture(scope="module")
def sample_test_cids():
    """Subset of held-out test customers for fast test execution."""
    return get_customer_ids("test")[:250]


def test_groups_with_no_data_show_na(fairness_data, sample_test_cids):
    """
    CRITICAL REQUIREMENT (U4 & Spec 9.4):
    Groups with no data must show None (JSON null or formatted as 'N/A'), NOT 0 or 1.
    If count == 0, rates must be None.
    """
    data = fairness_data
    attrs = data["customer_attributes"]

    # Filter to only male customers so female group has exactly 0 members
    male_cids = attrs[
        (attrs["customer_id"].isin(sample_test_cids)) & (attrs["gender"] == "male")
    ]["customer_id"].tolist()[:50]
    assert len(male_cids) > 0

    module = FairnessModule(data=data)
    # Also pass a custom synthetic group with 0 members ('other')
    report = module.compute(
        customer_ids=male_cids,
        custom_groups={"gender": ["male", "female", "other"]},
    )

    # 1. Inspect female group (0 count in sample)
    female_group = next((g for g in report.by_gender if g.group == "female"), None)
    assert female_group is not None
    assert female_group.count == 0
    assert female_group.ready_rate is None
    assert female_group.forecast_error is None
    assert female_group.false_not_yet_rate is None

    # Crucial check: rates must strictly be None, NEVER numeric 0, 0.0, 1, or 1.0
    assert female_group.ready_rate is not 0
    assert female_group.ready_rate is not 0.0
    assert female_group.ready_rate is not 1
    assert female_group.ready_rate is not 1.0

    # Test N/A string representation
    assert format_fairness_rate(female_group.ready_rate) == "N/A"
    assert format_fairness_rate(female_group.forecast_error) == "N/A"
    assert format_fairness_rate(female_group.false_not_yet_rate) == "N/A"

    # 2. Inspect synthetic 'other' group
    other_group = next((g for g in report.by_gender if g.group == "other"), None)
    assert other_group is not None
    assert other_group.count == 0
    assert other_group.ready_rate is None
    assert other_group.forecast_error is None
    assert other_group.false_not_yet_rate is None

    # 3. Serialization check: None serializes to None / null in dict
    report_dict = report.model_dump()
    female_dict = next(g for g in report_dict["by_gender"] if g["group"] == "female")
    assert female_dict["ready_rate"] is None
    assert female_dict["forecast_error"] is None
    assert female_dict["false_not_yet_rate"] is None


def test_counts_match_attributes(fairness_data, sample_test_cids):
    """Group counts must aggregate exactly from customer_attributes table."""
    data = fairness_data
    attrs_df = data["customer_attributes"].set_index("customer_id")
    target_attrs = attrs_df.loc[sample_test_cids]

    module = FairnessModule(data=data)
    report = module.compute(customer_ids=sample_test_cids)

    # Gender counts
    total_gender = sum(g.count for g in report.by_gender)
    assert total_gender == len(sample_test_cids)
    for g in report.by_gender:
        expected = int((target_attrs["gender"] == g.group).sum())
        assert g.count == expected, f"Gender {g.group} count mismatch: got {g.count}, expected {expected}"

    # Region counts
    total_region = sum(r.count for r in report.by_region)
    assert total_region == len(sample_test_cids)
    for r in report.by_region:
        expected = int((target_attrs["region_type"] == r.group).sum())
        assert r.count == expected, f"Region {r.group} count mismatch: got {r.count}, expected {expected}"

    # Age band counts
    total_age = sum(a.count for a in report.by_age_band)
    assert total_age == len(sample_test_cids)
    for a in report.by_age_band:
        expected = int((target_attrs["age_band"] == a.group).sum())
        assert a.count == expected, f"Age band {a.group} count mismatch: got {a.count}, expected {expected}"


def test_protected_attributes_not_in_features(fairness_data):
    """
    CRITICAL FAIRNESS RULE:
    Protected attributes (gender, religion, region, age) and latent traits are
    NEVER model inputs — audit-only. Verify zero leakage into feature vectors.
    """
    forbidden_tokens = [
        "gender",
        "religion",
        "region",
        "age",
        "persona",
        "stability",
        "exposure",
        "discipline",
    ]

    # 1. Feature builder feature names
    for col in FEATURE_COLUMNS:
        col_lower = col.lower()
        assert col_lower not in FORBIDDEN_COLUMNS
        for token in forbidden_tokens:
            assert token not in col_lower, f"Forbidden token '{token}' found in FEATURE_COLUMNS: '{col}'"

    # 2. Forecaster feature list
    for feat in FORECASTER_FEATURES:
        feat_lower = feat.lower()
        for token in forbidden_tokens:
            assert token not in feat_lower, f"Forbidden token '{token}' found in FORECASTER_FEATURES: '{feat}'"

    # 3. Forecaster model object feature names
    forecaster = CashFlowForecaster()
    for feat in forecaster.feature_names:
        feat_lower = feat.lower()
        for token in forbidden_tokens:
            assert token not in feat_lower, f"Forbidden token '{token}' found in Forecaster instance: '{feat}'"

    # 4. Risk model feature list
    for feat in RISK_FEATURES:
        feat_lower = feat.lower()
        for token in forbidden_tokens:
            assert token not in feat_lower, f"Forbidden token '{token}' found in RISK_FEATURES: '{feat}'"

    risk_model = CalibratedRiskModel()
    for feat in risk_model.feature_names:
        feat_lower = feat.lower()
        for token in forbidden_tokens:
            assert token not in feat_lower, f"Forbidden token '{token}' found in RiskModel instance: '{feat}'"

    # 5. Output features dataframe from build_features
    sample_cids = get_customer_ids("test")[:10]
    data = fairness_data
    df = build_features(
        data["transactions"],
        data["daily_balances"],
        data["bills"],
        cutoff_date="2025-09-30",
        customer_ids=sample_cids,
    )
    for col in df.columns:
        col_lower = col.lower()
        for token in forbidden_tokens:
            assert token not in col_lower, f"Forbidden token '{token}' leaked into generated features: '{col}'"


def test_mitigation_before_after(fairness_data, sample_test_cids):
    """
    Test real mitigation (U4 & Spec B10):
    Adjusting minimum cushion threshold (৳300 floor for micro-savers)
    produces a measurable improvement in Ready rate for female customers.
    """
    module = FairnessModule(data=fairness_data)
    report = module.compute(customer_ids=sample_test_cids)

    mitigation = report.mitigation
    assert isinstance(mitigation, dict)
    assert mitigation["target_group"] == "female"
    assert "Alternative cushion threshold" in mitigation["description"]
    assert "300" in mitigation["description"]

    before = mitigation["before"]
    after = mitigation["after"]

    assert "ready_rate" in before
    assert "false_not_yet_rate" in before
    assert "shortfall_rate_among_ready" in before

    assert "ready_rate" in after
    assert "false_not_yet_rate" in after
    assert "shortfall_rate_among_ready" in after

    assert isinstance(before["ready_rate"], float)
    assert isinstance(after["ready_rate"], float)

    # Measurable improvement: Ready rate increases after threshold mitigation
    assert after["ready_rate"] > before["ready_rate"], (
        f"Mitigation failed to improve female ready rate: before={before['ready_rate']}, after={after['ready_rate']}"
    )

    # Impact summary sentence exists and contains actionable insight
    assert isinstance(mitigation["impact_summary"], str)
    assert len(mitigation["impact_summary"]) > 0
    assert "Female Ready rate" in mitigation["impact_summary"]
    assert "%" in mitigation["impact_summary"]


def test_report_structure(sample_test_cids):
    """Verify generated report matches the FairnessResponse schema."""
    report = compute_fairness_report(sample_size=100)

    assert isinstance(report, FairnessReport)
    assert isinstance(report, FairnessResponse)

    # Validate against Pydantic schema
    validated = FairnessResponse.model_validate(report.model_dump())
    assert len(validated.by_gender) >= 2
    assert len(validated.by_region) >= 2
    assert len(validated.by_age_band) >= 5

    # Check Meta
    assert validated.meta.model_version != ""
    assert validated.meta.data_as_of != ""
    assert len(validated.meta.disclaimer) > 0

    # Ensure to_dict method functions
    d = report.to_dict()
    assert isinstance(d, dict)
    assert "by_gender" in d
    assert "by_region" in d
    assert "by_age_band" in d
    assert "mitigation" in d
    assert "meta" in d


def test_compute_fairness_report_caching():
    """Verify compute_fairness_report caching returns quickly on repeated calls."""
    # First call computes or retrieves
    r1 = compute_fairness_report(sample_size=150)
    # Second call returns cached reference
    r2 = compute_fairness_report(sample_size=150)
    assert r1 is r2

    # Reload forces re-computation
    r3 = compute_fairness_report(sample_size=150, reload=True)
    assert isinstance(r3, FairnessReport)
