"""
CreditPath Machine Learning Package (B3, B8, B12).

Provides cash flow forecaster, calibrated risk model, naive/logistic baselines,
and model store for artifact persistence.
"""
from __future__ import annotations

from app.ml.forecaster import CashFlowForecaster, NaiveForecaster, FORECASTER_FEATURES
from app.ml.risk_model import CalibratedRiskModel, LogisticRiskBaseline, RISK_FEATURES
from app.ml.model_store import (
    ModelStore,
    save_model,
    load_model,
    get_model_version,
    get_data_as_of,
)

__all__ = [
    "CashFlowForecaster",
    "NaiveForecaster",
    "FORECASTER_FEATURES",
    "CalibratedRiskModel",
    "LogisticRiskBaseline",
    "RISK_FEATURES",
    "ModelStore",
    "save_model",
    "load_model",
    "get_model_version",
    "get_data_as_of",
]
