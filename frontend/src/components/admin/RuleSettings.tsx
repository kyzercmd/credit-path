"use client";

import React, { useState, useEffect } from "react";
import { ConfigResponse, putAdminConfig } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Sliders, Save, CheckCircle, AlertCircle, RefreshCw, History, ShieldAlert } from "lucide-react";

interface RuleSettingsProps {
  data?: ConfigResponse | null;
  isLoading?: boolean;
  onConfigSaved?: (newConfig: ConfigResponse) => void;
}

export function RuleSettings({ data, isLoading = false, onConfigSaved }: RuleSettingsProps) {
  const [formData, setFormData] = useState({
    min_history_months: 3,
    min_bill_payment_rate: 0.60,
    min_income_months: 8,
    min_cushion_ratio: 0.70,
    max_dti_ratio: 0.40,
    stress_income_drop_pct: 0.30,
    annual_interest_rate_pct: 0.15,
    max_loan_cap: 50000,
  });

  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Sync form with incoming data
  useEffect(() => {
    if (data?.config) {
      const cfg = data.config;
      setFormData({
        min_history_months: Number(cfg.min_history_months ?? 3),
        min_bill_payment_rate: Number(cfg.min_bill_payment_rate ?? cfg.bill_on_time_pct ?? 0.60),
        min_income_months: Number(cfg.min_income_months ?? cfg.regularity_n ?? 8),
        min_cushion_ratio: Number(cfg.min_cushion_ratio ?? cfg.min_balance_pct_days ?? 0.70),
        max_dti_ratio: Number(cfg.max_dti_ratio ?? cfg.affordability_cap ?? 0.40),
        stress_income_drop_pct: Number(cfg.stress_income_drop_pct ?? cfg.stress_pct ?? 0.30),
        annual_interest_rate_pct: Number(cfg.annual_interest_rate_pct ?? cfg.illustrative_rate ?? 0.15),
        max_loan_cap: Number(cfg.max_loan_cap ?? 50000),
      });
    }
  }, [data]);

  const handleChange = (field: keyof typeof formData, value: string) => {
    setMessage(null);
    const num = parseFloat(value);
    setFormData((prev) => ({
      ...prev,
      [field]: isNaN(num) ? 0 : num,
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      // Send both backend model keys and requested prompt keys so both work seamlessly
      const payload: Record<string, any> = {
        ...(data?.config || {}),
        min_history_months: Number(formData.min_history_months),
        bill_on_time_pct: Number(formData.min_bill_payment_rate),
        min_bill_payment_rate: Number(formData.min_bill_payment_rate),
        regularity_n: Number(formData.min_income_months),
        min_income_months: Number(formData.min_income_months),
        min_balance_pct_days: Number(formData.min_cushion_ratio),
        min_cushion_ratio: Number(formData.min_cushion_ratio),
        affordability_cap: Number(formData.max_dti_ratio),
        max_dti_ratio: Number(formData.max_dti_ratio),
        stress_pct: Number(formData.stress_income_drop_pct),
        stress_income_drop_pct: Number(formData.stress_income_drop_pct),
        illustrative_rate: Number(formData.annual_interest_rate_pct),
        annual_interest_rate_pct: Number(formData.annual_interest_rate_pct),
        max_loan_cap: Number(formData.max_loan_cap),
      };

      const res = await putAdminConfig(payload);
      setMessage({
        type: "success",
        text: `Configuration saved successfully! Version updated to v${res.version}.`,
      });
      if (onConfigSaved) {
        onConfigSaved(res);
      }
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err?.message || "Failed to update configuration.",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (data?.config) {
      const cfg = data.config;
      setFormData({
        min_history_months: Number(cfg.min_history_months ?? 3),
        min_bill_payment_rate: Number(cfg.min_bill_payment_rate ?? cfg.bill_on_time_pct ?? 0.60),
        min_income_months: Number(cfg.min_income_months ?? cfg.regularity_n ?? 8),
        min_cushion_ratio: Number(cfg.min_cushion_ratio ?? cfg.min_balance_pct_days ?? 0.70),
        max_dti_ratio: Number(cfg.max_dti_ratio ?? cfg.affordability_cap ?? 0.40),
        stress_income_drop_pct: Number(cfg.stress_income_drop_pct ?? cfg.stress_pct ?? 0.30),
        annual_interest_rate_pct: Number(cfg.annual_interest_rate_pct ?? cfg.illustrative_rate ?? 0.15),
        max_loan_cap: Number(cfg.max_loan_cap ?? 50000),
      });
      setMessage(null);
    }
  };

  const formatTimestamp = (ts?: string) => {
    if (!ts) return "Just now";
    try {
      const d = new Date(ts);
      return isNaN(d.getTime()) ? ts : d.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
    } catch {
      return ts;
    }
  };

  if (isLoading) {
    return (
      <Card title="Rule Settings (U3)" subtitle="Policy threshold and readiness rule tuning">
        <div className="space-y-4 animate-pulse">
          <div className="h-10 bg-gray-100 rounded-xl" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-100 rounded-xl" />
            ))}
          </div>
          <div className="h-12 bg-gray-100 rounded-xl w-32" />
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="Rule Settings (U3)"
      subtitle="Tunable policy thresholds, safety cushions, and underwriting simulation boundaries"
      className="w-full"
    >
      {/* Version Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-gray-50 border border-[#E8E8EC] rounded-xl mb-6">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-semibold uppercase tracking-wider text-[#6B6B76]">
            Active Configuration
          </span>
          <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 text-xs font-bold border border-blue-200">
            Version {data?.version ?? 1}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#6B6B76]">
          <History className="w-3.5 h-3.5" />
          <span>Last modified: {formatTimestamp(data?.timestamp)}</span>
        </div>
      </div>

      {message && (
        <div
          role="alert"
          className={`flex items-start gap-3 p-4 rounded-xl mb-6 text-sm ${
            message.type === "success"
              ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
              : "bg-red-50 text-red-900 border border-red-200"
          }`}
        >
          {message.type === "success" ? (
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          )}
          <div className="flex-1 font-medium">{message.text}</div>
        </div>
      )}

      {/* Threshold Editing Form */}
      <form onSubmit={handleSave}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {/* 1: min_history_months */}
          <div className="p-3.5 rounded-xl border border-[#E8E8EC] bg-white">
            <label htmlFor="min_history_months" className="block text-xs font-semibold text-[#1A1A1F] mb-1">
              Min History Months
            </label>
            <p className="text-[11px] text-[#6B6B76] mb-2">Active wallet duration requirement</p>
            <div className="relative">
              <input
                id="min_history_months"
                type="number"
                min="1"
                max="36"
                step="1"
                value={formData.min_history_months}
                onChange={(e) => handleChange("min_history_months", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
              <span className="absolute right-3 top-2.5 text-xs text-[#6B6B76]">months</span>
            </div>
          </div>

          {/* 2: min_bill_payment_rate */}
          <div className="p-3.5 rounded-xl border border-[#E8E8EC] bg-white">
            <label htmlFor="min_bill_payment_rate" className="block text-xs font-semibold text-[#1A1A1F] mb-1">
              Min Bill Payment Rate
            </label>
            <p className="text-[11px] text-[#6B6B76] mb-2">On-time utility bill compliance</p>
            <div className="relative">
              <input
                id="min_bill_payment_rate"
                type="number"
                min="0.0"
                max="1.0"
                step="0.05"
                value={formData.min_bill_payment_rate}
                onChange={(e) => handleChange("min_bill_payment_rate", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
              <span className="absolute right-3 top-2.5 text-xs text-[#6B6B76]">
                {(formData.min_bill_payment_rate * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* 3: min_income_months */}
          <div className="p-3.5 rounded-xl border border-[#E8E8EC] bg-white">
            <label htmlFor="min_income_months" className="block text-xs font-semibold text-[#1A1A1F] mb-1">
              Min Income Regularity
            </label>
            <p className="text-[11px] text-[#6B6B76] mb-2">Active income weeks (out of 12)</p>
            <div className="relative">
              <input
                id="min_income_months"
                type="number"
                min="1"
                max="12"
                step="1"
                value={formData.min_income_months}
                onChange={(e) => handleChange("min_income_months", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
              <span className="absolute right-3 top-2.5 text-xs text-[#6B6B76]">weeks</span>
            </div>
          </div>

          {/* 4: min_cushion_ratio */}
          <div className="p-3.5 rounded-xl border border-[#E8E8EC] bg-white">
            <label htmlFor="min_cushion_ratio" className="block text-xs font-semibold text-[#1A1A1F] mb-1">
              Min Cushion Ratio
            </label>
            <p className="text-[11px] text-[#6B6B76] mb-2">Days balance stays above floor</p>
            <div className="relative">
              <input
                id="min_cushion_ratio"
                type="number"
                min="0.0"
                max="1.0"
                step="0.05"
                value={formData.min_cushion_ratio}
                onChange={(e) => handleChange("min_cushion_ratio", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
              <span className="absolute right-3 top-2.5 text-xs text-[#6B6B76]">
                {(formData.min_cushion_ratio * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* 5: max_dti_ratio */}
          <div className="p-3.5 rounded-xl border border-[#E8E8EC] bg-white">
            <label htmlFor="max_dti_ratio" className="block text-xs font-semibold text-[#1A1A1F] mb-1">
              Max DTI Ratio (Affordability Cap)
            </label>
            <p className="text-[11px] text-[#6B6B76] mb-2">Max repayment share of monthly spare money</p>
            <div className="relative">
              <input
                id="max_dti_ratio"
                type="number"
                min="0.05"
                max="0.80"
                step="0.05"
                value={formData.max_dti_ratio}
                onChange={(e) => handleChange("max_dti_ratio", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
              <span className="absolute right-3 top-2.5 text-xs text-[#6B6B76]">
                {(formData.max_dti_ratio * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* 6: stress_income_drop_pct */}
          <div className="p-3.5 rounded-xl border border-[#E8E8EC] bg-white">
            <label htmlFor="stress_income_drop_pct" className="block text-xs font-semibold text-[#1A1A1F] mb-1">
              Stress Income Drop %
            </label>
            <p className="text-[11px] text-[#6B6B76] mb-2">Simulated revenue reduction stress</p>
            <div className="relative">
              <input
                id="stress_income_drop_pct"
                type="number"
                min="0.05"
                max="0.80"
                step="0.05"
                value={formData.stress_income_drop_pct}
                onChange={(e) => handleChange("stress_income_drop_pct", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
              <span className="absolute right-3 top-2.5 text-xs text-[#6B6B76]">
                {(formData.stress_income_drop_pct * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* 7: annual_interest_rate_pct */}
          <div className="p-3.5 rounded-xl border border-[#E8E8EC] bg-white">
            <label htmlFor="annual_interest_rate_pct" className="block text-xs font-semibold text-[#1A1A1F] mb-1">
              Annual Interest Rate %
            </label>
            <p className="text-[11px] text-[#6B6B76] mb-2">Illustrative cost rate (used for Conventional financing only)</p>
            <div className="relative">
              <input
                id="annual_interest_rate_pct"
                type="number"
                min="0.01"
                max="0.50"
                step="0.01"
                value={formData.annual_interest_rate_pct}
                onChange={(e) => handleChange("annual_interest_rate_pct", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
              <span className="absolute right-3 top-2.5 text-xs text-[#6B6B76]">
                {(formData.annual_interest_rate_pct * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* 8: max_loan_cap */}
          <div className="p-3.5 rounded-xl border border-[#E8E8EC] bg-white">
            <label htmlFor="max_loan_cap" className="block text-xs font-semibold text-[#1A1A1F] mb-1">
              Max Loan Cap
            </label>
            <p className="text-[11px] text-[#6B6B76] mb-2">Platform lending exposure ceiling</p>
            <div className="relative">
              <input
                id="max_loan_cap"
                type="number"
                min="5000"
                max="200000"
                step="5000"
                value={formData.max_loan_cap}
                onChange={(e) => handleChange("max_loan_cap", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
              <span className="absolute right-3 top-2.5 text-xs text-[#6B6B76]">৳ BDT</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#E8E8EC]">
          <div className="flex items-center gap-2 text-xs text-[#6B6B76]">
            <ShieldAlert className="w-4 h-4 text-amber-500" />
            <span>Changes create a new immutable configuration version in SQLite.</span>
          </div>

          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="secondary"
              fullWidth={false}
              onClick={handleReset}
              disabled={saving}
              leftIcon={<RefreshCw className="w-4 h-4" />}
            >
              Reset
            </Button>

            <Button
              type="submit"
              variant="primary"
              fullWidth={false}
              isLoading={saving}
              leftIcon={<Save className="w-4 h-4" />}
            >
              Save Configuration
            </Button>
          </div>
        </div>
      </form>
    </Card>
  );
}

export default RuleSettings;
