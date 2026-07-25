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
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
