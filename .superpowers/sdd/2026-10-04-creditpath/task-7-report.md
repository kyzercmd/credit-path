# Task 7 Report: REST API (B13)

**Execution Status**: DONE

## Overview
Implemented the complete REST API for CreditPath using FastAPI (`backend/app/main.py`, `backend/app/api/customer.py`, `backend/app/api/admin.py`, B13). Every response is computed on demand from real models and rules, strictly adheres to Pydantic schemas, provides full traceability (`model_version`, `data_as_of`, `disclaimer`), supports consent opt-in/opt-out gating, implements policy kill-switches, and eliminates all prohibited financial jargon in customer texts.

## Components Implemented

1. **FastAPI Application & Lifespan (`backend/app/main.py`)**
   - Application instance with `title="CreditPath API"`, `version="0.1.0"`.
   - Permissive CORS middleware (`allow_origins=["*"]`, `allow_credentials=True`, all methods/headers) for Next.js frontend integration.
   - Lifespan context manager:
     - Automatically runs `init_db()` and seeds baseline config version 1 in SQLite if fresh.
     - Loads trained forecaster and risk estimators into memory/state.
     - Sets `app.state.model_loaded = True`, `model_version`, and `data_as_of`.
   - Mounted routers: `/customer` and `/admin`.
   - Health endpoint: `GET /health` returning `HealthResponse` (`status="ok"`, `model_loaded=True`, `model_version`, `data_as_of`, `disclaimer`, `meta`).

2. **Customer Coach Router (`backend/app/api/customer.py`)**
   - **Consent Enforcement**: Returns HTTP 403 (`{"detail": "Customer has turned off credit coaching. Turn coach on in settings to resume."}`) when a customer has opted out (`get_consent_status(id) == 'opt-out'`).
   - **Customer Validation**: Nonexistent customer IDs return HTTP 404 Not Found.
   - **Kill Switch Enforcement**: Returns HTTP 403 Forbidden with plain policy reason when `config.kill_safe_range` or `config.kill_loan_check` is engaged.
   - **Traceability**: Every customer response includes standard `meta` (`model_version`, `data_as_of`, `disclaimer`).
   - Endpoints:
     - `GET /customer/{id}/status`: Evaluates readiness and 3 policy checks via `evaluate_customer`.
     - `GET /customer/{id}/safe-range`: Only accessible to "Ready" customers (returns 400 for "Not yet"); calculates sustainable monthly range and stressed range via `calculate_safe_range`.
     - `POST /customer/{id}/loan-check`: Amortized repayment calculations, verdicts ("Comfortable", "Tight", "Too much"), stress test checks, and nearest comfortable search via `evaluate_loan_check`.
     - `GET /customer/{id}/calendar`: Multi-week cash-flow forecast and optimal payment windows via `generate_calendar_forecast`, with dynamic `HeadsUpCard` generation for tight weeks.
     - `GET /customer/{id}/path`: Transparent recourse steps for unpassed checks via `compute_recourse_path`.
     - `GET /customer/{id}/progress`: 12-month historical checks progress evaluation over past months in the dataset, identifying `became_ready` milestone and latest metrics.
     - `POST /customer/{id}/consent`: Records consent/opt-out actions to SQLite via `log_consent`.

3. **Admin Monitoring & Control Router (`backend/app/api/admin.py`)**
   - `GET /admin/funnel`: Computes readiness counts across total customers (10,000) and aggregates missing check counts ("History", "Regularity", "Cushion & Bills") using vectorized evaluation.
   - `GET /admin/forecast-quality`: Computes weekly MAE/WAPE vs naive baseline on test split, with breakdown across all 5 personas (`wage_worker`, `seasonal_farmer`, `informal_merchant`, `woman_led_household`, `salaried_user`).
   - `GET /admin/fairness`: Disparity audit and policy mitigation impact across protected demographic groups via `compute_fairness_report`.
   - `GET /admin/config`: Retrieves active policy configuration, version number, and timestamp.
   - `PUT /admin/config`: Updates thresholds in active config, invalidates caches, persists new version to SQLite via `save_config_version`, and returns updated `ConfigResponse`.
   - `POST /admin/kill-switch`: Updates `kill_safe_range` and `kill_loan_check`, persists to SQLite via `save_kill_switch`, and returns `KillSwitchResponse`.
   - `GET /admin/audit-log`: Returns audit log events from SQLite via `get_audit_log()`.

4. **Engine Convenience Helpers & Schema Enhancements**
   - Added module-level aliases and convenience functions: `evaluate_customer` in `ready.py`, `calculate_safe_range` and `evaluate_loan_check` in `affordability.py`, `generate_calendar_forecast` in `timing.py`, and `compute_recourse_path` in `recourse.py`.
   - Updated `database.py` with `get_latest_config_version()` and initial config seeding in `init_db()`.
   - Enhanced `schemas.py` with `HeadsUpCard`, `KillSwitchResponse`, `AuditEvent`, `AuditLogResponse`, and `meta` fields across all responses.

5. **Test Suite (`backend/tests/test_api.py`)**
   - 11 comprehensive integration tests covering all customer and admin endpoints, consent gating, kill-switch behavior, config versioning, traceability metadata, and zero prohibited financial jargon.

## Test Verification
- API test suite (`uv run pytest tests/test_api.py -v`): 11 passed in 11.93s
- Full test suite (`uv run pytest -v`): 49 passed in 40.84s (100% pass rate)
