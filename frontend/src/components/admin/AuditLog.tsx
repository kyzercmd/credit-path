"use client";

import React, { useState, useMemo } from "react";
import { AuditEvent, AuditLogResponse } from "@/lib/api";
import { Card } from "@/components/Card";
import { ScrollText, Search, Filter, Calendar, Activity, CheckCircle, ShieldAlert, Sliders, ToggleRight } from "lucide-react";

interface AuditLogProps {
  data?: AuditLogResponse | null;
  isLoading?: boolean;
  onRefresh?: () => void;
}

export function AuditLog({ data, isLoading = false, onRefresh }: AuditLogProps) {
  const [filterType, setFilterType] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const events: AuditEvent[] = data?.events || [];

  // Identify distinct event types for the filter dropdown
  const eventTypes = useMemo(() => {
    const set = new Set<string>();
    events.forEach((e) => {
      if (e.event_type) set.add(e.event_type);
    });
    return Array.from(set);
  }, [events]);

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      const matchesType = filterType === "all" || e.event_type === filterType;
      const matchesSearch =
        searchQuery === "" ||
        e.details.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.event_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.timestamp.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesType && matchesSearch;
    });
  }, [events, filterType, searchQuery]);

  const getEventBadge = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes("kill")) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
          <ToggleRight className="w-3 h-3" />
          {type}
        </span>
      );
    }
    if (t.includes("config") || t.includes("rule")) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
          <Sliders className="w-3 h-3" />
          {type}
        </span>
      );
    }
    if (t.includes("consent")) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle className="w-3 h-3" />
          {type}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
        <Activity className="w-3 h-3" />
        {type}
      </span>
    );
  };

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return ts;
      return d.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return ts;
    }
  };

  if (isLoading) {
    return (
      <Card title="Audit Log (U6)" subtitle="Immutable compliance trail of rule edits, kill switches, and customer consent">
        <div className="space-y-4 animate-pulse">
          <div className="h-10 bg-gray-100 rounded-xl" />
          <div className="h-48 bg-gray-100 rounded-xl" />
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="Audit Log (U6)"
      subtitle="Complete chronological audit trail of configuration modifications, emergency kill-switch toggles, and consent records"
      className="w-full"
    >
      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search audit trail..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-[#E8E8EC] focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-[#6B6B76]" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg border border-[#E8E8EC] bg-white text-[#1A1A1F] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
          >
            <option value="all">All Event Types ({events.length})</option>
            {eventTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>

          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="px-3 py-1.5 text-xs rounded-lg border border-[#E8E8EC] hover:bg-gray-50 text-[#1A1A1F] transition-colors"
            >
              Refresh
            </button>
          )}
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="overflow-x-auto border border-[#E8E8EC] rounded-xl bg-white">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="bg-gray-50/80 border-b border-[#E8E8EC] text-xs font-semibold text-[#6B6B76] uppercase tracking-wider">
              <th scope="col" className="px-4 py-3 w-48">Timestamp</th>
              <th scope="col" className="px-4 py-3 w-48">Event Type</th>
              <th scope="col" className="px-4 py-3">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E8E8EC]">
            {filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-sm text-[#6B6B76]">
                  {searchQuery || filterType !== "all"
                    ? "No audit events match your filter criteria."
                    : "No audit events recorded in system history."}
                </td>
              </tr>
            ) : (
              filteredEvents.map((evt, idx) => (
                <tr key={idx} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-3.5 text-xs text-[#6B6B76] whitespace-nowrap font-mono">
                    {formatTimestamp(evt.timestamp)}
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    {getEventBadge(evt.event_type)}
                  </td>
                  <td className="px-4 py-3.5 text-xs text-[#1A1A1F] font-mono break-all leading-relaxed">
                    {evt.details}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px] text-[#6B6B76]">
        <span>Showing {filteredEvents.length} of {events.length} recorded events</span>
        <span>Storage: SQLite audit_log table</span>
      </div>
    </Card>
  );
}

export default AuditLog;
