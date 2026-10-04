"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useConsent } from "@/contexts/ConsentContext";
import { Skeleton } from "@/components/Skeleton";

export default function RootPage() {
  const router = useRouter();
  const { hasConsented } = useConsent();

  useEffect(() => {
    if (!hasConsented) {
      router.replace("/consent");
    } else {
      router.replace("/home");
    }
  }, [hasConsented, router]);

  return (
    <div className="p-6 flex flex-col items-center justify-center min-h-[60vh] space-y-4">
      <div className="w-12 h-12 rounded-full bg-[var(--accent-soft)] animate-pulse" />
      <Skeleton lines={2} className="w-48" />
    </div>
  );
}
