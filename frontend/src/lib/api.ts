/**
 * CreditPath Typed API Client
 * Interfaces match backend/app/schemas.py
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export interface Meta {
  model_version: string;
  data_as_of: string;
  disclaimer: string;
}

export interface CheckResult {
  name: string;
  passed: boolean;
  reason: string;
  reason_code?: string;
  current_value?: number | null;
  target_value?: number | null;
}

export interface StatusResponse {
  customer_id: string;
  ready: boolean;
  status_label: string;
  status_sentence: string;
  checks: CheckResult[];
  meta: Meta;
}

export interface SafeRangeResponse {
  customer_id: string;
  monthly_low: number;
  monthly_high: number;
  stressed_low: number;
  stressed_high: number;
  basis_months: number;
  basis_sentence: string;
  meta: Meta;
}

export interface LoanCheckRequest {
  amount: number;
  tenor_months: number;
}

export interface NearestComfortable {
  amount: number;
  tenor_months: number;
  monthly_payment: number;
}

export interface LoanCheckResponse {
  customer_id: string;
  amount: number;
  tenor_months: number;
  monthly_payment: number;
  total_repayment: number;
  surplus_share: number;
  verdict: "Comfortable" | "Tight" | "Too much" | string;
  verdict_reason: string;
  stress_verdict: string;
  stress_reason: string;
  nearest_comfortable: NearestComfortable | null;
  meta: Meta;
}

export interface WeekForecast {
  week_start: string;
  money_in: number;
  money_out: number;
  expected_balance: number;
  status: "safe" | "tight" | string;
  reason: string;
}

export interface HeadsUpCard {
  message: string;
  suggestion: string;
  week: string;
}

export interface CalendarResponse {
  customer_id: string;
  weeks: WeekForecast[];
  recommended_window: string;
  avoid_weeks: string[];
  heads_up: HeadsUpCard | null;
  meta: Meta;
}

export interface PathStep {
  item: string;
  action: string;
  estimated_weeks: number;
  reason: string;
}

export interface PathResponse {
  customer_id: string;
  missing_items: PathStep[];
  meta: Meta;
}

export interface CheckHistory {
  month: string;
  history_ok: boolean;
  income_regular: boolean;
  cushion_ok: boolean;
}

export interface ProgressResponse {
  customer_id: string;
  history: CheckHistory[];
  became_ready: string | null;
  current_values: Record<string, any>;
  meta: Meta;
}

export interface ConsentRequest {
  action: "consent" | "opt-out";
}

export interface ConsentResponse {
  customer_id: string;
  action: string;
  recorded: boolean;
  meta?: Meta | null;
}

export interface FunnelBucket {
  label: string;
  count: number;
}

export interface AdminFunnelResponse {
  total_customers: number;
  ready_count: number;
  not_yet_count: number;
  missing_checks: FunnelBucket[];
  meta: Meta;
}

export interface ForecastQualityResponse {
  overall_mae: number;
  overall_wape: number;
  naive_mae: number;
  naive_wape: number;
  by_persona: Record<string, Record<string, any>>;
  meta: Meta;
}

export interface FairnessGroup {
  group: string;
  count: number;
  ready_rate: number | null;
  forecast_error: number | null;
  false_not_yet_rate: number | null;
}

export interface FairnessResponse {
  by_gender: FairnessGroup[];
  by_region: FairnessGroup[];
  by_age_band: FairnessGroup[];
  mitigation: Record<string, any>;
  meta: Meta;
}

export interface ConfigResponse {
  config: Record<string, any>;
  version: number;
  timestamp: string;
  meta?: Meta | null;
}

export interface KillSwitchRequest {
  kill_safe_range: boolean;
  kill_loan_check: boolean;
}

export interface KillSwitchResponse {
  message: string;
  kill_safe_range: boolean;
  kill_loan_check: boolean;
  meta: Meta;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  model_version: string;
  data_as_of: string;
  disclaimer: string;
  meta?: Meta | null;
}

export interface AuditEvent {
  event_type: string;
  details: string;
  timestamp: string;
}

export interface AuditLogResponse {
  events: AuditEvent[];
  meta: Meta;
}

export interface WhyExplanation {
  code: string;
  explanation: string;
  feature_value: string;
}

export interface FunnelStageMetric {
  unique_users: number;
  step_conversion_pct: number;
  overall_conversion_pct: number;
}

export interface FunnelAnalyticsResponse {
  total_tracked_users: number;
  stages: Record<string, FunnelStageMetric>;
  counts_by_stage: Record<string, number>;
  meta: Meta;
}

export interface TrialCohortMetric {
  regime_name: string;
  approved_count: number;
  approval_rate: number;
  simulated_defaults: number;
  default_rate_pd: number;
  expected_loss_per_loan: number;
}

export interface TrialUpliftMetric {
  default_rate_reduction_pct: number;
  approval_rate_delta_pct: number;
  expected_loss_savings_per_loan_bdt: number;
  timing_shortfalls_avoided_pct: number;
  conclusion: string;
}

export interface TrialEvaluationResponse {
  disclaimer: string;
  sample_size: number;
  baseline_control: TrialCohortMetric;
  treatment_creditpath: TrialCohortMetric;
  empirical_uplift: TrialUpliftMetric;
  meta: Meta;
}

export interface ReadinessTransitionDelta {
  previous_ready: boolean;
  current_ready: boolean;
  status_changed: boolean;
  previous_status: string;
  current_status: string;
  checks_passed_count: number;
  total_checks_count: number;
  message: string;
}

export interface IngestEventResponse {
  customer_id: string;
  event_type: string;
  recorded: boolean;
  as_of_date: string;
  transition: ReadinessTransitionDelta | null;
  meta: Meta | null;
}

let adminApiKey: string = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "creditpath-admin-secret-key-2026";
let adminToken: string = process.env.NEXT_PUBLIC_ADMIN_TOKEN || "";

export function setAdminAuth(tokenOrKey: { apiKey?: string; token?: string }) {
  if (tokenOrKey.apiKey !== undefined) adminApiKey = tokenOrKey.apiKey;
  if (tokenOrKey.token !== undefined) adminToken = tokenOrKey.token;
}

export async function fetchAPI<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  let res: Response;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (endpoint.startsWith("/admin")) {
    if (adminApiKey) {
      headers["X-Admin-API-Key"] = adminApiKey;
    } else if (adminToken) {
      headers["Authorization"] = `Bearer ${adminToken}`;
    }
  }

  try {
    res = await fetch(url, {
      ...options,
      headers,
    });
  } catch (networkErr: any) {
    throw new ApiError(0, networkErr?.message || "Network request failed", networkErr);
  }

  let data: any = null;
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  } else {
    try {
      data = await res.text();
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const errorMsg =
      (data && typeof data === "object" && (data.detail || data.message)) ||
      `Request failed with status ${res.status}`;
    throw new ApiError(res.status, errorMsg, data);
  }

  return data as T;
}

export async function getStatus(customerId: string, asOf?: string): Promise<StatusResponse> {
  const q = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return fetchAPI<StatusResponse>(`/customer/${encodeURIComponent(customerId)}/status${q}`);
}

export async function getSafeRange(customerId: string, asOf?: string): Promise<SafeRangeResponse> {
  const q = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return fetchAPI<SafeRangeResponse>(`/customer/${encodeURIComponent(customerId)}/safe-range${q}`);
}

export async function postLoanCheck(
  customerId: string,
  amount: number,
  tenorMonths: number,
  asOf?: string
): Promise<LoanCheckResponse> {
  const q = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return fetchAPI<LoanCheckResponse>(`/customer/${encodeURIComponent(customerId)}/loan-check${q}`, {
    method: "POST",
    body: JSON.stringify({ amount, tenor_months: tenorMonths }),
  });
}

export async function getCalendar(customerId: string, asOf?: string): Promise<CalendarResponse> {
  const q = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return fetchAPI<CalendarResponse>(`/customer/${encodeURIComponent(customerId)}/calendar${q}`);
}

export async function getPath(customerId: string, asOf?: string): Promise<PathResponse> {
  const q = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return fetchAPI<PathResponse>(`/customer/${encodeURIComponent(customerId)}/path${q}`);
}

export async function getProgress(customerId: string): Promise<ProgressResponse> {
  return fetchAPI<ProgressResponse>(`/customer/${encodeURIComponent(customerId)}/progress`);
}

export async function ingestTransaction(
  customerId: string,
  date: string,
  type: "inflow" | "outflow",
  amount: number,
  description?: string
): Promise<IngestEventResponse> {
  return fetchAPI<IngestEventResponse>(`/customer/${encodeURIComponent(customerId)}/ingest/transaction`, {
    method: "POST",
    body: JSON.stringify({ date, type, amount, description }),
  });
}

export async function ingestDailyBalance(
  customerId: string,
  date: string,
  balance: number,
  shortfall: number = 0
): Promise<IngestEventResponse> {
  return fetchAPI<IngestEventResponse>(`/customer/${encodeURIComponent(customerId)}/ingest/balance`, {
    method: "POST",
    body: JSON.stringify({ date, balance, shortfall }),
  });
}

export async function ingestBill(
  customerId: string,
  dueDate: string,
  amount: number,
  paidDate?: string,
  onTime: number = 1,
  biller?: string
): Promise<IngestEventResponse> {
  return fetchAPI<IngestEventResponse>(`/customer/${encodeURIComponent(customerId)}/ingest/bill`, {
    method: "POST",
    body: JSON.stringify({ due_date: dueDate, amount, paid_date: paidDate, on_time: onTime, biller }),
  });
}

export async function postConsent(
  customerId: string,
  action: "consent" | "opt-out"
): Promise<ConsentResponse> {
  return fetchAPI<ConsentResponse>(`/customer/${encodeURIComponent(customerId)}/consent`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export async function getAdminFunnel(): Promise<AdminFunnelResponse> {
  return fetchAPI<AdminFunnelResponse>("/admin/funnel");
}

export async function getAdminForecastQuality(): Promise<ForecastQualityResponse> {
  return fetchAPI<ForecastQualityResponse>("/admin/forecast-quality");
}

export async function getAdminFairness(): Promise<FairnessResponse> {
  return fetchAPI<FairnessResponse>("/admin/fairness");
}

export async function getAdminConfig(): Promise<ConfigResponse> {
  return fetchAPI<ConfigResponse>("/admin/config");
}

export async function putAdminConfig(config: Record<string, any>): Promise<ConfigResponse> {
  return fetchAPI<ConfigResponse>("/admin/config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

export async function postAdminKillSwitch(
  killSafeRange: boolean,
  killLoanCheck: boolean
): Promise<KillSwitchResponse> {
  return fetchAPI<KillSwitchResponse>("/admin/kill-switch", {
    method: "POST",
    body: JSON.stringify({
      kill_safe_range: killSafeRange,
      kill_loan_check: killLoanCheck,
    }),
  });
}

export async function getAdminAuditLog(): Promise<AuditLogResponse> {
  return fetchAPI<AuditLogResponse>("/admin/audit-log");
}

export async function getAdminBaselineTrial(): Promise<TrialEvaluationResponse> {
  return fetchAPI<TrialEvaluationResponse>("/admin/baseline-trial");
}

export async function getAdminFunnelAnalytics(): Promise<FunnelAnalyticsResponse> {
  return fetchAPI<FunnelAnalyticsResponse>("/admin/funnel-analytics");
}

export async function postFunnelEvent(
  customerId: string,
  stage: string,
  metadata?: Record<string, any>
): Promise<{ status: string; event_id: number }> {
  return fetchAPI<{ status: string; event_id: number }>(`/customer/${encodeURIComponent(customerId)}/funnel-event`, {
    method: "POST",
    body: JSON.stringify({ stage, metadata }),
  });
}

export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI<HealthResponse>("/health");
}
