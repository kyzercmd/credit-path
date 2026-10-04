"""
CreditPath Feature Engineering Engine (B2).

Builds leakage-safe rolling, lag, and calendar features from transactions,
daily balances, and bills. Explicit cutoff dates ensure zero future leakage.
Protected attributes (gender, religion, region, age) and latent traits are
strictly excluded from model inputs.
"""
from __future__ import annotations

import datetime
from typing import Sequence
import numpy as np
import pandas as pd

from app.data.loader import load_data, get_customer_ids

FEATURE_COLUMNS = [
    "customer_id",
    "week",
    "weekly_inflow",
    "weekly_outflow",
    "balance_mean",
    "balance_min",
    "income_regularity_ratio",
    "bill_on_time_ratio",
    "months_active",
    "lag_1_inflow",
    "lag_2_inflow",
    "lag_3_inflow",
    "lag_4_inflow",
    "lag_1_outflow",
    "lag_2_outflow",
    "lag_1_balance",
    "week_of_month",
    "month",
    "is_month_end",
    "is_eid_period",
    "is_harvest_period",
    "day_of_week_mode",
    "shortfall_next_week",
]

# Protected or latent columns that must never leak into features
FORBIDDEN_COLUMNS = {
    "gender", "region_type", "region", "age_band", "age",
    "religion", "persona", "income_stability", "shock_exposure", "bill_discipline"
}


def build_features(
    transactions: pd.DataFrame,
    balances: pd.DataFrame,
    bills: pd.DataFrame,
    cutoff_date: str | datetime.date | datetime.datetime | pd.Timestamp,
    customer_ids: Sequence[str] | None = None,
) -> pd.DataFrame:
    """
    Build weekly feature matrix up to cutoff_date with strict leakage prevention.

    Parameters
    ----------
    transactions : pd.DataFrame
        Customer transactions with columns: customer_id, date, type, amount.
    balances : pd.DataFrame
        Customer daily balances with columns: customer_id, date, balance, shortfall.
    bills : pd.DataFrame
        Customer bills with columns: customer_id, due_date, amount, paid_date, on_time.
    cutoff_date : str | datetime | pd.Timestamp
        Strict cutoff date. All records after this date are discarded.
    customer_ids : Sequence[str] | None
        Optional list of customer IDs to include. If None, uses all unique customers.

    Returns
    -------
    pd.DataFrame
        DataFrame with rows indexed by (customer_id, week) and exactly FEATURE_COLUMNS.
    """
    cutoff_dt = pd.to_datetime(cutoff_date)

    # 1. Enforce strict cutoff date filtering upfront
    tx = transactions[pd.to_datetime(transactions["date"]) <= cutoff_dt].copy() if len(transactions) > 0 else transactions.copy()
    bal = balances[pd.to_datetime(balances["date"]) <= cutoff_dt].copy() if len(balances) > 0 else balances.copy()
    bi = bills[pd.to_datetime(bills["due_date"]) <= cutoff_dt].copy() if len(bills) > 0 else bills.copy()

    # 2. Filter customer IDs if requested
    if customer_ids is not None:
        cids_set = set(customer_ids)
        if len(tx) > 0:
            tx = tx[tx["customer_id"].isin(cids_set)]
        if len(bal) > 0:
            bal = bal[bal["customer_id"].isin(cids_set)]
        if len(bi) > 0:
            bi = bi[bi["customer_id"].isin(cids_set)]
        unique_cids = list(customer_ids)
    else:
        found_cids = set()
        if len(bal) > 0:
            found_cids.update(bal["customer_id"].dropna().unique())
        if len(tx) > 0:
            found_cids.update(tx["customer_id"].dropna().unique())
        if len(bi) > 0:
            found_cids.update(bi["customer_id"].dropna().unique())
        unique_cids = sorted(list(found_cids))

    # Empty edge case
    if not unique_cids:
        empty_df = pd.DataFrame(columns=FEATURE_COLUMNS)
        return _format_feature_dtypes(empty_df)

    # 3. Determine weekly windows (Monday-to-Sunday periods)
    all_dates = []
    if len(bal) > 0:
        all_dates.append(pd.to_datetime(bal["date"]))
    if len(tx) > 0:
        all_dates.append(pd.to_datetime(tx["date"]))
    if len(bi) > 0:
        all_dates.append(pd.to_datetime(bi["due_date"]))

    if not all_dates:
        # Default single week if no dates available
        periods = [cutoff_dt.to_period("W-SUN")]
    else:
        combined_dates = pd.concat(all_dates)
        min_date = combined_dates.min()
        max_date = min(combined_dates.max(), cutoff_dt)
        periods = sorted(pd.date_range(min_date, max_date, freq="D").to_period("W-SUN").unique())

    if not periods:
        periods = [cutoff_dt.to_period("W-SUN")]

    p_to_week = {p: i + 1 for i, p in enumerate(periods)}
    n_weeks = len(periods)

    # 4. Create base grid of (customer_id, week)
    idx = pd.MultiIndex.from_product([unique_cids, range(1, n_weeks + 1)], names=["customer_id", "week"])
    df = pd.DataFrame(index=idx).reset_index()

    # 5. Calendar features
    cal_rows = []
    for p in periods:
        w = p_to_week[p]
        # Midpoint of the week (Thursday) represents the calendar context
        thu = p.start_time + pd.Timedelta(days=3)
        month = thu.month
        wom = (thu.day - 1) // 7 + 1
        is_me = int(thu.day >= 25)
        is_eid = int(month in [4, 11])
        is_har = int(month in [3, 9])
        cal_rows.append({
            "week": w,
            "week_of_month": wom,
            "month": month,
            "is_month_end": is_me,
            "is_eid_period": is_eid,
            "is_harvest_period": is_har,
        })
    df_cal = pd.DataFrame(cal_rows)
    df = df.merge(df_cal, on="week", how="left")

    # 6. Transactions aggregations
    if len(tx) > 0:
        tx_dt = pd.to_datetime(tx["date"])
        tx["week_period"] = tx_dt.dt.to_period("W-SUN")
        tx["week"] = tx["week_period"].map(p_to_week)
        tx_valid = tx[tx["week"].notna()].copy()
        tx_valid["week"] = tx_valid["week"].astype(int)

        tx_valid["inflow"] = np.where(tx_valid["type"].isin(["cash_in", "p2p_in"]), tx_valid["amount"], 0.0)
        tx_valid["outflow"] = np.where(tx_valid["type"].isin(["cash_out", "merchant_payment", "bill_payment"]), tx_valid["amount"], 0.0)
        tx_valid["dow"] = pd.to_datetime(tx_valid["date"]).dt.weekday

        tx_agg = tx_valid.groupby(["customer_id", "week"], as_index=False).agg(
            weekly_inflow=("inflow", "sum"),
            weekly_outflow=("outflow", "sum")
        )

        dow_counts = tx_valid.groupby(["customer_id", "week", "dow"]).size().reset_index(name="n")
        dow_counts = dow_counts.sort_values(["customer_id", "week", "n"], ascending=[True, True, False])
        dow_mode = dow_counts.drop_duplicates(["customer_id", "week"])[["customer_id", "week", "dow"]].rename(columns={"dow": "day_of_week_mode"})

        tx_valid["month_period"] = pd.to_datetime(tx_valid["date"]).dt.to_period("M")
        first_tx_month = tx_valid.groupby(["customer_id", "month_period"])["week"].min().reset_index()
        first_tx_month["is_new_month"] = 1
    else:
        tx_agg = pd.DataFrame(columns=["customer_id", "week", "weekly_inflow", "weekly_outflow"])
        dow_mode = pd.DataFrame(columns=["customer_id", "week", "day_of_week_mode"])
        first_tx_month = pd.DataFrame(columns=["customer_id", "week", "is_new_month"])

    # Merge transactions aggregations
    df = df.merge(tx_agg, on=["customer_id", "week"], how="left")
    df["weekly_inflow"] = df["weekly_inflow"].fillna(0.0)
    df["weekly_outflow"] = df["weekly_outflow"].fillna(0.0)

    df = df.merge(dow_mode, on=["customer_id", "week"], how="left")
    df["day_of_week_mode"] = df.groupby("customer_id", sort=False)["day_of_week_mode"].ffill().bfill().fillna(4).astype(int)

    # 7. Balances aggregations
    if len(bal) > 0:
        bal_dt = pd.to_datetime(bal["date"])
        bal["week_period"] = bal_dt.dt.to_period("W-SUN")
        bal["week"] = bal["week_period"].map(p_to_week)
        bal_valid = bal[bal["week"].notna()].copy()
        bal_valid["week"] = bal_valid["week"].astype(int)

        bal_agg = bal_valid.groupby(["customer_id", "week"], as_index=False).agg(
            balance_mean=("balance", "mean"),
            balance_min=("balance", "min"),
            has_shortfall=("shortfall", "any")
        )
    else:
        bal_agg = pd.DataFrame(columns=["customer_id", "week", "balance_mean", "balance_min", "has_shortfall"])

    df = df.merge(bal_agg, on=["customer_id", "week"], how="left")
    df["balance_mean"] = df.groupby("customer_id", sort=False)["balance_mean"].ffill().bfill().fillna(0.0)
    df["balance_min"] = df.groupby("customer_id", sort=False)["balance_min"].ffill().bfill().fillna(0.0)
    df["has_shortfall"] = df["has_shortfall"].fillna(False).astype(bool)

    # Risk modeling label: shortfall in subsequent week (0 for the last week before cutoff)
    df["shortfall_next_week"] = df.groupby("customer_id", sort=False)["has_shortfall"].shift(-1).fillna(False).astype(int)
    df = df.drop(columns=["has_shortfall"])

    # 8. Lag features
    df["lag_1_inflow"] = df.groupby("customer_id", sort=False)["weekly_inflow"].shift(1).fillna(0.0)
    df["lag_2_inflow"] = df.groupby("customer_id", sort=False)["weekly_inflow"].shift(2).fillna(0.0)
    df["lag_3_inflow"] = df.groupby("customer_id", sort=False)["weekly_inflow"].shift(3).fillna(0.0)
    df["lag_4_inflow"] = df.groupby("customer_id", sort=False)["weekly_inflow"].shift(4).fillna(0.0)
    df["lag_1_outflow"] = df.groupby("customer_id", sort=False)["weekly_outflow"].shift(1).fillna(0.0)
    df["lag_2_outflow"] = df.groupby("customer_id", sort=False)["weekly_outflow"].shift(2).fillna(0.0)
    df["lag_1_balance"] = df.groupby("customer_id", sort=False)["balance_mean"].shift(1).fillna(0.0)

    # 9. Income regularity ratio (rolling 12-week proportion with inflow > 0)
    df["has_income"] = (df["weekly_inflow"] > 0).astype(float)
    df["income_regularity_ratio"] = df.groupby("customer_id", sort=False)["has_income"].rolling(12, min_periods=1).mean().to_numpy()
    df = df.drop(columns=["has_income"])

    # 10. Months active (distinct calendar months with transactions up to week)
    df = df.merge(first_tx_month[["customer_id", "week", "is_new_month"]], on=["customer_id", "week"], how="left")
    df["is_new_month"] = pd.to_numeric(df["is_new_month"], errors="coerce").fillna(0).astype(int)
    df["months_active"] = df.groupby("customer_id", sort=False)["is_new_month"].cumsum().astype(int)
    df = df.drop(columns=["is_new_month"])

    # 11. Bills on-time ratio (cumulative ratio of on-time bills among bills due up to week)
    if len(bi) > 0:
        bi_dt = pd.to_datetime(bi["due_date"])
        bi["week_period"] = bi_dt.dt.to_period("W-SUN")
        bi["week"] = bi["week_period"].map(p_to_week)
        bi_valid = bi[bi["week"].notna()].copy()
        bi_valid["week"] = bi_valid["week"].astype(int)

        bi_valid["on_time_int"] = bi_valid["on_time"].astype(int)
        bi_agg = bi_valid.groupby(["customer_id", "week"], as_index=False).agg(
            bills_due_count=("on_time_int", "count"),
            bills_ontime_count=("on_time_int", "sum")
        )
    else:
        bi_agg = pd.DataFrame(columns=["customer_id", "week", "bills_due_count", "bills_ontime_count"])

    df = df.merge(bi_agg, on=["customer_id", "week"], how="left")
    df["bills_due_count"] = pd.to_numeric(df["bills_due_count"], errors="coerce").fillna(0).astype(int)
    df["bills_ontime_count"] = pd.to_numeric(df["bills_ontime_count"], errors="coerce").fillna(0).astype(int)
    cum_due = df.groupby("customer_id", sort=False)["bills_due_count"].cumsum()
    cum_ontime = df.groupby("customer_id", sort=False)["bills_ontime_count"].cumsum()
    df["bill_on_time_ratio"] = np.where(cum_due > 0, cum_ontime / cum_due, 1.0)
    df = df.drop(columns=["bills_due_count", "bills_ontime_count"])

    # Safety check: ensure forbidden columns are never in the result
    for col in FORBIDDEN_COLUMNS:
        if col in df.columns:
            df = df.drop(columns=[col])

    return _format_feature_dtypes(df[FEATURE_COLUMNS])


def _format_feature_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Format and ensure strict dtypes and zero NaNs across all feature columns."""
    df = df.copy()

    float_cols = [
        "weekly_inflow", "weekly_outflow", "balance_mean", "balance_min",
        "income_regularity_ratio", "bill_on_time_ratio", "lag_1_inflow",
        "lag_2_inflow", "lag_3_inflow", "lag_4_inflow", "lag_1_outflow",
        "lag_2_outflow", "lag_1_balance",
    ]
    for fc in float_cols:
        if fc in df.columns:
            df[fc] = df[fc].fillna(0.0).astype(float)

    int_cols = [
        "week", "months_active", "week_of_month", "month",
        "is_month_end", "is_eid_period", "is_harvest_period",
        "day_of_week_mode", "shortfall_next_week",
    ]
    for ic in int_cols:
        if ic in df.columns:
            df[ic] = df[ic].fillna(0).astype(int)

    if "customer_id" in df.columns:
        df["customer_id"] = df["customer_id"].astype(str)

    return df


def build_customer_features(
    customer_id: str,
    cutoff_date: str | datetime.date | datetime.datetime | pd.Timestamp = "2025-12-31",
) -> pd.DataFrame:
    """
    Build weekly feature matrix for a single customer from saved parquet data.

    Parameters
    ----------
    customer_id : str
        Customer identifier.
    cutoff_date : str | datetime | pd.Timestamp
        Cutoff date for features (default: '2025-12-31').

    Returns
    -------
    pd.DataFrame
        DataFrame of weekly features for the specified customer.
    """
    data = load_data()
    return build_features(
        data["transactions"],
        data["daily_balances"],
        data["bills"],
        cutoff_date=cutoff_date,
        customer_ids=[customer_id],
    )


def build_training_features(
    cutoff_date: str | datetime.date | datetime.datetime | pd.Timestamp = "2025-09-30",
    sample_size: int | None = None,
) -> pd.DataFrame:
    """
    Build training features across training customers up to split cutoff date.

    Parameters
    ----------
    cutoff_date : str | datetime | pd.Timestamp
        Training cutoff date (default: '2025-09-30' matching train/test split).
    sample_size : int | None
        Optional number of customers to sample from the training split.

    Returns
    -------
    pd.DataFrame
        DataFrame of training features across sampled training customers.
    """
    data = load_data()
    train_cids = get_customer_ids("train")
    if sample_size is not None:
        train_cids = train_cids[:sample_size]

    return build_features(
        data["transactions"],
        data["daily_balances"],
        data["bills"],
        cutoff_date=cutoff_date,
        customer_ids=train_cids,
    )
