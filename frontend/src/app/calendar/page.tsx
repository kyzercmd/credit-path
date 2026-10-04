"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { useConsent } from "@/contexts/ConsentContext";
import { getCalendar, CalendarResponse } from "@/lib/api";
import { WeeklyChart } from "@/components/WeeklyChart";
import { HeadsUpCard } from "@/components/HeadsUpCard";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Footer } from "@/components/Footer";
import { Skeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/ErrorState";
import { WhySheet } from "@/components/WhySheet";
import { Calendar as CalendarIcon, Clock, AlertTriangle, ArrowLeft, HelpCircle } from "lucide-react";

export default function CalendarPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const { customerId } = useConsent();

  const [data, setData] = useState<CalendarResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showWhy, setShowWhy] = useState<boolean>(false);

  const loadCalendar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getCalendar(customerId);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load repayment calendar");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    loadCalendar();
  }, [loadCalendar]);

  if (loading) {
    return (
      <div className="p-5 space-y-6">
        <Skeleton lines={1} className="w-24 h-6" />
        <Skeleton lines={6} className="h-64 rounded-2xl" />
        <Skeleton lines={4} className="h-40 rounded-2xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-5 min-h-[60vh] flex flex-col justify-center">
        <ErrorState
          message={error || t("common.error_desc")}
          onRetry={loadCalendar}
        />
      </div>
    );
  }

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <header className="flex items-center justify-between pt-1">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-xs font-semibold text-[#6B6B76] hover:text-[#1A1A1F]"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{t("common.back")}</span>
        </button>
        <button
          onClick={() => setShowWhy(true)}
          className="flex items-center gap-1 text-xs font-semibold text-[var(--accent)] hover:underline"
        >
          <HelpCircle className="w-4 h-4" />
          <span>{t("common.why")}</span>
        </button>
      </header>

      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold text-[#1A1A1F]">
          {t("calendar.title")}
        </h1>
        <p className="text-xs text-[#6B6B76] mt-0.5">
          {t("calendar.subtitle")}
        </p>
      </div>

      {/* Heads-up Card (F6) if present */}
      {data.heads_up && (
        <HeadsUpCard
          headsUp={data.heads_up}
          onWhyClick={() => setShowWhy(true)}
        />
      )}

      {/* Recommended Repayment Window (Card 1) */}
      <Card className="bg-gradient-to-r from-[#F0FDF4] to-[#EAF5EE] border-[#C3E4CD]">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl bg-white text-[#107C41] flex items-center justify-center shrink-0 border border-[#C3E4CD] shadow-2xs">
            <Clock className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[#107C41]">
              {t("calendar.recommended_window")}
            </span>
            <div className="text-lg font-bold text-[#1A1A1F] mt-0.5">
              {data.recommended_window || "Early in the monthly cycle"}
            </div>
            <p className="text-xs text-[#6B6B76] mt-1 leading-relaxed">
              {t("calendar.recommended_window_desc")}
            </p>
          </div>
        </div>
      </Card>

      {/* Weekly Forecast Chart (Card 2) */}
      <Card
        title={t("calendar.forecast_title")}
        subtitle="Predicted weekly cash flow and end-of-week cushion"
      >
        <WeeklyChart weeks={data.weeks} />
      </Card>

      {/* Weeks to Avoid (Card 3) if any */}
      {data.avoid_weeks && data.avoid_weeks.length > 0 && (
        <Card className="border-[#FAC7C7] bg-[#FFF8F8]">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-white text-[#C5221F] flex items-center justify-center shrink-0 border border-[#FAC7C7]">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-bold text-[#C5221F]">
                {t("calendar.avoid_weeks")}
              </h4>
              <p className="text-xs text-[#6B6B76] mt-0.5 mb-2 leading-relaxed">
                {t("calendar.avoid_weeks_desc")}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {data.avoid_weeks.map((wk, i) => (
                  <span
                    key={i}
                    className="inline-block px-2.5 py-1 rounded-lg bg-white border border-[#FAC7C7] text-xs font-semibold text-[#C5221F]"
                  >
                    {wk}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      <Footer meta={data.meta} />

      {/* Why Sheet */}
      <WhySheet
        isOpen={showWhy}
        onClose={() => setShowWhy(false)}
        title={t("calendar.title")}
        explanation="Repayment timing schedules your payment 1-2 days after your historical income arrives, avoiding month-end bill spikes or low-balance weeks."
        featureValue={data.recommended_window}
        targetValue="Peak wallet balance window"
        code="timing_repayment_window"
      />
    </div>
  );
}
