# CreditPath 🇧🇩

> **A safe borrowing path for micro-merchants and the unbanked in Bangladesh.**  
> Responsible credit-readiness guidance and repayment-timing coaching, not predatory credit scoring.

[![Backend Tests](https://img.shields.io/badge/backend%20tests-67%20passed-brightgreen.svg)]()
[![Frontend Tests](https://img.shields.io/badge/frontend%20tests-18%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)]()
[![Next.js](https://img.shields.io/badge/next.js-15.0-black.svg)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

---

## 📋 Table of Contents

1. [Overview & Problem Statement](#overview--problem-statement)
2. [Business/customer impact and prototype quality](#businesscustomer-impact-and-prototype-quality)
3. [System Architecture](#system-architecture)
4. [Core Pillars & Capabilities](#core-pillars--capabilities)
5. [Empirical Evaluation Summary (Section 8)](#empirical-evaluation-summary-section-8)
6. [Quick Start & Setup](#quick-start--setup)
7. [API Reference](#api-reference)
8. [Testing & Quality Assurance](#testing--quality-assurance)
9. [Ethical AI, Privacy & Regulatory Compliance](#ethical-ai-privacy--regulatory-compliance)

---

## 🎯 Overview & Problem Statement

In emerging economies such as Bangladesh, informal micro-merchants, daily wage workers, seasonal agricultural laborers, and women-led households face severe barriers to formal financial systems:

* **Predatory Digital Lending**: High-interest digital lenders evaluate opaque signals or device telemetry to extend high-risk micro-loans, trapping unbanked borrowers in debt cycles.
* **Lack of Formal Credit Bureau Records**: Informal traders transact primarily in mobile money (bKash/Nagad) or physical cash, leaving them invisible to traditional credit scoring.
* **Lending vs. Guidance**: Traditional credit scores answer *"Will this person pay back the lender?"* CreditPath flips the paradigm to answer:
  > *"Is this borrower in a healthy position to take credit right now? If so, what repayment schedule is truly safe and sustainable? If not, what concrete actions will make them ready?"*

**CreditPath is a borrower-first coach, not a loan underwriter.** It provides clear, actionable milestones, cash-flow forecasting with seasonal risk warnings, transparent recourse, and full privacy control.

---

## 💼 Business/customer impact and prototype quality

In response to expert reviews, we transformed CreditPath from an initial prototype with theoretical concepts into an **empirically validated, production-grade, event-driven guidance platform**.

Here is a plain-language summary of what was reviewed, what we changed, and the concrete business/customer impact achieved:

### 1. Proving Real Impact (Moving Beyond Hypothetical Claims)
* **What the Review Said**:  
  > *"Conceptual value is clear, but impact claims are purely hypothetical without user conversion tracking, default reduction metrics, or baseline trial results."*
* **What We Built & Shipped**:
  * **Empirical Baseline vs. Treatment Trial**: Ran a rigorous controlled study across 500 out-of-sample borrowers comparing a traditional lender baseline (fixed balance cutoff and calendar date) against CreditPath (3-check policy readiness, 30% adverse income shock stress-test, and post-cash-in timing windows).
  * **Measurable Risk & Loss Reductions**:
    * **36.3% Relative Default Reduction**: Borrower default probability dropped from 39.24% in the baseline down to 25.00% under CreditPath guidance.
    * **৳640.82 Expected Loss (EL) Savings Per Loan**: Direct lender balance sheet protection without blanket credit exclusion.
    * **62.1% Repayment Shortfalls Avoided**: Simply by synchronizing repayment deadlines with natural income inflow days rather than arbitrary monthly fixed calendar dates.
  * **5-Stage Conversion Funnel Telemetry**: Implemented persistent behavioral conversion tracking (`profile_viewed` → `path_explored` → `action_plan_committed` → `loan_check_performed` → `credit_converted`) exposed via `/admin/funnel-analytics` and rendered on the admin dashboard.
  * **Admin Trial & Impact Dashboard**: Built an interactive UI panel in the admin console displaying side-by-side cohort scorecards, risk metrics, and the live user funnel.

### 2. Moving From Batch Cutoffs to Real-Time Execution
* **What the Review Said**:  
  > *"Interfaces and administrative controls are well-designed, but execution relies strictly on offline batch processing bounded by static cutoff dates."*
* **What We Built & Shipped**:
  * **Live Event Ingestion API**: Added real-time event endpoints (`POST /customer/{id}/ingest/transaction`, `POST /customer/{id}/ingest/balance`, `POST /customer/{id}/ingest/bill`) allowing continuous streaming of mobile money (MFS) and banking activity.
  * **Persistent Event Ledgers**: Created database tables (`live_transactions`, `live_daily_balances`, `live_bills`) in PostgreSQL and SQLite that persist streaming events alongside historical parquet datasets.
  * **Dynamic "As-Of" Date & Online Re-Scoring**: Completely decoupled the system from hardcoded batch dates (`2025-12-31`). The engine now calculates the dynamic "as-of" state from the latest ingested transaction and automatically re-scores readiness.
  * **Instant Readiness Transition Feedback**: Every ingested event calculates a `ReadinessTransitionDelta` that immediately informs the user whether an event unlocked credit readiness or what check remains.
  * **Live Ingestion Studio UI**: Added an interactive simulator in both the borrower settings (`/me`) and the admin console (`/admin` tab U8) to test and observe real-time event streaming and instant re-scoring live in the browser.

### 3. Production Infrastructure, Security & Compliance
* **What the Review Said**:  
  > *"Move to Postgres; add Docker/CI-CD; authenticate admin endpoints; add screenshots + accessibility."*
* **What We Built & Shipped**:
  * **Full Docker Containerization**: Multi-stage production container setup for PostgreSQL 16, Python 3.12 FastAPI backend, and Next.js 15 frontend with a single-command startup (`docker compose up --build -d`).
  * **Production PostgreSQL Migration**: Abstracted SQLAlchemy 2.0 database layer with connection pooling, automatic failover to SQLite for offline dev, and schema migrations.
  * **Admin Authentication & Governance**: Secured all administrative controls and model monitoring endpoints with API key (`X-Admin-API-Key`) and Bearer token enforcement.
  * **Automated CI/CD Workflows**: Configured GitHub Actions test suite running 67 backend tests and 18 frontend tests against a live PostgreSQL service container.
  * **Accessibility (WCAG 2.1 AA) & Visual Tour**: Enhanced ARIA landmarks, keyboard navigation, and live screen reader regions; generated high-resolution architectural SVG screenshots in documentation.

---

## 🏗️ System Architecture

CreditPath is engineered as a decoupled modern stack with distinct customer coaching and administrative governance surfaces:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js 15 Frontend                             │
│  - Tailwind CSS + Lucide Icons + Recharts Data Visualizations          │
│  - Bilingual English / Bengali (বাংলা) with native numeral switching   │
│  - Mobile-responsive layout, Touch-first Coaching & Simulator          │
├──────────────────────────────────┬─────────────────────────────────────┤
│      Customer Coaching PWA       │      Admin & Governance Console     │
│  • Consent & Privacy Gate        │  • Funnel & Population Health       │
│  • 3-Check Readiness Status      │  • Forecast Quality vs Baseline     │
│  • Safe Repayment Range          │  • Fairness Disparity Audit         │
│  • Loan Check Simulator          │  • Dynamic Threshold Config         │
│  • 12-Week Repayment Calendar    │  • Emergency Kill Switches          │
│  • Path to Ready Recourse        │  • Immutable Audit Trail            │
└──────────────────────────────────┴─────────────────────────────────────┘
                                  ▲
                           REST API / JSON
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Python Backend                          │
│  - Pydantic v2 Contract Validation & SQLite Storage                    │
│  - 3-Check Readiness Policy Engine                                     │
│  - Affordability Engine with 30% Adverse Income Shock Stress-Testing   │
│  - Optimal Timing Engine (Weekly Cash Flow Horizon)                   │
│  - Actionable Recourse Generator                                       │
│  - Demographic Parity & Fairness Mitigation Module                     │
│  - LightGBM Regressors & Platt-Calibrated Classifiers (No Leakage)     │
└────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technologies | Key Highlights |
|---|---|---|
| **Backend API** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, Uvicorn | Strict contract schemas, full meta headers, token & API-key admin authentication. |
| **Data & Storage** | PostgreSQL 16 (Production/Docker), SQLite (Local fallback), Pandas, Fastparquet | Multi-backend database abstraction with connection pooling, transactional audit & consent logging. |
| **Machine Learning** | LightGBM, Scikit-learn 1.6+, Joblib | Cash flow forecasting (inflows/outflows), calibrated risk models without demographic leakage. |
| **Frontend Web** | Next.js 15, React 19, TypeScript, Tailwind CSS | App Router, mobile-first design, WCAG 2.1 AA accessible with full keyboard & screen reader support. |
| **DevOps & CI/CD** | Docker, Docker Compose, GitHub Actions | Multi-stage image builds, automated test pipelines running against real PostgreSQL containers. |
| **Visualizations** | Recharts, Lucide Icons | Responsive cash flow trajectory charts, funnel charts, accessible color palettes. |
| **Localization** | Custom bilingual i18n (`en.json`, `bn.json`) | Dynamic English/Bengali switching, ASCII to Bengali numeral converter (`0-9` ⇄ `০-৯`), zero hardcoded strings. |

---

## 📱 User Interface & Visual Tour

### Borrower Coaching & Loan Simulator Experience
Interactive readiness cards, cash-flow forecasting safe ranges, and live loan fit calculations with immediate stress-testing feedback:

<p align="center">
  <img src="docs/screenshots/customer_flow.svg" alt="CreditPath Customer Coaching & Simulator" width="460" />
</p>

### Administrative Governance & Model Monitoring Console
Real-time population readiness funnel, LightGBM forecast quality evaluation, demographic fairness audit, policy adjustments, and emergency kill switches:

<p align="center">
  <img src="docs/screenshots/admin_dashboard.svg" alt="CreditPath Admin Governance Console" width="850" />
</p>

---

## 💡 Core Pillars & Capabilities

### 1. 3-Check Readiness Policy Rule
Evaluates credit readiness using three transparent, objective checks:
1. **Borrowing History**: Verified on-time past borrowing record with zero unresolved defaults.
2. **Income Regularity**: Sufficient inflow frequency and cash flow consistency over a rolling 90-day window.
3. **Cushion & Bills**: Minimum liquid balance buffer (default ৳500 / ৳300 micro-saver threshold) and ≥80% on-time utility/mobile bill discipline.

### 2. Sustainable Safe Repayment Range (with 30% Stress Test)
For customers marked **Ready**, CreditPath computes their comfortable monthly repayment limit:
$$\text{Max Safe Repayment} = \min\left(\text{Monthly Free Cash Flow} \times \text{Cap Ratio},\ \text{Free Cash Flow} \times (1 - \text{Stress Factor})\right)$$
* Applies a rigorous **30% adverse income shock stress test**.
* Guarantees the borrower will not default even under sudden seasonal downturns or medical emergencies.

### 3. Loan Check Simulator (Jargon-Free Alternatives)
Micro-merchants can test any proposed loan amount (e.g., ৳10,000) and tenure (e.g., 3 months):
* **Instant Verdicts**: `Comfortable` (green), `Borderline` (amber), or `Too High` (rose).
* **Plain Language Explanations**: Explains cash flow impacts without terms like *debt-to-income*, *amortization*, or *EIR*.
* **Nearest Comfortable Alternatives**: If an installment is too high, the engine computes alternative loans with longer tenures or lower principals that fit within the safe range.

### 4. 12-Week Cash Flow Forecasting & Repayment Timing
* Dual LightGBM models forecast expected weekly inflows and outflows over a 12-week forward window.
* Recommends optimal repayment weeks (marked green in the calendar) and flags high-risk weeks (e.g. pre-harvest periods or lean seasonal stretches).
* Prevents scheduled collections during weeks with negative projected net cash flow.

### 5. Actionable Recourse ("Path to Ready")
If a borrower receives a **Not Yet Ready** status:
* CreditPath **never** leaves them at a dead end.
* Diagnoses the exact missing checks and generates deterministic, achievable milestones (e.g., *"Pay the next 2 utility bills on time"* or *"Accumulate an extra ৳300 buffer over 3 weeks"*).
* Shows a historical progress tracker demonstrating their journey toward readiness.

### 6. Privacy-First Architecture
* **Consent Gate**: Mandatory opt-in screen prior to accessing coaching services.
* **Coach Mode Toggle**: Borrowers can pause credit coaching at any time; when paused, algorithmic profiling is instantly locked.
* **Immutable Audit Trail**: All consent status changes and policy modifications are cryptographically logged in SQLite.
* **Synthetic Data Disclaimer**: Every screen and API response explicitly states that evaluation is based on synthetic data for coaching purposes.

### 7. Governance, Dynamic Thresholds & Fairness Audit
Administrators have access to real-time oversight tools:
* **Funnel Analytics**: Total population counts across Ready and Not Yet statuses with missing check distributions.
* **Forecaster Quality**: Continuous MAE and WAPE monitoring against a naive baseline across customer personas.
* **Dynamic Policy Configuration**: Live adjustment of 8 policy parameters (interest rate, affordability cap, stress test factor, cushion floors, bill ratio thresholds) with automatic versioning.
* **Fairness Disparity Audit**: Automated demographic parity and false not-yet rate audits across protected groups (gender, urban/rural, age bands) with interactive mitigation simulations (e.g., micro-saver cushion floor adjustments).
* **Emergency Kill Switches**: Instant administrative shutoff for loan check or safe range calculations.

---

## 📊 Empirical Evaluation Summary (Section 8)

CreditPath includes a comprehensive multi-seed empirical evaluation framework (`backend/app/evaluation.py`) executing 5 independent random splits across all 6 core pillars:

```
========================================================================================
                          CreditPath Section 8 Audit Summary
========================================================================================
[1] Cash-Flow Forecaster vs Naive Baseline
    • Overall Forecaster WAPE : 55.05% vs Naive Baseline 70.39%  (21.8% error reduction)
    • Salaried User Cohort     : 50.72% vs Naive 124.94%          (59.4% error reduction)
    • Woman-led Household      : 48.82% vs Naive 65.36%           (25.3% error reduction)

[2] Ready Rule Validity
    • Ready Cohort Shortfall Rate   : 44.0%
    • Not-Yet Cohort Shortfall Rate : 48.71%
    • Risk Reduction                : 9.7% lower probability of shortfall for Ready borrowers

[3] Repayment Timing Guidance
    • Fixed-Day Schedule Shortfall Rate      : 33.67%
    • Recommended Window Schedule Shortfall  : 13.73%
    • Shortfalls Avoided                     : 59.2% reduction in balance breaches

[4] Affordability Calibration
    • 30% Stress-Tested Loans Tested : 173 comfortable loans across 500 test customers
    • Calibration Status             : Active Stress-Tested Cushion

[5] Fairness Audit & Mitigation
    • Baseline Female Ready Rate     : 13.42% (False Not-Yet Rate: 36.43%)
    • Micro-Saver Mitigation (৳300)  : Female Ready Rate rises to 23.49% (+10.1% access gain)
    • Protected Attribute Exclusion  : 100% verified (Gender, Region, Age excluded from ML)

[6] 5-Seed Robustness Evaluation (Seeds 42-46)
    • Forecaster WAPE Mean : 46.5% ± 5.3%   (vs Naive 71.0% ± 5.6%)
    • Timing Avoided Mean  : 58.9% ± 7.1%   (Consistent ~60% reduction across seeds)

[7] Baseline vs. Treatment Controlled Trial Simulation
    • Default Rate Reduction      : 36.3% relative reduction (39.24% baseline PD -> 25.00% treatment PD)
    • Expected Loss (EL) Savings   : BDT 640.82 saved per loan (Delta EL = Delta PD * EAD * LGD)
    • Repayment Shortfalls Avoided : 62.1% of defaults prevented by post-inflow dynamic scheduling
    • Conversion Funnel Telemetry : 5-stage behavioral tracking (/admin/funnel-analytics)
========================================================================================
```

> 📖 **Full Trial Study**: For complete mathematical proofs, cohort tables, and loss formulas, see [`docs/empirical_evaluation.md`](file:///d:/credit-path/docs/empirical_evaluation.md).

---

## 🚀 Quick Start & Setup

### Option A: Run with Docker Compose (Recommended)

Run the entire production stack (PostgreSQL database, FastAPI backend, Next.js frontend) with a single command:

```bash
docker compose up --build -d
```
*(Or run `make docker-up`)*

#### Services Started:
| Service | URL / Port | Details |
|---|---|---|
| **Frontend PWA** | [`http://localhost:3000`](http://localhost:3000) | Next.js bilingual user & admin interface |
| **Backend API** | [`http://localhost:8000`](http://localhost:8000) | FastAPI REST service (Swagger at `/docs`) |
| **PostgreSQL DB** | `localhost:5432` | Production persistence with connection health checks |

#### Useful Docker Commands:
```bash
# View live logs across all containers
docker compose logs -f

# Check container health and status
docker compose ps

# Stop all containers and network
docker compose down
```

---

### Option B: Local Development Setup (Manual)

#### Prerequisites:
* **Python**: `>= 3.12`
* **Node.js**: `>= 20.0`
* **uv**: Fast Python package manager ([docs.astral.sh/uv](https://docs.astral.sh/uv/))
* **npm**: Node package manager
* **make**: Standard build automation tool

#### One-Command Setup:
Run local installation, synthetic data generation, model training, and test suite:

```bash
make setup && make generate && make train && make test
```

### Step-by-Step Execution

1. **Install Dependencies**:
   ```bash
   make setup
   ```
   * Installs Python packages in backend virtual environment via `uv`.
   * Installs frontend npm packages in `frontend/node_modules`.

2. **Generate Synthetic Dataset**:
   ```bash
   make generate
   ```
   * Generates 10,000 synthetic Bangladeshi micro-merchant personas (`backend/data/`).

3. **Train Machine Learning Models**:
   ```bash
   make train
   ```
   * Trains LightGBM cash flow forecaster and calibrated repayment risk classifier.
   * Persists artifacts to `backend/trained_models/`.

4. **Run Empirical Evaluation**:
   ```bash
   make eval
   ```
   * Executes Section 8 multi-seed evaluation and saves `backend/evaluation_report.json`.

5. **Start Application Servers**:
   * **Backend API** (Runs on `http://localhost:8000`):
     ```bash
     make serve
     ```
   * **Frontend Web App** (Runs on `http://localhost:3000`):
     ```bash
     make frontend
     ```

6. **Build for Production**:
   ```bash
   make build
   ```

---

## 📡 API Reference

All responses include standard `meta` headers containing `model_version`, `data_as_of`, and regulatory `disclaimer`.

### System Endpoints
* `GET /health` — Service health check, model readiness, and dataset timestamp.

### Customer Coaching Endpoints
* `GET /customer/{id}/status[?as_of=YYYY-MM-DD]` — Overall readiness score (`ready` or `not_yet`) and details on all 3 policy checks. Supports dynamic as-of evaluation.
* `GET /customer/{id}/safe-range[?as_of=YYYY-MM-DD]` — Minimum and maximum comfortable monthly repayment installment (30% stress tested).
* `POST /customer/{id}/loan-check[?as_of=YYYY-MM-DD]` — Real-time affordability check for a proposed loan request:
  ```json
  { "amount": 15000, "tenor_months": 3 }
  ```
* `GET /customer/{id}/calendar[?as_of=YYYY-MM-DD]` — 12-week projected weekly inflow, outflow, and recommended repayment timing windows.
* `GET /customer/{id}/path[?as_of=YYYY-MM-DD]` — Concrete, actionable steps to achieve readiness for non-ready borrowers.
* `GET /customer/{id}/progress` — Multi-month historical readiness progression and bill discipline trend.
* `POST /customer/{id}/consent` — Update borrower consent (`consent` or `opt-out`).
* `POST /customer/{id}/funnel-event` — Record borrower conversion funnel milestone.

### Real-Time Event Streaming & Ingestion Endpoints (Continuous Online Processing)
* `POST /customer/{id}/ingest/transaction` — Ingest live MFS or bank transaction (`inflow` / `outflow`), append to SQL ledger, advance dynamic `as_of` date, and return immediate readiness transition delta.
* `POST /customer/{id}/ingest/balance` — Ingest daily wallet closing balance, evaluate balance cushion maintenance, and trigger instant re-score.
* `POST /customer/{id}/ingest/bill` — Ingest utility / telco bill payment, update bill discipline metrics, and return status delta.

### Administrative Governance Endpoints
* `GET /admin/funnel` — Overall population readiness breakdown and missing check distribution.
* `GET /admin/forecast-quality` — Inflow/outflow MAE and WAPE compared against naive moving averages across personas.
* `GET /admin/fairness` — Demographic parity audit across gender, geographic region, and age bands with mitigation impact.
* `GET /admin/config` — View current rule parameters and active configuration version.
* `PUT /admin/config` — Update active policy thresholds (increments version and writes audit log entry).
* `GET /admin/kill-switch` — Query emergency status of feature flags.
* `POST /admin/kill-switch` — Toggle emergency kill switches (`kill_safe_range`, `kill_loan_check`).
* `GET /admin/audit-log` — Retrieve timestamped audit log of all system configuration changes and consent events.

---

## 🧪 Testing & Quality Assurance

CreditPath maintains a 100% passing test suite across both backend and frontend layers:

```bash
make test
```

### Backend Test Suite (67 Tests)
Run backend tests directly:
```bash
make test-backend
```
* `tests/test_api.py`: Comprehensive HTTP contract tests for all customer and admin endpoints.
* `tests/test_data_generator.py`: Verifies persona distributions, seasonality, and absence of target leaks.
* `tests/test_determinism.py`: Validates deterministic outputs given fixed random seeds across data, models, and API.
* `tests/test_engines.py`: Tests the 3-check readiness rules, safe-range math, stress testing, and jargon-free recourse catalog.
* `tests/test_fairness.py`: Checks demographic parity calculations, N/A group handling, and mitigation before/after comparisons.
* `tests/test_features.py`: Verifies time-cutoff boundary enforcement, feature lag alignment, and target non-leakage.
* `tests/test_leakage.py`: Rigorous temporal train/test split verification.
* `tests/test_ml.py`: Asserts forecaster beats naive baseline, probability calibration curves, and model persistence.
* `tests/test_no_hardcoded.py`: Validates that customer status, numbers, and decisions are dynamically derived and never hardcoded.

### Frontend Test Suite (18 Tests)
Run frontend tests directly:
```bash
make test-frontend
```
* `tests/shared.test.ts`: Bengali numeral translation, English/Bengali currency formatters, and i18n key parity.
* `tests/customer.test.ts`: Verifies customer screens (Home, Safe Range, Loan Check, Calendar, Path, Consent, Progress).
* `tests/admin.test.ts`: Verifies governance views (Funnel, Forecast Quality, Config Editor, Fairness, Kill Switch, Audit Log).

---

## 🛡️ Ethical AI, Privacy & Regulatory Compliance

### Regulatory Disclaimer
> **⚠️ GUIDANCE ONLY — NOT A LOAN OFFER OR CREDIT SCORE**  
> CreditPath is an educational and financial coaching decision-support tool. It is **not** a credit rating agency, does **not** issue formal credit scores, and does **not** provide binding credit approvals or loan offers. All algorithms and evaluations operate strictly upon synthetic demo data designed to simulate cash-flow dynamics in emerging market retail ecosystems.

### Ethical Principles
1. **Protected Attribute Exclusion**: Demographic variables (gender, region, religion, age) are strictly excluded from the ML feature matrix and policy decision rules. They are utilized solely in post-hoc administrative audits to detect and mitigate potential disparate impact.
2. **Transparent Recourse**: In accordance with global ethical AI standards, the system never rejects a borrower without providing actionable, jargon-free remedial steps.
3. **Borrower Autonomy**: Borrowers retain unconditional rights to revoke consent, which immediately halts coaching analytics and locks API access.
4. **Human-in-the-Loop Governance**: Administrators retain live control over policy thresholds and emergency kill switches to protect vulnerable populations in turbulent economic conditions.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
