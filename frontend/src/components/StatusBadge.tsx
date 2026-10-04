import React from "react";
import { CheckCircle2, Clock, AlertTriangle, XCircle, Info } from "lucide-react";

export type StatusType =
  | "ready"
  | "not_yet"
  | "comfortable"
  | "tight"
  | "too_much"
  | "safe"
  | "neutral"
  | string;

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function StatusBadge({
  status,
  label,
  size = "md",
  className = "",
}: StatusBadgeProps) {
  const normalized = status?.toLowerCase().replace(/\s+/g, "_") || "";

  let bgClass = "bg-[#F4F4F6] text-[#6B6B76] border-[#E8E8EC]";
  let icon = <Info className="shrink-0" />;
  let defaultLabel = label || status;

  if (normalized === "ready" || normalized === "comfortable" || normalized === "safe") {
    bgClass = "bg-[#EAF5EE] text-[#107C41] border-[#C3E4CD]";
    icon = <CheckCircle2 className="shrink-0" />;
    defaultLabel = label || (normalized === "ready" ? "Ready" : normalized === "comfortable" ? "Comfortable" : "Safe");
  } else if (normalized === "tight") {
    bgClass = "bg-[#FEF5E7] text-[#B25E02] border-[#FBDCA8]";
    icon = <Clock className="shrink-0" />;
    defaultLabel = label || "Tight";
  } else if (
    normalized === "not_yet" ||
    normalized === "not_yet_ready" ||
    normalized === "too_much" ||
    normalized === "error"
  ) {
    bgClass = "bg-[#FDE8E8] text-[#C5221F] border-[#FAC7C7]";
    icon = normalized === "too_much" ? <AlertTriangle className="shrink-0" /> : <XCircle className="shrink-0" />;
    defaultLabel = label || (normalized === "too_much" ? "Too much" : "Not yet");
  }

  let sizeStyles = "px-3 py-1 text-sm gap-1.5 font-medium";
  let iconSize = "w-4 h-4";
  if (size === "sm") {
    sizeStyles = "px-2 py-0.5 text-xs gap-1 font-medium";
    iconSize = "w-3.5 h-3.5";
  } else if (size === "lg") {
    sizeStyles = "px-4 py-2 text-base gap-2 font-semibold";
    iconSize = "w-5 h-5";
  }

  return (
    <span
      className={`inline-flex items-center rounded-full border ${bgClass} ${sizeStyles} ${className}`}
      role="status"
    >
      <span className={iconSize}>{icon}</span>
      <span>{defaultLabel}</span>
    </span>
  );
}

export default StatusBadge;
