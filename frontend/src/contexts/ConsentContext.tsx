"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { postConsent } from "@/lib/api";

export interface ConsentLogEntry {
  action: "consent" | "opt-out";
  timestamp: string;
  customerId: string;
}

interface ConsentContextType {
  customerId: string;
  hasConsented: boolean;
  coachActive: boolean;
  consentLog: ConsentLogEntry[];
  setConsent: (consented: boolean) => Promise<void>;
  setCoachActive: (active: boolean) => Promise<void>;
  switchCustomer: (id: string) => void;
}

const ConsentContext = createContext<ConsentContextType | undefined>(undefined);

const DEFAULT_CUSTOMER_ID = "C00001";

function normalizeCustomerId(id: string): string {
  return /^C\d{4}$/.test(id) ? `C0${id.slice(1)}` : id;
}

export function ConsentProvider({ children }: { children: ReactNode }) {
  const [customerId, setCustomerId] = useState<string>(DEFAULT_CUSTOMER_ID);
  const [hasConsented, setHasConsented] = useState<boolean>(true);
  const [coachActive, setCoachActiveState] = useState<boolean>(true);
  const [consentLog, setConsentLog] = useState<ConsentLogEntry[]>([]);

  useEffect(() => {
    try {
      const savedCustomer = localStorage.getItem("creditpath_customer_id");
      const normalizedCustomer = savedCustomer
        ? normalizeCustomerId(savedCustomer)
        : DEFAULT_CUSTOMER_ID;
      setCustomerId(normalizedCustomer);
      if (normalizedCustomer !== savedCustomer) {
        localStorage.setItem("creditpath_customer_id", normalizedCustomer);
      }
      const savedConsent = localStorage.getItem("creditpath_consent");
      if (savedConsent !== null) {
        setHasConsented(savedConsent === "true");
      }
      const savedCoach = localStorage.getItem("creditpath_coach_active");
      if (savedCoach !== null) {
        setCoachActiveState(savedCoach === "true");
      }
      const savedLog = localStorage.getItem("creditpath_consent_log");
      if (savedLog) {
        try {
          const parsed = JSON.parse(savedLog);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setConsentLog(parsed);
          } else {
            setConsentLog([
              {
                action: "consent",
                timestamp: new Date().toISOString(),
                customerId: normalizedCustomer,
              },
            ]);
          }
        } catch {
          setConsentLog([
            {
              action: "consent",
              timestamp: new Date().toISOString(),
              customerId: normalizedCustomer,
            },
          ]);
        }
      } else {
        const initialEntry: ConsentLogEntry = {
          action: "consent",
          timestamp: new Date().toISOString(),
          customerId: normalizedCustomer,
        };
        setConsentLog([initialEntry]);
        try {
          localStorage.setItem("creditpath_consent_log", JSON.stringify([initialEntry]));
        } catch {}
      }
    } catch {
      // Ignore storage errors
    }
  }, []);

  const switchCustomer = useCallback((id: string) => {
    setCustomerId(id);
    try {
      localStorage.setItem("creditpath_customer_id", id);
    } catch {}
  }, []);

  const setConsent = useCallback(
    async (consented: boolean) => {
      setHasConsented(consented);
      setCoachActiveState(consented);
      const entry: ConsentLogEntry = {
        action: consented ? "consent" : "opt-out",
        timestamp: new Date().toISOString(),
        customerId,
      };
      setConsentLog((prev) => {
        const next = [entry, ...prev];
        try {
          localStorage.setItem("creditpath_consent_log", JSON.stringify(next));
        } catch {}
        return next;
      });
      try {
        localStorage.setItem("creditpath_consent", String(consented));
        localStorage.setItem("creditpath_coach_active", String(consented));
      } catch {}

      try {
        await postConsent(customerId, consented ? "consent" : "opt-out");
      } catch (err) {
        console.warn("Failed to record consent on backend:", err);
      }
    },
    [customerId]
  );

  const setCoachActive = useCallback(
    async (active: boolean) => {
      setCoachActiveState(active);
      const entry: ConsentLogEntry = {
        action: active ? "consent" : "opt-out",
        timestamp: new Date().toISOString(),
        customerId,
      };
      setConsentLog((prev) => {
        const next = [entry, ...prev];
        try {
          localStorage.setItem("creditpath_consent_log", JSON.stringify(next));
        } catch {}
        return next;
      });
      try {
        localStorage.setItem("creditpath_coach_active", String(active));
      } catch {}

      if (!active) {
        try {
          await postConsent(customerId, "opt-out");
        } catch (err) {
          console.warn("Failed to record opt-out on backend:", err);
        }
      } else {
        try {
          await postConsent(customerId, "consent");
        } catch (err) {
          console.warn("Failed to record consent on backend:", err);
        }
      }
    },
    [customerId]
  );

  return (
    <ConsentContext.Provider
      value={{
        customerId,
        hasConsented,
        coachActive,
        consentLog,
        setConsent,
        setCoachActive,
        switchCustomer,
      }}
    >
      {children}
    </ConsentContext.Provider>
  );
}

export function useConsent(): ConsentContextType {
  const context = useContext(ConsentContext);
  if (!context) {
    throw new Error("useConsent must be used within a ConsentProvider");
  }
  return context;
}
