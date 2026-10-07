"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getAdminFunnel,
  getAdminForecastQuality,
  getAdminFairness,
  getAdminConfig,
  getAdminAuditLog,
  getAdminBaselineTrial,
  getAdminFunnelAnalytics,
  AdminFunnelResponse,
  ForecastQualityResponse,
  FairnessResponse,
  ConfigResponse,
  AuditLogResponse,
  TrialEvaluationResponse,
  FunnelAnalyticsResponse,
} from "@/lib/api";
import { FunnelTable } from "@/components/admin/FunnelTable";
import { ForecastQuality } from "@/components/admin/ForecastQuality";
import { RuleSettings } from "@/components/admin/RuleSettings";
import { FairnessPanel } from "@/components/admin/FairnessPanel";
import { KillSwitch } from "@/components/admin/KillSwitch";
import { AuditLog } from "@/components/admin/AuditLog";
import { BaselineTrialPanel } from "@/components/admin/BaselineTrialPanel";
import { EventSimulator } from "@/components/EventSimulator";
import { Skeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/ErrorState";
import {
  ArrowLeft,
  RefreshCw,
  LayoutDashboard,
  TrendingUp,
  Sliders,
  Scale,
  Power,
  ScrollText,
  ShieldCheck,
  CheckCircle2,
  TrendingDown,
  Zap,
} from "lucide-react";

export default function AdminPage() {
  const [funnel, setFunnel] = useState<AdminFunnelResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastQualityResponse | null>(null);
  const [configData, setConfigData] = useState<ConfigResponse | null>(null);
  const [fairness, setFairness] = useState<FairnessResponse | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLogResponse | null>(null);
  const [baselineTrial, setBaselineTrial] = useState<TrialEvaluationResponse | null>(null);
  const [funnelAnalytics, setFunnelAnalytics] = useState<FunnelAnalyticsResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("all");

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [funnelRes, forecastRes, configRes, fairnessRes, auditRes, trialRes, funnelAnalyticsRes] =
        await Promise.all([
          getAdminFunnel(),
          getAdminForecastQuality(),
          getAdminConfig(),
          getAdminFairness(),
          getAdminAuditLog(),
          getAdminBaselineTrial().catch(() => null),
          getAdminFunnelAnalytics().catch(() => null),
        ]);

      setFunnel(funnelRes);
      setForecast(forecastRes);
      setConfigData(configRes);
      setFairness(fairnessRes);
      setAuditLog(auditRes);
      setBaselineTrial(trialRes);
      setFunnelAnalytics(funnelAnalyticsRes);
    } catch (err: any) {
      setError(err?.message || "Failed to load admin telemetry data.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleConfigSaved = (newConfig: ConfigResponse) => {
    setConfigData(newConfig);
    // Reload funnel and audit log to reflect updated configuration version
    getAdminFunnel().then(setFunnel).catch(console.error);
    getAdminAuditLog().then(setAuditLog).catch(console.error);
  };

  const handleKillSwitchChanged = (killSafeRange: boolean, killLoanCheck: boolean) => {
    if (configData) {
      setConfigData({
        ...configData,
        config: {
          ...configData.config,
          kill_safe_range: killSafeRange,
          kill_loan_check: killLoanCheck,
        },
      });
    }
    getAdminAuditLog().then(setAuditLog).catch(console.error);
  };

  // Meta information from any of the responses
  const meta =
    configData?.meta ||
    funnel?.meta ||
    forecast?.meta ||
    fairness?.meta ||
    auditLog?.meta || {
      model_version: "v1",
      data_as_of: "2025-12-31",
      disclaimer: "Built on synthetic data. Guidance only, not a loan offer.",
    };

  const [adminSimulatorCustomer, setAdminSimulatorCustomer] = useState<string>("CUST_000001");

  const tabs = [
    { id: "all", label: "All Sections", icon: LayoutDashboard },
    { id: "funnel", label: "Readiness Funnel (U1)", icon: CheckCircle2 },
    { id: "forecast", label: "Forecast Quality (U2)", icon: TrendingUp },
    { id: "rules", label: "Rule Settings (U3)", icon: Sliders },
    { id: "fairness", label: "Fairness Audit (U4)", icon: Scale },
    { id: "killswitch", label: "Kill Switch (U5)", icon: Power },
    { id: "audit", label: "Audit Log (U6)", icon: ScrollText },
    { id: "simulator", label: "Live Ingestion Studio (U8)", icon: Zap },
    { id: "trial", label: "Impact & Trial (U7)", icon: TrendingDown },
  ];

  return (
    <div data-admin-page="true" className="w-full min-h-screen bg-[#F4F4F6] text-[#1A1A1F] pb-16">
      {/* Top Admin Header Bar */}
      <header className="bg-white border-b border-[#E8E8EC] sticky top-0 z-30 shadow-2xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/home"
              aria-label="Back to customer home"
              className="p-2 rounded-xl text-[#6B6B76] hover:text-[#1A1A1F] hover:bg-gray-100 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-[#1A1A1F] leading-tight">
                  CreditPath Admin Console
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-gray-100 text-gray-700 border border-gray-200">
                  Internal
                </span>
              </div>
              <p className="text-xs text-[#6B6B76] mt-0.5">
                Model: <strong className="text-gray-700 font-medium">{meta.model_version}</strong> • Data as of:{" "}
                <strong className="text-gray-700 font-medium">{meta.data_as_of || "2025-12-31"}</strong>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/me"
              className="hidden sm:inline-flex items-center text-xs font-semibold px-3 py-1.5 rounded-lg border border-[#E8E8EC] text-[#6B6B76] hover:text-[#1A1A1F] hover:bg-gray-50 transition-colors"
            >
              Customer Profile
            </Link>
            <button
              type="button"
              onClick={() => loadData(true)}
              disabled={isRefreshing || isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E8E8EC] bg-white text-xs font-semibold text-[#1A1A1F] hover:bg-gray-50 active:scale-[0.98] transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-blue-600" : ""}`} />
              <span className="hidden sm:inline">{isRefreshing ? "Refreshing..." : "Refresh"}</span>
            </button>
          </div>
        </div>

        {/* Section Navigation Tabs: flex-wrap to prevent horizontal scrolling */}
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <nav className="flex flex-wrap items-center gap-1.5 sm:gap-2 py-2" role="tablist" aria-label="Admin Navigation Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  id={`tab-${tab.id}`}
                  aria-selected={isActive}
                  aria-controls={`panel-${tab.id}`}
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors select-none focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-600 ${
                    isActive
                      ? "bg-blue-50 text-blue-700 font-semibold shadow-2xs"
                      : "text-[#6B6B76] hover:text-[#1A1A1F] hover:bg-gray-100"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? "text-blue-600" : "text-[#6B6B76]"}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
        {error ? (
          <ErrorState
            title="Telemetry Unavailable"
            message={error}
            onRetry={() => loadData()}
            className="my-8"
          />
        ) : isLoading ? (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-[#E8E8EC] space-y-4 animate-pulse">
              <div className="h-6 w-48 bg-gray-200 rounded" />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="h-20 bg-gray-100 rounded-xl" />
                <div className="h-20 bg-gray-100 rounded-xl" />
                <div className="h-20 bg-gray-100 rounded-xl" />
              </div>
              <div className="h-44 bg-gray-100 rounded-xl" />
            </div>
            <div className="bg-white p-6 rounded-2xl border border-[#E8E8EC] space-y-4 animate-pulse">
              <div className="h-6 w-48 bg-gray-200 rounded" />
              <div className="h-32 bg-gray-100 rounded-xl" />
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Section 1: Funnel Table (U1) */}
            {(activeTab === "all" || activeTab === "funnel") && (
              <section id="panel-funnel" role="tabpanel" aria-labelledby="tab-funnel">
                <FunnelTable data={funnel} />
              </section>
            )}

            {/* Section 2: Forecast Quality (U2) */}
            {(activeTab === "all" || activeTab === "forecast") && (
              <section id="panel-forecast" role="tabpanel" aria-labelledby="tab-forecast">
                <ForecastQuality data={forecast} />
              </section>
            )}

            {/* Section 3: Rule Settings (U3) */}
            {(activeTab === "all" || activeTab === "rules") && (
              <section id="panel-rules" role="tabpanel" aria-labelledby="tab-rules">
                <RuleSettings
                  data={configData}
                  onConfigSaved={handleConfigSaved}
                />
              </section>
            )}

            {/* Section 4: Fairness Panel (U4) */}
            {(activeTab === "all" || activeTab === "fairness") && (
              <section id="panel-fairness" role="tabpanel" aria-labelledby="tab-fairness">
                <FairnessPanel data={fairness} />
              </section>
            )}

            {/* Section 5: Kill Switch (U5) */}
            {(activeTab === "all" || activeTab === "killswitch") && (
              <section id="panel-killswitch" role="tabpanel" aria-labelledby="tab-killswitch">
                <KillSwitch
                  initialKillSafeRange={Boolean(configData?.config?.kill_safe_range)}
                  initialKillLoanCheck={Boolean(configData?.config?.kill_loan_check)}
                  onKillSwitchChanged={handleKillSwitchChanged}
                />
              </section>
            )}

            {/* Section 6: Audit Log (U6) */}
            {(activeTab === "all" || activeTab === "audit") && (
              <section id="panel-audit" role="tabpanel" aria-labelledby="tab-audit">
                <AuditLog data={auditLog} onRefresh={() => loadData(true)} />
              </section>
            )}

            {/* Section 8: Live Ingestion Studio (U8) */}
            {(activeTab === "all" || activeTab === "simulator") && (
              <section id="panel-simulator" role="tabpanel" aria-labelledby="tab-simulator" className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-white rounded-xl border border-gray-200 shadow-2xs">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-gray-700">Target Customer ID:</span>
                    <input
                      type="text"
                      value={adminSimulatorCustomer}
                      onChange={(e) => setAdminSimulatorCustomer(e.target.value.toUpperCase())}
                      className="px-2.5 py-1 text-xs font-mono font-bold border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 w-36 uppercase"
                    />
                  </div>
                  <span className="text-[11px] text-gray-500">
                    Live events update SQLite/Postgres in real-time
                  </span>
                </div>
                <EventSimulator
                  customerId={adminSimulatorCustomer}
                  onEventProcessed={() => loadData(true)}
                />
              </section>
            )}

            {/* Section 7: Impact & Baseline Trial (U7) */}
            {(activeTab === "all" || activeTab === "trial") && (
              <section id="panel-trial" role="tabpanel" aria-labelledby="tab-trial">
                <BaselineTrialPanel
                  trialData={baselineTrial}
                  funnelAnalytics={funnelAnalytics}
                  isLoading={isLoading}
                />
              </section>
            )}
          </div>
        )}

        {/* Admin Footer */}
        <footer className="mt-12 pt-6 border-t border-[#E8E8EC] text-center text-xs text-[#6B6B76] space-y-1">
          <p className="font-medium text-[#1A1A1F]">CreditPath Governance & Model Monitoring</p>
          <p>{meta.disclaimer}</p>
        </footer>
      </main>
    </div>
  );
}
