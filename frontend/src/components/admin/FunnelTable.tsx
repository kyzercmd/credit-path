"use client";

import React from "react";
import { AdminFunnelResponse } from "@/lib/api";
import { Card } from "@/components/Card";
import { Users, CheckCircle2, Clock, AlertTriangle } from "lucide-react";

interface FunnelTableProps {
  data?: AdminFunnelResponse | null;
  isLoading?: boolean;
}

export function FunnelTable({ data, isLoading = false }: FunnelTableProps) {
  if (isLoading) {
    return (
      <Card title="Readiness Funnel (U1)" subtitle="Customer progression through qualification checks">
        <div className="space-y-4 animate-pulse">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="h-20 bg-gray-100 rounded-xl" />
            <div className="h-20 bg-gray-100 rounded-xl" />
            <div className="h-20 bg-gray-100 rounded-xl" />
          </div>
          <div className="h-44 bg-gray-100 rounded-xl" />
        </div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card title="Readiness Funnel (U1)" subtitle="Customer progression through qualification checks">
        <p className="text-sm text-[#6B6B76] py-4">No funnel data available.</p>
      </Card>
    );
  }

  const { total_customers = 0, ready_count = 0, not_yet_count = 0, missing_checks = [] } = data;
  const readyPct = total_customers > 0 ? ((ready_count / total_customers) * 100).toFixed(1) : "0.0";
  const notYetPct = total_customers > 0 ? ((not_yet_count / total_customers) * 100).toFixed(1) : "0.0";

  // Check mapping to ensure familiar labels: Borrowing history, Regular income, Repayment cushion & bills
  const getDisplayName = (label: string) => {
    const lower = label.toLowerCase();
    if (lower.includes("history")) return "Borrowing history";
    if (lower.includes("regular")) return "Regular income";
    if (lower.includes("cushion") || lower.includes("bill")) return "Repayment cushion & bills";
    return label;
  };

  const getCheckDescription = (label: string) => {
    const lower = label.toLowerCase();
    if (lower.includes("history")) return "Requires minimum months of active wallet activity";
    if (lower.includes("regular")) return "Requires consistent inflows across recent weeks";
    if (lower.includes("cushion") || lower.includes("bill")) return "Requires minimum balance cushion and on-time bill payment";
    return "Readiness rule threshold requirement";
  };

  return (
    <Card
      title="Readiness Funnel (U1)"
      subtitle="Customer progression through qualification checks and missing criteria distribution"
      className="w-full"
    >
      {/* Top Level KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="p-4 rounded-xl bg-gray-50 border border-[#E8E8EC] flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-[#6B6B76] uppercase tracking-wider">Total Customers</p>
            <p className="text-2xl font-bold text-[#1A1A1F] mt-0.5">{total_customers.toLocaleString()}</p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-100 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-xs font-medium text-emerald-800 uppercase tracking-wider">Ready Count</p>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold">
                {readyPct}%
              </span>
            </div>
            <p className="text-2xl font-bold text-emerald-950 mt-0.5">{ready_count.toLocaleString()}</p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-amber-50/50 border border-amber-100 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-xs font-medium text-amber-800 uppercase tracking-wider">Not Yet Count</p>
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-semibold">
                {notYetPct}%
              </span>
            </div>
            <p className="text-2xl font-bold text-amber-950 mt-0.5">{not_yet_count.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Missing Checks Breakdown Table */}
      <div className="mt-2">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-[#1A1A1F] flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Missing Checks Breakdown
          </h4>
          <span className="text-xs text-[#6B6B76]">Failing check distribution across customer base</span>
        </div>

        <div className="overflow-x-auto border border-[#E8E8EC] rounded-xl bg-white">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50/80 border-b border-[#E8E8EC] text-xs font-semibold text-[#6B6B76] uppercase tracking-wider">
                <th scope="col" className="px-4 py-3">Qualification Check</th>
                <th scope="col" className="px-4 py-3 text-right">Missing Count</th>
                <th scope="col" className="px-4 py-3 text-right">Failure Rate</th>
                <th scope="col" className="px-4 py-3 text-right">Pass Rate</th>
                <th scope="col" className="px-4 py-3 w-40">Funnel Adherence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8EC]">
              {missing_checks.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-sm text-[#6B6B76]">
                    No missing check breakdown available.
                  </td>
                </tr>
              ) : (
                missing_checks.map((bucket, index) => {
                  const checkName = getDisplayName(bucket.label);
                  const description = getCheckDescription(bucket.label);
                  const failCount = bucket.count;
                  const failPctVal = total_customers > 0 ? (failCount / total_customers) * 100 : 0;
                  const passPctVal = Math.max(0, 100 - failPctVal);
                  const failRateStr = `${failPctVal.toFixed(1)}%`;
                  const passRateStr = `${passPctVal.toFixed(1)}%`;

                  return (
                    <tr key={index} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="font-medium text-[#1A1A1F]">{checkName}</div>
                        <div className="text-xs text-[#6B6B76] mt-0.5">{description}</div>
                      </td>
                      <td className="px-4 py-3.5 text-right font-semibold text-[#1A1A1F]">
                        {failCount.toLocaleString()}
                      </td>
                      <td className="px-4 py-3.5 text-right font-medium text-amber-700">
                        {failRateStr}
                      </td>
                      <td className="px-4 py-3.5 text-right font-medium text-emerald-700">
                        {passRateStr}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden flex">
                            <div
                              className="bg-emerald-500 h-2"
                              style={{ width: `${passPctVal}%` }}
                              title={`Passing: ${passRateStr}`}
                            />
                            <div
                              className="bg-amber-400 h-2"
                              style={{ width: `${failPctVal}%` }}
                              title={`Failing: ${failRateStr}`}
                            />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

export default FunnelTable;
