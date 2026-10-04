"use client";

import React from "react";
import { useLanguage } from "@/contexts/LanguageContext";

interface NumberFormatProps {
  value: number | null | undefined;
  type?: "currency" | "number";
  className?: string;
}

export function NumberFormat({
  value,
  type = "number",
  className = "",
}: NumberFormatProps) {
  const { formatNumber, formatCurrency } = useLanguage();

  if (value === null || value === undefined || isNaN(value)) {
    return <span className={className}>—</span>;
  }

  const formatted =
    type === "currency" ? formatCurrency(value) : formatNumber(value);

  return <span className={className}>{formatted}</span>;
}

export default NumberFormat;
