"""
Determinism Test Suite (B14).

Verifies strict reproducibility across:
1. Synthetic Data Generation: Same seed produces identical DataFrames across all tables.
2. Machine Learning Models: Same seed produces identical predictions to floating point tolerance.
3. API Endpoints: Same seed/data produces bit-for-bit identical JSON responses for
   status, safe-range, loan-check, calendar, and path endpoints.
"""
import pytest
import numpy as np
import pandas as pd
from starlette.testclient import TestClient

from app.main import app
from app.data.generator import generate_dataset
from app.ml.forecaster import CashFlowForecaster
from app.ml.risk_model import CalibratedRiskModel
from app.features.builder import build_training_features, build_features
from app.data.loader import load_data, get_customer_ids
from app.engines.ready import ReadyEngine
from app.config import get_config


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def ready_and_not_yet_cids() -> tuple[str, str]:
    """Find one Ready and one Not yet customer for testing."""
    cids = get_customer_ids("all")
    engine = ReadyEngine(config=get_config())
    data = load_data()

    ready_id = None
    not_yet_id = None

    for cid in cids[:50]:
        res = engine.evaluate(cid, data=data)
        if res.ready and ready_id is None:
            ready_id = cid
        elif not res.ready and not_yet_id is None:
            not_yet_id = cid
        if ready_id and not_yet_id:
            break

    assert ready_id is not None, "Could not find a Ready customer in test slice"
    assert not_yet_id is not None, "Could not find a Not yet customer in test slice"
    return ready_id, not_yet_id


def test_data_generator_determinism():
    """Same seed generates bit-for-bit identical DataFrames across all 5 tables."""
    data_a = generate_dataset(seed=42, n_customers=100)
    data_b = generate_dataset(seed=42, n_customers=100)

    for table in ["customers", "transactions", "daily_balances", "bills", "customer_attributes"]:
        assert table in data_a
        assert table in data_b
        pd.testing.assert_frame_equal(data_a[table], data_b[table])

    # Distinct seed produces differing data
    data_c = generate_dataset(seed=43, n_customers=100)
    assert not np.array_equal(
        data_a["customers"]["income_stability"].values,
        data_c["customers"]["income_stability"].values,
    )


def test_model_prediction_determinism():
    """Same seed produces identical model predictions to floating point tolerance."""
    train_df = build_training_features(cutoff_date="2025-09-30", sample_size=30)
    
    data = load_data()
    test_cids = get_customer_ids("test")[:15]
    test_df = build_features(
        data["transactions"],
        data["daily_balances"],
        data["bills"],
        cutoff_date="2025-12-31",
        customer_ids=test_cids,
    )
    test_eval = test_df[test_df["month"] >= 10].reset_index(drop=True)

    # 1. CashFlowForecaster determinism
    forecaster_1 = CashFlowForecaster(seed=42, n_estimators=25, max_depth=3)
    forecaster_1.fit(train_df, train_df["weekly_inflow"], train_df["weekly_outflow"])
    preds_1 = forecaster_1.predict(test_eval)

    forecaster_2 = CashFlowForecaster(seed=42, n_estimators=25, max_depth=3)
    forecaster_2.fit(train_df, train_df["weekly_inflow"], train_df["weekly_outflow"])
    preds_2 = forecaster_2.predict(test_eval)

    np.testing.assert_allclose(
        preds_1["predicted_inflow"].to_numpy(),
        preds_2["predicted_inflow"].to_numpy(),
        rtol=1e-5,
        atol=1e-5,
    )
    np.testing.assert_allclose(
        preds_1["predicted_outflow"].to_numpy(),
        preds_2["predicted_outflow"].to_numpy(),
        rtol=1e-5,
        atol=1e-5,
    )

    # 2. CalibratedRiskModel determinism
    risk_1 = CalibratedRiskModel(seed=42, n_estimators=25, max_depth=3, cv=3)
    risk_1.fit(train_df, train_df["shortfall_next_week"])
    probas_1 = risk_1.predict_proba(test_eval)

    risk_2 = CalibratedRiskModel(seed=42, n_estimators=25, max_depth=3, cv=3)
    risk_2.fit(train_df, train_df["shortfall_next_week"])
    probas_2 = risk_2.predict_proba(test_eval)

    np.testing.assert_allclose(probas_1, probas_2, rtol=1e-5, atol=1e-5)


def test_api_responses_determinism(client: TestClient, ready_and_not_yet_cids: tuple[str, str]):
    """
    Same API requests on identical state produce bit-for-bit identical JSON responses
    across status, safe-range, loan-check, calendar, and path endpoints.
    """
    ready_id, not_yet_id = ready_and_not_yet_cids

    endpoints = [
        ("GET", f"/customer/{ready_id}/status", None),
        ("GET", f"/customer/{ready_id}/safe-range", None),
        ("POST", f"/customer/{ready_id}/loan-check", {"amount": 2500.0, "tenor_months": 6}),
        ("GET", f"/customer/{ready_id}/calendar", None),
        ("GET", f"/customer/{not_yet_id}/path", None),
        ("GET", f"/customer/{ready_id}/progress", None),
    ]

    for method, url, payload in endpoints:
        # First call
        if method == "GET":
            res_1 = client.get(url)
            res_2 = client.get(url)
        else:
            res_1 = client.post(url, json=payload)
            res_2 = client.post(url, json=payload)

        assert res_1.status_code == 200, f"{url} returned status {res_1.status_code}"
        assert res_2.status_code == 200, f"{url} returned status {res_2.status_code}"

        json_1 = res_1.json()
        json_2 = res_2.json()

        assert json_1 == json_2, f"Non-deterministic response detected for {url}:\n{json_1}\nvs\n{json_2}"
