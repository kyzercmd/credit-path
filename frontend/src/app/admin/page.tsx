"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getAdminFunnel,
  getAdminForecastQuality,
  getAdminFairness,
  getAdminConfig,
  getAdminAuditLog,
  AdminFunnelResponse,
  ForecastQualityResponse,
  FairnessResponse,
  ConfigResponse,
  AuditLogResponse,
} from "@/lib/api";
import { FunnelTable } from "@/components/admin/FunnelTable";
import { ForecastQuality } from "@/components/admin/ForecastQuality";
import { RuleSettings } from "@/components/admin/RuleSettings";
import { FairnessPanel } from "@/components/admin/FairnessPanel";
import { KillSwitch } from "@/components/admin/KillSwitch";
import { AuditLog } from "@/components/admin/AuditLog";
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
} from "lucide-react";

export default function AdminPage() {
  const [funnel, setFunnel] = useState<AdminFunnelResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastQualityResponse | null>(null);
  const [configData, setConfigData] = useState<ConfigResponse | null>(null);
  const [fairness, setFairness] = useState<FairnessResponse | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLogResponse | null>(null);

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
      const [funnelRes, forecastRes, configRes, fairnessRes, auditRes] = await Promise.all([
        getAdminFunnel(),
        getAdminForecastQuality(),
        getAdminConfig(),
        getAdminFairness(),
        getAdminAuditLog(),
      ]);

      setFunnel(funnelRes);
      setForecast(forecastRes);
      setConfigData(configRes);
      setFairness(fairnessRes);
      setAuditLog(auditRes);
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

  const tabs = [
    { id: "all", label: "All Sections", icon: LayoutDashboard },
    { id: "funnel", label: "Funnel (U1)", icon: CheckCircle2 },
    { id: "forecast", label: "Forecast Quality (U2)", icon: TrendingUp },
    { id: "rules", label: "Rule Settings (U3)", icon: Sliders },
    { id: "fairness", label: "Fairness Audit (U4)", icon: Scale },
    { id: "killswitch", label: "Kill Switch (U5)", icon: Power },
    { id: "audit", label: "Audit Log (U6)", icon: ScrollText },
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

        {/* Section Navigation Tabs */}
        <div className="max-w-6xl mx-auto px-4 sm:px-6 overflow-x-auto no-scrollbar">
          <nav className="flex space-x-1 sm:space-x-2 py-2" aria-label="Admin Navigation Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors select-none ${
                    isActive
                      ? "bg-blue-50 text-blue-700 font-semibold"
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
              <section id="section-funnel">
                <FunnelTable data={funnel} />
              </section>
            )}

            {/* Section 2: Forecast Quality (U2) */}
            {(activeTab === "all" || activeTab === "forecast") && (
              <section id="section-forecast">
                <ForecastQuality data={forecast} />
              </section>
            )}

            {/* Section 3: Rule Settings (U3) */}
            {(activeTab === "all" || activeTab === "rules") && (
              <section id="section-rules">
                <RuleSettings
                  data={configData}
                  onConfigSaved={handleConfigSaved}
                />
              </section>
            )}

            {/* Section 4: Fairness Panel (U4) */}
            {(activeTab === "all" || activeTab === "fairness") && (
              <section id="section-fairness">
                <FairnessPanel data={fairness} />
              </section>
            )}

            {/* Section 5: Kill Switch (U5) */}
            {(activeTab === "all" || activeTab === "killswitch") && (
              <section id="section-killswitch">
                <KillSwitch
                  initialKillSafeRange={Boolean(configData?.config?.kill_safe_range)}
                  initialKillLoanCheck={Boolean(configData?.config?.kill_loan_check)}
                  onKillSwitchChanged={handleKillSwitchChanged}
                />
              </section>
            )}

            {/* Section 6: Audit Log (U6) */}
            {(activeTab === "all" || activeTab === "audit") && (
              <section id="section-audit">
                <AuditLog data={auditLog} onRefresh={() => loadData(true)} />
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
