"use client";

import React from "react";
import { useLanguage } from "@/contexts/LanguageContext";
import { Minus, Plus } from "lucide-react";

interface LoanSlidersProps {
  amount: number;
  tenor: number;
  onAmountChange: (amount: number) => void;
  onTenorChange: (tenor: number) => void;
  minAmount?: number;
  maxAmount?: number;
  stepAmount?: number;
  minTenor?: number;
  maxTenor?: number;
}

export function LoanSliders({
  amount,
  tenor,
  onAmountChange,
  onTenorChange,
  minAmount = 1000,
  maxAmount = 50000,
  stepAmount = 500,
  minTenor = 1,
  maxTenor = 24,
}: LoanSlidersProps) {
  const { t, formatCurrency, formatNumber } = useLanguage();

  const handleAmountStep = (delta: number) => {
    const next = Math.max(minAmount, Math.min(maxAmount, amount + delta));
    onAmountChange(next);
  };

  const handleTenorStep = (delta: number) => {
    const next = Math.max(minTenor, Math.min(maxTenor, tenor + delta));
    onTenorChange(next);
  };

  return (
    <div className="space-y-6">
      {/* Amount Slider */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label htmlFor="loan-amount-slider" className="text-sm font-medium text-[#6B6B76]">
            {t("loan_check.amount_label")}
          </label>
          <span className="text-xl font-bold text-[#1A1A1F]">
            {formatCurrency(amount)}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => handleAmountStep(-stepAmount)}
            disabled={amount <= minAmount}
            aria-label="Decrease loan amount"
            className="w-10 h-10 rounded-xl border border-[#E8E8EC] flex items-center justify-center text-[#1A1A1F] hover:bg-gray-50 active:bg-gray-100 disabled:opacity-40 transition-colors shrink-0"
          >
            <Minus className="w-4 h-4" />
          </button>

          <input
            id="loan-amount-slider"
            type="range"
            min={minAmount}
            max={maxAmount}
            step={stepAmount}
            value={amount}
            onChange={(e) => onAmountChange(Number(e.target.value))}
            className="w-full h-2.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[var(--accent)] focus:outline-none"
            aria-valuemin={minAmount}
            aria-valuemax={maxAmount}
            aria-valuenow={amount}
          />

          <button
            type="button"
            onClick={() => handleAmountStep(stepAmount)}
            disabled={amount >= maxAmount}
            aria-label="Increase loan amount"
            className="w-10 h-10 rounded-xl border border-[#E8E8EC] flex items-center justify-center text-[#1A1A1F] hover:bg-gray-50 active:bg-gray-100 disabled:opacity-40 transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex justify-between text-xs text-[#6B6B76] mt-1.5 px-0.5">
          <span>{formatCurrency(minAmount)}</span>
          <span>{formatCurrency(maxAmount)}</span>
        </div>
      </div>

      {/* Tenor Slider */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label htmlFor="loan-tenor-slider" className="text-sm font-medium text-[#6B6B76]">
            {t("loan_check.tenor_label")}
          </label>
          <span className="text-xl font-bold text-[#1A1A1F]">
            {formatNumber(tenor)} {tenor === 1 ? t("common.month") : t("common.months")}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => handleTenorStep(-1)}
            disabled={tenor <= minTenor}
            aria-label="Decrease repayment tenor"
            className="w-10 h-10 rounded-xl border border-[#E8E8EC] flex items-center justify-center text-[#1A1A1F] hover:bg-gray-50 active:bg-gray-100 disabled:opacity-40 transition-colors shrink-0"
          >
            <Minus className="w-4 h-4" />
          </button>

          <input
            id="loan-tenor-slider"
            type="range"
            min={minTenor}
            max={maxTenor}
            step={1}
            value={tenor}
            onChange={(e) => onTenorChange(Number(e.target.value))}
            className="w-full h-2.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[var(--accent)] focus:outline-none"
            aria-valuemin={minTenor}
            aria-valuemax={maxTenor}
            aria-valuenow={tenor}
          />

          <button
            type="button"
            onClick={() => handleTenorStep(1)}
            disabled={tenor >= maxTenor}
            aria-label="Increase repayment tenor"
            className="w-10 h-10 rounded-xl border border-[#E8E8EC] flex items-center justify-center text-[#1A1A1F] hover:bg-gray-50 active:bg-gray-100 disabled:opacity-40 transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex justify-between text-xs text-[#6B6B76] mt-1.5 px-0.5">
          <span>{formatNumber(minTenor)} {t("common.month")}</span>
          <span>{formatNumber(maxTenor)} {t("common.months")}</span>
        </div>
      </div>
    </div>
  );
}

export default LoanSliders;
