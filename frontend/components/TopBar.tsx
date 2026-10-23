"use client";

import Link from "next/link";

import { TOP_BAR_LINKS } from "@/lib/present";

// The name, links to the pages that exist (REQ-U10, U14), and Reset (REQ-U9).
export function TopBar() {
  return (
    <header className="topbar">
      <Link href="/" className="topbar__name">
        Policy Assistant
      </Link>
      <nav className="topbar__nav" aria-label="Pages">
        {TOP_BAR_LINKS.map((link) => (
          <Link key={link.href} href={link.href} className="topbar__link">
            {link.label}
          </Link>
        ))}
        <button
          type="button"
          className="button"
          onClick={() => {
            // A full reload to the ask page clears everything on screen.
            window.location.assign("/");
          }}
        >
          Reset
        </button>
      </nav>
    </header>
  );
}
