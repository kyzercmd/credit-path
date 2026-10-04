"use client";

import React from "react";
import { useLanguage, Locale } from "@/contexts/LanguageContext";
import { Globe } from "lucide-react";

interface LanguageToggleProps {
  showNumeralToggle?: boolean;
  className?: string;
}

export function LanguageToggle({
  showNumeralToggle = false,
  className = "",
}: LanguageToggleProps) {
  const {
    locale,
    setLocale,
    useBanglaNumerals,
    toggleBanglaNumerals,
    t,
  } = useLanguage();

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {/* Language Toggle */}
      <div
        role="group"
        aria-label="Language selection"
        className="inline-flex items-center p-1 rounded-full bg-gray-100 border border-[#E8E8EC] self-start"
      >
        <button
          type="button"
          aria-pressed={locale === "en"}
          onClick={() => setLocale("en")}
          className={`min-h-[36px] min-w-[70px] px-3.5 py-1 text-sm font-medium rounded-full transition-all ${
            locale === "en"
              ? "bg-white text-[#1A1A1F] shadow-xs font-semibold"
              : "text-[#6B6B76] hover:text-[#1A1A1F]"
          }`}
        >
          English
        </button>
        <button
          type="button"
          aria-pressed={locale === "bn"}
          onClick={() => setLocale("bn")}
          className={`min-h-[36px] min-w-[70px] px-3.5 py-1 text-sm font-medium rounded-full transition-all ${
            locale === "bn"
              ? "bg-white text-[#1A1A1F] shadow-xs font-semibold"
              : "text-[#6B6B76] hover:text-[#1A1A1F]"
          }`}
        >
          বাংলা
        </button>
      </div>

      {/* Numeral preference toggle if enabled */}
      {showNumeralToggle && (
        <button
          type="button"
          onClick={toggleBanglaNumerals}
          className="flex items-center justify-between p-3 rounded-xl border border-[#E8E8EC] bg-white hover:bg-gray-50 text-left transition-colors min-h-[48px]"
        >
          <div className="flex items-center gap-2.5">
            <Globe className="w-4 h-4 text-[#6B6B76]" />
            <span className="text-sm font-medium text-[#1A1A1F]">
              {useBanglaNumerals ? t("me.bangla_numerals") : t("me.english_numerals")}
            </span>
          </div>
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gray-100 text-[#1A1A1F]">
            {useBanglaNumerals ? "১২৩" : "123"}
          </span>
        </button>
      )}
    </div>
  );
}

export default LanguageToggle;
