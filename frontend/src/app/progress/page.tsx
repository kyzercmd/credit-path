"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { useConsent } from "@/contexts/ConsentContext";
import { getProgress, ProgressResponse } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Footer } from "@/components/Footer";
import { Skeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/ErrorState";
import { ArrowLeft, Award, CheckCircle2, CircleDot, TrendingUp } from "lucide-react";

export default function ProgressPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const { customerId } = useConsent();

  const [data, setData] = useState<ProgressResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadProgress = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getProgress(customerId);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load progress history");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    loadProgress();
  }, [loadProgress]);

  if (loading) {
    return (
      <div className="p-5 space-y-6">
        <Skeleton lines={1} className="w-24 h-6" />
        <Skeleton lines={4} className="h-36 rounded-2xl" />
        <Skeleton lines={6} className="h-64 rounded-2xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-5 min-h-[60vh] flex flex-col justify-center">
        <ErrorState
          message={error || t("common.error_desc")}
          onRetry={loadProgress}
        />
      </div>
    );
  }

  const history = data.history || [];

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
      </header>

      {/* Hero */}
      <div>
        <h1 className="text-2xl font-bold text-[#1A1A1F]">
          {t("progress.title")}
        </h1>
        <p className="text-xs text-[#6B6B76] mt-0.5">
          {t("progress.subtitle")}
        </p>
      </div>

      {/* Milestone Card if became ready */}
      {data.became_ready ? (
        <Card className="bg-[#EAF5EE] border-[#C3E4CD] py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white text-[#107C41] flex items-center justify-center shrink-0 border border-[#C3E4CD]">
              <Award className="w-6 h-6 stroke-[2.2]" />
            </div>
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-[#107C41]">
                Milestone reached
              </span>
              <p className="text-sm font-bold text-[#1A1A1F]">
                {t("progress.became_ready", { month: data.became_ready })}
              </p>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="bg-gray-50 border-gray-200 py-3.5">
          <div className="flex items-center gap-2.5 text-xs text-[#6B6B76]">
            <TrendingUp className="w-4 h-4 text-gray-500 shrink-0" />
            <span>{t("progress.track_record")}</span>
          </div>
        </Card>
      )}

      {/* Monthly History Breakdown */}
      <Card
        title={t("progress.monthly_history")}
        subtitle="Readiness criteria met across recent months"
      >
        {history.length === 0 ? (
          <p className="text-xs text-[#6B6B76] py-4 text-center">
            No past monthly records yet.
          </p>
        ) : (
          <div className="space-y-3 pt-1">
            {history.map((item, idx) => (
              <div
                key={item.month || idx}
                className="p-3 rounded-xl border border-[#E8E8EC] bg-[#FAFAFB] space-y-2"
              >
                <div className="flex items-center justify-between text-xs font-bold text-[#1A1A1F] border-b border-[#E8E8EC] pb-1.5">
                  <span>{item.month}</span>
                  <span className="text-[11px] font-normal text-[#6B6B76]">
                    {(item.history_ok ? 1 : 0) +
                      (item.income_regular ? 1 : 0) +
                      (item.cushion_ok ? 1 : 0)}{" "}
                    / 3 checks met
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="flex items-center gap-1.5">
                    {item.history_ok ? (
                      <CheckCircle2 className="w-4 h-4 text-[#107C41] shrink-0" />
                    ) : (
                      <CircleDot className="w-4 h-4 text-gray-400 shrink-0" />
                    )}
                    <span className="text-[#1A1A1F]">History</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {item.income_regular ? (
                      <CheckCircle2 className="w-4 h-4 text-[#107C41] shrink-0" />
                    ) : (
                      <CircleDot className="w-4 h-4 text-gray-400 shrink-0" />
                    )}
                    <span className="text-[#1A1A1F]">Income</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {item.cushion_ok ? (
                      <CheckCircle2 className="w-4 h-4 text-[#107C41] shrink-0" />
                    ) : (
                      <CircleDot className="w-4 h-4 text-gray-400 shrink-0" />
                    )}
                    <span className="text-[#1A1A1F]">Cushion</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Footer meta={data.meta} />
    </div>
  );
}
