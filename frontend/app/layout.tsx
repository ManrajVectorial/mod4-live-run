import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { TopBar } from "@/components/TopBar";

import "./globals.css";

export const metadata: Metadata = {
  title: "Policy Assistant",
  description: "Answers staff policy questions from the bank's policy documents, with citations.",
};

// REQ-U13: lay out at the device width (375 px phones included).
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <TopBar />
        {children}
      </body>
    </html>
  );
}
