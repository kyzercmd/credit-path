"""
Config Effects Test Suite (B14).

Verifies dynamic configuration effects:
1. Ready Thresholds: Changing policy thresholds dynamically alters Ready status
   (e.g., raising min_balance_threshold / bill_on_time_pct / min_balance_pct_days
   turns Ready customers into Not yet).
2. Affordability Cap: Changing affordability_cap alters the computed safe range proportionally.
3. Annual Interest Rate: Changing illustrative_rate (annual interest rate) alters the
   computed monthly loan payment and total repayment in loan check.
"""
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.config import Config, get_config, update_config
from app.engines.ready import ReadyEngine
from app.engines.affordability import AffordabilityEngine, calculate_amortization
from app.data.loader import load_data, get_customer_ids


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def sample_ready_customer_id() -> str:
    """Find a confirmed Ready customer with positive capacity under baseline config."""
    cids = get_customer_ids("all")
    ready_engine = ReadyEngine(config=get_config())
    affordability_engine = AffordabilityEngine(config=get_config())
    data = load_data()

    for cid in cids[:100]:
        res = ready_engine.evaluate(cid, data=data)
        if res.ready:
            sr = affordability_engine.safe_range(cid, data=data)
            if sr.monthly_high > 0:
                return cid
    pytest.fail("Could not find a Ready customer with positive capacity in test slice")


def test_ready_threshold_change_affects_status_engine(sample_ready_customer_id: str):
    """
    Engine-level test: raising cushion/bill thresholds changes a customer's status
    from Ready to Not yet.
    """
    data = load_data()
    base_cfg = get_config()
    engine = ReadyEngine()

    # Baseline: customer is Ready
    res_base = engine.evaluate(sample_ready_customer_id, config=base_cfg, data=data)
    assert res_base.ready is True
    assert res_base.status_label == "Ready"

    # 1. Raise min_balance_threshold to an unattainable level (e.g. 100,000 BDT)
    strict_balance_cfg = Config(**{**base_cfg.to_dict(), "min_balance_threshold": 100000.0})
    res_strict_bal = engine.evaluate(sample_ready_customer_id, config=strict_balance_cfg, data=data)
    assert res_strict_bal.ready is False
    assert res_strict_bal.status_label == "Not yet"
    assert any("Cushion" in check.name for check in res_strict_bal.missing_checks)

    # 2. Raise bill_on_time_pct to 100% (1.0)
    strict_bill_cfg = Config(**{**base_cfg.to_dict(), "bill_on_time_pct": 1.0})
    res_strict_bill = engine.evaluate(sample_ready_customer_id, config=strict_bill_cfg, data=data)
    # If the customer had any bill delinquency, they should fail Check 3
    # If customer has 100% on-time bills, raising min_balance_pct_days to 1.0 will fail
    strict_pct_cfg = Config(**{**base_cfg.to_dict(), "min_balance_pct_days": 1.0})
    res_strict_pct = engine.evaluate(sample_ready_customer_id, config=strict_pct_cfg, data=data)
    assert (not res_strict_bill.ready) or (not res_strict_pct.ready)


def test_ready_threshold_change_affects_status_api(
    client: TestClient,
    sample_ready_customer_id: str,
):
    """
    API-level test: PUT /admin/config dynamically changes GET /customer/{id}/status.
    """
    # 1. Confirm customer is Ready initially
    res_init = client.get(f"/customer/{sample_ready_customer_id}/status")
    assert res_init.status_code == 200
    assert res_init.json()["ready"] is True

    orig_cfg = client.get("/admin/config").json()["config"]

    try:
        # 2. Update config via admin API with very high balance threshold
        put_res = client.put("/admin/config", json={"min_balance_threshold": 500000.0})
        assert put_res.status_code == 200
        assert put_res.json()["config"]["min_balance_threshold"] == 500000.0

        # 3. Customer status should now dynamically be Not yet
        res_after = client.get(f"/customer/{sample_ready_customer_id}/status")
        assert res_after.status_code == 200
        data_after = res_after.json()
        assert data_after["ready"] is False
        assert data_after["status_label"] == "Not yet"
    finally:
        # 4. Restore original config
        client.put("/admin/config", json=orig_cfg)

    # 5. Verify customer is Ready again
    res_restored = client.get(f"/customer/{sample_ready_customer_id}/status")
    assert res_restored.status_code == 200
    assert res_restored.json()["ready"] is True


def test_affordability_cap_change_affects_safe_range(
    client: TestClient,
    sample_ready_customer_id: str,
):
    """
    Changing affordability_cap directly scales monthly_high and monthly_low safe bounds.
    """
    engine = AffordabilityEngine()
    base_cfg = get_config()

    # 1. Baseline range (affordability_cap = 0.40)
    cfg_40 = Config(**{**base_cfg.to_dict(), "affordability_cap": 0.40})
    sr_40 = engine.safe_range(sample_ready_customer_id, config=cfg_40)
    assert sr_40.monthly_high > 0

    # 2. Reduced cap (affordability_cap = 0.20 -> half capacity)
    cfg_20 = Config(**{**base_cfg.to_dict(), "affordability_cap": 0.20})
    sr_20 = engine.safe_range(sample_ready_customer_id, config=cfg_20)
    assert sr_20.monthly_high < sr_40.monthly_high
    assert abs(sr_20.monthly_high - (sr_40.monthly_high * 0.5)) <= 20.0  # round to nearest 10

    # 3. Increased cap (affordability_cap = 0.60 -> 1.5x capacity)
    cfg_60 = Config(**{**base_cfg.to_dict(), "affordability_cap": 0.60})
    sr_60 = engine.safe_range(sample_ready_customer_id, config=cfg_60)
    assert sr_60.monthly_high > sr_40.monthly_high

    # 4. Test via API
    orig_cfg = client.get("/admin/config").json()["config"]
    try:
        # Halve affordability cap
        client.put("/admin/config", json={"affordability_cap": 0.20})
        res_api_20 = client.get(f"/customer/{sample_ready_customer_id}/safe-range")
        assert res_api_20.status_code == 200
        assert res_api_20.json()["monthly_high"] == sr_20.monthly_high
    finally:
        client.put("/admin/config", json=orig_cfg)


def test_annual_interest_rate_change_affects_loan_payment(
    client: TestClient,
    sample_ready_customer_id: str,
):
    """
    Changing illustrative_rate (annual interest rate) alters monthly payment
    and total repayment in calculate_amortization and loan-check.
    """
    amount = 10000.0
    tenor = 12

    # 1. Amortization formula direct calculation
    pmt_0 = calculate_amortization(amount, tenor, annual_rate=0.0)
    pmt_15 = calculate_amortization(amount, tenor, annual_rate=0.15)
    pmt_30 = calculate_amortization(amount, tenor, annual_rate=0.30)

    # 0% interest is simple principal division (10000 / 12 = 833.33)
    assert pmt_0 == round(10000.0 / 12.0, 2)
    assert pmt_15 > pmt_0
    assert pmt_30 > pmt_15

    # 2. Engine-level loan check evaluation
    engine = AffordabilityEngine()
    base_cfg = get_config()

    cfg_15 = Config(**{**base_cfg.to_dict(), "illustrative_rate": 0.15})
    lc_15 = engine.loan_check(sample_ready_customer_id, amount=amount, tenor_months=tenor, config=cfg_15)

    cfg_30 = Config(**{**base_cfg.to_dict(), "illustrative_rate": 0.30})
    lc_30 = engine.loan_check(sample_ready_customer_id, amount=amount, tenor_months=tenor, config=cfg_30)

    assert lc_30.monthly_payment > lc_15.monthly_payment
    assert lc_30.total_repayment > lc_15.total_repayment
    assert lc_30.surplus_share >= lc_15.surplus_share

    # 3. API-level loan check evaluation
    orig_cfg = client.get("/admin/config").json()["config"]
    try:
        # Test 15% rate
        client.put("/admin/config", json={"illustrative_rate": 0.15})
        res_15 = client.post(
            f"/customer/{sample_ready_customer_id}/loan-check",
            json={"amount": amount, "tenor_months": tenor},
        )
        assert res_15.status_code == 200
        pay_15 = res_15.json()["monthly_payment"]

        # Test 30% rate
        client.put("/admin/config", json={"illustrative_rate": 0.30})
        res_30 = client.post(
            f"/customer/{sample_ready_customer_id}/loan-check",
            json={"amount": amount, "tenor_months": tenor},
        )
        assert res_30.status_code == 200
        pay_30 = res_30.json()["monthly_payment"]

        assert pay_30 > pay_15
    finally:
        client.put("/admin/config", json=orig_cfg)
