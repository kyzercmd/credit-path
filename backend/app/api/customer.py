"""
Customer API endpoints (B13).

Provides coaching endpoints for individual customers:
- /customer/{id}/status: Overall readiness & 3 policy checks
- /customer/{id}/safe-range: Sustainable monthly repayment range (Ready only)
- /customer/{id}/loan-check: Evaluation of specific loan proposal
- /customer/{id}/calendar: Weekly cash-flow & repayment timing calendar
- /customer/{id}/path: Actionable steps to readiness
- /customer/{id}/progress: Historical readiness progress over past months
- /customer/{id}/consent: Opt-in / opt-out recording
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

from app.config import Config, get_config
from app.data.loader import get_customer_ids, load_data
from app.database import (
    get_consent_status,
    log_consent,
    log_funnel_event,
    insert_live_transaction,
    insert_live_daily_balance,
    insert_live_bill,
)
from app.engines.ready import ReadyEngine, evaluate_customer
from app.engines.affordability import calculate_safe_range, evaluate_loan_check
from app.engines.timing import generate_calendar_forecast
from app.engines.recourse import compute_recourse_path
from app.features.builder import build_customer_features, get_customer_as_of_date, get_merged_customer_data
from app.ml.model_store import get_data_as_of, get_model_version
from app.schemas import (
    CalendarResponse,
    CheckHistory,
    ConsentRequest,
    ConsentResponse,
    FunnelEventRequest,
    HeadsUpCard,
    IngestBillRequest,
    IngestDailyBalanceRequest,
    IngestEventResponse,
    IngestTransactionRequest,
    LoanCheckRequest,
    LoanCheckResponse,
    Meta,
    PathResponse,
    ProgressResponse,
    ReadinessTransitionDelta,
    SafeRangeResponse,
    StatusResponse,
)

router = APIRouter(prefix="/customer", tags=["customer"])

OPT_OUT_DETAIL = "Customer has turned off credit coaching. Turn coach on in settings to resume."
KILL_SAFE_RANGE_DETAIL = "Safe repayment range feature is temporarily disabled by policy."
KILL_LOAN_CHECK_DETAIL = "Loan check feature is temporarily disabled by policy."

_ALL_CUSTOMER_IDS: set[str] | None = None


def get_all_valid_customer_ids() -> set[str]:
    """Cache and return set of all valid customer IDs."""
    global _ALL_CUSTOMER_IDS
    if _ALL_CUSTOMER_IDS is None:
        _ALL_CUSTOMER_IDS = set(get_customer_ids("all"))
    return _ALL_CUSTOMER_IDS


def verify_customer_exists(customer_id: str) -> None:
    """Validate customer existence in dataset."""
    valid_ids = get_all_valid_customer_ids()
    if customer_id not in valid_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{customer_id}' not found.",
        )


def verify_coach_consent(customer_id: str) -> None:
    """Enforce consent policy. Returns 403 if customer has opted out."""
    consent = get_consent_status(customer_id)
    if consent == "opt-out":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=OPT_OUT_DETAIL,
        )


def get_meta(cfg: Config, as_of: str | None = None) -> Meta:
    """Construct standard Meta payload with dynamic as_of date support."""
    data_date = as_of or get_data_as_of()
    return Meta(
        model_version=get_model_version("forecaster"),
        data_as_of=data_date,
        disclaimer=cfg.disclaimer,
    )


@router.get("/{customer_id}/status", response_model=StatusResponse)
def get_customer_status(
    customer_id: str,
    as_of: str | None = Query(None, description="Optional dynamic as-of date (YYYY-MM-DD). If omitted, inferred from latest live/historical data."),
) -> StatusResponse:
    """Evaluate overall readiness and policy checks with dynamic as-of support."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    target_cutoff = as_of or get_customer_as_of_date(customer_id)
    result = evaluate_customer(customer_id, config=cfg, cutoff_date=target_cutoff)
    try:
        log_funnel_event(customer_id, "profile_viewed", {"ready": result.ready, "as_of": target_cutoff})
    except Exception:
        pass
    return StatusResponse(
        customer_id=customer_id,
        ready=result.ready,
        status_label=result.status_label,
        status_sentence=result.status_sentence,
        checks=result.checks,
        meta=get_meta(cfg, as_of=target_cutoff),
    )


@router.get("/{customer_id}/safe-range", response_model=SafeRangeResponse)
def get_customer_safe_range(
    customer_id: str,
    as_of: str | None = Query(None, description="Optional dynamic as-of date (YYYY-MM-DD)."),
) -> SafeRangeResponse:
    """Compute safe monthly payment ranges for ready customers with dynamic as-of support."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    if cfg.kill_safe_range:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=KILL_SAFE_RANGE_DETAIL,
        )

    target_cutoff = as_of or get_customer_as_of_date(customer_id)
    # Only ready customers can calculate safe range
    ready_result = evaluate_customer(customer_id, config=cfg, cutoff_date=target_cutoff)
    if not ready_result.ready:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Safe repayment range is available once you become Ready. Check your path to get ready.",
        )

    range_result = calculate_safe_range(customer_id, config=cfg, cutoff_date=target_cutoff)
    return SafeRangeResponse(
        customer_id=customer_id,
        monthly_low=range_result.monthly_low,
        monthly_high=range_result.monthly_high,
        stressed_low=range_result.stressed_low,
        stressed_high=range_result.stressed_high,
        basis_months=range_result.basis_months,
        basis_sentence=range_result.basis_sentence,
        meta=get_meta(cfg, as_of=target_cutoff),
    )


@router.post("/{customer_id}/loan-check", response_model=LoanCheckResponse)
def post_customer_loan_check(
    customer_id: str,
    payload: LoanCheckRequest,
    as_of: str | None = Query(None, description="Optional dynamic as-of date (YYYY-MM-DD)."),
) -> LoanCheckResponse:
    """Evaluate specific loan proposal against cash flow and policy stress test with dynamic as-of support."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    if cfg.kill_loan_check:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=KILL_LOAN_CHECK_DETAIL,
        )

    target_cutoff = as_of or get_customer_as_of_date(customer_id)
    loan_result = evaluate_loan_check(
        customer_id=customer_id,
        amount=payload.amount,
        tenor_months=payload.tenor_months,
        config=cfg,
        cutoff_date=target_cutoff,
    )
    response = LoanCheckResponse(
        customer_id=customer_id,
        amount=loan_result.amount,
        tenor_months=loan_result.tenor_months,
        monthly_payment=loan_result.monthly_payment,
        total_repayment=loan_result.total_repayment,
        surplus_share=loan_result.surplus_share,
        verdict=loan_result.verdict,
        verdict_reason=loan_result.verdict_reason,
        stress_verdict=loan_result.stress_verdict,
        stress_reason=loan_result.stress_reason,
        nearest_comfortable=loan_result.nearest_comfortable,
        meta=get_meta(cfg, as_of=target_cutoff),
    )
    try:
        log_funnel_event(
            customer_id,
            "loan_check_performed",
            {
                "amount": loan_result.amount,
                "tenor_months": loan_result.tenor_months,
                "verdict": loan_result.verdict,
                "as_of": target_cutoff,
            },
        )
    except Exception:
        pass
    return response


@router.get("/{customer_id}/calendar", response_model=CalendarResponse)
def get_customer_calendar(
    customer_id: str,
    as_of: str | None = Query(None, description="Optional dynamic as-of date (YYYY-MM-DD)."),
) -> CalendarResponse:
    """Generate weekly cash-flow forecast and optimal repayment windows with dynamic as-of support."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    target_cutoff = as_of or get_customer_as_of_date(customer_id)
    cal_result = generate_calendar_forecast(customer_id, config=cfg, cutoff_date=target_cutoff)

    # Determine heads-up card if any week is projected as tight
    heads_up: HeadsUpCard | None = None
    tight_weeks = [w for w in cal_result.weeks if w.status == "tight"]
    if tight_weeks:
        first_tight = tight_weeks[0]
        heads_up = HeadsUpCard(
            message=f"Caution: Week of {first_tight.week_start} is projected to be tight.",
            suggestion=first_tight.reason,
            week=first_tight.week_start,
        )

    return CalendarResponse(
        customer_id=customer_id,
        weeks=cal_result.weeks,
        recommended_window=cal_result.recommended_window,
        avoid_weeks=cal_result.avoid_weeks,
        heads_up=heads_up,
        meta=get_meta(cfg, as_of=target_cutoff),
    )


@router.get("/{customer_id}/path", response_model=PathResponse)
def get_customer_path(
    customer_id: str,
    as_of: str | None = Query(None, description="Optional dynamic as-of date (YYYY-MM-DD)."),
) -> PathResponse:
    """Compute actionable steps for missing readiness checks with dynamic as-of support."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    target_cutoff = as_of or get_customer_as_of_date(customer_id)
    path_result = compute_recourse_path(customer_id, config=cfg, cutoff_date=target_cutoff)
    try:
        log_funnel_event(customer_id, "path_explored", {"missing_count": len(path_result.missing_items), "as_of": target_cutoff})
    except Exception:
        pass
    return PathResponse(
        customer_id=customer_id,
        missing_items=path_result.missing_items,
        meta=get_meta(cfg, as_of=target_cutoff),
    )


@router.get("/{customer_id}/progress", response_model=ProgressResponse)
def get_customer_progress(customer_id: str) -> ProgressResponse:
    """Compute monthly historical checks over past months in dataset."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    data = load_data()
    engine = ReadyEngine(config=cfg)

    # Pre-filter customer transactions, balances, and bills for fast evaluation
    c_tx = data["transactions"][data["transactions"]["customer_id"] == customer_id]
    c_bal = data["daily_balances"][data["daily_balances"]["customer_id"] == customer_id]
    c_bi = data["bills"][data["bills"]["customer_id"] == customer_id]
    cust_data = {
        "transactions": c_tx,
        "daily_balances": c_bal,
        "bills": c_bi,
    }

    # Precompute features once up to end of 2025
    cust_features = build_customer_features(customer_id, cutoff_date="2025-12-31")

    # Evaluate across all 12 calendar months
    months = [
        ("2025-01", "2025-01-31"),
        ("2025-02", "2025-02-28"),
        ("2025-03", "2025-03-31"),
        ("2025-04", "2025-04-30"),
        ("2025-05", "2025-05-31"),
        ("2025-06", "2025-06-30"),
        ("2025-07", "2025-07-31"),
        ("2025-08", "2025-08-31"),
        ("2025-09", "2025-09-30"),
        ("2025-10", "2025-10-31"),
        ("2025-11", "2025-11-30"),
        ("2025-12", "2025-12-31"),
    ]

    history: list[CheckHistory] = []
    became_ready: str | None = None
    latest_result = None

    for m_label, cutoff_dt in months:
        sub_feats = cust_features[pd.to_datetime(cust_features["week"]) <= pd.to_datetime(cutoff_dt)]
        res = engine.evaluate(
            customer_id=customer_id,
            config=cfg,
            cutoff_date=cutoff_dt,
            customer_features=sub_feats,
            data=cust_data,
        )
        latest_result = res
        chk1 = res.checks[0].passed
        chk2 = res.checks[1].passed
        chk3 = res.checks[2].passed

        history.append(
            CheckHistory(
                month=m_label,
                history_ok=chk1,
                income_regular=chk2,
                cushion_ok=chk3,
            )
        )

        if became_ready is None and res.ready:
            became_ready = m_label

    current_values = {}
    if latest_result is not None:
        current_values = {
            chk.name: chk.current_value for chk in latest_result.checks
        }
        if len(c_bi) > 0:
            current_values["bill_on_time_pct"] = round(float(c_bi["on_time"].astype(bool).mean()) * 100.0, 1)
        else:
            current_values["bill_on_time_pct"] = 100.0

    return ProgressResponse(
        customer_id=customer_id,
        history=history,
        became_ready=became_ready,
        current_values=current_values,
        meta=get_meta(cfg),
    )


@router.post("/{customer_id}/consent", response_model=ConsentResponse)
def post_customer_consent(
    customer_id: str,
    payload: ConsentRequest,
) -> ConsentResponse:
    """Record consent or opt-out action."""
    verify_customer_exists(customer_id)

    action = payload.action.strip().lower()
    if action not in ("consent", "opt-out"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'consent' or 'opt-out'.",
        )

    log_consent(customer_id, action)
    cfg = get_config()
    return ConsentResponse(
        customer_id=customer_id,
        action=action,
        recorded=True,
        meta=get_meta(cfg),
    )


@router.post("/{customer_id}/funnel-event")
def post_customer_funnel_event(
    customer_id: str,
    payload: FunnelEventRequest,
) -> dict[str, Any]:
    """Record a user conversion funnel milestone (e.g., action_plan_committed, credit_converted)."""
    verify_customer_exists(customer_id)
    log_funnel_event(customer_id, payload.stage, payload.metadata)
    return {
        "customer_id": customer_id,
        "stage": payload.stage,
        "recorded": True,
    }


def _compute_readiness_delta(customer_id: str, before_eval, after_eval) -> ReadinessTransitionDelta:
    status_changed = (before_eval.ready != after_eval.ready) or (before_eval.status_label != after_eval.status_label)
    passed_count = sum(1 for c in after_eval.checks if c.passed)
    
    if before_eval.ready != after_eval.ready:
        if after_eval.ready:
            msg = "Congratulations! This event fulfilled your final policy check and unlocked credit readiness."
        else:
            msg = "Caution: This event reduced your financial cushion or regularity below policy readiness thresholds."
    elif status_changed:
        msg = f"Status updated from '{before_eval.status_label}' to '{after_eval.status_label}'."
    else:
        msg = f"Readiness confirmed: {passed_count}/3 policy checks passing ({after_eval.status_label})."

    return ReadinessTransitionDelta(
        previous_ready=before_eval.ready,
        current_ready=after_eval.ready,
        status_changed=status_changed,
        previous_status=before_eval.status_label,
        current_status=after_eval.status_label,
        checks_passed_count=passed_count,
        total_checks_count=3,
        message=msg,
    )


@router.post("/{customer_id}/ingest/transaction", response_model=IngestEventResponse)
def post_customer_ingest_transaction(
    customer_id: str,
    payload: IngestTransactionRequest,
) -> IngestEventResponse:
    """Ingest a real-time banking/MFS transaction and compute dynamic readiness transition."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    # Baseline readiness before ingestion
    prior_cutoff = get_customer_as_of_date(customer_id)
    before_eval = evaluate_customer(customer_id, config=cfg, cutoff_date=prior_cutoff)

    # Ingest event into SQL persistence
    insert_live_transaction(
        customer_id=customer_id,
        date=payload.date,
        tx_type=payload.type,
        amount=payload.amount,
        description=payload.description,
    )

    # Post-ingestion readiness evaluation
    new_cutoff = get_customer_as_of_date(customer_id)
    after_eval = evaluate_customer(customer_id, config=cfg, cutoff_date=new_cutoff)
    delta = _compute_readiness_delta(customer_id, before_eval, after_eval)

    return IngestEventResponse(
        customer_id=customer_id,
        event_type="transaction",
        recorded=True,
        as_of_date=new_cutoff,
        transition=delta,
        meta=get_meta(cfg, as_of=new_cutoff),
    )


@router.post("/{customer_id}/ingest/balance", response_model=IngestEventResponse)
def post_customer_ingest_balance(
    customer_id: str,
    payload: IngestDailyBalanceRequest,
) -> IngestEventResponse:
    """Ingest a real-time daily closing balance and evaluate cushion/readiness transition."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    prior_cutoff = get_customer_as_of_date(customer_id)
    before_eval = evaluate_customer(customer_id, config=cfg, cutoff_date=prior_cutoff)

    insert_live_daily_balance(
        customer_id=customer_id,
        date=payload.date,
        balance=payload.balance,
        shortfall=payload.shortfall,
    )

    new_cutoff = get_customer_as_of_date(customer_id)
    after_eval = evaluate_customer(customer_id, config=cfg, cutoff_date=new_cutoff)
    delta = _compute_readiness_delta(customer_id, before_eval, after_eval)

    return IngestEventResponse(
        customer_id=customer_id,
        event_type="daily_balance",
        recorded=True,
        as_of_date=new_cutoff,
        transition=delta,
        meta=get_meta(cfg, as_of=new_cutoff),
    )


@router.post("/{customer_id}/ingest/bill", response_model=IngestEventResponse)
def post_customer_ingest_bill(
    customer_id: str,
    payload: IngestBillRequest,
) -> IngestEventResponse:
    """Ingest a utility/telco bill payment and evaluate bill discipline/readiness transition."""
    verify_customer_exists(customer_id)
    verify_coach_consent(customer_id)

    cfg = get_config()
    prior_cutoff = get_customer_as_of_date(customer_id)
    before_eval = evaluate_customer(customer_id, config=cfg, cutoff_date=prior_cutoff)

    insert_live_bill(
        customer_id=customer_id,
        due_date=payload.due_date,
        amount=payload.amount,
        paid_date=payload.paid_date,
        on_time=payload.on_time,
        biller=payload.biller,
    )

    new_cutoff = get_customer_as_of_date(customer_id)
    after_eval = evaluate_customer(customer_id, config=cfg, cutoff_date=new_cutoff)
    delta = _compute_readiness_delta(customer_id, before_eval, after_eval)

    return IngestEventResponse(
        customer_id=customer_id,
        event_type="bill",
        recorded=True,
        as_of_date=new_cutoff,
        transition=delta,
        meta=get_meta(cfg, as_of=new_cutoff),
    )
