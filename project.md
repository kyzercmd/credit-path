CreditPath: Feature List for the Build Agent

What it is: A loan-readiness and repayment-timing coach inside the upay app. It tells a customer (1) whether their cash flow is steady enough to repay a small loan, (2) how much they could safely repay, and (3) which weeks are safest to pay. It gives guidance only. It makes no lending decision and shows no loan offer.

Hackathon: DIU CPC x upay AI Hackathon 2026, Track 03 (Customer Innovation & Financial Independence): Responsible Credit Readiness, Cash-Flow Forecasting.

0. Non-negotiable rules
0.1 Nothing is mocked or simulated except the dataset
The only simulated thing is the synthetic dataset. Everything built on it must be real, computed code.
Every number, status, forecast, date, reason, and step shown in the UI must be computed at request time from the dataset by the real models and rules. No hardcoded outputs, canned responses, random values, fake API stubs, placeholder text, or "demo mode" shortcuts.
No fabricated fast-forward or "coached vs. uncoached" simulation inside the product. Progress over time uses real later months already present in the dataset.
The "loan" a customer checks is a hypothetical amount and tenor typed in by the user. The interest rate used in the calculation comes from a visible config value labeled "illustrative rate". No real loan product is implied.
Models are trained for real, saved to disk, and loaded by the API. Retraining must be reproducible from a fixed seed.
Every API response includes model_version and data_as_of so any number can be traced.
If a component fails or lacks data, the UI shows an honest "not enough data" state. It never substitutes a default value.
Footer or About page on every screen: "Built on synthetic data. Guidance only, not a loan offer."
0.2 Product guardrails
Guidance only: no loan approval, rejection, offer, or score shown as a judgment of the person.
Never use gender, religion, region, or age as model inputs. These live in an audit-only table used by the fairness report.
No urgency language, no pushing a loan, no hidden fees, no upsell.
Every status and number has a plain-language reason.
Forecasts are labeled "estimate based on your past activity".
1. Definition of "Ready"

Ready means: based on your wallet history, you could repay a small loan on time without running short.

A customer is Ready when all three checks pass (thresholds live in a config file and are editable by upay):

Check	Default rule
1. Enough history	3 or more months of wallet activity
2. Steady money in	Money arrives in at least N of the last M weeks (regularity), even if amounts vary
3. A cushion	Balance stays above a minimum in at least X% of days, and utility bills are paid on time in at least Y% of cases

Two states only: Ready or Not yet. If income is too irregular to forecast, the state is Not yet.

2. Customer app features
F1. Home screen
Large status: Ready or Not yet, with one plain sentence.
The three checks shown as tick or empty rows (history, steady income, cushion and bills).
One primary button: "See what I can safely repay" (if Ready) or "See what's missing" (if Not yet).
Maximum 3 cards on the screen.
F2. Safe repayment range
Shows a monthly amount range the customer could repay comfortably, computed as a policy-capped share of the forecasted monthly surplus (money in minus money out).
Shows a stressed version: "Still affordable if your income drops 30%." The stress percentage is config.
Shows the data it rests on in one line: "Based on your last N months."
Hidden if the customer is Not yet, which shows F4 instead.
F3. Loan check (what-if)
User enters an amount and a tenor using simple sliders or steppers.
The app computes the monthly payment using the config rate and shows total repayment.
Verdict in three levels: Comfortable, Tight, Too much, with the reason ("This payment is 62% of your usual spare money").
Stress check: result if income drops by the config percentage.
If Too much, suggests the nearest comfortable combination of amount and tenor, computed by search, not typed in.
Always labeled "guidance, not an offer."
F4. Path to Ready (when Not yet)
Lists the 1 to 3 missing items, most important first.
Each item has one concrete action ("Pay your electricity bill on time next month") and an estimated time to reach Ready.
Steps and timelines come from a recourse calculation: re-scoring the customer's real features with the step applied, and only steps that actually change the result are shown. Label: "indicative, based on patterns in the data."
Only actionable behaviors are suggested (bill timing, minimum balance, regular top-ups, reducing avoidable cash-outs). Nothing the customer cannot change.
F5. Repayment calendar (safe timing)
Weekly forecast of money in, money out, and expected balance for the next 4 to 8 weeks.
Highlights "tight" weeks and "safe" weeks.
Recommends a repayment date window just after typical income days, and marks weeks to avoid, with the reason ("Your wallet usually runs low in week 4").
Seasonal and festival effects are included in the forecast (harvest income, Eid).
One simple chart: weekly bars with the balance line. No other charts in the customer app.
F6. Low-balance heads-up
In-app card, computed from the forecast: "Your balance may be low for your planned payment on the 28th. Consider paying part on the 20th."
Shown only when the forecast supports it. No push notification infrastructure required.
F7. Why this? (explanations)
Every status, range, verdict, and step has a "Why?" link opening a plain-language explanation.
Explanations come from a fixed reason-code catalog mapped from real features and model contributions (for example, "Your income arrived in only 5 of the last 12 weeks"). No free-text generation.
F8. Progress
Shows how the customer's three checks changed over the real months in the dataset ("Bill payments on time: 60% to 85%").
If the customer became Ready, shows when.
F9. Language and number format
English and Bangla toggle on every screen, with Bangla numerals optional.
All strings in a translation file. Bangla text must be reviewed by a native speaker.
Currency shown as ৳.
F10. Privacy and data view
A "My data" screen lists which kinds of data the coach uses (cash-in and out, bills, top-ups, balance) and over what period.
Customer can turn the coach off, which hides all coach screens for that customer.
Plain consent screen on first open, with a consent log entry.
F11. About and limits
Plain statement: synthetic data, guidance only, forecasts can be wrong, not a loan offer, no guarantee.
3. upay internal view (small, 1 page, not for customers)
U1. Readiness funnel
Counts of customers: Ready, Not yet, and by which check is missing.
U2. Forecast quality
Weekly forecast error on held-out data vs. a naive baseline, including for seasonal and irregular earners.
U3. Rule settings
Edit the Ready thresholds, affordability cap, stress percentage, and illustrative rate. Changes are versioned with timestamps and recompute results.
U4. Fairness panel
Ready rate, forecast error, and "false Not yet" rate by gender, rural/urban, and age band, with counts. Groups with no data show N/A, not 0 or 1.
One real mitigation applied, with before and after.
U5. Kill switch
One toggle to hide Safe range and Loan check from all customers.
U6. Audit log
Consent events, rule changes, and kill-switch changes with timestamp and user.
4. Backend features
ID	Feature
B1	Synthetic data generator (see section 6) writing real tables, deterministic by seed
B2	Feature builder with all windows relative to an explicit cutoff date (no future leakage)
B3	Weekly cash-flow forecaster (LightGBM or similar on lag and calendar features) predicting weekly inflow and outflow, plus a naive baseline
B4	Ready rule engine reading thresholds from config
B5	Affordability engine: surplus forecast, capped share, stress test, nearest-comfortable-loan search
B6	Repayment-timing engine: safe and tight weeks, recommended due-date window
B7	Recourse engine: constrained search over actionable features only, validated by re-scoring
B8	Repayment-risk check: a calibrated model (with a logistic baseline) predicting whether a customer will hit a shortfall in the next period, used to check the Ready rule and rank which missing check matters most
B9	Reason-code catalog mapped from features
B10	Fairness module computing group tables and the mitigation
B11	Persistence: SQLite for consent, config versions, kill switch, and audit log
B12	Model store: saved models, loaded at startup, with version and training date
B13	REST API (see section 5)
B14	Tests: leakage, determinism, config effects, API contract, and a check that no UI value is hardcoded
5. API endpoints (all real, no stubs)
GET  /health
GET  /customer/{id}/status        -> Ready/Not yet, 3 checks, reasons
GET  /customer/{id}/safe-range    -> range, stressed range, basis
POST /customer/{id}/loan-check    -> {amount, tenor} -> payment, verdict, stress result, nearest comfortable option
GET  /customer/{id}/calendar      -> weekly forecast, safe/tight weeks, recommended window
GET  /customer/{id}/path          -> missing items, steps, estimated time
GET  /customer/{id}/progress      -> check history over real months
POST /customer/{id}/consent       -> record consent / opt-out
GET  /admin/funnel | /admin/forecast-quality | /admin/fairness
GET/PUT /admin/config             -> versioned rule settings
POST /admin/kill-switch

Every response includes model_version, data_as_of, and a disclaimer field.

6. Dataset requirements (the only simulated part)
5,000 to 20,000 customers, 12 months of daily wallet activity.
Personas: wage worker, seasonal farmer, informal merchant, woman-led household with irregular income, salaried user.
Tables: customers, transactions (cash-in, cash-out, P2P, bill payment, top-up, merchant payment), daily balances, bills, and an audit-only attributes table (gender, region type, age band).
Seasonality and events: month-end pressure, Eid spikes, harvest income, income shocks, and unexpected expenses.
Generated from latent traits (income stability, shock exposure, bill discipline) plus noise, so models do not simply invert the generator.
Planted group differences (for example, women with lower volume but similar reliability) so the fairness check finds something real.
Outcome used for validation: a "shortfall week" (a week where outflows exceed inflows plus balance, or the balance falls below an essentials threshold). No fake loan defaults are needed.
Splits: by customer (hold-out customers) and by time (train on earlier months, test on later months). Never split by random row.
7. UI and design specification
7.1 Principle

Simple, calm, uncluttered, for an average mobile banking user. One main message and one main action per screen.

7.2 Theme
Fully white theme. Background 
#FFFFFF; surfaces are white with a light grey border (
#E8E8EC) or a very soft shadow. No dark mode.
upay accents: use upay's brand colors for the primary button, active tab, key highlights, and links. Use the official upay brand guide for exact hex values (I have not verified them). Define them as CSS variables (--accent, --accent-soft, --accent-text) so they can be swapped in one place.
Status colors (used sparingly, never alone): green for Ready or Comfortable, amber for Tight, a soft red for Too much. Every status also has an icon and a text label.
Text: near-black 
#1A1A1F for primary text, grey 
#6B6B76 for secondary text. Body contrast must meet WCAG AA.
7.3 Layout and typography
Mobile-first, 360 to 430 px wide, usable up to tablet. Desktop shows the mobile layout centered in a phone-width column.
Body text 16 px or larger, headings 20 to 28 px, one font family with Bangla support (for example Noto Sans Bengali plus a Latin pair).
Tap targets 48 px or larger. Generous spacing, 16 to 24 px between cards.
Maximum 3 cards per screen. No tables in the customer app.
Bottom navigation with 4 tabs: Home, Loan check, Calendar, Me. Steps (Path to Ready) opens from Home.
One primary button per screen, full width. Secondary actions are text links.
7.4 Language and tone
Plain words only. Say "monthly payment," not "EMI." Say "spare money," not "surplus." Avoid financial jargon and abbreviations.
Short sentences. Each screen explains itself in one line.
No blame ("you failed"). Use "not yet" language with a clear next step.
No urgency, countdown, or pressure wording.
7.5 States
Loading: simple skeleton placeholders.
Empty: a friendly explanation ("We need 3 months of activity to build your picture. You have 2.").
Error: plain message and a retry button. Never show raw errors.
Not enough data: honest message, no fallback numbers.
7.6 Accessibility
Color is never the only signal.
Screen-reader labels, visible focus states, and respect for the OS font scaling.
Numbers readable at a glance, with thousand separators.
7.7 Internal upay view

Same white theme, one page, tables allowed, but still clean. It is the only place with tables.

7.8 Screens (customer app)
Consent (first open only)
Home
Safe range
Loan check
Calendar
Path to Ready
Why? (a bottom sheet)
Progress
Me (language, My data, turn coach off, About)
8. Evaluation (offline, on held-out data; not a product feature)
Forecast: weekly MAE or WAPE vs. a naive baseline, split by persona. Report irregular and seasonal earners separately.
Ready rule validity: among Ready customers, the shortfall-week rate vs. among Not yet customers, on held-out months.
Timing guidance: among customers with a recommended window, the share of shortfall weeks avoided vs. a fixed day-of-month baseline, computed from held-out data.
Affordability: how often the "Comfortable" verdict is followed by a shortfall, vs. a naive limit.
Fairness: by gender, region type, and age band, with counts and one mitigation before and after.
Seeds: mean and standard deviation over 5 seeds.
Everything is labeled "synthetic data, relative comparison."
9. Definition of done
 No hardcoded or random values anywhere in the UI or API outputs (an automated test scans for this).
 Every displayed number traces to a model or rule output carrying model_version and data_as_of.
 Models saved to disk, loaded by the API, and reload to identical outputs.
 Customer-level and time-based splits tested for leakage.
 Ready thresholds, cap, stress percentage, and rate are editable and change results.
 Kill switch hides Safe range and Loan check.
 Consent and audit log persist across a restart.
 Bangla and English both complete and reviewed.
 Fairness table shows counts and N/A where there is no data.
 All nine customer screens meet the 7.3 limits (3 cards max, 1 primary action).
 No jargon terms (EMI, surplus, PD) in customer text.
 A clean clone runs end to end with one command and reproduces the evaluation numbers.
10. Out of scope

Real customer data, real loans or lender integration, loan approval or offers, credit scores or bureau data, push notifications, voice features, real payments, and any simulated behavior inside the product.

11. Open points to verify
upay's exact brand colors and fonts (use the official brand guide).
Current Bangladesh Bank rules on lending, alternative data, and data consent. Not verified here.