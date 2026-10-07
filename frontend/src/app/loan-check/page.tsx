"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { useConsent } from "@/contexts/ConsentContext";
import { postLoanCheck, postFunnelEvent, LoanCheckResponse, ApiError } from "@/lib/api";
import { postLoanCheck, LoanCheckResponse, ApiError, FinancingStructure } from "@/lib/api";
import { LoanSliders } from "@/components/LoanSliders";
import { StatusBadge } from "@/components/StatusBadge";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Footer } from "@/components/Footer";
import { Skeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/ErrorState";
import { WhySheet } from "@/components/WhySheet";
import { ArrowLeft, HelpCircle, Sparkles, AlertCircle, ShieldAlert } from "lucide-react";

export default function LoanCheckPage() {
  const router = useRouter();
  const { t, locale, formatCurrency, formatNumber } = useLanguage();
  const { customerId } = useConsent();

  const [amount, setAmount] = useState<number>(10000);
  const [tenor, setTenor] = useState<number>(6);

  // Financing structure inputs (request-only; never stored on the profile).
  const [structure, setStructure] = useState<FinancingStructure>("conventional");
  const [totalAgreed, setTotalAgreed] = useState<string>("");
  const [providerFees, setProviderFees] = useState<string>("0");
  const financingRef = useRef<{ structure: FinancingStructure; totalAgreed: string; providerFees: string }>({
    structure: "conventional",
    totalAgreed: "",
    providerFees: "0",
  });

  const [data, setData] = useState<LoanCheckResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [calculating, setCalculating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isKilled, setIsKilled] = useState<boolean>(false);
  const [showWhy, setShowWhy] = useState<boolean>(false);

  const reqSeqRef = useRef<number>(0);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const buildFinancing = () => {
    const f = financingRef.current;
    if (f.structure === "fixed_payment") {
      return { financing_structure: f.structure, total_repayment: Number(f.totalAgreed) || undefined };
    }
    if (f.structure === "interest_free") {
      return { financing_structure: f.structure, provider_fees: Number(f.providerFees) || 0 };
    }
    return { financing_structure: f.structure };
  };

  const runCheck = useCallback(
    async (amt: number, tnr: number, isInitial = false) => {
      const seq = ++reqSeqRef.current;
      if (isInitial) setLoading(true);
      else setCalculating(true);
      setError(null);
      setIsKilled(false);

      try {
        const res = await postLoanCheck(customerId, amt, tnr, buildFinancing());
        if (seq === reqSeqRef.current) {
          setData(res);
          postFunnelEvent(customerId, "loan_check_performed", {
            amount: amt,
            tenor: tnr,
            verdict: res.verdict,
          }).catch(() => {});
          if (res.verdict === "Comfortable") {
            postFunnelEvent(customerId, "credit_converted", {
              amount: amt,
              monthly_payment: res.monthly_payment,
            }).catch(() => {});
          }
        }
      } catch (err: any) {
        if (seq === reqSeqRef.current) {
          if (err instanceof ApiError && err.status === 403) {
            setIsKilled(true);
          } else if (err instanceof ApiError && err.status === 422) {
            setError(t("loan_check.total_below_amount"));
          } else {
            setError(err?.message || "Failed to calculate loan check");
          }
        }
      } finally {
        if (seq === reqSeqRef.current) {
          setLoading(false);
          setCalculating(false);
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [customerId]
  );

  useEffect(() => {
    runCheck(amount, tenor, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId]);

  const scheduleCheck = useCallback(
    (amt: number, tnr: number) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(() => {
        runCheck(amt, tnr, false);
      }, 250);
    },
    [runCheck]
  );

  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const handleAmountChange = (newAmt: number) => {
    setAmount(newAmt);
    scheduleCheck(newAmt, tenor);
  };

  const handleTenorChange = (newTenor: number) => {
    setTenor(newTenor);
    scheduleCheck(amount, newTenor);
  };

  const handleStructureChange = (next: FinancingStructure) => {
    setStructure(next);
    // Pre-fill the agreed total with the amount the user already chose (no computation).
    const nextTotal = next === "fixed_payment" && !totalAgreed ? String(amount) : totalAgreed;
    setTotalAgreed(nextTotal);
    financingRef.current = { ...financingRef.current, structure: next, totalAgreed: nextTotal };
    scheduleCheck(amount, tenor);
  };

  const handleTotalAgreedChange = (value: string) => {
    setTotalAgreed(value);
    financingRef.current = { ...financingRef.current, totalAgreed: value };
    scheduleCheck(amount, tenor);
  };

  const handleProviderFeesChange = (value: string) => {
    setProviderFees(value);
    financingRef.current = { ...financingRef.current, providerFees: value };
    scheduleCheck(amount, tenor);
  };

  const applyNearestComfortable = () => {
    if (data?.nearest_comfortable) {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      const newAmt = data.nearest_comfortable.amount;
      const newTenor = data.nearest_comfortable.tenor_months;
      setAmount(newAmt);
      setTenor(newTenor);
      runCheck(newAmt, newTenor, false);
    }
  };

  if (loading) {
    return (
      <div className="p-5 space-y-6">
        <Skeleton lines={1} className="w-24 h-6" />
        <Skeleton lines={5} className="h-56 rounded-2xl" />
        <Skeleton lines={4} className="h-44 rounded-2xl" />
      </div>
    );
  }

  if (isKilled) {
    return (
      <div className="p-5 min-h-[60vh] flex flex-col justify-center text-center">
        <Card className="py-6">
          <div className="w-12 h-12 rounded-full bg-amber-50 text-[#B25E02] mx-auto flex items-center justify-center mb-3">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-[#1A1A1F] mb-1">
            Loan Check Temporarily Disabled
          </h2>
          <p className="text-sm text-[#6B6B76] mb-5">
            Emergency controls are active. Loan fit calculations are paused.
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

  if (error && !data) {
    return (
      <div className="p-5 min-h-[60vh] flex flex-col justify-center">
        <ErrorState
          message={error || t("common.error_desc")}
          onRetry={() => runCheck(amount, tenor, true)}
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
          {t("loan_check.title")}
        </h1>
        <p className="text-xs text-[#6B6B76] mt-0.5">
          {t("loan_check.subtitle")}
        </p>
      </div>

      {/* Card 1: Financing type + Sliders */}
      <Card>
        <div className="mb-5" data-financing-selector>
          <span className="block text-xs font-semibold text-[#1A1A1F] mb-2">
            {t("loan_check.financing_type")}
          </span>
          {/* TODO: native-speaker review - Bangla translations for financing structures, labels, and disclaimers */}
          <div role="radiogroup" className="grid grid-cols-3 gap-1 p-1 rounded-xl bg-[#F3F4F6]">
            {(["conventional", "fixed_payment", "interest_free"] as FinancingStructure[]).map((opt) => (
              <button
                key={opt}
                type="button"
                role="radio"
                aria-checked={structure === opt}
                onClick={() => handleStructureChange(opt)}
                className={`text-sm text-center whitespace-normal px-2 py-2 rounded-lg font-semibold transition-colors ${
                  structure === opt
                    ? "bg-white text-[#1A1A1F] shadow-sm"
                    : "text-[#6B6B76] hover:text-[#1A1A1F]"
                }`}
              >
                {t(`loan_check.financing_${opt}`)}
              </button>
            ))}
          </div>

          {structure === "fixed_payment" && (
            <label className="block mt-3">
              <span className="block text-xs font-semibold text-[#1A1A1F] mb-1">
                {t("loan_check.total_repayment")}
              </span>
              <input
                type="number"
                inputMode="decimal"
                min={0}
                value={totalAgreed}
                onChange={(e) => handleTotalAgreedChange(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-[#E8E8EC] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </label>
          )}

          {structure === "interest_free" && (
            <label className="block mt-3">
              <span className="block text-xs font-semibold text-[#1A1A1F] mb-1">
                {t("loan_check.provider_fees")}
              </span>
              <input
                type="number"
                inputMode="decimal"
                min={0}
                value={providerFees}
                onChange={(e) => handleProviderFeesChange(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-[#E8E8EC] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </label>
          )}
        </div>

        <LoanSliders
          amount={amount}
          tenor={tenor}
          onAmountChange={handleAmountChange}
          onTenorChange={handleTenorChange}
        />

        {error && data && (
          <p className="mt-3 text-xs text-red-600" role="alert">
            {error}
          </p>
        )}
      </Card>

      {/* Card 2: Verdict & Monthly Breakdown */}
      {data && (
        <Card
          aria-live="polite"
          aria-atomic="true"
          className={`transition-opacity ${calculating ? "opacity-60" : "opacity-100"}`}
        >
          {/* Verdict Banner */}
          <div className="flex items-center justify-between gap-2 pb-4 border-b border-[#E8E8EC] mb-4">
            <div>
              <span className="text-xs uppercase tracking-wider font-semibold text-[#6B6B76]">
                {t("loan_check.verdict_title")}
              </span>
              <div className="mt-1">
                <StatusBadge
                  status={data.verdict}
                  size="md"
                />
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs text-[#6B6B76]">
                {t("loan_check.monthly_payment_label")}
              </span>
              <div className="text-xl font-extrabold text-[#1A1A1F]">
                {formatCurrency(data.monthly_payment)}
                <span className="text-xs font-normal text-[#6B6B76]">
                  {t("common.per_month")}
                </span>
              </div>
            </div>
          </div>

          {/* Verdict Plain Description */}
          <div className="space-y-2 mb-4">
            <p className="text-sm text-[#1A1A1F] leading-relaxed">
              {data.verdict_reason}
            </p>

            {data.stress_reason && (
              <div className="p-3 rounded-xl bg-gray-50 border border-gray-100 text-xs text-[#6B6B76] flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-gray-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-[#1A1A1F]">
                    {t("loan_check.stress_note")}:{" "}
                  </span>
                  <span>{data.stress_reason}</span>
                </div>
              </div>
            )}
          </div>

          {/* Totals Summary Row (values come from the API, never computed here) */}
          <div className="flex justify-between items-center py-2.5 px-3 bg-[#F8F9FA] rounded-xl text-xs">
            <span className="text-[#6B6B76]">{t("loan_check.total_repayment")}</span>
            <span className="font-bold text-[#1A1A1F]">
              {formatCurrency(data.total_repayment)}
            </span>
          </div>
          <div className="mt-1.5 flex justify-between items-center py-2.5 px-3 bg-[#F8F9FA] rounded-xl text-xs">
            <span className="text-[#6B6B76]">{t("loan_check.extra_cost")}</span>
            <span className="font-bold text-[#1A1A1F]">
              {formatCurrency(data.extra_cost)}
            </span>
          </div>

          {/* Nearest Comfortable Option (if Too Much) */}
          {data.nearest_comfortable && (
            <div className="mt-4 p-4 rounded-xl bg-[#EAF5EE] border border-[#C3E4CD] space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#107C41]">
                <Sparkles className="w-4 h-4" />
                <span>{t("loan_check.nearest_title")}</span>
              </div>
              <p className="text-xs text-[#1A1A1F] leading-relaxed">
                ৳{formatNumber(data.nearest_comfortable.amount)} over{" "}
                {formatNumber(data.nearest_comfortable.tenor_months)} months (৳
                {formatNumber(data.nearest_comfortable.monthly_payment)}/mo) would fit comfortably.
              </p>
              <button
                type="button"
                onClick={applyNearestComfortable}
                className="text-xs font-bold text-[var(--accent)] hover:underline inline-block pt-1"
              >
                Apply this combination →
              </button>
            </div>
          )}

          <p className="mt-4 text-[11px] leading-relaxed text-[#6B6B76]" data-financing-disclaimer>
            {t("loan_check.disclaimer")}
          </p>
        </Card>
      )}

      {/* Meta Footer */}
      {data && <Footer meta={data.meta} />}

      {/* Why Sheet */}
      {data && (
        <WhySheet
          isOpen={showWhy}
          onClose={() => setShowWhy(false)}
          title={t("loan_check.title")}
          explanation={data.verdict_reason}
          featureValue={`৳${formatNumber(data.monthly_payment)} / mo (${formatNumber(Math.round(data.surplus_share * 100))}% of spare money)`}
          targetValue="< 40% spare money = Comfortable"
          code="affordability_verdict"
        />
      )}
    </div>
  );
}
