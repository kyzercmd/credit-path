"""
Weekly Cash-Flow Forecaster (B3).

Predicts weekly inflow and outflow using LightGBM regressors trained on
leakage-free lag and calendar features. Protected attributes (gender, age, region, etc.)
are strictly excluded. Includes a Naive baseline and multi-week roll-forward forecasting.
"""
from __future__ import annotations

import datetime
from typing import Sequence
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from app.features.builder import FORBIDDEN_COLUMNS

FORECASTER_FEATURES = [
    "lag_1_inflow",
    "lag_2_inflow",
    "lag_3_inflow",
    "lag_4_inflow",
    "lag_1_outflow",
    "lag_2_outflow",
    "lag_3_outflow",
    "lag_4_outflow",
    "inflow_roll_mean_4",
    "inflow_roll_std_4",
    "outflow_roll_mean_4",
    "outflow_roll_std_4",
    "lag_1_balance",
    "balance_mean",
    "balance_min",
    "income_regularity_ratio",
    "day_of_week_mode",
    "day_of_month",
    "week_of_month",
    "month",
    "is_month_end",
    "is_eid_period",
    "is_harvest_period",
]


class SeasonalNaiveForecaster:
    """
    Seasonal naive baseline forecaster (same period in previous monthly cycle, ~4 weeks ago).
    """

    def __init__(self, seasonal_lag: int = 4) -> None:
        self.seasonal_lag = seasonal_lag
        self.is_fitted = True

    def fit(
        self,
        X: pd.DataFrame | None = None,
        y_inflow: pd.Series | None = None,
        y_outflow: pd.Series | None = None,
    ) -> SeasonalNaiveForecaster:
        """Fit method for compatibility with estimator interface."""
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """Predict next week inflow and outflow from the seasonal cycle (4 weeks prior)."""
        col_in = f"lag_{self.seasonal_lag}_inflow"
        col_out = f"lag_{self.seasonal_lag}_outflow"

        if col_in in X.columns:
            inflow = X[col_in].fillna(0.0).to_numpy()
        elif "lag_1_inflow" in X.columns:
            inflow = X["lag_1_inflow"].fillna(0.0).to_numpy()
        elif "weekly_inflow" in X.columns:
            inflow = X["weekly_inflow"].fillna(0.0).to_numpy()
        else:
            inflow = np.zeros(len(X))

        if col_out in X.columns:
            outflow = X[col_out].fillna(0.0).to_numpy()
        elif "lag_1_outflow" in X.columns:
            outflow = X["lag_1_outflow"].fillna(0.0).to_numpy()
        elif "weekly_outflow" in X.columns:
            outflow = X["weekly_outflow"].fillna(0.0).to_numpy()
        else:
            outflow = np.zeros(len(X))

        return pd.DataFrame(
            {
                "predicted_inflow": np.clip(inflow, 0.0, None),
                "predicted_outflow": np.clip(outflow, 0.0, None),
            },
            index=X.index,
        )


class NaiveForecaster:
    """
    Naive baseline forecaster.

    Predicts next week's inflow and outflow as the last week's actual
    values (lag_1_inflow / lag_1_outflow, or weekly_inflow / weekly_outflow).
    """

    def __init__(self) -> None:
        self.is_fitted = True

    def fit(
        self,
        X: pd.DataFrame | None = None,
        y_inflow: pd.Series | None = None,
        y_outflow: pd.Series | None = None,
    ) -> NaiveForecaster:
        """Fit method for compatibility with estimator interface."""
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """Predict next week inflow and outflow from the most recent known values."""
        if "lag_1_inflow" in X.columns:
            inflow = X["lag_1_inflow"].fillna(0.0).to_numpy()
        elif "weekly_inflow" in X.columns:
            inflow = X["weekly_inflow"].fillna(0.0).to_numpy()
        else:
            inflow = np.zeros(len(X))

        if "lag_1_outflow" in X.columns:
            outflow = X["lag_1_outflow"].fillna(0.0).to_numpy()
        elif "weekly_outflow" in X.columns:
            outflow = X["weekly_outflow"].fillna(0.0).to_numpy()
        else:
            outflow = np.zeros(len(X))

        return pd.DataFrame(
            {
                "predicted_inflow": np.clip(inflow, 0.0, None),
                "predicted_outflow": np.clip(outflow, 0.0, None),
            },
            index=X.index,
        )


class CashFlowForecaster:
    """
    LightGBM cash-flow forecaster predicting weekly inflow and outflow.

    Strictly excludes all protected demographic attributes.
    """

    def __init__(
        self,
        seed: int = 42,
        feature_names: Sequence[str] | None = None,
        n_estimators: int = 100,
        max_depth: int = 5,
        learning_rate: float = 0.05,
        **kwargs,
    ) -> None:
        self.seed = seed
        self.feature_names = list(feature_names or FORECASTER_FEATURES)
        self._validate_feature_names(self.feature_names)

        self.inflow_model = LGBMRegressor(
            random_state=seed,
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            verbose=-1,
            **kwargs,
        )
        self.outflow_model = LGBMRegressor(
            random_state=seed,
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            verbose=-1,
            **kwargs,
        )
        self.is_fitted = False

    @staticmethod
    def _validate_feature_names(features: list[str]) -> None:
        """Verify no protected or forbidden attributes are among model inputs."""
        for feat in features:
            f_lower = feat.lower()
            if f_lower in FORBIDDEN_COLUMNS:
                raise ValueError(f"Forbidden protected column '{feat}' in forecaster features.")
            for forbidden in FORBIDDEN_COLUMNS:
                if forbidden in f_lower:
                    raise ValueError(f"Feature '{feat}' contains forbidden attribute token '{forbidden}'.")

    def fit(
        self,
        X: pd.DataFrame,
        y_inflow: pd.Series,
        y_outflow: pd.Series,
    ) -> CashFlowForecaster:
        """
        Fit inflow and outflow models on training feature matrix and targets.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix containing self.feature_names.
        y_inflow : pd.Series
            Actual weekly inflow amounts.
        y_outflow : pd.Series
            Actual weekly outflow amounts.
        """
        X_feats = X[self.feature_names]
        self.inflow_model.fit(X_feats, y_inflow)
        self.outflow_model.fit(X_feats, y_outflow)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Predict weekly inflow and outflow for provided feature rows.

        Outputs are guaranteed non-negative.
        """
        if not self.is_fitted:
            raise RuntimeError("CashFlowForecaster must be fit before calling predict.")

        X_feats = X[self.feature_names]
        pred_inflow = np.clip(self.inflow_model.predict(X_feats), 0.0, None)
        pred_outflow = np.clip(self.outflow_model.predict(X_feats), 0.0, None)

        return pd.DataFrame(
            {
                "predicted_inflow": pred_inflow,
                "predicted_outflow": pred_outflow,
            },
            index=X.index,
        )

    def predict_future_weeks(
        self,
        customer_features: pd.DataFrame,
        weeks: int = 8,
        base_date: str | datetime.date | datetime.datetime | pd.Timestamp = "2025-12-31",
    ) -> pd.DataFrame:
        """
        Generate multi-week rolling projections into future weeks.

        Iteratively rolls forward lag features, updates calendar features based
        on projected future dates, and updates the expected wallet balance.

        Parameters
        ----------
        customer_features : pd.DataFrame
            Historical weekly features for a customer up to the latest known week.
        weeks : int
            Number of future weeks to project (default: 8).
        base_date : str | date | datetime | pd.Timestamp
            Cutoff date representing the end of historical data (default: "2025-12-31").

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: week_index, predicted_inflow, predicted_outflow, expected_balance.
        """
        if customer_features.empty:
            raise ValueError("customer_features cannot be empty for future forecasting.")

        if "week" in customer_features.columns:
            sorted_feats = customer_features.sort_values("week")
        else:
            sorted_feats = customer_features

        last_row = sorted_feats.iloc[-1]

        # Initialize rolling state from customer's latest known metrics
        curr_bal = float(last_row.get("balance_mean", 0.0))
        curr_min_bal = float(last_row.get("balance_min", curr_bal))
        curr_reg = float(last_row.get("income_regularity_ratio", 1.0))
        curr_dow = int(last_row.get("day_of_week_mode", 4))

        lag_1_in = float(last_row.get("weekly_inflow", last_row.get("lag_1_inflow", 0.0)))
        lag_2_in = float(last_row.get("lag_1_inflow", 0.0))
        lag_3_in = float(last_row.get("lag_2_inflow", 0.0))
        lag_4_in = float(last_row.get("lag_3_inflow", 0.0))

        lag_1_out = float(last_row.get("weekly_outflow", last_row.get("lag_1_outflow", 0.0)))
        lag_2_out = float(last_row.get("lag_1_outflow", 0.0))
        lag_3_out = float(last_row.get("lag_2_outflow", 0.0))
        lag_4_out = float(last_row.get("lag_3_outflow", 0.0))
        lag_1_bal = curr_bal

        base_dt = pd.to_datetime(base_date)

        results = []
        for w in range(1, weeks + 1):
            # Calendar context for future week midpoint (Thursday)
            midpoint = base_dt + pd.Timedelta(days=7 * (w - 1) + 4)
            month = midpoint.month
            wom = (midpoint.day - 1) // 7 + 1
            is_me = int(midpoint.day >= 25)
            is_eid = int(month in [4, 11])
            is_har = int(month in [3, 9])
            day_of_month = midpoint.day

            in_lags = [lag_1_in, lag_2_in, lag_3_in, lag_4_in]
            out_lags = [lag_1_out, lag_2_out, lag_3_out, lag_4_out]

            step_dict = {
                "lag_1_inflow": lag_1_in,
                "lag_2_inflow": lag_2_in,
                "lag_3_inflow": lag_3_in,
                "lag_4_inflow": lag_4_in,
                "lag_1_outflow": lag_1_out,
                "lag_2_outflow": lag_2_out,
                "lag_3_outflow": lag_3_out,
                "lag_4_outflow": lag_4_out,
                "inflow_roll_mean_4": float(np.mean(in_lags)),
                "inflow_roll_std_4": float(np.std(in_lags)),
                "outflow_roll_mean_4": float(np.mean(out_lags)),
                "outflow_roll_std_4": float(np.std(out_lags)),
                "lag_1_balance": lag_1_bal,
                "balance_mean": curr_bal,
                "balance_min": curr_min_bal,
                "income_regularity_ratio": curr_reg,
                "day_of_week_mode": curr_dow,
                "day_of_month": day_of_month,
                "week_of_month": wom,
                "month": month,
                "is_month_end": is_me,
                "is_eid_period": is_eid,
                "is_harvest_period": is_har,
            }

            step_df = pd.DataFrame([step_dict])
            pred_step = self.predict(step_df)
            pred_in = float(pred_step["predicted_inflow"].iloc[0])
            pred_out = float(pred_step["predicted_outflow"].iloc[0])

            # Update expected wallet balance (cannot drop below zero)
            curr_bal = max(0.0, curr_bal + pred_in - pred_out)
            curr_min_bal = min(curr_min_bal, curr_bal)

            # Roll lags forward
            lag_4_in = lag_3_in
            lag_3_in = lag_2_in
            lag_2_in = lag_1_in
            lag_1_in = pred_in

            lag_4_out = lag_3_out
            lag_3_out = lag_2_out
            lag_2_out = lag_1_out
            lag_1_out = pred_out

            lag_1_bal = curr_bal
            curr_reg = (curr_reg * 11.0 + (1.0 if pred_in > 0 else 0.0)) / 12.0

            results.append(
                {
                    "week_index": w,
                    "predicted_inflow": round(pred_in, 2),
                    "predicted_outflow": round(pred_out, 2),
                    "expected_balance": round(curr_bal, 2),
                }
            )

        return pd.DataFrame(results)
