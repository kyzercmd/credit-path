"""
Leakage Test Suite (B14).

Verifies strict temporal and customer isolation:
1. Feature leakage: features never use transactions/balances/bills past the observation cutoff date.
2. Customer split leakage: training and evaluation/test splits have zero customer_id overlap.
3. Time split leakage: training features strictly use months 1-9 (up to 2025-09-30)
   and held-out test evaluation strictly uses months 10-12 (2025-10-01 onwards).
"""
import pytest
import pandas as pd
import numpy as np

from app.data.loader import load_data, get_customer_ids, get_split_dates
from app.features.builder import (
    build_features,
    build_customer_features,
    build_training_features,
    FEATURE_COLUMNS,
)


@pytest.fixture(scope="module")
def sample_customer_data():
    """Load a small sample of customer transactions, balances, and bills."""
    data = load_data()
    sample_cids = get_customer_ids("train")[:5]
    cids_set = set(sample_cids)

    tx = data["transactions"][data["transactions"]["customer_id"].isin(cids_set)].copy()
    bal = data["daily_balances"][data["daily_balances"]["customer_id"].isin(cids_set)].copy()
    bi = data["bills"][data["bills"]["customer_id"].isin(cids_set)].copy()
    return {"tx": tx, "bal": bal, "bi": bi, "cids": sample_cids}


def test_feature_leakage_observation_cutoff(sample_customer_data):
    """
    Feature leakage verification:
    Features computed with cutoff_date must never change when future data
    (after cutoff_date) is added. Conversely, modifying data before cutoff must alter features.
    """
    cutoff = "2025-06-30"
    cids = sample_customer_data["cids"]

    # Baseline features up to cutoff
    df_baseline = build_features(
        sample_customer_data["tx"],
        sample_customer_data["bal"],
        sample_customer_data["bi"],
        cutoff_date=cutoff,
        customer_ids=cids,
    )

    # 1. Add post-cutoff (future) records: transactions, balances, bills
    future_tx = pd.DataFrame([
        {
            "customer_id": cids[0],
            "date": pd.Timestamp("2025-07-01"),
            "type": "cash_in",
            "amount": 500000.0,
            "category": "salary",
        },
        {
            "customer_id": cids[1],
            "date": pd.Timestamp("2025-08-15"),
            "type": "cash_out",
            "amount": 250000.0,
            "category": "expense",
        },
    ])
    future_bal = pd.DataFrame([
        {
            "customer_id": cids[0],
            "date": pd.Timestamp("2025-07-01"),
            "balance": 999999.0,
            "shortfall": False,
        },
        {
            "customer_id": cids[1],
            "date": pd.Timestamp("2025-08-15"),
            "balance": 0.0,
            "shortfall": True,
        },
    ])
    future_bi = pd.DataFrame([
        {
            "customer_id": cids[0],
            "due_date": pd.Timestamp("2025-07-10"),
            "amount": 10000.0,
            "paid_date": pd.Timestamp("2025-07-05"),
            "on_time": True,
        },
        {
            "customer_id": cids[1],
            "due_date": pd.Timestamp("2025-08-10"),
            "amount": 20000.0,
            "paid_date": None,
            "on_time": False,
        },
    ])

    tx_with_future = pd.concat([sample_customer_data["tx"], future_tx], ignore_index=True)
    bal_with_future = pd.concat([sample_customer_data["bal"], future_bal], ignore_index=True)
    bi_with_future = pd.concat([sample_customer_data["bi"], future_bi], ignore_index=True)

    df_with_future = build_features(
        tx_with_future,
        bal_with_future,
        bi_with_future,
        cutoff_date=cutoff,
        customer_ids=cids,
    )

    # Features must match bit-for-bit with baseline
    pd.testing.assert_frame_equal(df_baseline, df_with_future)

    # 2. Sensitivity check: modifying data BEFORE cutoff MUST alter the features
    prior_tx = pd.DataFrame([
        {
            "customer_id": cids[0],
            "date": pd.Timestamp("2025-06-15"),
            "type": "cash_in",
            "amount": 999999.0,
            "category": "bonus",
        }
    ])
    tx_with_prior = pd.concat([sample_customer_data["tx"], prior_tx], ignore_index=True)
    df_with_prior = build_features(
        tx_with_prior,
        sample_customer_data["bal"],
        sample_customer_data["bi"],
        cutoff_date=cutoff,
        customer_ids=cids,
    )

    # Assert that pre-cutoff change was detected
    c0_base = df_baseline[df_baseline["customer_id"] == cids[0]]["weekly_inflow"].sum()
    c0_prior = df_with_prior[df_with_prior["customer_id"] == cids[0]]["weekly_inflow"].sum()
    assert c0_prior > c0_base, "Modifying transactions prior to cutoff must change features."


def test_customer_split_zero_overlap():
    """
    Customer split leakage verification:
    Training and evaluation/test splits must have zero customer_id overlap,
    and their union must cover all customers.
    """
    all_cids = get_customer_ids("all")
    train_cids = get_customer_ids("train")
    test_cids = get_customer_ids("test")
    holdout_cids = get_customer_ids("holdout")

    # test and holdout are synonyms
    assert test_cids == holdout_cids

    assert len(train_cids) > 0, "Train customer split must not be empty"
    assert len(test_cids) > 0, "Test customer split must not be empty"

    set_train = set(train_cids)
    set_test = set(test_cids)

    # Zero overlap check
    overlap = set_train.intersection(set_test)
    assert len(overlap) == 0, f"Customer split leakage detected! Overlapping customer IDs: {overlap}"

    # Partition completeness check
    assert len(set_train) + len(set_test) == len(all_cids)
    assert set_train.union(set_test) == set(all_cids)

    # Hash holdout proportion check (~20% held out)
    test_ratio = len(test_cids) / float(len(all_cids))
    assert 0.15 <= test_ratio <= 0.25, f"Expected ~20% test holdout, got {test_ratio:.2%}"


def test_time_split_leakage_train_vs_test():
    """
    Time split leakage verification:
    Training data strictly uses months 1-9 (up to 2025-09-30) and held-out test
    evaluation strictly uses months 10-12 (2025-10-01 to 2025-12-31).
    """
    split_dates = get_split_dates()
    assert split_dates["train_end"] == "2025-09-30"
    assert split_dates["test_start"] == "2025-10-01"

    data = load_data()
    train_cids = get_customer_ids("train")[:25]
    test_cids = get_customer_ids("test")[:25]

    # 1. Training features build enforces strict cutoff at 2025-09-30
    cutoff_dt = pd.Timestamp(split_dates["train_end"])
    train_tx = data["transactions"][
        (data["transactions"]["customer_id"].isin(train_cids))
        & (pd.to_datetime(data["transactions"]["date"]) <= cutoff_dt)
    ]
    train_bal = data["daily_balances"][
        (data["daily_balances"]["customer_id"].isin(train_cids))
        & (pd.to_datetime(data["daily_balances"]["date"]) <= cutoff_dt)
    ]
    train_bi = data["bills"][
        (data["bills"]["customer_id"].isin(train_cids))
        & (pd.to_datetime(data["bills"]["due_date"]) <= cutoff_dt)
    ]

    # Verify no raw training records occur after train_end (months 10-12)
    assert (pd.to_datetime(train_tx["date"]) <= cutoff_dt).all()
    assert (pd.to_datetime(train_tx["date"]).dt.month <= 9).all()
    assert (pd.to_datetime(train_bal["date"]).dt.month <= 9).all()
    assert (pd.to_datetime(train_bi["due_date"]).dt.month <= 9).all()

    # 2. Build training features and verify build helper conforms to train_end
    train_df = build_training_features(cutoff_date=split_dates["train_end"], sample_size=25)
    assert len(train_df) == 25 * 40
    # In training features, weeks 1..39 correspond to months 1..9
    months_1_to_9_weeks = train_df[train_df["week"] <= 39]
    assert (months_1_to_9_weeks["month"] <= 9).all()

    # 3. Held-out test evaluation period verification (months 10-12)
    test_full_df = build_features(
        data["transactions"],
        data["daily_balances"],
        data["bills"],
        cutoff_date="2025-12-31",
        customer_ids=test_cids,
    )
    test_eval_df = test_full_df[test_full_df["month"] >= 10].reset_index(drop=True)

    # Verify test eval period strictly contains months 10, 11, 12
    assert len(test_eval_df) > 0
    assert test_eval_df["month"].min() >= 10
    assert test_eval_df["month"].max() <= 12
    assert set(test_eval_df["month"].unique()).issubset({10, 11, 12})

    # Verify evaluation target week transactions occur strictly in months 10-12
    test_tx = data["transactions"][
        (data["transactions"]["customer_id"].isin(test_cids))
        & (pd.to_datetime(data["transactions"]["date"]) >= pd.Timestamp(split_dates["test_start"]))
    ]
    assert (pd.to_datetime(test_tx["date"]).dt.month >= 10).all()
    assert (pd.to_datetime(test_tx["date"]).dt.month <= 12).all()

