"use client";

import React, { useState } from "react";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import {
  Zap,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Clock,
  TrendingUp,
  Receipt,
  Wallet,
  Sparkles,
} from "lucide-react";
import {
  ingestTransaction,
  ingestDailyBalance,
  ingestBill,
  IngestEventResponse,
} from "@/lib/api";

interface EventSimulatorProps {
  customerId: string;
  onEventProcessed?: (response: IngestEventResponse) => void;
}

export function EventSimulator({ customerId, onEventProcessed }: EventSimulatorProps) {
  const [activeTab, setActiveTab] = useState<"tx" | "bal" | "bill">("tx");
  const [loading, setLoading] = useState(false);
  const [latestResponse, setLatestResponse] = useState<IngestEventResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form states
  const todayStr = new Date().toISOString().split("T")[0];
  const [txDate, setTxDate] = useState("2026-01-15");
  const [txType, setTxType] = useState<"inflow" | "outflow">("inflow");
  const [txAmount, setTxAmount] = useState("15000");
  const [txDesc, setTxDesc] = useState("Freelance contract payout / Cash-in");

  const [balDate, setBalDate] = useState("2026-01-15");
  const [balAmount, setBalAmount] = useState("3500");

  const [billDueDate, setBillDueDate] = useState("2026-01-10");
  const [billAmount, setBillAmount] = useState("1200");
  const [billPaidDate, setBillPaidDate] = useState("2026-01-08");
  const [billOnTime, setBillOnTime] = useState(1);
  const [biller, setBiller] = useState("DESCO Electricity");

  const handleSimulateTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await ingestTransaction(
        customerId,
        txDate,
        txType,
        parseFloat(txAmount) || 0,
        txDesc
      );
      setLatestResponse(res);
      if (onEventProcessed) onEventProcessed(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to ingest transaction");
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateBalance = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await ingestDailyBalance(
        customerId,
        balDate,
        parseFloat(balAmount) || 0,
        0
      );
      setLatestResponse(res);
      if (onEventProcessed) onEventProcessed(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to ingest balance");
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateBill = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await ingestBill(
        customerId,
        billDueDate,
        parseFloat(billAmount) || 0,
        billPaidDate,
        billOnTime,
        biller
      );
      setLatestResponse(res);
      if (onEventProcessed) onEventProcessed(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to ingest bill");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title="Live Event Simulator & Ingestion Studio"
      subtitle="Feed real-time MFS transactions, balances, or bills beyond batch cutoffs to observe instant readiness updates."
      headerRight={
        <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
          <Zap className="w-4 h-4" />
        </div>
      }
    >
      <div className="space-y-4">
        {/* Simulator mode pills */}
        <div className="flex p-1 bg-gray-100 rounded-xl gap-1 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab("tx")}
            className={`flex-1 py-1.5 px-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === "tx"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
            <span>Transaction</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("bal")}
            className={`flex-1 py-1.5 px-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === "bal"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            <Wallet className="w-3.5 h-3.5 text-blue-600" />
            <span>Daily Cushion</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("bill")}
            className={`flex-1 py-1.5 px-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === "bill"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            <Receipt className="w-3.5 h-3.5 text-purple-600" />
            <span>Bill Payment</span>
          </button>
        </div>

        {/* Tab 1: Transaction Ingestion */}
        {activeTab === "tx" && (
          <form onSubmit={handleSimulateTransaction} className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Event Date
                </label>
                <input
                  type="date"
                  value={txDate}
                  onChange={(e) => setTxDate(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 font-mono text-xs focus:ring-2 focus:ring-emerald-500 outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Direction
                </label>
                <select
                  value={txType}
                  onChange={(e) => setTxType(e.target.value as "inflow" | "outflow")}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 text-xs focus:ring-2 focus:ring-emerald-500 outline-none"
                >
                  <option value="inflow">Inflow (Money In)</option>
                  <option value="outflow">Outflow (Spend / Out)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Amount (BDT ৳)
                </label>
                <input
                  type="number"
                  step="50"
                  value={txAmount}
                  onChange={(e) => setTxAmount(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 font-mono text-xs focus:ring-2 focus:ring-emerald-500 outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Description
                </label>
                <input
                  type="text"
                  value={txDesc}
                  onChange={(e) => setTxDesc(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 text-xs focus:ring-2 focus:ring-emerald-500 outline-none"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              leftIcon={<Zap className="w-3.5 h-3.5" />}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-xl"
            >
              <span className="whitespace-nowrap">{loading ? "Streaming & Re-Scoring..." : "Stream Live Transaction"}</span>
            </Button>
          </form>
        )}

        {/* Tab 2: Balance Ingestion */}
        {activeTab === "bal" && (
          <form onSubmit={handleSimulateBalance} className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Closing Balance Date
                </label>
                <input
                  type="date"
                  value={balDate}
                  onChange={(e) => setBalDate(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 font-mono text-xs focus:ring-2 focus:ring-blue-500 outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Closing Balance (BDT ৳)
                </label>
                <input
                  type="number"
                  step="50"
                  value={balAmount}
                  onChange={(e) => setBalAmount(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 font-mono text-xs focus:ring-2 focus:ring-blue-500 outline-none"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              leftIcon={<Zap className="w-3.5 h-3.5" />}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl"
            >
              <span className="whitespace-nowrap">{loading ? "Streaming & Re-Scoring..." : "Stream Live Daily Balance"}</span>
            </Button>
          </form>
        )}

        {/* Tab 3: Bill Ingestion */}
        {activeTab === "bill" && (
          <form onSubmit={handleSimulateBill} className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Biller / Utility
                </label>
                <input
                  type="text"
                  value={biller}
                  onChange={(e) => setBiller(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 text-xs focus:ring-2 focus:ring-purple-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Bill Amount (BDT ৳)
                </label>
                <input
                  type="number"
                  step="50"
                  value={billAmount}
                  onChange={(e) => setBillAmount(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 font-mono text-xs focus:ring-2 focus:ring-purple-500 outline-none"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Due Date
                </label>
                <input
                  type="date"
                  value={billDueDate}
                  onChange={(e) => setBillDueDate(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 font-mono text-xs focus:ring-2 focus:ring-purple-500 outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Paid Date
                </label>
                <input
                  type="date"
                  value={billPaidDate}
                  onChange={(e) => setBillPaidDate(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 font-mono text-xs focus:ring-2 focus:ring-purple-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-1">
                  Status
                </label>
                <select
                  value={billOnTime}
                  onChange={(e) => setBillOnTime(parseInt(e.target.value))}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 text-xs focus:ring-2 focus:ring-purple-500 outline-none"
                >
                  <option value={1}>Paid On-Time</option>
                  <option value={0}>Late / Overdue</option>
                </select>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              leftIcon={<Zap className="w-3.5 h-3.5" />}
              className="w-full py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-xl"
            >
              <span className="whitespace-nowrap">{loading ? "Streaming & Re-Scoring..." : "Stream Live Bill Payment"}</span>
            </Button>
          </form>
        )}

        {/* Error message */}
        {errorMsg && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-xs text-red-700">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Dynamic Transition Feedback Card */}
        {latestResponse && latestResponse.transition && (
          <div
            className={`p-3.5 rounded-xl border transition-all ${
              latestResponse.transition.current_ready
                ? "bg-emerald-50/80 border-emerald-200"
                : "bg-amber-50/80 border-amber-200"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                    latestResponse.transition.current_ready
                      ? "bg-emerald-600 text-white"
                      : "bg-amber-600 text-white"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-gray-900">
                    Real-Time Re-Score Triggered
                  </h4>
                  <p className="text-[10px] text-gray-500 font-mono">
                    Dynamic As-Of: {latestResponse.as_of_date}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <span
                  className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    latestResponse.transition.current_ready
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {latestResponse.transition.current_status}
                </span>
              </div>
            </div>

            <div className="mt-2.5 pt-2.5 border-t border-black/5 text-xs text-gray-700">
              <p className="font-medium">{latestResponse.transition.message}</p>
              <div className="mt-2 flex items-center gap-4 text-[11px] text-gray-600">
                <span>
                  Policy Checks Passing:{" "}
                  <strong className="text-gray-900 font-bold">
                    {latestResponse.transition.checks_passed_count}/
                    {latestResponse.transition.total_checks_count}
                  </strong>
                </span>
                {latestResponse.transition.status_changed && (
                  <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Status Transition Detected!
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
