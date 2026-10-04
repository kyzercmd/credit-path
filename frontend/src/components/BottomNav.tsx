"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Calculator, Calendar, User } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

export function BottomNav() {
  const pathname = usePathname();
  const { t } = useLanguage();

  // If on admin or consent page, or why sheet, we might still show or hide nav.
  // Generally hide nav on /consent and /admin
  const isConsent = pathname === "/consent";
  const isAdmin = pathname?.startsWith("/admin");

  if (isConsent || isAdmin) {
    return null;
  }

  const tabs = [
    {
      href: "/home",
      label: t("nav.home"),
      icon: Home,
      isActive: pathname === "/home" || pathname === "/",
    },
    {
      href: "/loan-check",
      label: t("nav.loan_check"),
      icon: Calculator,
      isActive: pathname === "/loan-check" || pathname === "/safe-range",
    },
    {
      href: "/calendar",
      label: t("nav.calendar"),
      icon: Calendar,
      isActive: pathname === "/calendar",
    },
    {
      href: "/me",
      label: t("nav.me"),
      icon: User,
      isActive: pathname === "/me" || pathname === "/progress" || pathname === "/path",
    },
  ];

  return (
    <nav
      aria-label="Bottom Navigation"
      className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[430px] bg-white border-t border-[#E8E8EC] shadow-[0_-2px_10px_rgba(0,0,0,0.03)] z-40 h-16 flex items-center justify-around px-2"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = tab.isActive;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`flex flex-col items-center justify-center min-w-[64px] min-h-[48px] px-2 py-1 rounded-lg transition-colors select-none ${
              active
                ? "text-[var(--accent)] font-semibold"
                : "text-[#6B6B76] hover:text-[#1A1A1F] active:opacity-75"
            }`}
          >
            <div className="relative">
              <Icon className={`w-5 h-5 ${active ? "stroke-[2.5]" : "stroke-[1.8]"}`} />
              {active && (
                <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
              )}
            </div>
            <span className="text-[11px] mt-1 leading-tight">{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export default BottomNav;
