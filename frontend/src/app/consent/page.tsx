"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { useConsent } from "@/contexts/ConsentContext";
import { Button } from "@/components/Button";
import { Footer } from "@/components/Footer";
import { LanguageToggle } from "@/components/LanguageToggle";
import { ShieldCheck, Calendar, TrendingUp } from "lucide-react";

export default function ConsentPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const { setConsent, consentLog } = useConsent();
  const [loading, setLoading] = useState(false);

  const handleAccept = async () => {
    setLoading(true);
    try {
      await setConsent(true);
      router.replace("/home");
    } finally {
      setLoading(false);
    }
  };

  const handleDecline = async () => {
    setLoading(true);
    try {
      await setConsent(false);
      router.replace("/home");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen p-6 justify-between max-w-[430px] mx-auto">
      <div>
        {/* Top bar with language toggle */}
        <div className="flex justify-end mb-6">
          <LanguageToggle />
        </div>

        {/* Brand & Hero */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] mx-auto flex items-center justify-center mb-4 shadow-sm">
            <TrendingUp className="w-8 h-8 stroke-[2.2]" />
          </div>
          <h1 className="text-2xl font-bold text-[#1A1A1F] tracking-tight">
            {t("consent.title")}
          </h1>
          <p className="text-sm text-[#6B6B76] mt-2 max-w-xs mx-auto leading-relaxed">
            {t("consent.subtitle")}
          </p>
        </div>

        {/* Feature Highlights */}
        <div className="space-y-4 mb-8">
          <div className="flex items-start gap-3.5 p-4 rounded-2xl bg-[#F8F9FA] border border-[#E8E8EC]">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0">
              <TrendingUp className="w-5 h-5 stroke-[2]" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[#1A1A1F]">
                {t("consent.feature1_title")}
              </h3>
              <p className="text-xs text-[#6B6B76] mt-0.5 leading-relaxed">
                {t("consent.feature1_desc")}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5 p-4 rounded-2xl bg-[#F8F9FA] border border-[#E8E8EC]">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0">
              <Calendar className="w-5 h-5 stroke-[2]" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[#1A1A1F]">
                {t("consent.feature2_title")}
              </h3>
              <p className="text-xs text-[#6B6B76] mt-0.5 leading-relaxed">
                {t("consent.feature2_desc")}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5 p-4 rounded-2xl bg-[#F8F9FA] border border-[#E8E8EC]">
            <div className="w-10 h-10 rounded-xl bg-[#EAF5EE] text-[#107C41] flex items-center justify-center shrink-0">
              <ShieldCheck className="w-5 h-5 stroke-[2]" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[#1A1A1F]">
                {t("consent.feature3_title")}
              </h3>
              <p className="text-xs text-[#6B6B76] mt-0.5 leading-relaxed">
                {t("consent.feature3_desc")}
              </p>
            </div>
          </div>
        </div>

        {/* Prior Consent Activity (if exists) */}
        {consentLog && consentLog.length > 0 && (
          <div className="mb-6 p-3.5 rounded-2xl border border-[#E8E8EC] bg-[#F8F9FA]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#1A1A1F]">
                {t("consent.prior_consent")}
              </span>
              <span className="text-[10px] text-[#6B6B76] font-mono">
                {consentLog.length} record(s)
              </span>
            </div>
            <div className="space-y-1.5 max-h-28 overflow-y-auto">
              {consentLog.slice(0, 3).map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-[11px] text-[#6B6B76] border-t border-gray-100 pt-1.5"
                >
                  <span className="flex items-center gap-1.5">
                    <span
                      className={`inline-block w-1.5 h-1.5 rounded-full ${
                        item.action === "consent" ? "bg-[#107C41]" : "bg-[#B25E02]"
                      }`}
                    />
                    {item.action === "consent" ? t("me.consent_granted") : t("me.consent_revoked")} ({item.customerId})
                  </span>
                  <span className="font-mono text-[10px]">
                    {item.timestamp.replace("T", " ").slice(0, 16)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Action buttons & Footer */}
      <div className="pt-4 space-y-3">
        <Button
          onClick={handleAccept}
          isLoading={loading}
          variant="primary"
          fullWidth
        >
          {t("consent.accept_button")}
        </Button>

        <button
          type="button"
          onClick={handleDecline}
          disabled={loading}
          className="w-full text-center text-xs text-[#6B6B76] hover:text-[#1A1A1F] py-2 transition-colors disabled:opacity-50"
        >
          {t("consent.decline_link")}
        </button>

        <Footer />
      </div>
    </div>
  );
}
