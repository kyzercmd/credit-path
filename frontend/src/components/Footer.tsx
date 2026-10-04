"use client";

import React from "react";
import { useLanguage } from "@/contexts/LanguageContext";
import { Meta } from "@/lib/api";

interface FooterProps {
  meta?: Meta | null;
  className?: string;
}

export function Footer({ meta, className = "" }: FooterProps) {
  const { t } = useLanguage();

  return (
    <footer
      className={`mt-auto py-6 px-4 text-center border-t border-[#E8E8EC] bg-white ${className}`}
    >
      <p className="text-xs text-[#6B6B76] leading-relaxed">
        {meta?.disclaimer || t("footer.disclaimer")}
      </p>
      {meta && (
        <div className="mt-1 flex items-center justify-center gap-2 text-[10px] text-gray-400">
          <span>v{meta.model_version}</span>
          <span>•</span>
          <span>As of: {meta.data_as_of}</span>
        </div>
      )}
    </footer>
  );
}

export default Footer;
