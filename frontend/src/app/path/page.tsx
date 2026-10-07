"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { useConsent } from "@/contexts/ConsentContext";
import { getPath, postFunnelEvent, PathResponse, PathStep } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Footer } from "@/components/Footer";
import { Skeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/ErrorState";
import { WhySheet } from "@/components/WhySheet";
import { ArrowLeft, CheckCircle2, Clock, Compass, HelpCircle, Sparkles } from "lucide-react";

export default function PathPage() {
  const router = useRouter();
  const { t, formatNumber } = useLanguage();
  const { customerId } = useConsent();

  const [data, setData] = useState<PathResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState<PathStep | null>(null);

  const loadPath = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPath(customerId);
      setData(res);
      postFunnelEvent(customerId, "path_explored", { steps_count: res.missing_items.length }).catch(() => {});
    } catch (err: any) {
      setError(err?.message || "Failed to load path to ready");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    loadPath();
  }, [loadPath]);

  if (loading) {
    return (
      <div className="p-5 space-y-6">
        <Skeleton lines={1} className="w-24 h-6" />
        <Skeleton lines={3} className="h-28 rounded-2xl" />
        <Skeleton lines={5} className="h-52 rounded-2xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-5 min-h-[60vh] flex flex-col justify-center">
        <ErrorState
          message={error || t("common.error_desc")}
          onRetry={loadPath}
        />
      </div>
    );
  }

  const steps = data.missing_items || [];

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
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#EAF5EE] text-[#107C41] text-xs font-semibold mb-2">
          <Compass className="w-3.5 h-3.5" />
          <span>Personal Coaching</span>
        </div>
        <h1 className="text-2xl font-bold text-[#1A1A1F]">
          {t("path.title")}
        </h1>
        <p className="text-xs text-[#6B6B76] mt-0.5 leading-relaxed">
          {t("path.subtitle")}
        </p>
      </div>

      {/* Ready Already Card (Empty State) */}
      {steps.length === 0 ? (
        <Card className="text-center py-8">
          <div className="w-12 h-12 rounded-full bg-[#EAF5EE] text-[#107C41] mx-auto flex items-center justify-center mb-3">
            <CheckCircle2 className="w-6 h-6 stroke-[2.2]" />
          </div>
          <h3 className="text-lg font-bold text-[#1A1A1F] mb-1">
            All checks passed!
          </h3>
          <p className="text-xs text-[#6B6B76] mb-5 max-w-xs mx-auto">
            You currently meet all readiness benchmarks. You can review your comfortable loan range.
          </p>
          <Link href="/safe-range">
            <Button variant="primary" fullWidth>
              {t("home.see_safe_range")}
            </Button>
          </Link>
        </Card>
      ) : (
        /* Action Steps List */
        <div className="space-y-4">
          {steps.map((step, idx) => (
            <Card key={idx} className="border-l-4 border-l-[var(--accent)]">
              <div className="flex items-start justify-between gap-3 mb-2">
                <span className="text-xs font-bold text-[var(--accent)] uppercase tracking-wider">
                  Step {idx + 1}: {step.item}
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#6B6B76] bg-gray-100 px-2 py-0.5 rounded-full shrink-0">
                  <Clock className="w-3 h-3" />
                  <span>
                    ~{formatNumber(step.estimated_weeks)}{" "}
                    {step.estimated_weeks === 1 ? t("common.week") : t("common.weeks")}
                  </span>
                </span>
              </div>

              <h4 className="text-base font-semibold text-[#1A1A1F] leading-snug mb-1">
                {step.action}
              </h4>

              <p className="text-xs text-[#6B6B76] leading-relaxed mb-3">
                {step.reason}
              </p>

              <div className="flex items-center justify-between pt-2 border-t border-[#E8E8EC] text-xs">
                <span className="text-gray-400 italic">
                  Indicative, based on activity patterns
                </span>
                <button
                  type="button"
                  onClick={() => setActiveStep(step)}
                  className="font-semibold text-[var(--accent)] hover:underline inline-flex items-center gap-1"
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                  <span>{t("common.why")}</span>
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Return CTA */}
      <Link href="/home" className="block pt-2">
        <Button variant="secondary" fullWidth>
          {t("path.back_to_home")}
        </Button>
      </Link>

      <Footer meta={data.meta} />

      {/* Why Explanation Sheet */}
      {activeStep && (
        <WhySheet
          isOpen={Boolean(activeStep)}
          onClose={() => setActiveStep(null)}
          title={activeStep.item}
          explanation={activeStep.reason}
          targetValue={`~${activeStep.estimated_weeks} weeks of steady behavior`}
          code="recourse_behavior_counterfactual"
        />
      )}
    </div>
  );
}
