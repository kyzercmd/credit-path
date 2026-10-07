import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/contexts/LanguageContext";
import { ConsentProvider } from "@/contexts/ConsentContext";
import { BottomNav } from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "CreditPath — Loan Readiness Coach",
  description: "Loan-readiness and repayment-timing guidance by upay",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F4F4F6] text-[#1A1A1F] font-sans antialiased">
        <LanguageProvider>
          <ConsentProvider>
            {/* Mobile-first centered phone frame (expands on admin page) */}
            <div className="flex justify-center min-h-screen">
              <div className="w-full max-w-[430px] has-[[data-admin-page]]:max-w-6xl transition-[max-width] duration-200 min-h-screen bg-white shadow-sm flex flex-col relative pb-20 border-x border-[#E8E8EC]">
                {children}
                <BottomNav />
              </div>
            </div>
          </ConsentProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
