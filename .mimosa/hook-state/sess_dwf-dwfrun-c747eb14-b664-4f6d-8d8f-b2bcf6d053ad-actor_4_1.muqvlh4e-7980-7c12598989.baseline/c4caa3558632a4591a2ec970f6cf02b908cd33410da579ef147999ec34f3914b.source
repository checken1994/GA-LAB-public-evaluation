import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { CURRENT_ROUND, CURRENT_ROUND_LABEL } from "@/lib/audit-data/version";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: `SCP DNA Audit ${CURRENT_ROUND_LABEL} (recursive level 4)`,
  description:
    `Round ${CURRENT_ROUND} audit of SCP Vietnam codebase. R${CURRENT_ROUND} audits the prior round itself — don't trust prior reports, audit the auditor. Use SCP autofix + best world tools + SCP DNA to find root-cause bugs and fix them at the root. Autofix engine upgraded v3 → v4 (4,894 LOC, 6 NEW improvements IMP-19..24). Reality > Model.`,
  keywords: [
    "SCP",
    "DNA",
    "Audit",
    `Round ${CURRENT_ROUND}`,
    "Autofix v4",
    "Root Cause",
    "Reality > Model",
    "PASS ≠ TRUE",
    "Auditor's Paradox",
  ],
  authors: [{ name: "Gà Lab" }],
  icons: {
    // [Fix 4-c-019 · Task 3-B] Local favicon, not external CDN.
    // BEFORE: icon pointed to an external CDN URL (referrer leak, single
    // point of failure, broken offline / air-gapped deployments). DNA #6
    // (gốc tin cậy bên ngoài) + #19.
    // AFTER: /logo.svg — served from dashboard/public/logo.svg (verified exists).
    // Rollback: revert to the CDN URL if the local logo looks wrong.
    icon: "/logo.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        {/* Set theme class BEFORE React hydrates to prevent flash. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('scp-theme');var d=t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches);if(d){document.documentElement.classList.add('dark');}}catch(e){}})();`,
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
