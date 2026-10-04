"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import en from "@/i18n/en.json";
import bn from "@/i18n/bn.json";
import { toBanglaDigits, formatNumber as formatNumberUtil, formatCurrency as formatCurrencyUtil } from "@/lib/format";

export { toBanglaDigits };

export type Locale = "en" | "bn";

interface LanguageContextType {
  locale: Locale;
  useBanglaNumerals: boolean;
  t: (key: string, params?: Record<string, any>) => string;
  setLocale: (locale: Locale) => void;
  toggleLanguage: () => void;
  toggleBanglaNumerals: () => void;
  setUseBanglaNumerals: (val: boolean) => void;
  formatCurrency: (amount: number) => string;
  formatNumber: (num: number) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const dictionaries: Record<Locale, any> = { en, bn };

function getNestedValue(obj: any, path: string): string | undefined {
  const parts = path.split(".");
  let curr = obj;
  for (const part of parts) {
    if (curr === undefined || curr === null) return undefined;
    curr = curr[part];
  }
  return typeof curr === "string" ? curr : undefined;
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [useBanglaNumerals, setUseBanglaNumeralsState] = useState<boolean>(false);

  useEffect(() => {
    try {
      const savedLocale = localStorage.getItem("creditpath_locale") as Locale | null;
      if (savedLocale === "en" || savedLocale === "bn") {
        setLocaleState(savedLocale);
      }
      const savedNumerals = localStorage.getItem("creditpath_bangla_numerals");
      if (savedNumerals !== null) {
        setUseBanglaNumeralsState(savedNumerals === "true");
      }
    } catch {
      // Ignore localStorage errors (e.g. incognito)
    }
  }, []);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    try {
      localStorage.setItem("creditpath_locale", newLocale);
    } catch {}
  }, []);

  const toggleLanguage = useCallback(() => {
    setLocaleState((prev) => {
      const next = prev === "en" ? "bn" : "en";
      try {
        localStorage.setItem("creditpath_locale", next);
      } catch {}
      return next;
    });
  }, []);

  const setUseBanglaNumerals = useCallback((val: boolean) => {
    setUseBanglaNumeralsState(val);
    try {
      localStorage.setItem("creditpath_bangla_numerals", String(val));
    } catch {}
  }, []);

  const toggleBanglaNumerals = useCallback(() => {
    setUseBanglaNumeralsState((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("creditpath_bangla_numerals", String(next));
      } catch {}
      return next;
    });
  }, []);

  const formatNumber = useCallback(
    (num: number): string => {
      return formatNumberUtil(num, useBanglaNumerals);
    },
    [useBanglaNumerals]
  );

  const formatCurrency = useCallback(
    (amount: number): string => {
      return formatCurrencyUtil(amount, useBanglaNumerals);
    },
    [useBanglaNumerals]
  );

  const t = useCallback(
    (key: string, params?: Record<string, any>): string => {
      let raw = getNestedValue(dictionaries[locale], key);
      if (raw === undefined) {
        raw = getNestedValue(dictionaries.en, key);
      }
      if (raw === undefined) {
        return key;
      }

      if (params) {
        let result = raw;
        for (const [k, v] of Object.entries(params)) {
          const valStr = typeof v === "number" ? formatNumber(v) : String(v);
          result = result.replace(new RegExp(`\\{${k}\\}`, "g"), valStr);
        }
        return result;
      }

      return raw;
    },
    [locale, formatNumber]
  );

  return (
    <LanguageContext.Provider
      value={{
        locale,
        useBanglaNumerals,
        t,
        setLocale,
        toggleLanguage,
        toggleBanglaNumerals,
        setUseBanglaNumerals,
        formatCurrency,
        formatNumber,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
