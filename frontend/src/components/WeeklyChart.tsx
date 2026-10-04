"use client";

import React, { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { WeekForecast } from "@/lib/api";
import { useLanguage } from "@/contexts/LanguageContext";
import { formatCurrency, formatNumber } from "@/lib/format";

interface WeeklyChartProps {
  weeks: WeekForecast[];
}

export function WeeklyChart({ weeks }: WeeklyChartProps) {
  const { t, locale } = useLanguage();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return (
      <div className="w-full h-64 bg-gray-50 rounded-xl flex items-center justify-center border border-[#E8E8EC]">
        <div className="animate-pulse text-sm text-[#6B6B76]">
          {t("common.loading")}
        </div>
      </div>
    );
  }

  if (!weeks || weeks.length === 0) {
    return (
      <div className="w-full h-40 bg-gray-50 rounded-xl flex items-center justify-center border border-[#E8E8EC] p-4 text-center">
        <p className="text-sm text-[#6B6B76]">No forecast data available</p>
      </div>
    );
  }

  // Format chart data
  const data = weeks.map((w, idx) => {
    // Shorter week label: e.g. "W1", "W2" or month-day
    const dateStr = w.week_start ? w.week_start.slice(5) : `W${idx + 1}`;
    return {
      name: dateStr,
      rawWeek: w.week_start,
      moneyIn: Math.round(w.money_in || 0),
      moneyOut: Math.round(w.money_out || 0),
      expectedBalance: Math.round(w.expected_balance || 0),
      status: w.status,
      reason: w.reason,
    };
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="bg-white p-3 rounded-xl shadow-lg border border-[#E8E8EC] text-xs space-y-1.5 z-50">
          <p className="font-bold text-[#1A1A1F]">{item.rawWeek || label}</p>
          <div className="flex items-center justify-between gap-4 text-[#107C41]">
            <span>{t("calendar.money_in")}:</span>
            <span className="font-semibold">{formatCurrency(item.moneyIn, locale)}</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-[#C5221F]">
            <span>{t("calendar.money_out")}:</span>
            <span className="font-semibold">{formatCurrency(item.moneyOut, locale)}</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-[#005A9C] pt-1 border-t border-gray-100">
            <span>{t("calendar.expected_balance")}:</span>
            <span className="font-bold">{formatCurrency(item.expectedBalance, locale)}</span>
          </div>
          {item.status && (
            <div className="pt-1 text-[11px] text-[#6B6B76]">
              <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${item.status === "safe" ? "bg-[#107C41]" : "bg-[#B25E02]"}`} />
              {item.status === "safe" ? t("status.safe") : t("status.tight")}
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full">
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 12, right: 10, left: -20, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F0F0F2" />
            <XAxis
              dataKey="name"
              stroke="#6B6B76"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "#E8E8EC" }}
            />
            <YAxis
              stroke="#6B6B76"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "#E8E8EC" }}
              tickFormatter={(v) => `৳${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="top"
              height={32}
              formatter={(value) => {
                if (value === "moneyIn") return <span className="text-xs text-[#1A1A1F]">{t("calendar.money_in")}</span>;
                if (value === "moneyOut") return <span className="text-xs text-[#1A1A1F]">{t("calendar.money_out")}</span>;
                if (value === "expectedBalance") return <span className="text-xs text-[#1A1A1F]">{t("calendar.expected_balance")}</span>;
                return value;
              }}
            />
            <Bar dataKey="moneyIn" fill="#A8D5BA" radius={[4, 4, 0, 0]} maxBarSize={28} />
            <Bar dataKey="moneyOut" fill="#F8B4B4" radius={[4, 4, 0, 0]} maxBarSize={28} />
            <Line
              type="monotone"
              dataKey="expectedBalance"
              stroke="#005A9C"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#005A9C" }}
              activeDot={{ r: 5 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Week status pills row */}
      <div className="mt-3 flex items-center justify-between gap-1 overflow-x-auto pb-1 text-xs">
        {weeks.map((w, idx) => (
          <div
            key={idx}
            className={`flex-1 min-w-[50px] text-center px-1.5 py-1 rounded-lg border text-[11px] ${
              w.status === "safe"
                ? "bg-[#EAF5EE] text-[#107C41] border-[#C3E4CD]"
                : "bg-[#FEF5E7] text-[#B25E02] border-[#FBDCA8]"
            }`}
          >
            <div className="font-semibold">{w.week_start?.slice(5) || `W${idx + 1}`}</div>
            <div>{w.status === "safe" ? t("status.safe") : t("status.tight")}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default WeeklyChart;
