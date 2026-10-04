"use client";

import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { Button } from "./Button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title,
  message,
  onRetry,
  className = "",
}: ErrorStateProps) {
  const { t } = useLanguage();

  return (
    <div
      role="alert"
      className={`bg-white rounded-2xl border border-[#E8E8EC] p-6 text-center shadow-xs flex flex-col items-center justify-center ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-[#FDE8E8] text-[#C5221F] flex items-center justify-center mb-4">
        <AlertCircle className="w-6 h-6" />
      </div>

      <h3 className="text-lg font-semibold text-[#1A1A1F] mb-1">
        {title || t("common.error_title")}
      </h3>

      <p className="text-sm text-[#6B6B76] max-w-xs mb-6 leading-relaxed">
        {message || t("common.error_desc")}
      </p>

      {onRetry && (
        <Button
          variant="secondary"
          onClick={onRetry}
          leftIcon={<RefreshCw className="w-4 h-4" />}
          className="max-w-[200px]"
        >
          {t("common.retry")}
        </Button>
      )}
    </div>
  );
}

export default ErrorState;
