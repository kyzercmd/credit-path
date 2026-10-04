"use client";

import React, { ReactNode } from "react";
import { CalendarClock, Info } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { Button } from "./Button";

interface EmptyStateProps {
  title?: string;
  message?: string;
  monthsActive?: number;
  requiredMonths?: number;
  actionLabel?: string;
  onAction?: () => void;
  icon?: ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  message,
  monthsActive,
  requiredMonths = 3,
  actionLabel,
  onAction,
  icon,
  className = "",
}: EmptyStateProps) {
  const { t } = useLanguage();

  let displayDesc = message;
  if (!displayDesc) {
    if (monthsActive !== undefined) {
      displayDesc = t("common.empty_data_desc", { months: monthsActive });
    } else {
      displayDesc = t("common.empty_data_desc", { months: 0 });
    }
  }

  return (
    <div
      className={`bg-white rounded-2xl border border-[#E8E8EC] p-6 text-center shadow-xs flex flex-col items-center justify-center ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mb-4">
        {icon || <CalendarClock className="w-6 h-6" />}
      </div>

      <h3 className="text-lg font-semibold text-[#1A1A1F] mb-1.5">
        {title || t("common.empty_data_title")}
      </h3>

      <p className="text-sm text-[#6B6B76] max-w-sm mb-6 leading-relaxed">
        {displayDesc}
      </p>

      {monthsActive !== undefined && (
        <div className="w-full max-w-xs mb-6">
          <div className="flex justify-between text-xs text-[#6B6B76] mb-1.5">
            <span>Progress: {monthsActive} of {requiredMonths} months</span>
            <span>{Math.min(100, Math.round((monthsActive / requiredMonths) * 100))}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
            <div
              className="h-full bg-[var(--accent)] rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, (monthsActive / requiredMonths) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {actionLabel && onAction && (
        <Button
          variant="secondary"
          onClick={onAction}
          className="max-w-[200px]"
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

export default EmptyState;
