import type { Metadata } from "next";
import type { ReactNode } from "react";

import { TopBar } from "@/components/TopBar";

import "./globals.css";

export const metadata: Metadata = {
  title: "Policy Assistant",
  description: "Answers staff policy questions from the bank's policy documents, with citations.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TopBar />
        {children}
      </body>
    </html>
  );
}
