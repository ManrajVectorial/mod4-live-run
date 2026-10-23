// F9 — the design tokens: light theme only (U11) and readable contrast (WCAG AA, 4.5:1).
// Reads app/globals.css, so a token change that breaks contrast fails here, not by eye.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const CSS = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

function tokens(): Map<string, string> {
  const root = CSS.match(/:root\s*\{([^}]*)\}/);
  assert.ok(root, "globals.css defines its tokens on :root");
  const found = new Map<string, string>();
  for (const [, name, value] of root[1].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) found.set(name, value.trim());
  return found;
}

function luminance(hex: string): number {
  const m = hex.match(/^#([0-9a-f]{6})$/i);
  assert.ok(m, `expected a #rrggbb colour, got ${hex}`);
  const [r, g, b] = [0, 2, 4].map((i) => {
    const c = parseInt(m[1].slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Every text colour against every background it is used on.
const PAIRS: [string, string][] = [
  ["--text", "--bg"],
  ["--text", "--surface"],
  ["--muted", "--bg"],
  ["--muted", "--surface"],
  ["--accent", "--bg"],
  ["--accent", "--surface"],
  ["--on-accent", "--accent"],
  ["--topbar-text", "--topbar-bg"],
  ["--user-text", "--user-bg"],
  ["--answer-text", "--answer-bg"],
  ["--refusal-text", "--refusal-bg"],
  ["--passages-text", "--passages-bg"],
  ["--error-text", "--error-bg"],
  ["--conflict-text", "--conflict-bg"],
  ["--on-superseded", "--superseded"],
  ["--superseded", "--bg"],
  ["--text", "--page"],
  ["--muted", "--page"],
  ["--accent", "--page"],
  ["--topbar-muted", "--topbar-bg"],
  ["--on-accent", "--accent-hover"],
  ["--topbar-text", "--accent"],
  ["--accent", "--answer-bg"],
];

test("light theme only: no dark variant, whatever the system prefers (U11)", () => {
  assert.match(CSS, /color-scheme:\s*light/);
  assert.doesNotMatch(CSS, /prefers-color-scheme\s*:\s*dark/);
});

test("every text and background token pair meets WCAG AA contrast (4.5:1)", () => {
  const t = tokens();
  for (const [fg, bg] of PAIRS) {
    assert.ok(t.has(fg) && t.has(bg), `tokens ${fg} and ${bg} exist`);
    const ratio = contrast(t.get(fg)!, t.get(bg)!);
    assert.ok(ratio >= 4.5, `${fg} on ${bg} is ${ratio.toFixed(2)}:1, below 4.5:1`);
  }
});

test("focus is always visible (keyboard use)", () => {
  assert.match(CSS, /:focus-visible\s*\{[^}]*outline:[^;}]*var\(--focus\)/);
  assert.ok(tokens().has("--focus"));
});

test("colours come from the tokens: no raw hex outside :root", () => {
  const outside = CSS.replace(/:root\s*\{[^}]*\}/, "");
  assert.deepEqual(outside.match(/#[0-9a-f]{3,8}\b/gi) ?? [], []);
});
