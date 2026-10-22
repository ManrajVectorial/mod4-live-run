# T1-F5 — The web page

**Status:** todo
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
