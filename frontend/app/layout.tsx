import type { Metadata } from "next";
import { Sora, Be_Vietnam_Pro, JetBrains_Mono } from "next/font/google";
import { Sidebar } from "@/components/sidebar";
import "./globals.css";

// Distinctive, intentional type system (not Inter/system):
// Sora for display, Be Vietnam Pro for body (native Vietnamese), JetBrains Mono
// for data/IDs/timestamps — the monospace numerics give the SIEM its console feel.
const display = Sora({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

const body = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sentinel",
  description: "Unified monitoring platform — SIEM + Observability + SOAR + AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body className="font-sans text-slate-100 antialiased">
        {/* Fixed ambient backdrop (warm accent wash + grid) behind everything. */}
        <div className="app-ambient pointer-events-none fixed inset-0 -z-10" aria-hidden />
        <div className="flex min-h-[100dvh]">
          <Sidebar />
          <div className="flex-1 min-w-0 overflow-y-auto">
            <div className="fade-in">{children}</div>
          </div>
        </div>
      </body>
    </html>
  );
}
