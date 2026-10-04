/**
 * Formatting utilities for numbers and currency in CreditPath
 */

export const BANGLA_DIGITS: Record<string, string> = {
  "0": "০",
  "1": "১",
  "2": "২",
  "3": "৩",
  "4": "৪",
  "5": "৫",
  "6": "৬",
  "7": "৭",
  "8": "৮",
  "9": "৯",
};

export function toBanglaDigits(str: string): string {
  return str.replace(/[0-9]/g, (d) => BANGLA_DIGITS[d] || d);
}

export function formatNumber(num: number | null | undefined, useBanglaNumerals = false): string {
  if (num === null || num === undefined || isNaN(num)) return "0";
  const formatted = Math.round(num).toLocaleString("en-US");
  if (useBanglaNumerals) {
    return toBanglaDigits(formatted);
  }
  return formatted;
}

export function formatCurrency(amount: number | null | undefined, useBanglaNumerals = false): string {
  return `৳${formatNumber(amount, useBanglaNumerals)}`;
}
