"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { useConsent } from "@/contexts/ConsentContext";
import { getSafeRange, SafeRangeResponse, ApiError } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Footer } from "@/components/Footer";
import { Skeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/ErrorState";
import { WhySheet } from "@/components/WhySheet";
import { formatCurrency } from "@/lib/format";
import { ArrowLeft, ArrowRight, ShieldCheck, TrendingDown, HelpCircle } from "lucide-react";

export default function SafeRangePage() {
  const router = useRouter();
  const { t, locale } = useLanguage();
  const { customerId } = useConsent();

  const [data, setData] = useState<SafeRangeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isKilled, setIsKilled] = useState<boolean>(false);
  const [showWhy, setShowWhy] = useState<boolean>(false);

  const loadRange = useCallback(async () => {
    setLoading(true);
    setError(null);
    setIsKilled(false);
    try {
      const res = await getSafeRange(customerId);
      setData(res);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        setIsKilled(true);
      } else if (err instanceof ApiError && err.status === 400) {
        router.replace("/path");
        return;
      } else {
        setError(err?.message || "Failed to load safe range");
      }
    } finally {
      setLoading(false);
    }
  }, [customerId, router]);

  useEffect(() => {
    loadRange();
  }, [loadRange]);

  if (loading) {
    return (
      <div className="p-5 space-y-6">
        <Skeleton lines={1} className="w-24 h-6" />
        <Skeleton lines={4} className="h-48 rounded-2xl" />
        <Skeleton lines={3} className="h-32 rounded-2xl" />
      </div>
    );
  }

  if (isKilled) {
    return (
      <div className="p-5 min-h-[60vh] flex flex-col justify-center text-center">
        <Card className="py-6">
          <div className="w-12 h-12 rounded-full bg-amber-50 text-[#B25E02] mx-auto flex items-center justify-center mb-3">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-[#1A1A1F] mb-1">
            Guidance Temporarily Unavailable
          </h2>
          <p className="text-sm text-[#6B6B76] mb-5">
            Safe range calculations are temporarily paused for maintenance. Please check back shortly.
          </p>
          <Link href="/home">
            <Button variant="secondary" fullWidth>
              {t("common.back")}
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-5 min-h-[60vh] flex flex-col justify-center">
        <ErrorState
          message={error || t("common.error_desc")}
          onRetry={loadRange}
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

      {/* Main Safe Range Card */}
      <Card className="text-center py-6 px-4 bg-gradient-to-b from-[#F5F9F6] to-white border-[#C3E4CD]">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#EAF5EE] text-[#107C41] text-xs font-semibold mb-3 border border-[#C3E4CD]">
          <ShieldCheck className="w-4 h-4" />
          <span>Comfortable Repayment Limit</span>
        </div>

        <h1 className="text-2xl font-bold text-[#1A1A1F] mb-1">
          {t("safe_range.title")}
        </h1>
        <p className="text-xs text-[#6B6B76] mb-6 max-w-xs mx-auto">
          {t("safe_range.subtitle")}
        </p>

        {/* Big Range Display */}
        <div className="bg-white rounded-2xl p-5 border border-[#E8E8EC] shadow-sm mb-4">
          <div className="text-xs font-semibold text-[#6B6B76] uppercase tracking-wider mb-1">
            {t("safe_range.monthly_payment")}
          </div>
          <div className="text-3xl font-extrabold text-[#1A1A1F] tracking-tight">
            {formatCurrency(data.monthly_low, locale)} — {formatCurrency(data.monthly_high, locale)}
          </div>
          <div className="text-xs text-[#6B6B76] mt-1">
            {t("common.per_month")}
          </div>
        </div>

        {/* Stressed Range */}
        <div className="p-3.5 rounded-xl bg-[#FEF5E7] border border-[#FBDCA8] flex items-center justify-between text-left">
          <div className="flex items-start gap-2.5">
            <TrendingDown className="w-4 h-4 text-[#B25E02] mt-0.5 shrink-0" />
            <div>
              <div className="text-xs font-bold text-[#B25E02]">
                {t("safe_range.stressed_range")}
              </div>
              <div className="text-xs text-[#6B6B76]">
                {t("safe_range.comfort_rule")}
              </div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <span className="text-sm font-bold text-[#1A1A1F]">
              {formatCurrency(data.stressed_low, locale)} - {formatCurrency(data.stressed_high, locale)}
            </span>
          </div>
        </div>

        {/* Basis text */}
        <div className="mt-4 text-xs text-[#6B6B76]">
          {data.basis_sentence ||
            t("safe_range.basis", { months: data.basis_months.toString() })}
        </div>
      </Card>

      {/* Action to Loan Check */}
      <Card>
        <div className="space-y-3">
          <h3 className="text-base font-semibold text-[#1A1A1F]">
            {t("safe_range.try_loan_check")}
          </h3>
          <p className="text-xs text-[#6B6B76] leading-relaxed">
            Test specific loan amounts and repayment periods against your monthly budget.
          </p>
          <Link href="/loan-check" className="block w-full">
            <Button
              variant="primary"
              fullWidth
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              {t("nav.loan_check")}
            </Button>
          </Link>
        </div>
      </Card>

      <Footer meta={data.meta} />

      {/* Why Sheet */}
      <WhySheet
        isOpen={showWhy}
        onClose={() => setShowWhy(false)}
        title={t("safe_range.title")}
        explanation="Your safe repayment range is calculated from your verified monthly surplus (cash inflows minus predictable outflows), capped at 40% so you always keep a buffer for living expenses and emergencies."
        featureValue={`${formatCurrency(data.monthly_low, locale)} — ${formatCurrency(data.monthly_high, locale)} / mo`}
        targetValue="≤ 40% of free cash flow"
        code="affordability_surplus_cap"
      />
    </div>
  );
}
