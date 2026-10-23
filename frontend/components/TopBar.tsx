"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { BrandMark } from "@/components/Icon";
import { TOP_BAR_LINKS } from "@/lib/present";

// The product name, History and Corpus (REQ-U14, U15) and Reset (REQ-U9).
export function TopBar() {
  const path = usePathname();
  return (
    <header className="topbar">
      <div className="topbar__inner">
        <Link href="/" className="brand">
          <BrandMark />
          <span className="brand__name">Policy Assistant</span>
          <span className="brand__org">Aldermere Bank · internal</span>
        </Link>
        <nav className="topbar__nav" aria-label="Pages">
          {TOP_BAR_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="topbar__link"
              aria-current={path === link.href || path.startsWith(`${link.href}/`) ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
          <button
            type="button"
            className="button button--on-dark"
            onClick={() => {
              // A full reload to the ask page clears everything on screen.
              window.location.assign("/");
            }}
          >
            Reset
          </button>
        </nav>
      </div>
    </header>
  );
}
