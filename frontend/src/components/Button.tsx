import React, { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "primary" | "secondary" | "link" | "outline" | "danger";
  fullWidth?: boolean;
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export function Button({
  children,
  variant = "primary",
  fullWidth = true,
  isLoading = false,
  leftIcon,
  rightIcon,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center font-medium transition-all select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";

  let variantStyles = "";
  if (variant === "primary") {
    variantStyles =
      "min-h-[48px] px-5 py-3 rounded-xl bg-[var(--accent)] text-white shadow-sm hover:opacity-95 active:scale-[0.99] focus-visible:ring-[var(--accent)]";
  } else if (variant === "secondary" || variant === "outline") {
    variantStyles =
      "min-h-[48px] px-5 py-3 rounded-xl border border-[#E8E8EC] bg-white text-[#1A1A1F] hover:bg-gray-50 active:scale-[0.99] focus-visible:ring-gray-300";
  } else if (variant === "link") {
    variantStyles =
      "min-h-[44px] py-2 px-3 text-[var(--accent)] hover:underline active:opacity-80 focus-visible:ring-[var(--accent)] text-sm font-semibold";
  } else if (variant === "danger") {
    variantStyles =
      "min-h-[48px] px-5 py-3 rounded-xl bg-status-red text-white hover:opacity-95 active:scale-[0.99] focus-visible:ring-status-red";
  }

  const widthStyle = fullWidth ? "w-full" : "w-auto";

  return (
    <button
      disabled={disabled || isLoading}
      className={`${baseStyles} ${variantStyles} ${widthStyle} ${className}`}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg
            className="animate-spin h-5 w-5 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            ></path>
          </svg>
          <span>Loading...</span>
        </span>
      ) : (
        <span className="flex items-center justify-center gap-2">
          {leftIcon && <span className="shrink-0">{leftIcon}</span>}
          <span>{children}</span>
          {rightIcon && <span className="shrink-0">{rightIcon}</span>}
        </span>
      )}
    </button>
  );
}

export default Button;
