"""
No Hardcoded Constants Scanner Test Suite (B14).

Verifies dynamic execution across the entire stack:
1. API endpoints (status, safe-range, loan-check, calendar, path, progress):
   Responses vary meaningfully across distinct customers rather than returning static hardcoded constants.
2. Frontend translation files (en.json, bn.json):
   No hardcoded numerical customer decisions or static loan amounts exist in translation text.
"""
import json
import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.data.loader import load_data, get_customer_ids
from app.engines.ready import ReadyEngine
from app.config import get_config


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def distinct_customers() -> list[str]:
    """Find a diverse list of distinct customer IDs (different personas / readiness)."""
    data = load_data()
    engine = ReadyEngine(config=get_config())
    cids = get_customer_ids("all")

    ready_cids = []
    not_yet_cids = []

    for cid in cids[:100]:
        res = engine.evaluate(cid, data=data)
        if res.ready and len(ready_cids) < 3:
            ready_cids.append(cid)
        elif not res.ready and len(not_yet_cids) < 3:
            not_yet_cids.append(cid)
        if len(ready_cids) >= 3 and len(not_yet_cids) >= 3:
            break

    assert len(ready_cids) >= 2, "Expected at least 2 Ready customers"
    assert len(not_yet_cids) >= 2, "Expected at least 2 Not yet customers"
    return ready_cids + not_yet_cids


def test_api_status_varies_by_customer(client: TestClient, distinct_customers: list[str]):
    """GET /customer/{id}/status outputs vary by customer data."""
    results = [client.get(f"/customer/{cid}/status").json() for cid in distinct_customers]

    # Verify both Ready and Not yet exist
    labels = {r["status_label"] for r in results}
    assert "Ready" in labels
    assert "Not yet" in labels

    # Verify check current values differ across customers (e.g. regularity weeks or cushion %)
    regularity_vals = {r["checks"][1]["current_value"] for r in results}
    cushion_vals = {r["checks"][2]["current_value"] for r in results}
    assert len(regularity_vals) > 1 or len(cushion_vals) > 1, (
        f"Readiness check values must vary across customers: reg={regularity_vals}, cushion={cushion_vals}"
    )


def test_api_safe_range_varies_by_customer(client: TestClient, distinct_customers: list[str]):
    """GET /customer/{id}/safe-range safe repayment bounds vary by customer surplus."""
    ready_cids = [
        cid for cid in distinct_customers
        if client.get(f"/customer/{cid}/status").json()["ready"] is True
    ]
    assert len(ready_cids) >= 2

    safe_ranges = [client.get(f"/customer/{cid}/safe-range").json() for cid in ready_cids]
    monthly_highs = {sr["monthly_high"] for sr in safe_ranges}
    assert len(monthly_highs) > 1, f"Safe range monthly_high should vary, got {monthly_highs}"


def test_api_loan_check_varies_by_customer(client: TestClient, distinct_customers: list[str]):
    """POST /customer/{id}/loan-check evaluates proposal against distinct customer surplus."""
    req_payload = {"amount": 5000.0, "tenor_months": 6}
    results = [
        client.post(f"/customer/{cid}/loan-check", json=req_payload).json()
        for cid in distinct_customers
    ]

    surplus_shares = {r["surplus_share"] for r in results}
    assert len(surplus_shares) > 1, f"surplus_share should vary, got {surplus_shares}"


def test_api_calendar_varies_by_customer(client: TestClient, distinct_customers: list[str]):
    """GET /customer/{id}/calendar produces distinct customer-specific cash-flow forecasts."""
    calendars = [client.get(f"/customer/{cid}/calendar").json() for cid in distinct_customers]

    total_inflows = {
        sum(w["money_in"] for w in cal["weeks"])
        for cal in calendars
    }
    assert len(total_inflows) > 1, f"Calendar forecast inflows must vary, got {total_inflows}"


def test_api_path_varies_by_customer(client: TestClient, distinct_customers: list[str]):
    """GET /customer/{id}/path outputs specific recourse items for different not-yet customers."""
    not_yet_cids = [
        cid for cid in distinct_customers
        if client.get(f"/customer/{cid}/status").json()["ready"] is False
    ]
    assert len(not_yet_cids) >= 2

    paths = [client.get(f"/customer/{cid}/path").json() for cid in not_yet_cids]
    missing_counts = {len(p["missing_items"]) for p in paths}
    missing_items_texts = {tuple(step["item"] for step in p["missing_items"]) for p in paths}
    # Either the count or the items themselves must reflect customer-specific shortcomings
    assert len(missing_counts) > 1 or len(missing_items_texts) > 1, (
        f"Recourse path items should vary across not-yet customers: {missing_items_texts}"
    )


def test_api_progress_varies_by_customer(client: TestClient, distinct_customers: list[str]):
    """GET /customer/{id}/progress returns customer-specific historical habit trajectories."""
    progresses = [client.get(f"/customer/{cid}/progress").json() for cid in distinct_customers]

    became_ready_months = {p["became_ready"] for p in progresses}
    assert len(became_ready_months) > 1, (
        f"became_ready month must vary across customers, got {became_ready_months}"
    )


def test_translation_files_no_hardcoded_loan_amounts_or_decisions():
    """
    Scan frontend translation files (en.json, bn.json) to ensure:
    1. No hardcoded numerical loan amounts (e.g. ৳5000, ৳10000) - must use {amount}/{payment} placeholders.
    2. No hardcoded customer decisions (e.g. 'approved for 5000', 'loan granted').
    3. Structural completeness across language catalogs.
    """
    i18n_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "i18n"
    assert i18n_dir.is_dir(), f"Frontend i18n directory not found at {i18n_dir}"

    en_file = i18n_dir / "en.json"
    bn_file = i18n_dir / "bn.json"

    assert en_file.is_file(), "en.json missing"
    assert bn_file.is_file(), "bn.json missing"

    with open(en_file, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    with open(bn_file, "r", encoding="utf-8") as f:
        bn_data = json.load(f)

    # Check matching top-level keys
    assert set(en_data.keys()) == set(bn_data.keys()), "en.json and bn.json top-level keys must match"

    def extract_string_leaves(node: dict | list | str, path: str = "") -> list[tuple[str, str]]:
        leaves = []
        if isinstance(node, dict):
            for k, v in node.items():
                leaves.extend(extract_string_leaves(v, f"{path}.{k}" if path else k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                leaves.extend(extract_string_leaves(v, f"{path}[{i}]"))
        elif isinstance(node, str):
            leaves.append((path, node))
        return leaves

    en_strings = extract_string_leaves(en_data)
    bn_strings = extract_string_leaves(bn_data)

    # Regex detecting concrete currency amounts not using template placeholders:
    # Matches currency symbols (৳, BDT, Tk) directly followed by digits (e.g. ৳5000, ৳ 10000)
    hardcoded_currency_regex = re.compile(r"(?:৳|BDT|Tk\.?)\s*\d+", re.IGNORECASE)

    # Regex detecting hardcoded underwriting verdicts with concrete values
    hardcoded_verdicts = [
        re.compile(r"\bapproved for \d+", re.IGNORECASE),
        re.compile(r"\beligible for \d+", re.IGNORECASE),
        re.compile(r"\bloan granted\b", re.IGNORECASE),
        re.compile(r"\bcredit limit of \d+", re.IGNORECASE),
    ]

    for lang_code, strings in [("en", en_strings), ("bn", bn_strings)]:
        for key_path, text in strings:
            # Skip definition of currency symbol itself
            if key_path == "common.currency":
                continue

            # Check 1: No hardcoded concrete amounts
            currency_match = hardcoded_currency_regex.search(text)
            assert not currency_match, (
                f"[{lang_code}] Hardcoded amount '{currency_match.group(0)}' found in {key_path}: \"{text}\""
            )

            # Check 2: No hardcoded underwriting verdicts
            for verdict_regex in hardcoded_verdicts:
                v_match = verdict_regex.search(text)
                assert not v_match, (
                    f"[{lang_code}] Hardcoded verdict '{v_match.group(0)}' found in {key_path}: \"{text}\""
                )
