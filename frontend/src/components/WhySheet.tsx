"use client";

import React, { useEffect, ReactNode } from "react";
import { X, HelpCircle, Info } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

interface WhySheetProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  explanation: string;
  featureValue?: string | number | null;
  targetValue?: string | number | null;
  code?: string;
  children?: ReactNode;
}

export function WhySheet({
  isOpen,
  onClose,
  title,
  explanation,
  featureValue,
  targetValue,
  code,
  children,
}: WhySheetProps) {
  const { t } = useLanguage();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="why-sheet-title"
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[430px] bg-white rounded-t-3xl border-t border-[#E8E8EC] p-6 shadow-2xl flex flex-col max-h-[85vh] overflow-y-auto animate-in slide-in-from-bottom duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Grab bar */}
        <div className="mx-auto w-12 h-1.5 rounded-full bg-gray-200 mb-4 shrink-0" />

        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs uppercase tracking-wider font-semibold text-[#6B6B76]">
                {t("common.why")}
              </span>
              <h2 id="why-sheet-title" className="text-lg font-bold text-[#1A1A1F] leading-tight">
                {title}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("common.close")}
            className="w-10 h-10 -mr-2 -mt-2 rounded-full flex items-center justify-center text-[#6B6B76] hover:text-[#1A1A1F] hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Plain Language Explanation */}
        <div className="bg-[#F8F9FA] rounded-xl p-4 border border-[#E8E8EC] mb-4">
          <p className="text-[#1A1A1F] text-base leading-relaxed">
            {explanation}
          </p>
        </div>

        {/* Feature / Target Details */}
        {(featureValue !== undefined && featureValue !== null) && (
          <div className="space-y-2 mb-4">
            <div className="flex items-center justify-between text-sm py-2 border-b border-[#E8E8EC]">
              <span className="text-[#6B6B76]">Current Activity</span>
              <span className="font-semibold text-[#1A1A1F]">
                {featureValue}
              </span>
            </div>
            {targetValue !== undefined && targetValue !== null && (
              <div className="flex items-center justify-between text-sm py-2 border-b border-[#E8E8EC]">
                <span className="text-[#6B6B76]">Target / Benchmark</span>
                <span className="font-semibold text-[#107C41]">
                  {targetValue}
                </span>
              </div>
            )}
            {code && (
              <div className="flex items-center justify-between text-xs py-1.5 text-gray-400">
                <span>Rule Reference</span>
                <span className="font-mono">{code}</span>
              </div>
            )}
          </div>
        )}

        {children}

        {/* Action Button */}
        <div className="mt-6 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="w-full min-h-[48px] rounded-xl bg-[var(--accent)] text-white font-medium hover:opacity-95 active:scale-[0.99] transition-all"
          >
            {t("common.close")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default WhySheet;
