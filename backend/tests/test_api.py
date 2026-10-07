"""
Comprehensive REST API Integration Tests (B13).

Verifies:
- test_health: status="ok", model_loaded=True, model_version, data_as_of
- test_customer_status_ready_and_not_yet: Ready vs Not yet status checks and schemas
- test_customer_safe_range_and_loan_check: Safe range (400 for Not yet, 200 for Ready) and loan check
- test_customer_calendar_and_path: Calendar forecast, tight weeks, and actionable recourse steps
- test_customer_progress: Monthly historical checks progression
- test_consent_opt_out_blocks_access: Opt-out blocks customer endpoints with 403, opt-in unblocks
- test_kill_switch_hides_features: Emergency kill-switch hides safe-range and loan-check with 403
- test_admin_funnel_and_forecast_quality: Readiness funnel counts and forecast quality metrics
- test_admin_fairness: Demographic parity report and mitigation results
- test_admin_config_put_updates_and_versions: Policy threshold updates and version increments
- test_all_responses_contain_meta_fields: All responses contain meta with traceability fields & no prohibited jargon
"""
from __future__ import annotations

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_config, update_config, Config
from app.database import get_audit_log, log_consent


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Admin authentication header."""
    return {"X-Admin-API-Key": get_config().admin_api_key}


@pytest.fixture
def ready_customer_id() -> str:
    """Known ready customer."""
    return "C00009"


@pytest.fixture
def not_yet_customer_id() -> str:
    """Known not yet customer."""
    return "C00001"


def test_admin_auth_required(client: TestClient):
    """Admin endpoints require valid X-Admin-API-Key or Bearer token header."""
    res_no_auth = client.get("/admin/config")
    assert res_no_auth.status_code == 401

    res_bad_auth = client.get("/admin/config", headers={"X-Admin-API-Key": "wrong-key"})
    assert res_bad_auth.status_code == 401

    res_bearer_ok = client.get(
        "/admin/config",
        headers={"Authorization": f"Bearer {get_config().admin_token}"},
    )
    assert res_bearer_ok.status_code == 200

    res_api_key_ok = client.get(
        "/admin/config",
        headers={"X-Admin-API-Key": get_config().admin_api_key},
    )
    assert res_api_key_ok.status_code == 200


def test_health(client: TestClient):
    """GET /health returns status='ok', model_loaded=True, model_version, and data_as_of."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert isinstance(data["model_version"], str) and len(data["model_version"]) > 0
    assert isinstance(data["data_as_of"], str) and len(data["data_as_of"]) > 0
    assert "disclaimer" in data


def test_customer_status_ready_and_not_yet(
    client: TestClient,
    ready_customer_id: str,
    not_yet_customer_id: str,
):
    """GET /customer/{id}/status for ready and not yet customers."""
    # 1. Ready customer
    res_ready = client.get(f"/customer/{ready_customer_id}/status")
    assert res_ready.status_code == 200
    ready_data = res_ready.json()
    assert ready_data["customer_id"] == ready_customer_id
    assert ready_data["ready"] is True
    assert ready_data["status_label"] == "Ready"
    assert len(ready_data["checks"]) == 3
    for chk in ready_data["checks"]:
        assert chk["passed"] is True
        assert len(chk["reason"]) > 0
        assert len(chk["reason_code"]) > 0

    # 2. Not yet customer
    res_not_yet = client.get(f"/customer/{not_yet_customer_id}/status")
    assert res_not_yet.status_code == 200
    not_yet_data = res_not_yet.json()
    assert not_yet_data["customer_id"] == not_yet_customer_id
    assert not_yet_data["ready"] is False
    assert not_yet_data["status_label"] == "Not yet"
    assert any(not chk["passed"] for chk in not_yet_data["checks"])

    # 3. Nonexistent customer returns 404
    res_404 = client.get("/customer/NONEXISTENT_99999/status")
    assert res_404.status_code == 404


def test_customer_safe_range_and_loan_check(
    client: TestClient,
    ready_customer_id: str,
    not_yet_customer_id: str,
):
    """
    GET /customer/{id}/safe-range enforces readiness.
    POST /customer/{id}/loan-check evaluates proposals.
    """
    # 1. Safe range for ready customer
    res_sr = client.get(f"/customer/{ready_customer_id}/safe-range")
    assert res_sr.status_code == 200
    sr_data = res_sr.json()
    assert sr_data["customer_id"] == ready_customer_id
    assert sr_data["monthly_low"] <= sr_data["monthly_high"]
    assert sr_data["stressed_low"] <= sr_data["stressed_high"]
    assert sr_data["stressed_high"] <= sr_data["monthly_high"]
    assert sr_data["basis_months"] >= 1
    assert len(sr_data["basis_sentence"]) > 0

    # 2. Safe range for not-yet customer returns 400
    res_sr_ny = client.get(f"/customer/{not_yet_customer_id}/safe-range")
    assert res_sr_ny.status_code == 400
    assert "ready" in res_sr_ny.json()["detail"].lower()

    # 3. Loan check for reasonable amount
    req_body = {"amount": 5000.0, "tenor_months": 6}
    res_lc = client.post(f"/customer/{ready_customer_id}/loan-check", json=req_body)
    assert res_lc.status_code == 200
    lc_data = res_lc.json()
    assert lc_data["customer_id"] == ready_customer_id
    assert lc_data["amount"] == 5000.0
    assert lc_data["tenor_months"] == 6
    assert lc_data["monthly_payment"] > 0
    assert lc_data["verdict"] in ("Comfortable", "Tight", "Too much")
    assert len(lc_data["verdict_reason"]) > 0
    assert len(lc_data["stress_verdict"]) > 0

    # 4. Loan check for excessive amount triggers "Too much" and offers nearest comfortable option
    res_excess = client.post(
        f"/customer/{ready_customer_id}/loan-check",
        json={"amount": 500000.0, "tenor_months": 6},
    )
    assert res_excess.status_code == 200
    excess_data = res_excess.json()
    assert excess_data["verdict"] == "Too much"

    # 5. Invalid parameters return 422
    res_invalid = client.post(
        f"/customer/{ready_customer_id}/loan-check",
        json={"amount": -100.0, "tenor_months": 50},
    )
    assert res_invalid.status_code == 422


def test_customer_calendar_and_path(
    client: TestClient,
    ready_customer_id: str,
    not_yet_customer_id: str,
):
    """
    GET /customer/{id}/calendar returns forecast weeks.
    GET /customer/{id}/path returns actionable steps.
    """
    # 1. Calendar
    res_cal = client.get(f"/customer/{ready_customer_id}/calendar")
    assert res_cal.status_code == 200
    cal_data = res_cal.json()
    assert cal_data["customer_id"] == ready_customer_id
    assert len(cal_data["weeks"]) == 8
    assert len(cal_data["recommended_window"]) > 0
    assert isinstance(cal_data["avoid_weeks"], list)
    for w in cal_data["weeks"]:
        assert "week_start" in w
        assert w["money_in"] >= 0
        assert w["money_out"] >= 0
        assert w["status"] in ("safe", "tight")

    # 2. Path for not-yet customer
    res_path = client.get(f"/customer/{not_yet_customer_id}/path")
    assert res_path.status_code == 200
    path_data = res_path.json()
    assert path_data["customer_id"] == not_yet_customer_id
    assert len(path_data["missing_items"]) > 0
    for step in path_data["missing_items"]:
        assert len(step["item"]) > 0
        assert len(step["action"]) > 0
        assert step["estimated_weeks"] > 0
        assert len(step["reason"]) > 0


def test_customer_progress(
    client: TestClient,
    ready_customer_id: str,
):
    """GET /customer/{id}/progress returns monthly history over past dataset months."""
    res_prog = client.get(f"/customer/{ready_customer_id}/progress")
    assert res_prog.status_code == 200
    prog_data = res_prog.json()
    assert prog_data["customer_id"] == ready_customer_id
    assert len(prog_data["history"]) == 12
    for item in prog_data["history"]:
        assert "month" in item
        assert isinstance(item["history_ok"], bool)
        assert isinstance(item["income_regular"], bool)
        assert isinstance(item["cushion_ok"], bool)
    assert prog_data["became_ready"] is not None
    assert isinstance(prog_data["current_values"], dict)


def test_consent_opt_out_blocks_access(
    client: TestClient,
    ready_customer_id: str,
):
    """Customer opt-out blocks all coach endpoints with HTTP 403; consent restores access."""
    # 1. Opt out
    res_opt_out = client.post(
        f"/customer/{ready_customer_id}/consent",
        json={"action": "opt-out"},
    )
    assert res_opt_out.status_code == 200
    assert res_opt_out.json()["recorded"] is True
    assert res_opt_out.json()["action"] == "opt-out"

    # 2. Verify all coach endpoints return 403 Forbidden
    for ep in ["status", "safe-range", "calendar", "path", "progress"]:
        r = client.get(f"/customer/{ready_customer_id}/{ep}")
        assert r.status_code == 403, f"Endpoint {ep} did not return 403"
        assert "turned off credit coaching" in r.json()["detail"]

    r_lc = client.post(
        f"/customer/{ready_customer_id}/loan-check",
        json={"amount": 2000.0, "tenor_months": 6},
    )
    assert r_lc.status_code == 403
    assert "turned off credit coaching" in r_lc.json()["detail"]

    # 3. Opt back in
    res_consent = client.post(
        f"/customer/{ready_customer_id}/consent",
        json={"action": "consent"},
    )
    assert res_consent.status_code == 200
    assert res_consent.json()["action"] == "consent"

    # 4. Verify access is restored
    res_restored = client.get(f"/customer/{ready_customer_id}/status")
    assert res_restored.status_code == 200


def test_kill_switch_hides_features(
    client: TestClient,
    ready_customer_id: str,
    admin_headers: dict[str, str],
):
    """Kill switch hides safe-range and loan-check with HTTP 403 while leaving others active."""
    # 1. Engage kill switch
    res_ks = client.post(
        "/admin/kill-switch",
        json={"kill_safe_range": True, "kill_loan_check": True},
        headers=admin_headers,
    )
    assert res_ks.status_code == 200
    assert res_ks.json()["kill_safe_range"] is True
    assert res_ks.json()["kill_loan_check"] is True

    # 2. Safe-range and loan-check are disabled
    r_sr = client.get(f"/customer/{ready_customer_id}/safe-range")
    assert r_sr.status_code == 403
    assert "temporarily disabled by policy" in r_sr.json()["detail"]

    r_lc = client.post(
        f"/customer/{ready_customer_id}/loan-check",
        json={"amount": 3000.0, "tenor_months": 6},
    )
    assert r_lc.status_code == 403
    assert "temporarily disabled by policy" in r_lc.json()["detail"]

    # 3. Other coach endpoints remain functional
    r_status = client.get(f"/customer/{ready_customer_id}/status")
    assert r_status.status_code == 200
    r_cal = client.get(f"/customer/{ready_customer_id}/calendar")
    assert r_cal.status_code == 200

    # 4. Disengage kill switch
    res_reset = client.post(
        "/admin/kill-switch",
        json={"kill_safe_range": False, "kill_loan_check": False},
        headers=admin_headers,
    )
    assert res_reset.status_code == 200

    # 5. Safe-range is re-enabled
    r_sr_again = client.get(f"/customer/{ready_customer_id}/safe-range")
    assert r_sr_again.status_code == 200


def test_admin_funnel_and_forecast_quality(
    client: TestClient,
    admin_headers: dict[str, str],
):
    """GET /admin/funnel and GET /admin/forecast-quality return accurate analytics."""
    # 1. Funnel
    res_funnel = client.get("/admin/funnel", headers=admin_headers)
    assert res_funnel.status_code == 200
    funnel_data = res_funnel.json()
    assert funnel_data["total_customers"] == 10000
    assert funnel_data["ready_count"] + funnel_data["not_yet_count"] == 10000
    assert len(funnel_data["missing_checks"]) == 3
    bucket_labels = {b["label"] for b in funnel_data["missing_checks"]}
    assert "History" in bucket_labels
    assert "Regularity" in bucket_labels
    assert "Cushion & Bills" in bucket_labels

    # 2. Forecast quality
    res_fq = client.get("/admin/forecast-quality", headers=admin_headers)
    assert res_fq.status_code == 200
    fq_data = res_fq.json()
    assert fq_data["overall_mae"] > 0
    assert fq_data["overall_wape"] > 0
    assert fq_data["naive_mae"] > 0
    assert fq_data["naive_wape"] > 0
    # LightGBM forecaster should beat naive baseline
    assert fq_data["overall_wape"] < fq_data["naive_wape"]
    assert len(fq_data["by_persona"]) == 5
    for p in [
        "wage_worker",
        "seasonal_farmer",
        "informal_merchant",
        "woman_led_household",
        "salaried_user",
    ]:
        assert p in fq_data["by_persona"]
        assert fq_data["by_persona"][p]["count"] > 0


def test_admin_fairness(
    client: TestClient,
    admin_headers: dict[str, str],
):
    """GET /admin/fairness returns demographic fairness breakdown and mitigation."""
    res = client.get("/admin/fairness", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["by_gender"]) >= 2
    assert len(data["by_region"]) >= 2
    assert len(data["by_age_band"]) >= 3
    assert "mitigation" in data
    assert "before" in data["mitigation"]
    assert "after" in data["mitigation"]
    assert "impact_summary" in data["mitigation"]


def test_admin_config_put_updates_and_versions(
    client: TestClient,
    admin_headers: dict[str, str],
):
    """GET /admin/config and PUT /admin/config update policy and increment versions."""
    # 1. Initial config
    res_init = client.get("/admin/config", headers=admin_headers)
    assert res_init.status_code == 200
    init_data = res_init.json()
    init_version = init_data["version"]
    orig_cap = init_data["config"]["affordability_cap"]

    # 2. Update config
    new_cap = 0.35
    res_put = client.put("/admin/config", json={"affordability_cap": new_cap}, headers=admin_headers)
    assert res_put.status_code == 200
    put_data = res_put.json()
    assert put_data["version"] > init_version
    assert put_data["config"]["affordability_cap"] == new_cap

    # Verify active config in memory matches update
    active_cfg = get_config()
    assert active_cfg.affordability_cap == new_cap

    # 3. Reset config back to original
    client.put("/admin/config", json={"affordability_cap": orig_cap}, headers=admin_headers)
    assert get_config().affordability_cap == orig_cap


def test_all_responses_contain_meta_fields(
    client: TestClient,
    ready_customer_id: str,
    not_yet_customer_id: str,
    admin_headers: dict[str, str],
):
    """
    Verify EVERY successful endpoint response contains model_version, data_as_of,
    and disclaimer. Also verify no prohibited jargon in customer texts.
    """
    forbidden_terms = ["emi", "surplus", "pd", "credit score", "default"]

    endpoints = [
        ("GET", "/health"),
        ("GET", f"/customer/{ready_customer_id}/status"),
        ("GET", f"/customer/{ready_customer_id}/safe-range"),
        ("POST", f"/customer/{ready_customer_id}/loan-check", {"amount": 2000.0, "tenor_months": 6}),
        ("GET", f"/customer/{ready_customer_id}/calendar"),
        ("GET", f"/customer/{not_yet_customer_id}/path"),
        ("GET", f"/customer/{ready_customer_id}/progress"),
        ("POST", f"/customer/{ready_customer_id}/consent", {"action": "consent"}),
        ("GET", "/admin/funnel"),
        ("GET", "/admin/forecast-quality"),
        ("GET", "/admin/fairness"),
        ("GET", "/admin/config"),
        ("GET", "/admin/audit-log"),
    ]

    for item in endpoints:
        method = item[0]
        url = item[1]
        payload = item[2] if len(item) > 2 else None
        headers = admin_headers if url.startswith("/admin") else None

        if method == "GET":
            res = client.get(url, headers=headers)
        else:
            res = client.post(url, json=payload, headers=headers)

        assert res.status_code == 200, f"Endpoint {url} failed with status {res.status_code}"
        data = res.json()

        # Check metadata fields presence
        if "meta" in data and data["meta"] is not None:
            meta = data["meta"]
            assert "model_version" in meta and len(meta["model_version"]) > 0
            assert "data_as_of" in meta and len(meta["data_as_of"]) > 0
            assert "disclaimer" in meta and len(meta["disclaimer"]) > 0
        else:
            # Fallback for health response which also contains them directly
            assert "model_version" in data and len(data["model_version"]) > 0
            assert "data_as_of" in data and len(data["data_as_of"]) > 0
            assert "disclaimer" in data and len(data["disclaimer"]) > 0

        # Prohibited customer jargon check
        text_dump = str(data).lower()
        if "/customer/" in url:
            for term in forbidden_terms:
                pattern = rf"\b{re.escape(term)}\b"
                assert not re.search(pattern, text_dump), (
                    f"Prohibited term '{term}' found in response from {url}: {data}"
                )


def test_contract_customer_and_admin_responses_meta_fields(
    client: TestClient,
    ready_customer_id: str,
    not_yet_customer_id: str,
):
    """
    Contract test: verify every customer response (status, safe-range, loan-check,
    calendar, path, progress) and admin health response contains model_version,
    data_as_of, and disclaimer in meta.
    """
    contract_endpoints = [
        ("GET", f"/customer/{ready_customer_id}/status", None),
        ("GET", f"/customer/{ready_customer_id}/safe-range", None),
        ("POST", f"/customer/{ready_customer_id}/loan-check", {"amount": 3000.0, "tenor_months": 6}),
        ("GET", f"/customer/{ready_customer_id}/calendar", None),
        ("GET", f"/customer/{not_yet_customer_id}/path", None),
        ("GET", f"/customer/{ready_customer_id}/progress", None),
        ("GET", "/health", None),
    ]

    for method, url, payload in contract_endpoints:
        if method == "GET":
            res = client.get(url)
        else:
            res = client.post(url, json=payload)

        assert res.status_code == 200, f"Contract check failed: {url} returned {res.status_code}"
        data = res.json()

        assert "meta" in data, f"Response from {url} is missing 'meta' object"
        meta = data["meta"]
        assert meta is not None, f"'meta' object in {url} is None"

        for field in ["model_version", "data_as_of", "disclaimer"]:
            assert field in meta, f"'{field}' missing from meta in {url}"
            assert isinstance(meta[field], str), f"'{field}' in meta in {url} is not a string"
            assert len(meta[field].strip()) > 0, f"'{field}' in meta in {url} is empty"


def test_real_time_ingestion_and_dynamic_readiness(
    client: TestClient,
    not_yet_customer_id: str,
):
    """
    Test real-time event ingestion (transactions, bills, daily balances)
    and dynamic 'as_of' date re-scoring without batch processing cutoffs.
    """
    cid = not_yet_customer_id

    # 1. Ingest transaction beyond batch cutoff
    res_tx = client.post(
        f"/customer/{cid}/ingest/transaction",
        json={
            "date": "2026-02-01",
            "type": "inflow",
            "amount": 18000.0,
            "description": "Direct bank salary credit",
        },
    )
    assert res_tx.status_code == 200
    tx_data = res_tx.json()
    assert tx_data["recorded"] is True
    assert tx_data["as_of_date"] == "2026-02-01"
    assert "transition" in tx_data
    assert tx_data["transition"]["total_checks_count"] == 3

    # 2. Ingest daily cushion balance
    res_bal = client.post(
        f"/customer/{cid}/ingest/balance",
        json={
            "date": "2026-02-05",
            "balance": 15000.0,
            "shortfall": 0,
        },
    )
    assert res_bal.status_code == 200
    bal_data = res_bal.json()
    assert bal_data["recorded"] is True
    assert bal_data["as_of_date"] == "2026-02-05"

    # 3. Ingest bill payment
    res_bill = client.post(
        f"/customer/{cid}/ingest/bill",
        json={
            "due_date": "2026-02-10",
            "amount": 2500.0,
            "paid_date": "2026-02-08",
            "on_time": 1,
            "biller": "Titas Gas",
        },
    )
    assert res_bill.status_code == 200
    bill_data = res_bill.json()
    assert bill_data["recorded"] is True

    # 4. Status reflects dynamic as-of without hardcoded 2025 cutoff
    res_status = client.get(f"/customer/{cid}/status?as_of=2026-02-10")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["meta"]["data_as_of"] == "2026-02-10"

