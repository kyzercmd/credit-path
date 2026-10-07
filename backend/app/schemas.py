"""Pydantic schemas for API requests and responses (B13)."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Meta(BaseModel):
    model_version: str
    data_as_of: str
    disclaimer: str


class CheckResult(BaseModel):
    name: str
    passed: bool
    reason: str
    reason_code: str = ""
    current_value: float | int | None = None
    target_value: float | int | None = None


class StatusResponse(BaseModel):
    customer_id: str
    ready: bool
    status_label: str
    status_sentence: str
    checks: list[CheckResult]
    meta: Meta


class SafeRangeResponse(BaseModel):
    customer_id: str
    monthly_low: float
    monthly_high: float
    stressed_low: float
    stressed_high: float
    basis_months: int
    basis_sentence: str
    low_confidence: bool = False
    meta: Meta


FinancingStructure = Literal["conventional", "fixed_payment", "interest_free"]


class LoanCheckRequest(BaseModel):
    amount: float = Field(gt=0)
    tenor_months: int = Field(gt=0, le=36)
    # Used only for this calculation; never stored on the profile or used as a model feature.
    financing_structure: FinancingStructure = "conventional"
    total_repayment: float | None = Field(default=None, gt=0)  # fixed_payment only
    provider_fees: float = Field(default=0.0, ge=0)  # interest_free only

    @model_validator(mode="after")
    def _check_structure_inputs(self) -> "LoanCheckRequest":
        if self.financing_structure == "fixed_payment":
            if self.total_repayment is None:
                raise ValueError("total_repayment is required for fixed_payment.")
            if self.total_repayment < self.amount:
                raise ValueError("total_repayment must be greater than or equal to amount.")
        return self


class NearestComfortable(BaseModel):
    amount: float
    tenor_months: int
    monthly_payment: float


class LoanCheckResponse(BaseModel):
    customer_id: str
    amount: float
    tenor_months: int
    financing_structure: FinancingStructure = "conventional"
    monthly_payment: float
    total_repayment: float
    extra_cost: float = 0.0
    surplus_share: float
    verdict: str  # "Comfortable", "Tight", "Too much"
    verdict_reason: str
    stress_verdict: str
    stress_reason: str
    nearest_comfortable: NearestComfortable | None
    meta: Meta


class WeekForecast(BaseModel):
    week_start: str
    money_in: float
    money_out: float
    expected_balance: float
    status: str  # "safe", "tight"
    reason: str


class HeadsUpCard(BaseModel):
    message: str
    suggestion: str
    week: str


class CalendarResponse(BaseModel):
    customer_id: str
    weeks: list[WeekForecast]
    recommended_window: str
    avoid_weeks: list[str]
    heads_up: HeadsUpCard | None = None
    low_confidence: bool = False
    meta: Meta


class PathStep(BaseModel):
    item: str
    action: str
    estimated_weeks: int
    reason: str


class PathResponse(BaseModel):
    customer_id: str
    missing_items: list[PathStep]
    meta: Meta


class CheckHistory(BaseModel):
    month: str
    history_ok: bool
    income_regular: bool
    cushion_ok: bool


class ProgressResponse(BaseModel):
    customer_id: str
    history: list[CheckHistory]
    became_ready: str | None
    current_values: dict
    meta: Meta


class ConsentRequest(BaseModel):
    action: str  # "consent" or "opt-out"


class ConsentResponse(BaseModel):
    customer_id: str
    action: str
    recorded: bool
    meta: Meta | None = None


class FunnelBucket(BaseModel):
    label: str
    count: int


class AdminFunnelResponse(BaseModel):
    total_customers: int
    ready_count: int
    not_yet_count: int
    missing_checks: list[FunnelBucket]
    meta: Meta


class ForecastQualityResponse(BaseModel):
    overall_mae: float
    overall_wape: float
    naive_mae: float
    naive_wape: float
    by_persona: dict[str, dict]
    meta: Meta


class FairnessGroup(BaseModel):
    group: str
    count: int
    ready_rate: float | None
    forecast_error: float | None
    false_not_yet_rate: float | None


class FairnessResponse(BaseModel):
    by_gender: list[FairnessGroup]
    by_region: list[FairnessGroup]
    by_age_band: list[FairnessGroup]
    mitigation: dict
    meta: Meta


class ConfigResponse(BaseModel):
    config: dict
    version: int
    timestamp: str
    meta: Meta | None = None


class KillSwitchRequest(BaseModel):
    kill_safe_range: bool
    kill_loan_check: bool


class KillSwitchResponse(BaseModel):
    message: str
    kill_safe_range: bool
    kill_loan_check: bool
    meta: Meta


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    data_as_of: str
    disclaimer: str = "Built on synthetic data. Guidance only, not a loan offer."
    meta: Meta | None = None


class AuditEvent(BaseModel):
    event_type: str
    details: str
    timestamp: str


class AuditLogResponse(BaseModel):
    events: list[AuditEvent]
    meta: Meta


class WhyExplanation(BaseModel):
    code: str
    explanation: str
    feature_value: str


