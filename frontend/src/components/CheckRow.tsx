import React from "react";
import { Check, CircleDot, HelpCircle } from "lucide-react";

interface CheckRowProps {
  title: string;
  passed: boolean;
  reason?: string;
  currentValue?: string | number | null;
  targetValue?: string | number | null;
  onWhyClick?: () => void;
  className?: string;
}

export function CheckRow({
  title,
  passed,
  reason,
  onWhyClick,
  className = "",
}: CheckRowProps) {
  return (
    <div
      className={`flex items-start justify-between gap-3 py-3 border-b border-[#E8E8EC] last:border-b-0 ${className}`}
    >
      <div className="flex items-start gap-3 flex-1 min-w-0">
        <div className="mt-0.5 shrink-0">
          {passed ? (
            <div
              className="w-6 h-6 rounded-full bg-[#EAF5EE] text-[#107C41] flex items-center justify-center border border-[#C3E4CD]"
              aria-label="Passed check"
            >
              <Check className="w-3.5 h-3.5 stroke-[2.5]" />
            </div>
          ) : (
            <div
              className="w-6 h-6 rounded-full bg-gray-100 text-[#6B6B76] flex items-center justify-center border border-[#E8E8EC]"
              aria-label="Not yet passed"
            >
              <CircleDot className="w-3.5 h-3.5 text-[#6B6B76]" />
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span
              className={`text-base font-medium leading-snug ${
                passed ? "text-[#1A1A1F]" : "text-[#1A1A1F]"
              }`}
            >
              {title}
            </span>
            {passed && (
              <span className="text-xs font-medium text-[#107C41] bg-[#EAF5EE] px-1.5 py-0.5 rounded">
                Met
              </span>
            )}
            {!passed && (
              <span className="text-xs font-medium text-[#6B6B76] bg-gray-100 px-1.5 py-0.5 rounded">
                Not yet
              </span>
            )}
          </div>
          {reason && (
            <p className="text-sm text-[#6B6B76] mt-0.5 leading-relaxed">
              {reason}
            </p>
          )}
        </div>
      </div>

      {onWhyClick && (
        <button
          type="button"
          onClick={onWhyClick}
          aria-label={`Why info for ${title}`}
          className="shrink-0 p-1 text-[var(--accent)] hover:text-[#004273] active:opacity-75 transition-colors inline-flex items-center gap-1 text-xs font-semibold"
        >
          <HelpCircle className="w-4 h-4" />
          <span>Why?</span>
        </button>
      )}
    </div>
  );
}

export default CheckRow;
