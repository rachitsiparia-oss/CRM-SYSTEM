import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RKPR Restaurant CRM",
  description: "Private, single-business CRM for RKPR Fast-Food Restaurant.",
};

// Sets data-theme on <html> before first paint, so there's no flash of the
// wrong theme while React hydrates. Reads the user's stored choice
// (theme-toggle.tsx writes it); falls back to the OS preference only when
// nothing has been stored yet. Must run as a blocking, standalone inline
// script (no imports) — the storage key literal here must match
// THEME_STORAGE_KEY in src/lib/theme.ts.
const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("rkpr:theme");if(t!=="light"&&t!=="dark"){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}document.documentElement.setAttribute("data-theme",t);}catch(e){}})();`;

// Deliberately minimal: the (app) route group's own layout adds the
// authenticated shell (nav + user menu). Auth pages (/login,
// /reset-password, /unauthorized, /forbidden, /session-expired) and
// /auth/callback render directly under this root layout with no nav —
// src/proxy.ts is what keeps them reachable without a session.
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
