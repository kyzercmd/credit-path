"use client";

import React from "react";
import { ForecastQualityResponse } from "@/lib/api";
import { Card } from "@/components/Card";
import { TrendingUp, BarChart3, Award, ArrowDownRight, ArrowUpRight } from "lucide-react";

interface ForecastQualityProps {
  data?: ForecastQualityResponse | null;
  isLoading?: boolean;
}

const PERSONA_LABELS: Record<string, { title: string; desc: string }> = {
  wage_worker: { title: "Wage Worker", desc: "Daily/weekly variable cash earnings" },
  seasonal_farmer: { title: "Seasonal Farmer", desc: "Agricultural harvest cyclicality" },
  informal_merchant: { title: "Informal Merchant", desc: "Small shop / retail merchant turnover" },
  woman_led_household: { title: "Woman-Led Household", desc: "Domestic micro-enterprise & family budget" },
  salaried_user: { title: "Salaried User", desc: "Predictable monthly payroll deposits" },
};

export function ForecastQuality({ data, isLoading = false }: ForecastQualityProps) {
  if (isLoading) {
    return (
      <Card title="Forecast Quality (U2)" subtitle="Cash flow model evaluation vs naive baseline">
        <div className="space-y-4 animate-pulse">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="h-24 bg-gray-100 rounded-xl" />
            <div className="h-24 bg-gray-100 rounded-xl" />
            <div className="h-24 bg-gray-100 rounded-xl" />
            <div className="h-24 bg-gray-100 rounded-xl" />
          </div>
          <div className="h-48 bg-gray-100 rounded-xl" />
        </div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card title="Forecast Quality (U2)" subtitle="Cash flow model evaluation vs naive baseline">
        <p className="text-sm text-[#6B6B76] py-4">No forecast quality metrics available.</p>
      </Card>
    );
  }

  const { overall_mae = 0, overall_wape = 0, naive_mae = 0, naive_wape = 0, by_persona = {} } = data;

  const maeDelta = naive_mae > 0 ? (((naive_mae - overall_mae) / naive_mae) * 100).toFixed(1) : "0.0";
  const wapeDelta = naive_wape > 0 ? (((naive_wape - overall_wape) / naive_wape) * 100).toFixed(1) : "0.0";

  const personaKeys = [
    "wage_worker",
    "seasonal_farmer",
    "informal_merchant",
    "woman_led_household",
    "salaried_user",
    ...Object.keys(by_persona).filter(
      (k) =>
        ![
          "wage_worker",
          "seasonal_farmer",
          "informal_merchant",
          "woman_led_household",
          "salaried_user",
        ].includes(k)
    ),
  ];

  return (
    <Card
      title="Forecast Quality (U2)"
      subtitle="Held-out test set evaluation: Model accuracy compared to naive baseline across customer personas"
      className="w-full"
    >
      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="p-4 rounded-xl bg-gray-50 border border-[#E8E8EC]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#6B6B76] uppercase tracking-wider">Model MAE</span>
            <Award className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-bold text-[#1A1A1F] mt-1">৳{overall_mae.toFixed(1)}</p>
          <div className="flex items-center gap-1 mt-1 text-xs text-emerald-700 font-medium">
            <ArrowDownRight className="w-3.5 h-3.5" />
            <span>{maeDelta}% better than naive</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-gray-50 border border-[#E8E8EC]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#6B6B76] uppercase tracking-wider">Naive Baseline MAE</span>
            <BarChart3 className="w-4 h-4 text-gray-400" />
          </div>
          <p className="text-2xl font-bold text-[#6B6B76] mt-1">৳{naive_mae.toFixed(1)}</p>
          <p className="text-xs text-[#6B6B76] mt-1">Historical 4-week average</p>
        </div>

        <div className="p-4 rounded-xl bg-gray-50 border border-[#E8E8EC]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#6B6B76] uppercase tracking-wider">Model WAPE</span>
            <TrendingUp className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-bold text-[#1A1A1F] mt-1">{(overall_wape * 100).toFixed(1)}%</p>
          <div className="flex items-center gap-1 mt-1 text-xs text-emerald-700 font-medium">
            <ArrowDownRight className="w-3.5 h-3.5" />
            <span>{wapeDelta}% error reduction</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-gray-50 border border-[#E8E8EC]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#6B6B76] uppercase tracking-wider">Naive Baseline WAPE</span>
            <BarChart3 className="w-4 h-4 text-gray-400" />
          </div>
          <p className="text-2xl font-bold text-[#6B6B76] mt-1">{(naive_wape * 100).toFixed(1)}%</p>
          <p className="text-xs text-[#6B6B76] mt-1">Weighted absolute percentage error</p>
        </div>
      </div>

      {/* Comparison Table by Persona */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-[#1A1A1F]">Performance by Customer Persona</h4>
          <span className="text-xs text-[#6B6B76]">Test split persona cohorts</span>
        </div>

        <div className="overflow-x-auto border border-[#E8E8EC] rounded-xl bg-white">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50/80 border-b border-[#E8E8EC] text-xs font-semibold text-[#6B6B76] uppercase tracking-wider">
                <th scope="col" className="px-4 py-3">Persona</th>
                <th scope="col" className="px-4 py-3 text-right">Sample (N)</th>
                <th scope="col" className="px-4 py-3 text-right">Model MAE</th>
                <th scope="col" className="px-4 py-3 text-right">Naive MAE</th>
                <th scope="col" className="px-4 py-3 text-right">MAE Edge</th>
                <th scope="col" className="px-4 py-3 text-right">Model WAPE</th>
                <th scope="col" className="px-4 py-3 text-right">Naive WAPE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8EC]">
              {personaKeys.map((key) => {
                const item = by_persona[key];
                const metaInfo = PERSONA_LABELS[key] || {
                  title: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
                  desc: "Customer persona cohort",
                };

                if (!item) {
                  return (
                    <tr key={key} className="hover:bg-gray-50/50">
                      <td className="px-4 py-3 font-medium text-[#1A1A1F]">{metaInfo.title}</td>
                      <td colSpan={6} className="px-4 py-3 text-center text-[#6B6B76] text-xs">
                        No evaluation data available
                      </td>
                    </tr>
                  );
                }

                const mae = item.mae != null ? `৳${Number(item.mae).toFixed(1)}` : "N/A";
                const naiveMae = item.naive_mae != null ? `৳${Number(item.naive_mae).toFixed(1)}` : "N/A";
                const wape = item.wape != null ? `${(Number(item.wape) * 100).toFixed(1)}%` : "N/A";
                const naiveWape =
                  item.naive_wape != null ? `${(Number(item.naive_wape) * 100).toFixed(1)}%` : "N/A";

                let edgePct = "—";
                if (item.mae != null && item.naive_mae != null && Number(item.naive_mae) > 0) {
                  const edge = ((Number(item.naive_mae) - Number(item.mae)) / Number(item.naive_mae)) * 100;
                  edgePct = `${edge >= 0 ? "+" : ""}${edge.toFixed(1)}%`;
                }

                return (
                  <tr key={key} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-[#1A1A1F]">{metaInfo.title}</div>
                      <div className="text-xs text-[#6B6B76] mt-0.5">{metaInfo.desc}</div>
                    </td>
                    <td className="px-4 py-3.5 text-right font-medium text-[#6B6B76]">
                      {item.count != null ? item.count.toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3.5 text-right font-semibold text-[#1A1A1F]">{mae}</td>
                    <td className="px-4 py-3.5 text-right text-[#6B6B76]">{naiveMae}</td>
                    <td className="px-4 py-3.5 text-right font-medium text-emerald-700">
                      {edgePct}
                    </td>
                    <td className="px-4 py-3.5 text-right font-semibold text-[#1A1A1F]">{wape}</td>
                    <td className="px-4 py-3.5 text-right text-[#6B6B76]">{naiveWape}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

export default ForecastQuality;
