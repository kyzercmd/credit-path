"use client";

import React, { useState } from "react";
import { FairnessGroup, FairnessResponse } from "@/lib/api";
import { Card } from "@/components/Card";
import { ShieldCheck, Scale, Sparkles, CheckCircle2, AlertCircle } from "lucide-react";

interface FairnessPanelProps {
  data?: FairnessResponse | null;
  isLoading?: boolean;
}

export function FairnessPanel({ data, isLoading = false }: FairnessPanelProps) {
  const [activeTab, setActiveTab] = useState<"gender" | "region" | "age">("gender");

  if (isLoading) {
    return (
      <Card title="Fairness & Disparity Audit (U4)" subtitle="Demographic parity and bias mitigation">
        <div className="space-y-4 animate-pulse">
          <div className="h-10 bg-gray-100 rounded-xl" />
          <div className="h-48 bg-gray-100 rounded-xl" />
          <div className="h-32 bg-gray-100 rounded-xl" />
        </div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card title="Fairness & Disparity Audit (U4)" subtitle="Demographic parity and bias mitigation">
        <p className="text-sm text-[#6B6B76] py-4">No fairness audit metrics available.</p>
      </Card>
    );
  }

  const { by_gender = [], by_region = [], by_age_band = [], mitigation = {} } = data;

  const formatRate = (rate: number | null | undefined): string => {
    if (rate === null || rate === undefined) return "N/A";
    return `${(rate * 100).toFixed(1)}%`;
  };

  const renderTable = (groups: FairnessGroup[], attributeTitle: string) => {
    return (
      <div className="overflow-x-auto border border-[#E8E8EC] rounded-xl bg-white">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="bg-gray-50/80 border-b border-[#E8E8EC] text-xs font-semibold text-[#6B6B76] uppercase tracking-wider">
              <th scope="col" className="px-4 py-3">{attributeTitle} Group</th>
              <th scope="col" className="px-4 py-3 text-right">Sample (N)</th>
              <th scope="col" className="px-4 py-3 text-right">Ready Rate</th>
              <th scope="col" className="px-4 py-3 text-right">Forecast Error (WAPE)</th>
              <th scope="col" className="px-4 py-3 text-right">False-Not-Yet Rate</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E8E8EC]">
            {groups.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-sm text-[#6B6B76]">
                  No demographic records found.
                </td>
              </tr>
            ) : (
              groups.map((item, index) => {
                const displayName = item.group
                  ? item.group.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
                  : "Unknown";
                const isInsufficient = item.count === 0 || item.ready_rate === null;

                return (
                  <tr key={index} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-[#1A1A1F] flex items-center gap-2">
                        {displayName}
                        {isInsufficient && (
                          <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-gray-100 text-[#6B6B76]">
                            No data
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-right font-medium text-[#6B6B76]">
                      {item.count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3.5 text-right font-semibold text-[#1A1A1F]">
                      {formatRate(item.ready_rate)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-medium text-[#1A1A1F]">
                      {formatRate(item.forecast_error)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-medium text-amber-700">
                      {formatRate(item.false_not_yet_rate)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    );
  };

  // Mitigation Data
  const before = mitigation?.before || {};
  const after = mitigation?.after || {};
  const targetGroup = mitigation?.target_group || "female";
  const targetLabel = targetGroup.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());

  return (
    <Card
      title="Fairness & Disparity Audit (U4)"
      subtitle="Protected demographic parity evaluation (gender, region, age) and policy threshold mitigation"
      className="w-full"
    >
      {/* Demographic Tabs */}
      <div className="mb-4">
        <div className="flex border-b border-[#E8E8EC] gap-2 pb-px">
          <button
            type="button"
            onClick={() => setActiveTab("gender")}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "gender"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-[#6B6B76] hover:text-[#1A1A1F]"
            }`}
          >
            Gender Breakdown ({by_gender.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("region")}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "region"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-[#6B6B76] hover:text-[#1A1A1F]"
            }`}
          >
            Region Breakdown ({by_region.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("age")}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "age"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-[#6B6B76] hover:text-[#1A1A1F]"
            }`}
          >
            Age Band Breakdown ({by_age_band.length})
          </button>
        </div>
      </div>

      {/* Active Table */}
      <div className="mb-8">
        {activeTab === "gender" && renderTable(by_gender, "Gender")}
        {activeTab === "region" && renderTable(by_region, "Region")}
        {activeTab === "age" && renderTable(by_age_band, "Age Band")}
      </div>

      {/* Policy Mitigation Before / After */}
      <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-50/40 via-white to-blue-50/30 border border-indigo-100">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded-md bg-indigo-100 text-indigo-700">
                <Sparkles className="w-4 h-4" />
              </span>
              <h4 className="text-sm font-bold text-[#1A1A1F]">
                Policy Mitigation: {mitigation?.description || "Alternative Cushion Threshold"}
              </h4>
            </div>
            <p className="text-xs text-[#6B6B76] mt-1">
              Target demographic: <strong className="text-[#1A1A1F]">{targetLabel} micro-savers</strong>.
              Comparing baseline readiness rules against calibrated liquidity cushion.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 shrink-0">
            Active Mitigation
          </span>
        </div>

        {/* Comparison Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <div className="p-3.5 rounded-xl bg-white border border-[#E8E8EC] shadow-2xs">
            <span className="text-xs font-semibold text-[#6B6B76] block mb-1">Ready Rate</span>
            <div className="flex items-baseline justify-between">
              <div>
                <span className="text-xs text-[#6B6B76] block">Before</span>
                <span className="text-base font-medium text-gray-500">{formatRate(before.ready_rate)}</span>
              </div>
              <span className="text-gray-300">→</span>
              <div className="text-right">
                <span className="text-xs text-emerald-700 font-semibold block">After</span>
                <span className="text-lg font-bold text-emerald-700">{formatRate(after.ready_rate)}</span>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-white border border-[#E8E8EC] shadow-2xs">
            <span className="text-xs font-semibold text-[#6B6B76] block mb-1">False-Not-Yet Rate</span>
            <div className="flex items-baseline justify-between">
              <div>
                <span className="text-xs text-[#6B6B76] block">Before</span>
                <span className="text-base font-medium text-gray-500">{formatRate(before.false_not_yet_rate)}</span>
              </div>
              <span className="text-gray-300">→</span>
              <div className="text-right">
                <span className="text-xs text-blue-700 font-semibold block">After</span>
                <span className="text-lg font-bold text-blue-700">{formatRate(after.false_not_yet_rate)}</span>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-white border border-[#E8E8EC] shadow-2xs">
            <span className="text-xs font-semibold text-[#6B6B76] block mb-1">Shortfall Rate (Ready)</span>
            <div className="flex items-baseline justify-between">
              <div>
                <span className="text-xs text-[#6B6B76] block">Before</span>
                <span className="text-base font-medium text-gray-500">
                  {formatRate(before.shortfall_rate_among_ready)}
                </span>
              </div>
              <span className="text-gray-300">→</span>
              <div className="text-right">
                <span className="text-xs text-gray-700 font-semibold block">After</span>
                <span className="text-lg font-bold text-gray-900">
                  {formatRate(after.shortfall_rate_among_ready)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Impact Summary Note */}
        {mitigation?.impact_summary && (
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-white/80 border border-indigo-100 text-xs text-indigo-950 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <span>{mitigation.impact_summary}</span>
          </div>
        )}
      </div>
    </Card>
  );
}

export default FairnessPanel;
