"use client";

import React, { useState, useEffect } from "react";
import { postAdminKillSwitch } from "@/lib/api";
import { Card } from "@/components/Card";
import { AlertOctagon, ShieldAlert, CheckCircle2, AlertCircle, Power } from "lucide-react";

interface KillSwitchProps {
  initialKillSafeRange?: boolean;
  initialKillLoanCheck?: boolean;
  onKillSwitchChanged?: (killSafeRange: boolean, killLoanCheck: boolean) => void;
}

export function KillSwitch({
  initialKillSafeRange = false,
  initialKillLoanCheck = false,
  onKillSwitchChanged,
}: KillSwitchProps) {
  const [killSafeRange, setKillSafeRange] = useState<boolean>(initialKillSafeRange);
  const [killLoanCheck, setKillLoanCheck] = useState<boolean>(initialKillLoanCheck);
  const [savingField, setSavingField] = useState<"safe_range" | "loan_check" | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    setKillSafeRange(initialKillSafeRange);
  }, [initialKillSafeRange]);

  useEffect(() => {
    setKillLoanCheck(initialKillLoanCheck);
  }, [initialKillLoanCheck]);

  const handleToggle = async (field: "safe_range" | "loan_check", currentVal: boolean) => {
    const nextVal = !currentVal;
    setSavingField(field);
    setFeedback(null);

    const nextSafeRange = field === "safe_range" ? nextVal : killSafeRange;
    const nextLoanCheck = field === "loan_check" ? nextVal : killLoanCheck;

    try {
      const res = await postAdminKillSwitch(nextSafeRange, nextLoanCheck);
      if (field === "safe_range") setKillSafeRange(res.kill_safe_range);
      if (field === "loan_check") setKillLoanCheck(res.kill_loan_check);

      const fieldName = field === "safe_range" ? "Safe Range" : "Loan Check";
      const actionText = nextVal ? "EMERGENCY KILLED (Hidden from users)" : "RESTORED (Visible to users)";
      setFeedback({
        type: "success",
        text: `${fieldName} feature successfully ${actionText}. Audit event recorded.`,
      });

      if (onKillSwitchChanged) {
        onKillSwitchChanged(res.kill_safe_range, res.kill_loan_check);
      }
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: err?.message || "Failed to update emergency kill switch.",
      });
    } finally {
      setSavingField(null);
    }
  };

  const anyActive = killSafeRange || killLoanCheck;

  return (
    <Card
      title="Emergency Kill Switches (U5)"
      subtitle="Instantly suppress customer-facing model calculations and underwriting simulators"
      className="w-full border-red-200"
    >
      {/* Warning Alert Banner */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 mb-6">
        <AlertOctagon className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed">
          <strong className="font-semibold block mb-0.5">High-Impact Production Control</strong>
          Activating either switch immediately suppresses feature calculation endpoints across all customer sessions.
          Use in case of model drift, upstream data anomalies, or emergency audit requirements. Every toggle change is
          permanently logged in the audit trail.
        </div>
      </div>

      {feedback && (
        <div
          role="alert"
          className={`flex items-start gap-3 p-3.5 rounded-xl mb-6 text-xs font-medium ${
            feedback.type === "success"
              ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
              : "bg-red-50 text-red-900 border border-red-200"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          )}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Switches Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Toggle 1: Safe Range */}
        <div
          className={`p-4 rounded-xl border transition-all ${
            killSafeRange
              ? "bg-red-50/70 border-red-300 shadow-xs"
              : "bg-white border-[#E8E8EC] hover:border-gray-300"
          }`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-[#1A1A1F]">Safe Range Guidance</span>
                {killSafeRange ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-800 uppercase tracking-wide">
                    Killed
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                    Active
                  </span>
                )}
              </div>
              <p className="text-xs text-[#6B6B76] leading-relaxed">
                Controls customer access to the monthly comfortable installment range and stress test buffers.
              </p>
            </div>

            {/* Toggle Button */}
            <button
              type="button"
              role="switch"
              aria-checked={killSafeRange}
              aria-label="Toggle kill Safe Range"
              disabled={savingField === "safe_range"}
              onClick={() => handleToggle("safe_range", killSafeRange)}
              className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 ${
                killSafeRange ? "bg-red-600" : "bg-gray-200"
              } ${savingField === "safe_range" ? "opacity-60 cursor-wait" : ""}`}
            >
              <span
                className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                  killSafeRange ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          <div className="mt-3 pt-3 border-t border-dashed border-[#E8E8EC] flex items-center justify-between text-[11px]">
            <span className="text-[#6B6B76]">API Parameter: `kill_safe_range`</span>
            <span className={`font-semibold ${killSafeRange ? "text-red-700" : "text-emerald-700"}`}>
              {killSafeRange ? "Suppressed (Hidden)" : "Operational (Visible)"}
            </span>
          </div>
        </div>

        {/* Toggle 2: Loan Check */}
        <div
          className={`p-4 rounded-xl border transition-all ${
            killLoanCheck
              ? "bg-red-50/70 border-red-300 shadow-xs"
              : "bg-white border-[#E8E8EC] hover:border-gray-300"
          }`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-[#1A1A1F]">Loan Check Simulator</span>
                {killLoanCheck ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-800 uppercase tracking-wide">
                    Killed
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                    Active
                  </span>
                )}
              </div>
              <p className="text-xs text-[#6B6B76] leading-relaxed">
                Controls customer access to loan amount/tenor sliders, verdicts (Comfortable/Tight), and nearest-comfortable suggestions.
              </p>
            </div>

            {/* Toggle Button */}
            <button
              type="button"
              role="switch"
              aria-checked={killLoanCheck}
              aria-label="Toggle kill Loan Check"
              disabled={savingField === "loan_check"}
              onClick={() => handleToggle("loan_check", killLoanCheck)}
              className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 ${
                killLoanCheck ? "bg-red-600" : "bg-gray-200"
              } ${savingField === "loan_check" ? "opacity-60 cursor-wait" : ""}`}
            >
              <span
                className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                  killLoanCheck ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          <div className="mt-3 pt-3 border-t border-dashed border-[#E8E8EC] flex items-center justify-between text-[11px]">
            <span className="text-[#6B6B76]">API Parameter: `kill_loan_check`</span>
            <span className={`font-semibold ${killLoanCheck ? "text-red-700" : "text-emerald-700"}`}>
              {killLoanCheck ? "Suppressed (Hidden)" : "Operational (Visible)"}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default KillSwitch;
