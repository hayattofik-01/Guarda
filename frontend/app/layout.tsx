import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Guarda — Know your external security score. Close the enterprise deal.",
  description:
    "External security monitoring for SaaS founders. Know your A–F score, fix exposures in "
    + "plain English, and pass enterprise security questionnaires.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
