"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useLanguage } from "@/contexts/LanguageContext";
import { useConsent } from "@/contexts/ConsentContext";
import { getStatus, StatusResponse, CheckResult } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { CheckRow } from "@/components/CheckRow";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Footer } from "@/components/Footer";
import { Skeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/ErrorState";
import { LanguageToggle } from "@/components/LanguageToggle";
import { WhySheet } from "@/components/WhySheet";
import { ArrowRight, Sparkles, User, AlertCircle } from "lucide-react";

export default function HomePage() {
  const { t } = useLanguage();
  const { customerId, coachActive, setCoachActive } = useConsent();

  const [data, setData] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Why sheet state
  const [activeCheck, setActiveCheck] = useState<CheckResult | null>(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getStatus(customerId);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load status");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  if (loading) {
    return (
      <div className="p-5 space-y-6">
        <div className="flex justify-between items-center pt-2">
          <Skeleton lines={1} className="w-28 h-6" />
          <Skeleton lines={1} className="w-16 h-8" />
        </div>
        <div className="space-y-4">
          <Skeleton lines={4} className="h-44 rounded-2xl" />
          <Skeleton lines={5} className="h-56 rounded-2xl" />
          <Skeleton lines={2} className="h-14 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-5 min-h-[60vh] flex flex-col justify-center">
        <ErrorState
          message={error || t("common.error_desc")}
          onRetry={loadStatus}
        />
      </div>
    );
  }

  const isReady = data.ready;

  return (
    <div className="p-5 space-y-5">
      {/* Top Header */}
      <header className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center font-bold text-sm">
            u
          </div>
          <div>
            <span className="text-xs uppercase tracking-wider font-semibold text-[#6B6B76]">
              CreditPath
            </span>
            <div className="flex items-center gap-1.5 text-xs text-[#1A1A1F] font-medium">
              <User className="w-3.5 h-3.5 text-[#6B6B76]" />
              <span>{data.customer_id}</span>
            </div>
          </div>
        </div>
        <LanguageToggle />
      </header>

      {/* Coach Paused Notice if opted out */}
      {!coachActive && (
        <div className="p-3.5 rounded-xl bg-gray-50 border border-gray-200 flex items-center justify-between text-xs text-[#6B6B76]">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-gray-500 shrink-0" />
            <span>Coaching paused for this profile</span>
          </div>
          <button
            onClick={() => setCoachActive(true)}
            className="font-semibold text-[var(--accent)] hover:underline"
          >
            Resume
          </button>
        </div>
      )}

      {/* Card 1: Main Status Hero */}
      <Card className="text-center py-6 px-4 bg-gradient-to-b from-white to-[#F8F9FA]">
        <div className="mb-3 flex justify-center">
          <StatusBadge
            status={isReady ? "ready" : "not_yet"}
            label={data.status_label || (isReady ? t("home.ready") : t("home.not_yet"))}
            size="lg"
          />
        </div>

        <h1 className="text-xl font-bold text-[#1A1A1F] mt-2 mb-2 leading-snug">
          {isReady ? t("home.ready_title") : t("home.not_yet_title")}
        </h1>

        <p className="text-sm text-[#6B6B76] leading-relaxed max-w-xs mx-auto">
          {data.status_sentence || (isReady ? t("home.ready_desc") : t("home.not_yet_desc"))}
        </p>

        {/* Primary CTA */}
        <div className="mt-6">
          {isReady ? (
            <Link href="/safe-range" className="block w-full">
              <Button
                variant="primary"
                fullWidth
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                {t("home.see_safe_range")}
              </Button>
            </Link>
          ) : (
            <Link href="/path" className="block w-full">
              <Button
                variant="primary"
                fullWidth
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                {t("home.see_whats_missing")}
              </Button>
            </Link>
          )}
        </div>
      </Card>

      {/* Card 2: Readiness Checks Breakdown */}
      <Card
        title={t("home.checks_summary")}
        subtitle={t("home.how_it_works")}
      >
        <div className="divide-y divide-[#E8E8EC]">
          {data.checks.map((chk, idx) => (
            <CheckRow
              key={chk.name || idx}
              title={chk.name}
              passed={chk.passed}
              reason={chk.reason}
              onWhyClick={() => setActiveCheck(chk)}
            />
          ))}
        </div>
      </Card>

      {/* Card 3: Quick Navigation / Secondary Info */}
      <Card className="bg-[#FAFAFB]">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h4 className="text-sm font-semibold text-[#1A1A1F]">
              {t("progress.title")}
            </h4>
            <p className="text-xs text-[#6B6B76]">
              {t("progress.subtitle")}
            </p>
          </div>
          <Link
            href="/progress"
            className="shrink-0 text-xs font-semibold text-[var(--accent)] hover:underline inline-flex items-center gap-1"
          >
            <span>View</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </Card>

      {/* Footer with meta traceability */}
      <Footer meta={data.meta} />

      {/* Why Explanation Sheet */}
      {activeCheck && (
        <WhySheet
          isOpen={Boolean(activeCheck)}
          onClose={() => setActiveCheck(null)}
          title={activeCheck.name}
          explanation={activeCheck.reason}
          featureValue={activeCheck.current_value}
          targetValue={activeCheck.target_value}
          code={activeCheck.reason_code}
        />
      )}
    </div>
  );
}
