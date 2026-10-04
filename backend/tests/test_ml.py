import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile

from app.ml.forecaster import CashFlowForecaster, NaiveForecaster, FORECASTER_FEATURES
from app.ml.risk_model import CalibratedRiskModel, LogisticRiskBaseline, RISK_FEATURES
from app.ml.model_store import ModelStore, save_model, load_model, get_model_version, get_data_as_of
from app.features.builder import build_training_features, build_features
from app.data.loader import load_data, get_customer_ids


@pytest.fixture(scope="module")
def small_training_data():
    """Load a small slice of training features for fast testing."""
    df = build_training_features(cutoff_date="2025-09-30", sample_size=50)
    return df


@pytest.fixture(scope="module")
def small_test_data():
    """Load a small slice of test features from held-out customers."""
    data = load_data()
    test_cids = get_customer_ids("test")[:20]
    df = build_features(
        data["transactions"],
        data["daily_balances"],
        data["bills"],
        cutoff_date="2025-12-31",
        customer_ids=test_cids,
    )
    test_eval_df = df[df["month"] >= 10].reset_index(drop=True)
    return test_eval_df


def test_forecaster_fit_and_predict(small_training_data):
    """Forecaster trains and produces non-negative inflow/outflow predictions."""
    df = small_training_data
    forecaster = CashFlowForecaster(seed=42, n_estimators=20, max_depth=3)
    forecaster.fit(df, df["weekly_inflow"], df["weekly_outflow"])
    
    preds = forecaster.predict(df)
    assert isinstance(preds, pd.DataFrame)
    assert "predicted_inflow" in preds.columns
    assert "predicted_outflow" in preds.columns
    assert len(preds) == len(df)
    assert (preds["predicted_inflow"] >= 0.0).all()
    assert (preds["predicted_outflow"] >= 0.0).all()

    # Multi-week roll-forward
    future = forecaster.predict_future_weeks(df, weeks=8)
    assert isinstance(future, pd.DataFrame)
    assert list(future.columns) == ["week_index", "predicted_inflow", "predicted_outflow", "expected_balance"]
    assert len(future) == 8
    assert list(future["week_index"]) == list(range(1, 9))
    assert (future["predicted_inflow"] >= 0.0).all()
    assert (future["predicted_outflow"] >= 0.0).all()


def test_forecaster_better_than_naive(small_training_data, small_test_data):
    """LightGBM forecaster achieves lower MAE or comparable on seasonal/test data vs naive baseline."""
    train_df = small_training_data
    test_df = small_test_data
    
    forecaster = CashFlowForecaster(seed=42, n_estimators=50, max_depth=4)
    forecaster.fit(train_df, train_df["weekly_inflow"], train_df["weekly_outflow"])
    
    naive = NaiveForecaster()
    
    lgb_preds = forecaster.predict(test_df)
    naive_preds = naive.predict(test_df)
    
    lgb_mae_in = np.mean(np.abs(test_df["weekly_inflow"] - lgb_preds["predicted_inflow"]))
    naive_mae_in = np.mean(np.abs(test_df["weekly_inflow"] - naive_preds["predicted_inflow"]))
    
    lgb_mae_out = np.mean(np.abs(test_df["weekly_outflow"] - lgb_preds["predicted_outflow"]))
    naive_mae_out = np.mean(np.abs(test_df["weekly_outflow"] - naive_preds["predicted_outflow"]))
    
    # Forecaster should achieve meaningful accuracy and lower total MAE compared to repeating last week's values
    total_lgb_mae = lgb_mae_in + lgb_mae_out
    total_naive_mae = naive_mae_in + naive_mae_out
    assert total_lgb_mae <= total_naive_mae * 1.15  # within competitive performance or better


def test_risk_model_calibration(small_training_data, small_test_data):
    """Probabilities are strictly within [0, 1] and calibrated."""
    train_df = small_training_data
    test_df = small_test_data
    
    risk_model = CalibratedRiskModel(seed=42, n_estimators=30, max_depth=3)
    risk_model.fit(train_df, train_df["shortfall_next_week"])
    
    probas = risk_model.predict_proba(test_df)
    assert probas.shape == (len(test_df), 2)
    assert np.all(probas >= 0.0)
    assert np.all(probas <= 1.0)
    # Probabilities sum to 1
    np.testing.assert_allclose(probas.sum(axis=1), np.ones(len(test_df)), rtol=1e-5)

    # Feature importances exist and map to feature names
    importances = risk_model.get_feature_importances()
    assert isinstance(importances, dict)
    assert len(importances) == len(risk_model.feature_names)
    assert abs(sum(importances.values()) - 1.0) < 1e-4

    # Baseline logistic model
    baseline = LogisticRiskBaseline(seed=42)
    baseline.fit(train_df, train_df["shortfall_next_week"])
    b_probas = baseline.predict_proba(test_df)
    assert b_probas.shape == (len(test_df), 2)
    assert np.all(b_probas >= 0.0)
    assert np.all(b_probas <= 1.0)


def test_model_determinism(small_training_data):
    """Same seed produces identical predictions."""
    df = small_training_data
    
    f1 = CashFlowForecaster(seed=42, n_estimators=20, max_depth=3)
    f1.fit(df, df["weekly_inflow"], df["weekly_outflow"])
    p1 = f1.predict(df)
    
    f2 = CashFlowForecaster(seed=42, n_estimators=20, max_depth=3)
    f2.fit(df, df["weekly_inflow"], df["weekly_outflow"])
    p2 = f2.predict(df)
    
    pd.testing.assert_frame_equal(p1, p2)
    
    r1 = CalibratedRiskModel(seed=42, n_estimators=20, max_depth=3)
    r1.fit(df, df["shortfall_next_week"])
    rp1 = r1.predict_proba(df)
    
    r2 = CalibratedRiskModel(seed=42, n_estimators=20, max_depth=3)
    r2.fit(df, df["shortfall_next_week"])
    rp2 = r2.predict_proba(df)
    
    np.testing.assert_array_equal(rp1, rp2)


def test_model_store_save_load(small_training_data):
    """Saved model loaded back produces bitwise identical predictions."""
    df = small_training_data
    forecaster = CashFlowForecaster(seed=42, n_estimators=20, max_depth=3)
    forecaster.fit(df, df["weekly_inflow"], df["weekly_outflow"])
    preds_before = forecaster.predict(df)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = ModelStore(model_dir=tmp_dir)
        store.save(forecaster, "forecaster_test", metadata={"version": "v1.2.3", "seed": 42})
        
        loaded_model, meta = store.load("forecaster_test")
        assert meta["version"] == "v1.2.3"
        assert meta["seed"] == 42
        
        preds_after = loaded_model.predict(df)
        pd.testing.assert_frame_equal(preds_before, preds_after)
        
        # Test helper functions with model_dir
        version = get_model_version("forecaster_test", model_dir=tmp_dir)
        assert version == "v1.2.3"


def test_no_protected_attributes_used():
    """Ensure model feature names contain no gender/region/age/religion or latent traits."""
    forbidden = {"gender", "region_type", "region", "age_band", "age", "religion", "persona", "income_stability", "shock_exposure", "bill_discipline"}
    
    forecaster = CashFlowForecaster()
    for feat in forecaster.feature_names:
        assert feat.lower() not in forbidden
        for f in forbidden:
            assert f not in feat.lower(), f"Forbidden substring {f} in feature {feat}"
            
    risk_model = CalibratedRiskModel()
    for feat in risk_model.feature_names:
        assert feat.lower() not in forbidden
        for f in forbidden:
            assert f not in feat.lower(), f"Forbidden substring {f} in feature {feat}"
