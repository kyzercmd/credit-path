"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/contexts/LanguageContext";
import { useConsent } from "@/contexts/ConsentContext";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Footer } from "@/components/Footer";
import { LanguageToggle } from "@/components/LanguageToggle";
import {
  ShieldCheck,
  User,
  Info,
  Sliders,
  Settings,
  ToggleLeft,
  ToggleRight,
  ExternalLink,
  Lock,
} from "lucide-react";

export default function MePage() {
  const { t, locale, useBanglaNumerals, toggleLanguage, setUseBanglaNumerals } = useLanguage();
  const { customerId, coachActive, setCoachActive, switchCustomer } = useConsent();

  const [inputCustomer, setInputCustomer] = useState(customerId);
  const [toggleLoading, setToggleLoading] = useState(false);

  const handleToggleCoach = async () => {
    setToggleLoading(true);
    try {
      await setCoachActive(!coachActive);
    } finally {
      setToggleLoading(false);
    }
  };

  const handleSwitchCustomer = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputCustomer.trim()) {
      switchCustomer(inputCustomer.trim().toUpperCase());
    }
  };

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <header className="pt-1">
        <h1 className="text-2xl font-bold text-[#1A1A1F]">
          {t("me.title")}
        </h1>
        <p className="text-xs text-[#6B6B76] mt-0.5">
          Manage your coaching preferences and data settings.
        </p>
      </header>

      {/* Card 1: Active Profile & Switcher */}
      <Card
        title={t("me.customer_account")}
        subtitle="Current test profile loaded in app"
      >
        <form onSubmit={handleSwitchCustomer} className="space-y-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inputCustomer}
              onChange={(e) => setInputCustomer(e.target.value)}
              placeholder="e.g. C0001"
              className="flex-1 min-h-[44px] px-3 py-2 rounded-xl border border-[#E8E8EC] text-sm font-mono uppercase focus:outline-none focus:border-[var(--accent)]"
            />
            <button
              type="submit"
              className="min-h-[44px] px-4 rounded-xl bg-[var(--accent)] text-white text-xs font-semibold hover:opacity-95"
            >
              {t("common.save")}
            </button>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap text-xs text-[#6B6B76] pt-1">
            <span>Quick switch:</span>
            {["C0001", "C0002", "C0003", "C0004", "C0005"].map((cid) => (
              <button
                key={cid}
                type="button"
                onClick={() => {
                  setInputCustomer(cid);
                  switchCustomer(cid);
                }}
                className={`px-2 py-0.5 rounded font-mono border text-[11px] ${
                  customerId === cid
                    ? "bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]/30 font-bold"
                    : "bg-gray-50 border-gray-200 text-[#1A1A1F] hover:bg-gray-100"
                }`}
              >
                {cid}
              </button>
            ))}
          </div>
        </form>
      </Card>

      {/* Card 2: Coach Control Toggle (F10) */}
      <Card>
        <div className="flex items-center justify-between gap-3">
          <div className="space-y-0.5">
            <h4 className="text-base font-semibold text-[#1A1A1F]">
              {t("me.coach_toggle")}
            </h4>
            <p className="text-xs text-[#6B6B76] leading-relaxed">
              {t("me.coach_toggle_desc")}
            </p>
          </div>

          <button
            type="button"
            onClick={handleToggleCoach}
            disabled={toggleLoading}
            aria-label={coachActive ? t("me.opt_out") : t("me.opt_in")}
            className="shrink-0 p-1 text-[var(--accent)] disabled:opacity-50 transition-opacity"
          >
            {coachActive ? (
              <ToggleRight className="w-9 h-9 fill-[var(--accent)] text-white" />
            ) : (
              <ToggleLeft className="w-9 h-9 text-gray-300" />
            )}
          </button>
        </div>

        <div className="mt-3 pt-3 border-t border-[#E8E8EC] flex items-center justify-between text-xs text-[#6B6B76]">
          <span>Coaching status</span>
          <span
            className={`font-semibold ${
              coachActive ? "text-[#107C41]" : "text-[#B25E02]"
            }`}
          >
            {coachActive ? t("common.active") : t("common.inactive")}
          </span>
        </div>
      </Card>

      {/* Card 3: Language & Numerals */}
      <Card
        title={t("me.language_section")}
        subtitle="Display language and number script"
      >
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-[#E8E8EC]">
            <span className="text-sm text-[#1A1A1F]">Language</span>
            <LanguageToggle />
          </div>

          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-[#1A1A1F]">Numerals</span>
            <div className="flex items-center gap-1 bg-[#F4F4F6] p-1 rounded-xl">
              <button
                type="button"
                onClick={() => setUseBanglaNumerals(false)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                  !useBanglaNumerals
                    ? "bg-white text-[#1A1A1F] shadow-2xs"
                    : "text-[#6B6B76]"
                }`}
              >
                123
              </button>
              <button
                type="button"
                onClick={() => setUseBanglaNumerals(true)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                  useBanglaNumerals
                    ? "bg-white text-[#1A1A1F] shadow-2xs"
                    : "text-[#6B6B76]"
                }`}
              >
                ১২৩
              </button>
            </div>
          </div>
        </div>
      </Card>

      {/* Card 4: Privacy & Ethics (F10) */}
      <Card
        title={t("me.privacy_data")}
        headerRight={
          <div className="w-7 h-7 rounded-lg bg-[#EAF5EE] text-[#107C41] flex items-center justify-center">
            <Lock className="w-4 h-4" />
          </div>
        }
      >
        <p className="text-xs text-[#6B6B76] leading-relaxed">
          {t("me.privacy_desc")}
        </p>
      </Card>

      {/* Card 5: About CreditPath (F11) */}
      <Card
        title={t("me.about_title")}
        headerRight={
          <div className="w-7 h-7 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
            <Info className="w-4 h-4" />
          </div>
        }
      >
        <p className="text-xs text-[#6B6B76] leading-relaxed">
          {t("me.about_desc")}
        </p>
      </Card>

      {/* Internal Admin Link */}
      <div className="pt-2">
        <Link
          href="/admin"
          className="flex items-center justify-between p-3.5 rounded-xl border border-gray-200 bg-gray-50 text-xs font-semibold text-[#6B6B76] hover:text-[#1A1A1F] hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4" />
            <span>Open Admin & Model Quality View</span>
          </div>
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>

      <Footer />
    </div>
  );
}
