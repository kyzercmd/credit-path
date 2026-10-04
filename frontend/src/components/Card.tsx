import React, { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  headerRight?: ReactNode;
  onClick?: () => void;
}

export function Card({
  children,
  className = "",
  title,
  subtitle,
  action,
  headerRight,
  onClick,
}: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl border border-[#E8E8EC] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.03)] transition-all ${
        onClick ? "cursor-pointer hover:border-gray-300" : ""
      } ${className}`}
    >
      {(title || subtitle || headerRight) && (
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            {title && (
              <h3 className="text-lg font-semibold text-[#1A1A1F] leading-snug">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-sm text-[#6B6B76] mt-0.5 leading-relaxed">
                {subtitle}
              </p>
            )}
          </div>
          {headerRight && <div className="shrink-0">{headerRight}</div>}
        </div>
      )}
      <div>{children}</div>
      {action && <div className="mt-4 pt-3 border-t border-[#E8E8EC]">{action}</div>}
    </div>
  );
}

export default Card;
