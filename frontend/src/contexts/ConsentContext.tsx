"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { postConsent } from "@/lib/api";

interface ConsentContextType {
  customerId: string;
  hasConsented: boolean;
  coachActive: boolean;
  setConsent: (consented: boolean) => Promise<void>;
  setCoachActive: (active: boolean) => Promise<void>;
  switchCustomer: (id: string) => void;
}

const ConsentContext = createContext<ConsentContextType | undefined>(undefined);

export function ConsentProvider({ children }: { children: ReactNode }) {
  const [customerId, setCustomerId] = useState<string>("C0001");
  const [hasConsented, setHasConsented] = useState<boolean>(true);
  const [coachActive, setCoachActiveState] = useState<boolean>(true);

  useEffect(() => {
    try {
      const savedCustomer = localStorage.getItem("creditpath_customer_id");
      if (savedCustomer) {
        setCustomerId(savedCustomer);
      }
      const savedConsent = localStorage.getItem("creditpath_consent");
      if (savedConsent !== null) {
        setHasConsented(savedConsent === "true");
      }
      const savedCoach = localStorage.getItem("creditpath_coach_active");
      if (savedCoach !== null) {
        setCoachActiveState(savedCoach === "true");
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
