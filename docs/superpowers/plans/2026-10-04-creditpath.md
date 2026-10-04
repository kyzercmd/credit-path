# CreditPath Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete loan-readiness and repayment-timing coaching app (CreditPath) with a Python/FastAPI backend, LightGBM ML models, synthetic data generation, and a Next.js React frontend — all computed from real data, nothing mocked except the dataset itself.

**Architecture:** Python backend with FastAPI serving REST endpoints, SQLite for persistence, LightGBM for cash-flow forecasting, logistic regression for risk scoring. Next.js frontend with Tailwind CSS, mobile-first design (360-430px), white theme with upay brand accents. The synthetic data generator creates 10,000 customers with 12 months of daily wallet activity from latent traits. Models are trained and saved to disk, loaded at API startup.

**Tech Stack:** Python 3.14, FastAPI, uvicorn, LightGBM, scikit-learn, numpy, pandas, SQLite (stdlib), uv for deps | Next.js 15, React 19, Tailwind CSS, TypeScript, Recharts

## Global Constraints

- **No mocks:** Every number in the UI/API is computed at request time from real models/rules. The only simulated thing is the synthetic dataset.
- **No hardcoded outputs:** No canned responses, random values, fake API stubs, placeholder text, or "demo mode."
- **Traceability:** Every API response includes `model_version`, `data_as_of`, and `disclaimer` fields.
- **Not-enough-data:** If a component lacks data, show honest "not enough data" state. Never substitute a default.
- **Protected attributes:** Gender, religion, region, age are NEVER model inputs. They exist in an audit-only table for fairness reporting.
- **Tone:** No jargon (EMI, surplus, PD). Plain words. No urgency, blame, or pressure.
- **Footer:** Every screen: "Built on synthetic data. Guidance only, not a loan offer."
- **Reproducibility:** Models trained with fixed seed, saved to disk, reload to identical outputs.
- **Splits:** Customer-level hold-out + time-based split. Never random row split.
- **Currency:** Shown as ৳ (Bangladeshi Taka).
- **Config-driven:** Ready thresholds, affordability cap, stress %, illustrative rate are all editable and change results.

---

### Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/schemas.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/next.config.ts`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/i18n/en.json`
- Create: `frontend/src/i18n/bn.json`
- Create: `Makefile`
- Create: `README.md`
- Create: `.gitignore`

**Interfaces:**
- Produces: `Config` pydantic model with all tunable thresholds; `get_db()` SQLite connection factory; `StatusResponse`, `SafeRangeResponse`, `LoanCheckRequest/Response`, `CalendarResponse`, `PathResponse`, `ProgressResponse`, `ConsentRequest`, `AdminFunnelResponse`, `ForecastQualityResponse`, `FairnessResponse`, `ConfigResponse` pydantic schemas; frontend API client with typed fetch wrappers; translation JSON files with all UI strings.

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
*.db
backend/trained_models/
backend/data/*.parquet
backend/data/*.csv
node_modules/
.next/
frontend/.next/
frontend/node_modules/
.env
*.egg-info/
dist/
```

- [ ] **Step 2: Create `backend/pyproject.toml` and install deps**

```toml
[project]
name = "creditpath"
version = "0.1.0"
description = "Loan-readiness and repayment-timing coach"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.9",
    "numpy>=2.0",
    "pandas>=2.2",
    "lightgbm>=4.5",
    "scikit-learn>=1.5",
    "scipy>=1.14",
]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27"]
```

Run: `cd backend && uv venv && uv pip install -e ".[dev]"`

- [ ] **Step 3: Create `backend/app/__init__.py`** (empty)

- [ ] **Step 4: Create `backend/app/config.py`**

The central config with all tunable thresholds. Every engine reads from this.

```python
"""
CreditPath configuration — all tunable thresholds live here.
Loaded once at startup; the admin PUT /config endpoint updates the DB
and reloads this at runtime.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Config:
    # --- Ready rule thresholds (Section 1) ---
    min_history_months: int = 3
    regularity_n: int = 8          # income in at least N of last M weeks
    regularity_m: int = 12
    min_balance_pct_days: float = 0.70   # balance above min in X% of days
    min_balance_threshold: float = 500.0  # the "minimum" balance floor (৳)
    bill_on_time_pct: float = 0.60       # bills paid on time in Y% of cases

    # --- Affordability (F2, F3) ---
    affordability_cap: float = 0.40      # max share of surplus for repayment
    stress_pct: float = 0.30             # income-drop stress test
    illustrative_rate: float = 0.15      # annual interest rate for loan-check

    # --- Model ---
    forecast_weeks: int = 8
    model_version: str = "v1"
    data_as_of: str = ""                 # set after data generation

    # --- Kill switch ---
    kill_safe_range: bool = False
    kill_loan_check: bool = False

    # --- Disclaimer ---
    disclaimer: str = "Built on synthetic data. Guidance only, not a loan offer."

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid})


# Global mutable config — reloaded on admin config change
_config = Config()


def get_config() -> Config:
    return _config


def update_config(new: Config) -> None:
    global _config
    _config = new
```

- [ ] **Step 5: Create `backend/app/database.py`**

SQLite persistence for consent, config versions, kill switch, audit log.

```python
"""SQLite persistence layer (B11)."""
from __future__ import annotations
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "creditpath.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS consent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            action TEXT NOT NULL,          -- 'consent' or 'opt-out'
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS config_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_json TEXT NOT NULL,
            changed_by TEXT NOT NULL DEFAULT 'system',
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS kill_switch_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_json TEXT NOT NULL,
            changed_by TEXT NOT NULL DEFAULT 'system',
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def log_audit(event_type: str, details: str) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (event_type, details, timestamp) VALUES (?, ?, ?)",
        (event_type, details, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def log_consent(customer_id: str, action: str) -> None:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO consent_log (customer_id, action, timestamp) VALUES (?, ?, ?)",
        (customer_id, action, now),
    )
    conn.commit()
    conn.close()
    log_audit("consent", json.dumps({"customer_id": customer_id, "action": action}))


def save_config_version(config_dict: dict, changed_by: str = "system") -> None:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO config_versions (config_json, changed_by, timestamp) VALUES (?, ?, ?)",
        (json.dumps(config_dict), changed_by, now),
    )
    conn.commit()
    conn.close()
    log_audit("config_change", json.dumps({"changed_by": changed_by}))


def save_kill_switch(state: dict, changed_by: str = "system") -> None:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO kill_switch_log (state_json, changed_by, timestamp) VALUES (?, ?, ?)",
        (json.dumps(state), changed_by, now),
    )
    conn.commit()
    conn.close()
    log_audit("kill_switch", json.dumps({"changed_by": changed_by, "state": state}))


def get_audit_log() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT event_type, details, timestamp FROM audit_log ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_consent_status(customer_id: str) -> str | None:
    conn = get_db()
    row = conn.execute(
        "SELECT action FROM consent_log WHERE customer_id = ? ORDER BY id DESC LIMIT 1",
        (customer_id,),
    ).fetchone()
    conn.close()
    return row["action"] if row else None
```

- [ ] **Step 6: Create `backend/app/schemas.py`**

All Pydantic response/request models for the API.

```python
"""Pydantic schemas for API requests and responses (B13)."""
from __future__ import annotations
from pydantic import BaseModel, Field


class Meta(BaseModel):
    model_version: str
    data_as_of: str
    disclaimer: str


class CheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


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
    meta: Meta


class LoanCheckRequest(BaseModel):
    amount: float = Field(gt=0)
    tenor_months: int = Field(gt=0, le=36)


class NearestComfortable(BaseModel):
    amount: float
    tenor_months: int
    monthly_payment: float


class LoanCheckResponse(BaseModel):
    customer_id: str
    amount: float
    tenor_months: int
    monthly_payment: float
    total_repayment: float
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


class CalendarResponse(BaseModel):
    customer_id: str
    weeks: list[WeekForecast]
    recommended_window: str
    avoid_weeks: list[str]
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


class KillSwitchRequest(BaseModel):
    kill_safe_range: bool
    kill_loan_check: bool


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    data_as_of: str


class HeadsUpCard(BaseModel):
    message: str
    suggestion: str
    week: str


class WhyExplanation(BaseModel):
    code: str
    explanation: str
    feature_value: str
```

- [ ] **Step 7: Create Makefile**

```makefile
.PHONY: setup generate train serve frontend dev test clean

setup:
	cd backend && uv venv && uv pip install -e ".[dev]"
	cd frontend && npm install

generate:
	cd backend && uv run python -m app.data.generator

train:
	cd backend && uv run python -m app.ml.train

serve:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev: serve frontend

test:
	cd backend && uv run pytest tests/ -v

clean:
	rm -f backend/creditpath.db
	rm -rf backend/trained_models/
	rm -rf backend/data/
```

- [ ] **Step 8: Create frontend scaffolding**

Create `frontend/package.json`, `tsconfig.json`, `tailwind.config.ts`, `next.config.ts`, `postcss.config.mjs`, `src/app/layout.tsx`, `src/app/globals.css`, `src/lib/api.ts`.

The frontend uses Next.js 15 with App Router, Tailwind CSS, and the upay brand colors as CSS variables. Mobile-first layout centered in a phone-width column on desktop. Noto Sans Bengali + Inter for fonts.

- [ ] **Step 9: Create translation files `frontend/src/i18n/en.json` and `frontend/src/i18n/bn.json`**

All UI strings externalized. English and Bangla. Every status, label, action text, explanation, footer.

- [ ] **Step 10: Commit**

```bash
git add -A && git commit -m "feat: project scaffolding — backend config, schemas, DB, frontend setup, translations"
```

---

### Task 2: Synthetic Data Generator (B1)

**Files:**
- Create: `backend/app/data/__init__.py`
- Create: `backend/app/data/generator.py`
- Create: `backend/app/data/loader.py`
- Test: `backend/tests/test_data_generator.py`

**Interfaces:**
- Consumes: nothing (standalone)
- Produces: `generate_dataset(seed: int, n_customers: int, n_months: int) -> dict[str, pd.DataFrame]` returning tables `customers`, `transactions`, `daily_balances`, `bills`, `customer_attributes`. `load_data() -> dict[str, pd.DataFrame]` loads saved parquet files.

The generator creates 10,000 customers across 5 personas (wage worker, seasonal farmer, informal merchant, woman-led household, salaried user) with 12 months of daily wallet transactions. Each customer has latent traits (income_stability, shock_exposure, bill_discipline) that drive behavior through noise, so models cannot simply invert the generator.

Tables:
- `customers`: customer_id, persona, created_date
- `transactions`: customer_id, date, type (cash_in, cash_out, p2p_in, p2p_out, bill_payment, top_up, merchant_payment), amount, category
- `daily_balances`: customer_id, date, balance
- `bills`: customer_id, due_date, amount, paid_date, on_time (bool)
- `customer_attributes` (audit-only): customer_id, gender, region_type (urban/rural), age_band

Seasonality: month-end pressure, Eid spikes (months 4, 11 approximate), harvest income (months 3, 9 for farmers), income shocks, unexpected expenses.

Planted group differences: women with lower volume but similar reliability. Rural users with seasonal patterns.

Outcome column in daily_balances: `shortfall` (bool) — balance below essentials threshold.

Splits: hold-out 20% of customers by customer_id hash; time split — train months 1-9, test months 10-12. Never random row split.

- [ ] **Step 1: Write tests for data generator**

Test determinism (same seed → identical output), table shapes, persona distribution, no future leakage in splits, planted group differences exist, seasonality present, shortfall column computed correctly.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement `backend/app/data/generator.py`**

Full implementation with latent-trait-based generation, all 5 personas, seasonality, group differences, and proper splits.

- [ ] **Step 4: Implement `backend/app/data/loader.py`**

Save to parquet, load from parquet. `load_data()` returns all tables.

- [ ] **Step 5: Run tests to verify they pass**

- [ ] **Step 6: Run the generator**

```bash
cd backend && uv run python -m app.data.generator
```

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(B1): synthetic data generator — 10K customers, 12 months, 5 personas, latent traits"
```

---

### Task 3: Feature Builder (B2)

**Files:**
- Create: `backend/app/features/__init__.py`
- Create: `backend/app/features/builder.py`
- Test: `backend/tests/test_features.py`

**Interfaces:**
- Consumes: `load_data()` from Task 2
- Produces: `build_features(transactions: DataFrame, balances: DataFrame, bills: DataFrame, cutoff_date: str) -> DataFrame` with columns: customer_id, week, weekly_inflow, weekly_outflow, balance_mean, balance_min, income_regularity_ratio, bill_on_time_ratio, months_active, lag_1_inflow, lag_2_inflow, lag_3_inflow, lag_4_inflow, lag_1_outflow, lag_2_outflow, lag_1_balance, week_of_month, month, is_month_end, is_eid_period, is_harvest_period, day_of_week_mode. All windows relative to explicit cutoff_date — never look past cutoff.

- [ ] **Step 1: Write tests**

Test: no future leakage (all feature values computed only from data before cutoff), correct window sizes, lag features aligned, calendar features correct, handles missing data gracefully.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement feature builder**

All rolling windows, lags, calendar features. Explicit cutoff_date parameter — every aggregation filters `date <= cutoff_date`.

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(B2): feature builder — lag, calendar, rolling features with leakage-safe cutoff"
```

---

### Task 4: ML Models — Forecaster & Risk Model (B3, B8, B12)

**Files:**
- Create: `backend/app/ml/__init__.py`
- Create: `backend/app/ml/forecaster.py`
- Create: `backend/app/ml/risk_model.py`
- Create: `backend/app/ml/train.py`
- Create: `backend/app/ml/model_store.py`
- Test: `backend/tests/test_ml.py`

**Interfaces:**
- Consumes: `build_features()` from Task 3, `load_data()` from Task 2
- Produces:
  - `Forecaster.predict(features: DataFrame) -> DataFrame` with columns `predicted_inflow`, `predicted_outflow` per week
  - `RiskModel.predict_proba(features: DataFrame) -> ndarray` of shortfall probabilities
  - `NaiveBaseline.predict(features: DataFrame) -> DataFrame` (repeat last week's values)
  - `ModelStore.load(name: str) -> model`, `ModelStore.save(model, name: str, metadata: dict)`, `ModelStore.get_version() -> str`
  - `train_all(seed: int)` trains both models and saves to disk

**B3 Forecaster:** LightGBM regressor on lag + calendar features predicting weekly inflow and outflow. Trained on time-split (months 1-9), tested on months 10-12 per customer.

**B8 Risk Model:** Calibrated logistic regression predicting whether a customer will hit a shortfall week in the next period. A LightGBM model with `CalibratedClassifierCV` as the calibrated version. Also includes a logistic-regression baseline for comparison.

**B12 Model Store:** Models saved as joblib files under `backend/trained_models/` with metadata JSON (version, training_date, seed, metrics).

- [ ] **Step 1: Write tests**

Test: model trains and predicts without error, predictions are deterministic with same seed, model saves and loads to identical output, naive baseline returns last-week values, risk model probabilities are in [0,1], calibration improves on raw LightGBM.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement model store**

- [ ] **Step 4: Implement naive baseline**

- [ ] **Step 5: Implement forecaster (LightGBM)**

- [ ] **Step 6: Implement risk model (calibrated)**

- [ ] **Step 7: Implement `train.py` — orchestrates training pipeline**

- [ ] **Step 8: Run tests to verify they pass**

- [ ] **Step 9: Train models**

```bash
cd backend && uv run python -m app.ml.train
```

- [ ] **Step 10: Commit**

```bash
git add -A && git commit -m "feat(B3,B8,B12): LightGBM forecaster, calibrated risk model, model store"
```

---

### Task 5: Core Engines — Ready, Affordability, Timing, Recourse (B4-B7, B9)

**Files:**
- Create: `backend/app/engines/__init__.py`
- Create: `backend/app/engines/ready.py`
- Create: `backend/app/engines/affordability.py`
- Create: `backend/app/engines/timing.py`
- Create: `backend/app/engines/recourse.py`
- Create: `backend/app/engines/reasons.py`
- Test: `backend/tests/test_engines.py`

**Interfaces:**
- Consumes: `Config` from Task 1, `Forecaster` + `RiskModel` from Task 4, `build_features()` from Task 3
- Produces:
  - `ReadyEngine.evaluate(customer_id) -> ReadyResult` (ready bool, 3 checks with pass/fail + reason codes)
  - `AffordabilityEngine.safe_range(customer_id) -> SafeRange` (monthly low/high, stressed low/high)
  - `AffordabilityEngine.loan_check(customer_id, amount, tenor) -> LoanCheckResult` (payment, verdict, stress, nearest comfortable)
  - `TimingEngine.calendar(customer_id) -> CalendarResult` (weekly forecasts, safe/tight weeks, recommended window)
  - `RecourseEngine.path(customer_id) -> list[RecourseStep]` (missing items, actions, estimated weeks)
  - `ReasonCatalog.get(code: str) -> str` (plain-language explanation from fixed catalog)

**B4 Ready Engine:** Three checks against config thresholds. Two states only: Ready or Not yet.

**B5 Affordability:** Surplus = forecasted inflow - forecasted outflow. Safe range = surplus × affordability_cap (config). Stress test: recalculate with income reduced by stress_pct. Loan check: monthly payment = standard amortization with illustrative_rate. Verdict: Comfortable (<40% of surplus), Tight (40-60%), Too much (>60%). Nearest-comfortable search: binary search over amount and tenor.

**B6 Timing:** Weekly forecast for next 4-8 weeks. Safe week: expected balance > min_balance_threshold after typical outflows. Tight week: balance close to or below threshold. Recommended repayment window: 1-2 days after typical income days. Seasonal/festival effects from calendar features.

**B7 Recourse:** Constrained search over actionable features only (bill timing, min balance, regular top-ups, reducing avoidable cash-outs). Each step validated by re-scoring the customer's features with the step applied. Only steps that change the result are shown. Estimated time = weeks until the behavioral change would accumulate enough history to flip the check.

**B9 Reason Catalog:** Fixed dictionary mapping feature names + thresholds to plain-language explanations. E.g., `income_regularity_low` → "Your income arrived in only {n} of the last {m} weeks."

- [ ] **Step 1: Write tests**

Test: Ready engine flips correctly with config changes, affordability range is capped, loan check verdicts are correct at boundaries, stress test reduces range, nearest-comfortable search converges, timing identifies safe/tight weeks correctly, recourse steps are actionable and validated, reason codes cover all features.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement reason catalog**

- [ ] **Step 4: Implement ready engine**

- [ ] **Step 5: Implement affordability engine**

- [ ] **Step 6: Implement timing engine**

- [ ] **Step 7: Implement recourse engine**

- [ ] **Step 8: Run tests to verify they pass**

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat(B4-B7,B9): ready, affordability, timing, recourse engines + reason catalog"
```

---

### Task 6: Fairness Module (B10)

**Files:**
- Create: `backend/app/fairness/__init__.py`
- Create: `backend/app/fairness/module.py`
- Test: `backend/tests/test_fairness.py`

**Interfaces:**
- Consumes: `ReadyEngine` from Task 5, `Forecaster` from Task 4, `load_data()` from Task 2, `customer_attributes` table
- Produces: `FairnessModule.compute(customer_ids) -> FairnessReport` with ready_rate, forecast_error, false_not_yet_rate by gender, region_type, age_band, with counts. Groups with no data → N/A, not 0 or 1. One real mitigation (threshold adjustment for underperforming group) with before/after.

- [ ] **Step 1: Write tests**

Test: N/A for empty groups (not 0 or 1), counts correct, mitigation changes at least one group's rate, protected attributes never used as model inputs.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement fairness module**

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(B10): fairness module — group tables, N/A handling, threshold mitigation"
```

---

### Task 7: REST API (B13)

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/customer.py`
- Create: `backend/app/api/admin.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: All engines from Task 5, fairness from Task 6, config/DB from Task 1, model store from Task 4
- Produces: FastAPI app with all endpoints listed in project.md section 5

Endpoints:
```
GET  /health
GET  /customer/{id}/status
GET  /customer/{id}/safe-range
POST /customer/{id}/loan-check
GET  /customer/{id}/calendar
GET  /customer/{id}/path
GET  /customer/{id}/progress
POST /customer/{id}/consent
GET  /admin/funnel
GET  /admin/forecast-quality
GET  /admin/fairness
GET  /admin/config
PUT  /admin/config
POST /admin/kill-switch
GET  /admin/audit-log
```

Every response includes `model_version`, `data_as_of`, `disclaimer`. CORS enabled for frontend. Kill switch hides safe-range and loan-check (returns 403 with explanation). Consent check on customer endpoints (returns 403 if opted out).

- [ ] **Step 1: Write tests**

Test: all endpoints return correct schemas, model_version/data_as_of/disclaimer present in every response, kill switch hides safe-range and loan-check, consent opt-out blocks customer endpoints, config PUT changes config and is versioned, audit log records events.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement `backend/app/main.py`** — FastAPI app factory, startup event (init_db, load models, load data), CORS

- [ ] **Step 4: Implement `backend/app/api/customer.py`** — all customer endpoints

- [ ] **Step 5: Implement `backend/app/api/admin.py`** — all admin endpoints

- [ ] **Step 6: Run tests to verify they pass**

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(B13): REST API — all customer and admin endpoints with traceability"
```

---

### Task 8: Frontend — Shared Components & Layout

**Files:**
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/components/CheckRow.tsx`
- Create: `frontend/src/components/Card.tsx`
- Create: `frontend/src/components/Button.tsx`
- Create: `frontend/src/components/BottomNav.tsx`
- Create: `frontend/src/components/Footer.tsx`
- Create: `frontend/src/components/WhySheet.tsx`
- Create: `frontend/src/components/Skeleton.tsx`
- Create: `frontend/src/components/ErrorState.tsx`
- Create: `frontend/src/components/EmptyState.tsx`
- Create: `frontend/src/components/LanguageToggle.tsx`
- Create: `frontend/src/components/NumberFormat.tsx`
- Create: `frontend/src/contexts/LanguageContext.tsx`
- Create: `frontend/src/contexts/ConsentContext.tsx`
- Create: `frontend/src/app/page.tsx` (redirect to /home)

**Interfaces:**
- Consumes: Translation files from Task 1, API client from Task 1
- Produces: All shared UI components used by the customer screens in Tasks 9-10. `LanguageContext` with `locale`, `t()` function, `toggleLanguage()`. `ConsentContext` for opt-in/out state.

Design spec (section 7):
- White theme: bg #FFFFFF, borders #E8E8EC
- Text: primary #1A1A1F, secondary #6B6B76
- Accent: upay brand colors as CSS vars (--accent, --accent-soft, --accent-text)
- Status: green Ready/Comfortable, amber Tight, soft red Too much — always with icon + text
- Mobile-first 360-430px, desktop shows phone-width column centered
- Body 16px+, headings 20-28px, Inter + Noto Sans Bengali
- Tap targets 48px+, 16-24px spacing between cards
- Max 3 cards per screen, 1 primary button per screen
- Bottom nav: Home, Loan check, Calendar, Me
- Skeleton loading, friendly empty states, plain error + retry

- [ ] **Step 1: Implement contexts (Language, Consent)**

- [ ] **Step 2: Implement base components (Card, Button, StatusBadge, CheckRow, Footer, Skeleton, ErrorState, EmptyState, NumberFormat)**

- [ ] **Step 3: Implement BottomNav and LanguageToggle**

- [ ] **Step 4: Implement WhySheet (bottom sheet for explanations)**

- [ ] **Step 5: Set up app layout with BottomNav, Footer, font loading**

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: frontend shared components — layout, nav, cards, states, i18n context"
```

---

### Task 9: Frontend — Customer Screens (F1-F8, F10-F11)

**Files:**
- Create: `frontend/src/app/home/page.tsx` (F1 Home)
- Create: `frontend/src/app/safe-range/page.tsx` (F2 Safe Range)
- Create: `frontend/src/app/loan-check/page.tsx` (F3 Loan Check)
- Create: `frontend/src/app/calendar/page.tsx` (F5 Calendar)
- Create: `frontend/src/app/path/page.tsx` (F4 Path to Ready)
- Create: `frontend/src/app/progress/page.tsx` (F8 Progress)
- Create: `frontend/src/app/me/page.tsx` (F10 Privacy, F11 About, language)
- Create: `frontend/src/app/consent/page.tsx` (Consent screen)
- Create: `frontend/src/components/WeeklyChart.tsx` (F5 chart)
- Create: `frontend/src/components/LoanSliders.tsx` (F3 sliders)
- Create: `frontend/src/components/HeadsUpCard.tsx` (F6)

**Interfaces:**
- Consumes: All components from Task 8, API client from Task 1, schemas matching Task 7 responses
- Produces: All 9 customer-facing screens

**F1 Home:** Large status badge (Ready/Not yet), 3 check rows (tick/empty), primary button ("See what I can safely repay" if Ready, "See what's missing" if Not yet). Max 3 cards.

**F2 Safe Range:** Monthly amount range, stressed version ("Still affordable if income drops 30%"), basis line. Hidden if Not yet (shows F4 instead).

**F3 Loan Check:** Amount + tenor sliders, computed monthly payment + total. Verdict (Comfortable/Tight/Too much) with reason. Stress check. If Too much, nearest comfortable suggestion. "Guidance, not an offer."

**F4 Path to Ready:** 1-3 missing items, each with concrete action + estimated time. Only actionable behaviors. "Indicative, based on patterns."

**F5 Calendar:** Weekly forecast bars with balance line (Recharts). Safe/tight week highlights. Recommended repayment window. Weeks to avoid with reason. Seasonal effects.

**F6 Heads-up:** In-app card from forecast. "Your balance may be low..." Only shown when forecast supports it.

**F7 Why:** Every status/range/verdict/step has a "Why?" link opening WhySheet with plain-language explanation from reason codes.

**F8 Progress:** Three checks over real months. "Bill payments on time: 60% → 85%". When became Ready.

**F10 Privacy:** "My data" screen, turn coach off toggle, consent log.

**F11 About:** Plain statement about synthetic data, guidance only, limits.

**Consent:** First-open consent screen with consent log.

- [ ] **Step 1: Implement Consent page (first-open gate)**

- [ ] **Step 2: Implement Home page (F1)**

- [ ] **Step 3: Implement Safe Range page (F2) and HeadsUpCard (F6)**

- [ ] **Step 4: Implement Loan Check page (F3) with LoanSliders**

- [ ] **Step 5: Implement Calendar page (F5) with WeeklyChart**

- [ ] **Step 6: Implement Path to Ready page (F4)**

- [ ] **Step 7: Implement Progress page (F8)**

- [ ] **Step 8: Implement Me page (F10, F11 — privacy, about, language, coach toggle)**

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: customer app — all 9 screens with real data, i18n, why explanations"
```

---

### Task 10: Frontend — Admin Panel (U1-U6)

**Files:**
- Create: `frontend/src/app/admin/page.tsx`
- Create: `frontend/src/components/admin/FunnelTable.tsx` (U1)
- Create: `frontend/src/components/admin/ForecastQuality.tsx` (U2)
- Create: `frontend/src/components/admin/RuleSettings.tsx` (U3)
- Create: `frontend/src/components/admin/FairnessPanel.tsx` (U4)
- Create: `frontend/src/components/admin/KillSwitch.tsx` (U5)
- Create: `frontend/src/components/admin/AuditLog.tsx` (U6)

**Interfaces:**
- Consumes: API client from Task 1, admin endpoints from Task 7
- Produces: Single-page admin panel with all 6 sections

One page, same white theme, tables allowed (the only place with tables). Clean layout.

**U1 Funnel:** Ready/Not yet counts, by which check is missing.
**U2 Forecast Quality:** Weekly MAE/WAPE vs naive baseline, by persona.
**U3 Rule Settings:** Editable thresholds, cap, stress%, rate. Versioned with timestamps.
**U4 Fairness:** Ready rate, forecast error, false-not-yet rate by gender/region/age. N/A for no data. One mitigation before/after.
**U5 Kill Switch:** Toggle to hide Safe range and Loan check.
**U6 Audit Log:** Consent, rule changes, kill-switch changes with timestamp.

- [ ] **Step 1: Implement admin layout and FunnelTable (U1)**

- [ ] **Step 2: Implement ForecastQuality (U2)**

- [ ] **Step 3: Implement RuleSettings (U3)**

- [ ] **Step 4: Implement FairnessPanel (U4)**

- [ ] **Step 5: Implement KillSwitch (U5) and AuditLog (U6)**

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: admin panel — funnel, forecast quality, rules, fairness, kill switch, audit"
```

---

### Task 11: Backend Tests & Evaluation (B14, Section 8)

**Files:**
- Create: `backend/tests/test_leakage.py`
- Create: `backend/tests/test_determinism.py`
- Create: `backend/tests/test_config_effects.py`
- Create: `backend/tests/test_no_hardcoded.py`
- Create: `backend/app/evaluation.py`
- Modify: `backend/tests/test_api.py` (add contract tests)

**Interfaces:**
- Consumes: All backend modules
- Produces: Evaluation report (printed to stdout or saved as JSON), all required test suites

**B14 Tests:**
- Leakage: verify features never use data past cutoff; verify customer splits have no overlap; verify time split is months 1-9 vs 10-12
- Determinism: same seed → identical data, identical model predictions, identical API responses
- Config effects: changing thresholds changes Ready status; changing cap changes safe range; changing rate changes loan payment
- API contract: every response has model_version, data_as_of, disclaimer
- No hardcoded: scan all API responses and frontend translation files for hardcoded numbers/statuses

**Section 8 Evaluation:**
- Forecast: weekly MAE/WAPE vs naive baseline, by persona, irregular/seasonal separately
- Ready rule validity: shortfall rate among Ready vs Not yet on held-out months
- Timing guidance: shortfall weeks avoided with recommended window vs fixed day
- Affordability: how often "Comfortable" verdict followed by shortfall
- Fairness: by gender, region, age, with counts and one mitigation
- Seeds: mean ± std over 5 seeds
- All labeled "synthetic data, relative comparison"

- [ ] **Step 1: Write leakage tests**

- [ ] **Step 2: Write determinism tests**

- [ ] **Step 3: Write config effect tests**

- [ ] **Step 4: Write no-hardcoded scanner test**

- [ ] **Step 5: Implement evaluation script**

- [ ] **Step 6: Run all tests**

```bash
cd backend && uv run pytest tests/ -v
```

- [ ] **Step 7: Run evaluation**

```bash
cd backend && uv run python -m app.evaluation
```

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat(B14): tests — leakage, determinism, config effects, no-hardcoded + evaluation"
```

---

### Task 12: Integration, README, Final Polish

**Files:**
- Modify: `README.md`
- Modify: `Makefile`
- Create: `backend/app/data/__main__.py` (for `python -m app.data.generator`)
- Create: `backend/app/ml/__main__.py` (for `python -m app.ml.train`)

**Interfaces:**
- Consumes: Everything
- Produces: A clean clone → `make setup && make generate && make train && make serve` works end-to-end

- [ ] **Step 1: Write comprehensive README with setup, architecture, and usage**

- [ ] **Step 2: Verify end-to-end flow**

```bash
make clean && make setup && make generate && make train && make test
```

- [ ] **Step 3: Final commit**

```bash
git add -A && git commit -m "docs: README, final integration polish"
```
