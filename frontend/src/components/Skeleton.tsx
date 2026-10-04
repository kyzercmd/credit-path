import React from "react";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "rect" | "circle" | "card";
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export function Skeleton({
  className = "",
  variant = "rect",
  width,
  height,
  lines = 1,
}: SkeletonProps) {
  const base = "animate-pulse bg-gray-200/80";

  if (variant === "card") {
    return (
      <div
        className={`bg-white rounded-2xl border border-[#E8E8EC] p-5 shadow-xs space-y-4 ${className}`}
      >
        <div className="flex items-center justify-between">
          <div className="h-5 w-32 bg-gray-200 rounded animate-pulse" />
          <div className="h-6 w-16 bg-gray-200 rounded-full animate-pulse" />
        </div>
        <div className="space-y-2 pt-2">
          <div className="h-4 w-full bg-gray-200 rounded animate-pulse" />
          <div className="h-4 w-3/4 bg-gray-200 rounded animate-pulse" />
        </div>
        <div className="h-10 w-full bg-gray-100 rounded-xl animate-pulse mt-4" />
      </div>
    );
  }

  if (variant === "circle") {
    return (
      <div
        style={{ width, height }}
        className={`rounded-full shrink-0 ${base} ${className}`}
      />
    );
  }

  if (variant === "text" && lines > 1) {
    return (
      <div className={`space-y-2.5 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            style={{ width: i === lines - 1 ? "70%" : "100%", height: height || 16 }}
            className={`rounded ${base}`}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      style={{ width, height }}
      className={`rounded-lg ${base} ${className}`}
    />
  );
}

export function SkeletonCard() {
  return <Skeleton variant="card" />;
}

export default Skeleton;
