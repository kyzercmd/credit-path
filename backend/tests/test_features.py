import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.features.builder import (
    build_features,
    build_customer_features,
    build_training_features,
    FEATURE_COLUMNS,
)
from app.data.loader import load_data, get_customer_ids


@pytest.fixture(scope="module")
def sample_dataset():
    """Load small subset from real synthetic dataset."""
    data = load_data()
    cids = get_customer_ids("train")[:5]
    cids_set = set(cids)
    
    tx = data["transactions"][data["transactions"]["customer_id"].isin(cids_set)].copy()
    bal = data["daily_balances"][data["daily_balances"]["customer_id"].isin(cids_set)].copy()
    bi = data["bills"][data["bills"]["customer_id"].isin(cids_set)].copy()
    return {"tx": tx, "bal": bal, "bi": bi, "cids": cids}


def test_feature_columns_present(sample_dataset):
    """Verify all expected feature columns exist, with valid non-null types."""
    df = build_features(
        sample_dataset["tx"],
        sample_dataset["bal"],
        sample_dataset["bi"],
        cutoff_date="2025-06-30",
        customer_ids=sample_dataset["cids"],
    )
    
    # Assert exact columns
    assert list(df.columns) == FEATURE_COLUMNS
    assert len(df) > 0
    
    # Assert no null values anywhere
    assert df.isna().sum().sum() == 0
    
    # Check numeric types
    for col in [
        "weekly_inflow", "weekly_outflow", "balance_mean", "balance_min",
        "income_regularity_ratio", "bill_on_time_ratio", "lag_1_inflow",
        "lag_2_inflow", "lag_3_inflow", "lag_4_inflow", "lag_1_outflow",
        "lag_2_outflow", "lag_1_balance",
    ]:
        assert pd.api.types.is_float_dtype(df[col]), f"{col} should be float"
        
    for col in [
        "week", "months_active", "week_of_month", "month",
        "is_month_end", "is_eid_period", "is_harvest_period",
        "day_of_week_mode", "shortfall_next_week",
    ]:
        assert pd.api.types.is_integer_dtype(df[col]), f"{col} should be integer"


def test_no_future_leakage(sample_dataset):
    """Transactions/balances/bills after cutoff_date must not affect feature values."""
    cutoff = "2025-06-30"
    
    df1 = build_features(
        sample_dataset["tx"],
        sample_dataset["bal"],
        sample_dataset["bi"],
        cutoff_date=cutoff,
        customer_ids=sample_dataset["cids"],
    )
    
    # Add dummy future transactions, balances, and bills in July-December
    future_tx = pd.DataFrame([
        {
            "customer_id": sample_dataset["cids"][0],
            "date": pd.Timestamp("2025-07-15"),
            "type": "cash_in",
            "amount": 999999.0,
            "category": "bonus",
        }
    ])
    future_bal = pd.DataFrame([
        {
            "customer_id": sample_dataset["cids"][0],
            "date": pd.Timestamp("2025-07-15"),
            "balance": 999999.0,
            "shortfall": False,
        }
    ])
    future_bi = pd.DataFrame([
        {
            "customer_id": sample_dataset["cids"][0],
            "due_date": pd.Timestamp("2025-07-25"),
            "amount": 50000.0,
            "paid_date": pd.Timestamp("2025-07-20"),
            "on_time": True,
        }
    ])
    
    augmented_tx = pd.concat([sample_dataset["tx"], future_tx], ignore_index=True)
    augmented_bal = pd.concat([sample_dataset["bal"], future_bal], ignore_index=True)
    augmented_bi = pd.concat([sample_dataset["bi"], future_bi], ignore_index=True)
    
    df2 = build_features(
        augmented_tx,
        augmented_bal,
        augmented_bi,
        cutoff_date=cutoff,
        customer_ids=sample_dataset["cids"],
    )
    
    pd.testing.assert_frame_equal(df1, df2)


def test_lag_alignment():
    """Verify lag_1 is indeed the previous week's value, lag_2 is 2 weeks ago, etc."""
    cid = "C_TEST"
    dates = pd.date_range("2025-01-06", periods=35, freq="D")  # 5 full weeks Mon-Sun
    
    # Transactions in weeks 1, 2, 3
    tx = pd.DataFrame([
        {"customer_id": cid, "date": pd.Timestamp("2025-01-06"), "type": "cash_in", "amount": 1000.0},  # W1
        {"customer_id": cid, "date": pd.Timestamp("2025-01-07"), "type": "cash_out", "amount": 300.0},
        {"customer_id": cid, "date": pd.Timestamp("2025-01-13"), "type": "cash_in", "amount": 2000.0},  # W2
        {"customer_id": cid, "date": pd.Timestamp("2025-01-14"), "type": "cash_out", "amount": 500.0},
        {"customer_id": cid, "date": pd.Timestamp("2025-01-20"), "type": "cash_in", "amount": 3000.0},  # W3
        {"customer_id": cid, "date": pd.Timestamp("2025-01-21"), "type": "cash_out", "amount": 700.0},
        {"customer_id": cid, "date": pd.Timestamp("2025-01-27"), "type": "cash_in", "amount": 4000.0},  # W4
        {"customer_id": cid, "date": pd.Timestamp("2025-01-28"), "type": "cash_out", "amount": 900.0},
        {"customer_id": cid, "date": pd.Timestamp("2025-02-03"), "type": "cash_in", "amount": 5000.0},  # W5
        {"customer_id": cid, "date": pd.Timestamp("2025-02-04"), "type": "cash_out", "amount": 1100.0},
    ])
    
    bal = pd.DataFrame([
        {"customer_id": cid, "date": d, "balance": float(100 * (i + 1)), "shortfall": False}
        for i, d in enumerate(dates)
    ])
    
    bi = pd.DataFrame(columns=["customer_id", "due_date", "amount", "paid_date", "on_time"])
    
    df = build_features(tx, bal, bi, cutoff_date="2025-02-09", customer_ids=[cid])
    cdf = df[df["customer_id"] == cid].sort_values("week").reset_index(drop=True)
    
    assert len(cdf) == 5
    
    # Week 1
    assert cdf.loc[0, "lag_1_inflow"] == 0.0
    assert cdf.loc[0, "lag_1_outflow"] == 0.0
    assert cdf.loc[0, "lag_1_balance"] == 0.0
    
    # Week 2 lag_1 should match Week 1 values
    assert cdf.loc[1, "lag_1_inflow"] == cdf.loc[0, "weekly_inflow"] == 1000.0
    assert cdf.loc[1, "lag_1_outflow"] == cdf.loc[0, "weekly_outflow"] == 300.0
    assert cdf.loc[1, "lag_1_balance"] == cdf.loc[0, "balance_mean"]
    assert cdf.loc[1, "lag_2_inflow"] == 0.0
    
    # Week 3 lag_1 and lag_2
    assert cdf.loc[2, "lag_1_inflow"] == cdf.loc[1, "weekly_inflow"] == 2000.0
    assert cdf.loc[2, "lag_2_inflow"] == cdf.loc[0, "weekly_inflow"] == 1000.0
    assert cdf.loc[2, "lag_1_outflow"] == cdf.loc[1, "weekly_outflow"] == 500.0
    assert cdf.loc[2, "lag_2_outflow"] == cdf.loc[0, "weekly_outflow"] == 300.0
    
    # Week 5 lag_1..lag_4
    assert cdf.loc[4, "lag_1_inflow"] == cdf.loc[3, "weekly_inflow"] == 4000.0
    assert cdf.loc[4, "lag_2_inflow"] == cdf.loc[2, "weekly_inflow"] == 3000.0
    assert cdf.loc[4, "lag_3_inflow"] == cdf.loc[1, "weekly_inflow"] == 2000.0
    assert cdf.loc[4, "lag_4_inflow"] == cdf.loc[0, "weekly_inflow"] == 1000.0


def test_protected_attributes_excluded(sample_dataset):
    """Assert that 'gender', 'region_type', 'age_band', 'religion' are NOT in feature columns."""
    df = build_features(
        sample_dataset["tx"],
        sample_dataset["bal"],
        sample_dataset["bi"],
        cutoff_date="2025-06-30",
        customer_ids=sample_dataset["cids"],
    )
    
    forbidden = {
        "gender", "region_type", "region", "age_band", "age",
        "religion", "persona", "income_stability", "shock_exposure", "bill_discipline"
    }
    for col in forbidden:
        assert col not in df.columns, f"Forbidden protected attribute or latent trait found: {col}"


def test_income_regularity_and_bill_ratios():
    """Test edge cases like customer with no bills, partial bills, or no income in some weeks."""
    cid_no_bills = "C_NO_BILLS"
    cid_with_bills = "C_BILLS"
    cid_zero_income = "C_ZERO_INCOME"
    
    # 3 weeks of daily balances (Jan 6 to Jan 26, 2025)
    dates = pd.date_range("2025-01-06", periods=21, freq="D")
    bal_rows = []
    for cid in [cid_no_bills, cid_with_bills, cid_zero_income]:
        for d in dates:
            bal_rows.append({"customer_id": cid, "date": d, "balance": 1500.0, "shortfall": False})
    bal = pd.DataFrame(bal_rows)
    
    # Transactions:
    # cid_no_bills: income in week 1 and 3, none in week 2
    # cid_zero_income: only cash_out, 0 income
    # cid_with_bills: income in all 3 weeks
    tx = pd.DataFrame([
        {"customer_id": cid_no_bills, "date": pd.Timestamp("2025-01-06"), "type": "cash_in", "amount": 1000.0},
        {"customer_id": cid_no_bills, "date": pd.Timestamp("2025-01-20"), "type": "p2p_in", "amount": 500.0},
        
        {"customer_id": cid_zero_income, "date": pd.Timestamp("2025-01-07"), "type": "cash_out", "amount": 200.0},
        {"customer_id": cid_zero_income, "date": pd.Timestamp("2025-01-14"), "type": "cash_out", "amount": 200.0},
        
        {"customer_id": cid_with_bills, "date": pd.Timestamp("2025-01-06"), "type": "cash_in", "amount": 1000.0},
        {"customer_id": cid_with_bills, "date": pd.Timestamp("2025-01-13"), "type": "cash_in", "amount": 1000.0},
        {"customer_id": cid_with_bills, "date": pd.Timestamp("2025-01-20"), "type": "cash_in", "amount": 1000.0},
    ])
    
    # Bills: only cid_with_bills has 2 bills (1 on time, 1 late)
    bi = pd.DataFrame([
        {"customer_id": cid_with_bills, "due_date": pd.Timestamp("2025-01-10"), "amount": 500.0, "paid_date": pd.Timestamp("2025-01-08"), "on_time": True},
        {"customer_id": cid_with_bills, "due_date": pd.Timestamp("2025-01-20"), "amount": 500.0, "paid_date": pd.Timestamp("2025-01-25"), "on_time": False},
    ])
    
    df = build_features(tx, bal, bi, cutoff_date="2025-01-26")
    
    # Edge case 1: cid_no_bills has no bills -> bill_on_time_ratio should default to 1.0 (no late bills)
    df_no_bills = df[df["customer_id"] == cid_no_bills].sort_values("week").reset_index(drop=True)
    assert (df_no_bills["bill_on_time_ratio"] == 1.0).all()
    # Income in W1 and W3: W1=1/1 (1.0), W2=1/2 (0.5), W3=2/3 (~0.667)
    assert df_no_bills.loc[0, "income_regularity_ratio"] == 1.0
    assert df_no_bills.loc[1, "income_regularity_ratio"] == 0.5
    assert abs(df_no_bills.loc[2, "income_regularity_ratio"] - 2 / 3) < 1e-4
    
    # Edge case 2: cid_zero_income -> regularity is 0.0 for all weeks
    df_zero_in = df[df["customer_id"] == cid_zero_income].sort_values("week").reset_index(drop=True)
    assert (df_zero_in["income_regularity_ratio"] == 0.0).all()
    assert (df_zero_in["weekly_inflow"] == 0.0).all()
    
    # Edge case 3: cid_with_bills -> W1: 1 on-time bill (1.0), W2: no new bills (1.0), W3: 1 late bill (1/2 = 0.5)
    df_bills = df[df["customer_id"] == cid_with_bills].sort_values("week").reset_index(drop=True)
    assert df_bills.loc[0, "bill_on_time_ratio"] == 1.0
    assert df_bills.loc[1, "bill_on_time_ratio"] == 1.0
    assert df_bills.loc[2, "bill_on_time_ratio"] == 0.5


def test_determinism(sample_dataset):
    """Running build_features with same inputs yields identical outputs."""
    df1 = build_features(
        sample_dataset["tx"],
        sample_dataset["bal"],
        sample_dataset["bi"],
        cutoff_date="2025-06-30",
        customer_ids=sample_dataset["cids"],
    )
    df2 = build_features(
        sample_dataset["tx"],
        sample_dataset["bal"],
        sample_dataset["bi"],
        cutoff_date="2025-06-30",
        customer_ids=sample_dataset["cids"],
    )
    pd.testing.assert_frame_equal(df1, df2)


def test_calendar_features():
    """Verify calendar feature boundaries (week_of_month, month, eid, harvest, month_end)."""
    cid = "C_CAL"
    # Create 52 weeks of dates
    dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    bal = pd.DataFrame([{"customer_id": cid, "date": d, "balance": 1000.0, "shortfall": False} for d in dates])
    tx = pd.DataFrame([{"customer_id": cid, "date": pd.Timestamp("2025-01-03"), "type": "cash_in", "amount": 100.0}])
    bi = pd.DataFrame(columns=["customer_id", "due_date", "amount", "paid_date", "on_time"])
    
    df = build_features(tx, bal, bi, cutoff_date="2025-12-31", customer_ids=[cid])
    
    # Check bounds
    assert df["week_of_month"].between(1, 5).all()
    assert df["month"].between(1, 12).all()
    assert df["is_month_end"].isin([0, 1]).all()
    assert df["is_eid_period"].isin([0, 1]).all()
    assert df["is_harvest_period"].isin([0, 1]).all()
    assert df["day_of_week_mode"].between(0, 6).all()
    
    # Month 4 (April) and Month 11 (November) must have is_eid_period == 1
    eid_weeks = df[df["month"].isin([4, 11])]
    assert (eid_weeks["is_eid_period"] == 1).all()
    non_eid_weeks = df[~df["month"].isin([4, 11])]
    assert (non_eid_weeks["is_eid_period"] == 0).all()
    
    # Month 3 (March) and Month 9 (September) must have is_harvest_period == 1
    har_weeks = df[df["month"].isin([3, 9])]
    assert (har_weeks["is_harvest_period"] == 1).all()
    non_har_weeks = df[~df["month"].isin([3, 9])]
    assert (non_har_weeks["is_harvest_period"] == 0).all()


def test_shortfall_next_week_target():
    """Verify shortfall_next_week accurately labels shortfall in subsequent week and 0 at cutoff."""
    cid = "C_SHORTFALL"
    # 4 weeks of balances
    dates = pd.date_range("2025-01-06", periods=28, freq="D")  # 4 weeks: Jan 6-12, 13-19, 20-26, Jan 27-Feb 2
    bal_rows = []
    for d in dates:
        # Put shortfall in week 2 (e.g. Jan 15) and week 4 (e.g. Jan 30)
        is_sf = (d == pd.Timestamp("2025-01-15")) or (d == pd.Timestamp("2025-01-30"))
        bal_rows.append({"customer_id": cid, "date": d, "balance": 100.0 if is_sf else 1000.0, "shortfall": is_sf})
    bal = pd.DataFrame(bal_rows)
    tx = pd.DataFrame(columns=["customer_id", "date", "type", "amount", "category"])
    bi = pd.DataFrame(columns=["customer_id", "due_date", "amount", "paid_date", "on_time"])
    
    df = build_features(tx, bal, bi, cutoff_date="2025-02-02", customer_ids=[cid])
    cdf = df.sort_values("week").reset_index(drop=True)
    
    # Week 1: next week is Week 2 (which has shortfall) -> shortfall_next_week == 1
    assert cdf.loc[0, "shortfall_next_week"] == 1
    # Week 2: next week is Week 3 (which has no shortfall) -> shortfall_next_week == 0
    assert cdf.loc[1, "shortfall_next_week"] == 0
    # Week 3: next week is Week 4 (which has shortfall) -> shortfall_next_week == 1
    assert cdf.loc[2, "shortfall_next_week"] == 1
    # Week 4 (last week before cutoff): no future week known -> shortfall_next_week == 0
    assert cdf.loc[3, "shortfall_next_week"] == 0


def test_build_customer_features_helper():
    """Verify helper function builds features for a single customer from saved parquet data."""
    cids = get_customer_ids("train")
    cid = cids[0]
    
    df = build_customer_features(cid, cutoff_date="2025-09-30")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 40  # 40 weeks up to 2025-09-30
    assert (df["customer_id"] == cid).all()
    assert list(df.columns) == FEATURE_COLUMNS


def test_build_training_features_helper():
    """Verify helper function builds training features for sampled customers."""
    df = build_training_features(cutoff_date="2025-09-30", sample_size=10)
    assert isinstance(df, pd.DataFrame)
    assert df["customer_id"].nunique() == 10
    assert len(df) == 10 * 40
    assert list(df.columns) == FEATURE_COLUMNS
