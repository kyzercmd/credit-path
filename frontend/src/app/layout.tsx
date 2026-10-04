import type { Metadata } from "next";
import { Inter, Noto_Sans_Bengali } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const notoSansBengali = Noto_Sans_Bengali({
  subsets: ["bengali"],
  variable: "--font-noto-bengali",
});

export const metadata: Metadata = {
  title: "CreditPath",
  description: "Loan-readiness and repayment-timing coach",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${notoSansBengali.variable} font-sans bg-gray-50 text-foreground`}>
        <div className="mx-auto min-w-[360px] max-w-[430px] min-h-screen bg-background border-x border-border shadow-sm flex flex-col">
          {children}
        </div>
      </body>
    </html>
  );
}
