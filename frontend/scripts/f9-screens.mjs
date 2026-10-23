// F9 evidence: screenshots of every page and result state at 1280 px and 375 px in
// headless Edge, plus basic checks (no horizontal scroll, labels, headings, keyboard focus).
//
//   F9_BASE_URL=http://127.0.0.1:3014 EDGE_PATH="C:/…/msedge.exe" node scripts/f9-screens.mjs [--only a,b]
//
// Edge is driven over its DevTools protocol with Node's built-in WebSocket and fetch, so
// there is no test library (AGENTS.md rule 4). Exits non-zero if any check fails.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = process.env.F9_BASE_URL;
const EDGE = process.env.EDGE_PATH;
const PORT = Number(process.env.F9_DEBUG_PORT || 9333);
if (!BASE || !EDGE) {
  console.error("Set F9_BASE_URL (the web page) and EDGE_PATH (msedge.exe).");
  process.exit(2);
}
const OUT = resolve(dirname(fileURLToPath(import.meta.url)), "../../tickets/evidence/F9");
const ONLY = (process.argv.find((a) => a.startsWith("--only="))?.slice(7) ?? "").split(",").filter(Boolean);
const WIDTHS = [1280, 375];
const MAX_HEIGHT = 3200; // long pages (the whole history, a whole document) are cut here

const Q1 = "What is the approval threshold for a travel expense claim?";
const Q10 = "A provider holds our client correspondence. How long can they keep it after we terminate?";
const Q13 = "How many days of paid parental leave am I entitled to?";

// name → how to get the page into that state. "ask" types into the question box and
// presses Enter, as a keyboard user would.
const SHOTS = [
  { name: "ask-empty", path: "/" },
  { name: "ask-loading", path: "/", ask: [Q1], waitFor: ".result--loading", early: true },
  { name: "ask-answered", path: "/", ask: [Q1], waitFor: ".result--answer" },
  { name: "ask-conflict-q10", path: "/", ask: [Q10], waitFor: ".result--conflict" },
  { name: "ask-refused-q13", path: "/", ask: [Q13], waitFor: ".result--refusal" },
  {
    name: "ask-conversation",
    path: "/",
    ask: ["What is the accommodation cap for a night in London?", "And for Singapore?"],
    waitFor: ".turn:nth-child(2) .result",
  },
  { name: "ask-degraded", path: "/", ask: [Q1], waitFor: ".result--passages", needs: "generation off" },
  { name: "ask-error", path: "/", ask: [Q1], waitFor: ".result--error", needs: "API stopped" },
  { name: "history", path: "/history", waitFor: ".list-item, .notice-line" },
  { name: "history-conversation", path: "history-latest", waitFor: ".conversation .result" },
  { name: "corpus", path: "/corpus", waitFor: ".list-item" },
  { name: "corpus-document-superseded", path: "/corpus/travel-expense-policy-v3.0", waitFor: ".doc-section" },
  { name: "corpus-document-section", path: "/corpus/travel-expense-policy-v3.1#section-4.2", waitFor: ".doc-section" },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function cdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((ok, fail) => {
    ws.onopen = ok;
    ws.onerror = fail;
  });
  let id = 0;
  const waiting = new Map();
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && waiting.has(msg.id)) {
      const { ok, fail } = waiting.get(msg.id);
      waiting.delete(msg.id);
      msg.error ? fail(new Error(`${msg.error.message}`)) : ok(msg.result);
    }
  };
  const send = (method, params = {}) =>
    new Promise((ok, fail) => {
      id += 1;
      waiting.set(id, { ok, fail });
      ws.send(JSON.stringify({ id, method, params }));
    });
  return { send, close: () => ws.close() };
}

async function evaluate(page, expression) {
  const { result, exceptionDetails } = await page.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (exceptionDetails) throw new Error(exceptionDetails.text);
  return result.value;
}

async function waitFor(page, selector, timeoutMs = 60000) {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    if (await evaluate(page, `!!document.querySelector(${JSON.stringify(selector)})`)) return true;
    await sleep(100);
  }
  throw new Error(`timed out waiting for ${selector}`);
}

async function key(page, keyName, code, text) {
  await page.send("Input.dispatchKeyEvent", { type: "keyDown", key: keyName, code, text, windowsVirtualKeyCode: keyName === "Enter" ? 13 : 9 });
  await page.send("Input.dispatchKeyEvent", { type: "keyUp", key: keyName, code, windowsVirtualKeyCode: keyName === "Enter" ? 13 : 9 });
}

async function askQuestion(page, question) {
  const turns = await evaluate(page, "document.querySelectorAll('.conversation > .turn').length");
  await evaluate(page, "document.getElementById('question').focus()");
  await page.send("Input.insertText", { text: question });
  await key(page, "Enter", "Enter", "\r");
  return turns;
}

// The basic accessibility check: labels, one h1, no skipped heading level, named buttons
// and links, alt text, and no horizontal scrolling at this width.
const CHECKS = `(() => {
  const problems = [];
  const doc = document.documentElement;
  if (doc.scrollWidth > window.innerWidth + 1) problems.push('horizontal scroll: ' + doc.scrollWidth + ' > ' + window.innerWidth);
  for (const el of document.querySelectorAll('input, textarea, select')) {
    if (el.type === 'hidden') continue;
    const named = (el.labels && el.labels.length) || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
    if (!named) problems.push('unlabelled ' + el.tagName.toLowerCase() + '#' + el.id);
  }
  const h1s = document.querySelectorAll('h1');
  if (h1s.length !== 1) problems.push('expected one h1, found ' + h1s.length);
  let last = 0;
  for (const h of document.querySelectorAll('h1, h2, h3, h4, h5, h6')) {
    const level = Number(h.tagName[1]);
    if (last && level > last + 1) problems.push('heading jumps h' + last + ' to h' + level + ': ' + h.textContent.trim().slice(0, 40));
    last = level;
  }
  for (const b of document.querySelectorAll('button')) if (!b.textContent.trim() && !b.getAttribute('aria-label')) problems.push('unnamed button');
  for (const a of document.querySelectorAll('a[href]')) if (!a.textContent.trim() && !a.getAttribute('aria-label')) problems.push('unnamed link ' + a.href);
  for (const img of document.querySelectorAll('img')) if (!img.hasAttribute('alt')) problems.push('img without alt');
  if (document.documentElement.lang !== 'en') problems.push('no lang');
  return problems;
})()`;

// Keyboard: Tab from the top; every stop must show a visible focus outline.
const FOCUS_STATE = `(() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const s = getComputedStyle(el);
  return { tag: el.tagName.toLowerCase(), text: (el.textContent || el.getAttribute('aria-label') || el.id || '').trim().slice(0, 40), outline: s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2 };
})()`;

async function keyboardWalk(page, stops = 8) {
  const seen = [];
  await evaluate(page, "document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0)");
  for (let i = 0; i < stops; i += 1) {
    await key(page, "Tab", "Tab", "");
    await sleep(60);
    const state = await evaluate(page, FOCUS_STATE);
    if (state) seen.push(state);
  }
  return seen;
}

async function capture(page, file, width) {
  const { cssContentSize } = await page.send("Page.getLayoutMetrics");
  const height = Math.min(Math.ceil(cssContentSize.height), MAX_HEIGHT);
  const { data } = await page.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: true,
    clip: { x: 0, y: 0, width, height, scale: 1 },
  });
  writeFileSync(file, Buffer.from(data, "base64"));
  return height;
}

async function latestConversationPath() {
  const res = await fetch(`${BASE}/api/conversations`);
  if (!res.ok) throw new Error(`history list: HTTP ${res.status}`);
  const { conversations } = await res.json();
  const pick = conversations.find((c) => c.message_count >= 4 && c.statuses.every((s) => s === "answered")) ?? conversations[0];
  return `/history?c=${encodeURIComponent(pick.conversation_id)}`;
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const profile = mkdtempSync(join(tmpdir(), "f9-edge-"));
  const edge = spawn(EDGE, [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--hide-scrollbars",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    "about:blank",
  ], { stdio: "ignore" });
  let failures = 0;
  const report = [];
  try {
    let target;
    for (let i = 0; i < 50 && !target; i += 1) {
      await sleep(200);
      target = await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" })
        .then((r) => r.json())
        .catch(() => undefined);
    }
    if (!target) throw new Error("Edge did not start");
    const page = await cdp(target.webSocketDebuggerUrl);
    await page.send("Page.enable");
    await page.send("Runtime.enable");
    const shots = SHOTS.filter((s) => (ONLY.length ? ONLY.includes(s.name) : !s.needs));
    for (const shot of shots) {
      for (const width of WIDTHS) {
        await page.send("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: width < 500 });
        const path = shot.path === "history-latest" ? await latestConversationPath() : shot.path;
        await page.send("Page.navigate", { url: BASE + path });
        await waitFor(page, "main");
        await sleep(300);
        for (const question of shot.ask ?? []) {
          const before = await askQuestion(page, question);
          if (!shot.early) await waitFor(page, `.conversation > .turn:nth-child(${before + 1}) .result:not(.result--loading)`);
        }
        if (shot.waitFor) await waitFor(page, shot.waitFor);
        await sleep(shot.early ? 50 : 400);
        const file = join(OUT, `${shot.name}-${width}.png`);
        const height = await capture(page, file, width);
        const problems = shot.early ? [] : await evaluate(page, CHECKS);
        let focus = "";
        if (width === 1280 && !shot.early) {
          const walk = await keyboardWalk(page);
          const invisible = walk.filter((s) => !s.outline);
          if (!walk.length) problems.push("Tab reached nothing");
          if (invisible.length) problems.push("focus not visible on: " + invisible.map((s) => s.tag + " " + s.text).join(", "));
          focus = ` | Tab: ${walk.length} stops, outline on all: ${invisible.length === 0}`;
          if (shot.name === "ask-answered") await capture(page, join(OUT, "keyboard-focus-1280.png"), width);
        }
        failures += problems.length;
        const line = `${problems.length ? "FAIL" : "ok  "} ${shot.name}-${width}.png (${width}x${height})${focus}${problems.length ? " | " + problems.join("; ") : ""}`;
        report.push(line);
        console.log(line);
      }
    }
    page.close();
  } finally {
    edge.kill();
    await sleep(500);
    try {
      rmSync(profile, { recursive: true, force: true });
    } catch {
      console.error(`note: could not remove the temporary Edge profile ${profile}`);
    }
  }
  console.log(`${report.length - report.filter((l) => l.startsWith("FAIL")).length}/${report.length} screenshots passed their checks`);
  process.exit(failures ? 1 : 0);
}

main().catch((error) => {
  console.error(`f9-screens failed: ${error.message}`);
  process.exit(1);
});
