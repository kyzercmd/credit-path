"""
Repayment Risk Check & Shortfall Predictor (B8).

Predicts probability of a wallet shortfall in the next period using a calibrated
LightGBM classifier. Includes a standard Logistic Regression baseline.
Protected attributes (gender, age, region, etc.) are strictly excluded.
"""
from __future__ import annotations

from typing import Sequence
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.features.builder import FORBIDDEN_COLUMNS

RISK_FEATURES = [
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
]


class LogisticRiskBaseline:
    """Standard Logistic Regression baseline predicting probability of shortfall next week."""

    def __init__(
        self,
        seed: int = 42,
        feature_names: Sequence[str] | None = None,
        max_iter: int = 1000,
    ) -> None:
        self.seed = seed
        self.feature_names = list(feature_names or RISK_FEATURES)
        self._validate_feature_names(self.feature_names)
        self.pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(random_state=seed, max_iter=max_iter)),
            ]
        )
        self.is_fitted = False

    @staticmethod
    def _validate_feature_names(features: list[str]) -> None:
        for feat in features:
            f_lower = feat.lower()
            if f_lower in FORBIDDEN_COLUMNS:
                raise ValueError(f"Forbidden protected column '{feat}' in baseline features.")
            for forbidden in FORBIDDEN_COLUMNS:
                if forbidden in f_lower:
                    raise ValueError(f"Feature '{feat}' contains forbidden attribute token '{forbidden}'.")

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LogisticRiskBaseline:
        """Fit the logistic regression baseline."""
        X_feats = X[self.feature_names]
        self.pipeline.fit(X_feats, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities of shape (N, 2): [P(no shortfall), P(shortfall)]."""
        if not self.is_fitted:
            raise RuntimeError("LogisticRiskBaseline must be fit before calling predict_proba.")
        X_feats = X[self.feature_names]
        return self.pipeline.predict_proba(X_feats)

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """Predict binary outcome."""
        probas = self.predict_proba(X)[:, 1]
        return (probas >= threshold).astype(int)


class CalibratedRiskModel:
    """
    Calibrated classifier predicting the probability of shortfall in the next period.

    Uses LightGBM with probability calibration (sigmoid / Platt scaling) via cross-validation.
    Provides feature importances to rank factors contributing to risk.
    """

    def __init__(
        self,
        seed: int = 42,
        feature_names: Sequence[str] | None = None,
        n_estimators: int = 50,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        cv: int = 3,
        method: str = "sigmoid",
        **kwargs,
    ) -> None:
        self.seed = seed
        self.feature_names = list(feature_names or RISK_FEATURES)
        self._validate_feature_names(self.feature_names)

        base_estimator = LGBMClassifier(
            random_state=seed,
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            verbose=-1,
            **kwargs,
        )
        self.model = CalibratedClassifierCV(
            estimator=base_estimator,
            method=method,
            cv=cv,
        )
        self.is_fitted = False

    @staticmethod
    def _validate_feature_names(features: list[str]) -> None:
        for feat in features:
            f_lower = feat.lower()
            if f_lower in FORBIDDEN_COLUMNS:
                raise ValueError(f"Forbidden protected column '{feat}' in risk model features.")
            for forbidden in FORBIDDEN_COLUMNS:
                if forbidden in f_lower:
                    raise ValueError(f"Feature '{feat}' contains forbidden attribute token '{forbidden}'.")

    def fit(self, X: pd.DataFrame, y: pd.Series) -> CalibratedRiskModel:
        """Fit the calibrated classifier."""
        X_feats = X[self.feature_names]
        self.model.fit(X_feats, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Return calibrated probabilities of shape (N, 2): [P(no shortfall), P(shortfall)].

        Guaranteed strictly within [0.0, 1.0].
        """
        if not self.is_fitted:
            raise RuntimeError("CalibratedRiskModel must be fit before calling predict_proba.")
        X_feats = X[self.feature_names]
        probas = self.model.predict_proba(X_feats)
        return np.clip(probas, 0.0, 1.0)

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """Return binary prediction with specified probability threshold."""
        probas = self.predict_proba(X)[:, 1]
        return (probas >= threshold).astype(int)

    def get_feature_importances(self) -> dict[str, float]:
        """
        Compute normalized feature importances averaged across calibrated estimators.

        Returns
        -------
        dict[str, float]
            Mapping of feature name to normalized importance weight, sorted descending.
        """
        if not self.is_fitted:
            raise RuntimeError("CalibratedRiskModel must be fit before getting feature importances.")

        # Extract underlying estimators from calibration folds
        raw_importances = np.mean(
            [c.estimator.feature_importances_ for c in self.model.calibrated_classifiers_],
            axis=0,
        )

        total = np.sum(raw_importances)
        if total > 0:
            norm_importances = raw_importances / total
        else:
            norm_importances = np.ones_like(raw_importances) / len(raw_importances)

        importance_dict = {
            feat: round(float(imp), 4)
            for feat, imp in zip(self.feature_names, norm_importances)
        }

        return dict(
            sorted(
                importance_dict.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )
