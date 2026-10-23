# T1-F5 — The web page

**Status:** done (2026-10-23). The automated checks passed, and the product owner accepted F1 to F5 on 2026-10-23.
**Parent:** [T1](T1.md)
**Depends on:** F4
**Decisions it waits on:** D4, D5, D7

The ask page at `/`: question box, answer with expandable citations, a distinct refusal, a
distinct degraded state, the standing notice and the indexed date. The top bar has the name
and Reset. Light theme.

## Requirements

REQ-U1, U2, U3, U4, U5, U6, U7, U8, U9, U10, U11, U12, U13, U16, U17 · REQ-A10

## Done when (from `features.md`)

With API and web running, open `http://localhost:3000`, ask Q1 and see an answer with an expandable citation reading Travel and Expense Policy, §4.2 Approval thresholds, v3.1, plus the notice and the indexed date; any v3.0 passage shown carries a "Superseded" label; ask Q11 and see a refusal that looks clearly different; the top bar shows only "Policy Assistant" and Reset

## Command that checks it

```
cd frontend && npm run lint && npm run build && npm run dev
```

Then the manual check in the Done-when line, in desktop Chrome and at 375 px wide (A27, A31),
recorded below.

## Files it will touch

- `frontend/package.json`: new. Next.js app, with dependencies listed in the plan
- `frontend/app/layout.tsx`: new. Top bar with name and Reset, light theme only
  (U9, U10, U11)
- `frontend/app/page.tsx`: new. The ask page (U1, U2, U12, U13)
- `frontend/components/`: new. The citation (U3, U16, U17, U8), refusal (U4), degraded
  result (U5) and notice and indexed date (U6, U7)
- `frontend/lib/api.ts`: new. Calls `NEXT_PUBLIC_API_BASE_URL`
- `backend/app/main.py`: changed. CORS from `CORS_ALLOWED_ORIGINS` (A10)

## Not in it

- History or Corpus links and pages (F7, F8)
- Follow-ups within a conversation (F6): Reset clears the page only
- Dark theme
- Browser-automation tests (A31)

## Evidence

**Done-when, automated part:** the production web build (`npm run start`, port 3000) runs with
the API (port 8000). Requests go through the web app's same-origin proxy.

```
--- page (server HTML):
<p class="topbar__name">Policy Assistant</p>
>Reset</button>
<label class="ask__label" for="question">Ask a policy question</label>
History/Corpus links in top bar: 0

--- Q1 through the web app's proxy: answered
answer: Under the Travel and Expense Policy §4.2, claims below £75 are automatically approved on submission with no manager action required [1]. A claim of £75 or more requires line-manager approval before reimbursement, and thresholds are inclusive, so a claim of exactly £75 requires this approval [1]. Claims of £500 or more require line-manager and Department Head approval, and claims of £2,500 or more additionally require Group Finance approval [1].
  [1] Travel and Expense Policy, §4.2 Approval thresholds, v3.1  (current)
  [5] Travel and Expense Policy, §4.1 Approval thresholds, v3.0  (superseded)
indexed: 2026-10-22T23:57:18Z

--- Q11 through the proxy: refused | sources: []
refusal: The policy documents don't cover this, so there is no policy answer to give. Who to ask: expenses → Group Finance; leave, pay and benefits → HR; anything else → Compliance.
```

**The 13 questions after F5:** `eval 10/10 answered, 3/3 refused`.

**Visual check, still to do by you.** I have no browser here. The checks:
- Open `http://localhost:3000` and ask Q1. You should see:
  - the answer, with an expandable citation reading "Travel and Expense Policy, §4.2 Approval
    thresholds, v3.1";
  - the notice and the indexed date;
  - the v3.0 passage under "Earlier version (superseded, for reference only)", with a red
    "Superseded" badge.
- Ask Q11. The refusal should look clearly different: an amber box headed "Not covered by the
  policy documents".
- The top bar should show only "Policy Assistant" and Reset.
- Repeat at 375 px wide (A27). I haven't checked the layout in a browser at either width.

**Tests:**
- Frontend: `npm test` runs `lib/present.test.ts` with Node's built-in runner, 7 passed:
  - U16: the citation label;
  - U17: the superseded label;
  - U2, U8, D4 and D7: cited and earlier sources kept apart;
  - U2: answer markers;
  - U7: the indexed date;
  - U6: the notice;
  - U5: the degraded message.
- Backend: `test_cors.py` (A10), 2 passed. Whole backend suite: 90 passed.
- Other checks: the typecheck and `next build` are clean, and so are the licence check, the
  scope check and the 41 CI-script tests. CI now also runs `npm test`.

**Simplest options taken where the plan was silent:**
- **REQ-U6 notice text, drafted for your approval (A29):** "This tells you what the policy
  says. It is not a decision: an exception or judgement call goes to the team that owns the
  policy."
- **Testing without a browser:** the display logic is pure functions in `lib/present.ts`,
  tested with Node's built-in runner, which needs no new library. `engines.node` is now
  `>=24`, because running `.ts` files directly needs Node 24, which CI uses.
- **Status headings:** "What the policy says" (answered), "Not covered by the policy
  documents" (refused, amber) and "Policy passages only" (degraded, grey, dashed edge).
- **Reset:** reloads the ask page, which clears the question and the result (U9).
- **Answer markers:** `[n]` in an answer links to citation n on the page.
- **A10:** CORS is added only when `CORS_ALLOWED_ORIGINS` lists origins. It is empty locally,
  because the browser only ever calls the web app's proxy.
