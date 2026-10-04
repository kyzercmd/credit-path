"use client";

import React from "react";
import { AlertCircle, Lightbulb } from "lucide-react";
import { HeadsUpCard as HeadsUpData } from "@/lib/api";
import { useLanguage } from "@/contexts/LanguageContext";

interface HeadsUpCardProps {
  headsUp: HeadsUpData;
  className?: string;
  onWhyClick?: () => void;
}

export function HeadsUpCard({ headsUp, className = "", onWhyClick }: HeadsUpCardProps) {
  const { t } = useLanguage();

  if (!headsUp || !headsUp.message) return null;

  return (
    <div
      className={`rounded-2xl border border-[#FBDCA8] bg-[#FFFBF2] p-4 shadow-[0_2px_8px_rgba(178,94,2,0.05)] ${className}`}
      role="region"
      aria-label="Cash flow notice"
    >
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-xl bg-[#FEF5E7] text-[#B25E02] flex items-center justify-center shrink-0 border border-[#FBDCA8]">
          <Lightbulb className="w-4 h-4 stroke-[2.2]" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-[#B25E02]">
              {t("calendar.heads_up")}
            </span>
            {headsUp.week && (
              <span className="text-xs font-medium text-[#6B6B76] bg-white/80 px-2 py-0.5 rounded-full border border-[#FBDCA8]">
                {headsUp.week}
              </span>
            )}
          </div>

          <p className="text-sm font-medium text-[#1A1A1F] leading-snug">
            {headsUp.message}
          </p>

          {headsUp.suggestion && (
            <p className="text-xs text-[#6B6B76] mt-1.5 leading-relaxed bg-white/70 p-2 rounded-lg border border-[#FBDCA8]/60">
              💡 {headsUp.suggestion}
            </p>
          )}

          {onWhyClick && (
            <div className="mt-2.5">
              <button
                type="button"
                onClick={onWhyClick}
                className="text-xs font-semibold text-[var(--accent)] hover:underline inline-flex items-center gap-1"
              >
                {t("common.why")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default HeadsUpCard;
