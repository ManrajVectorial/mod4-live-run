# T1-F9 — UI refresh

**Status:** done (2026-10-23). Screenshots in `tickets/evidence/F9/`; live at http://127.0.0.1:3014
**Optional:** no. Requested by the product owner before release (2026-10-23)
**Parent:** [T1](T1.md)
**Depends on:** F8
**Decisions it waits on:** none of D0–D9. It keeps D4 (superseded shown and labelled), D5
(refusal text), D6 (conflict notice) and D7 (flat numbered citations) as they are.

The whole front end is refactored so that it looks and feels like a finished internal bank
tool. It covers `/`, `/history`, `/corpus` and `/corpus/[id]`, all on one design: a top bar,
a readable column, and spacing, type and colour from one set of design tokens. The ask page
reads like a conversation. Answers, refusals, passages-only results and errors each look
unmistakably different. The conflict case shows both policies side by side.

## Requirements

REQ-U1, U2, U3, U4, U5, U6, U7, U8, U9, U11, U12, U13, U14, U15, U16, U17 (all the REQ-U
interface requirements except U10, which F7 and F8 made obsolete). REQ-B4 (citations link to
their section) keeps working.

## Criteria (product owner, 2026-10-23; also in T1.md under F9)

- One consistent design across `/`, `/history`, `/corpus` and `/corpus/[id]`:
  - a clear top bar with the product name, Reset, History and Corpus;
  - a readable column;
  - consistent spacing, type and colour from one set of design tokens;
  - light theme only.
- The ask page reads like a conversation: questions on one side, answers on the other, with
  a clear loading state while it thinks.
- An answer shows its text first, then its citations as cards with document, section and
  version, each linking to that section in the corpus page. A superseded source is clearly
  badged.
- A refusal looks unmistakably different from an answer and from an error: its own colour
  and icon, the "not covered" message, and who to ask. A degraded response (AI off) says no
  answer was composed and shows the passages. An error says what to try.
- The conflict case (Q10) shows both policies side by side, with a clear "these policies
  conflict, escalate to Group Legal and Group Operational Risk" notice.
- It works at 375 px wide, is keyboard usable, has visible focus, and passes a basic
  accessibility check (labels, contrast, headings).
- No new libraries: plain CSS (modules or one global stylesheet with tokens). No change to
  the API or the data model.

## Done when

Every page renders correctly in headless Edge at 1280 px and 375 px, with a screenshot of
each saved under `tickets/evidence/F9/`. All frontend tests, the typecheck and the build
pass. The 13-question eval is unchanged.

## Command that checks it

```
cd frontend && npm run typecheck && npm test && npm run build
node scripts/f9-screens.mjs        # headless Edge: screenshots, 375 px, keyboard and a11y checks
cd backend && python -m app.eval   # unchanged: 10/10 answered, 3/3 refused
```

## Files it will touch

- `frontend/app/globals.css`: rewritten. One set of design tokens on `:root` (colour, type,
  spacing, radius, focus); light theme only (U11); every state's look; 375 px layout (U13);
  visible focus.
- `frontend/lib/present.ts`: changed. View models for each result kind (refused, degraded,
  answered, conflict), who-to-ask, error guidance and citation cards. Tested without a
  browser.
- `frontend/lib/present.test.ts`: changed. Tests first for the refusal, degraded and error
  states, citation links and the conflict notice.
- `frontend/lib/tokens.test.ts`: new. Contrast of every text and background token pair
  (WCAG AA).
- `frontend/components/Result.tsx`, `Citation.tsx`, `TopBar.tsx`: rewritten.
- `frontend/components/Icon.tsx`: new. Inline SVG icons, no icon library.
- `frontend/components/Conversation.tsx`: new. One turn list shared by `/` and `/history`.
- `frontend/app/page.tsx`, `app/history/page.tsx`, `app/corpus/page.tsx`,
  `app/corpus/[id]/page.tsx`, `app/layout.tsx`: restyled markup on the shared design.
- `frontend/scripts/f9-screens.mjs`: new. Drives headless Edge over its DevTools protocol
  with Node's built-in WebSocket (no library). It saves the screenshots and checks horizontal
  scrolling, keyboard focus, labels and headings.
- `tickets/evidence/F9/*.png`: new screenshots.

## Not in it

- A dark theme, or any theme switch
- New libraries (no CSS framework, component kit, icon set or test runner)
- Any change to the API, the data model, or the backend's answer, refusal or conflict wording
- New pages or features: same routes, same behaviour, new look
- Authentication; history's `HISTORY_ENABLED` switch stays as it is (FND-9)

## Evidence

## Notes (simplest option taken where the brief was open)

- **The conflict case** is recognised from the D6 notice the API already appends to the
  answer. It starts "These two current policies conflict:". `lib/views.test.ts` reads
  `backend/app/text/conflict.md`, so a wording change there fails the tests rather than
  quietly breaking the layout. No API change.
- **Who to ask** is split out of the fixed D5 refusal text ("Who to ask: expenses → Group
  Finance; …"). A refusal text of any other shape is shown whole.
- **Errors** are shown in the conversation, under the failed question, with what to try
  and a Try again button. The wording of the two suggestions is mine; no team is named
  that the brief doesn't name.
- **One global stylesheet** holds the tokens on `:root`, rather than CSS modules.
  `lib/tokens.test.ts` checks every text and background pair for contrast, checks that
  there's no raw colour outside `:root` and no dark variant, and that focus is visible.
- **T1-review FND-4 is fixed by F9:** citation anchors now carry the message ID, so `[n]`
  jumps to its own answer's card.
- **Screenshots are capped at 3,200 px tall.** The full history list and whole documents
  are longer than that.
- **The history screenshots** show what is stored locally: only test and eval questions
  asked during this build, no real user's question.

## Evidence

**Tests first.** The new view tests failed against the existing code:

```
$ cd frontend && npm test
SyntaxError: The requested module './present.ts' does not provide an export named 'CONFLICT_LEAD'
ℹ tests 18  ℹ pass 15  ℹ fail 3
$ node --test lib/tokens.test.ts      # against the old stylesheet
AssertionError: tokens --on-accent and --accent exist
expected: /:focus-visible\s*\{[^}]*outline:[^;}]*var\(--focus\)/
```

After the view models, 25 of 27 passed; the 2 contrast and focus tests waited on the
stylesheet. After the stylesheet:

```
$ cd frontend && npm run typecheck && npm test && npm run build
typecheck ok
ℹ tests 27  ℹ pass 27  ℹ fail 0
✓ Compiled successfully · ○ /  ○ /corpus  ƒ /corpus/[id]  ○ /history
```

**Unchanged elsewhere.** No backend, dependency or API change:

```
$ git diff --stat -- frontend/package.json frontend/package-lock.json backend/requirements.txt backend/app
(nothing)
$ cd backend && ruff check . && ruff format --check . && python -m pytest -q
All checks passed!  62 files already formatted
129 passed, 4 warnings in 12.91s
$ python -m pytest -q -p no:cacheprovider ci/tests
41 passed in 13.81s
$ python ci/check_scope.py --base plan-approved
Scope check passed: no protected file has changed since refs/tags/plan-approved.
$ python ci/check_licences.py --node-modules frontend/node_modules
Checked 77 packages.  Licence check passed: no copyleft or unknown licences.
```

**Done-when: headless Edge at 1280 px and 375 px, API on 8014 and web on 3014.** Each
check below covers four things:
- no horizontal scroll;
- every field labelled, one `h1`, and no skipped heading level;
- every button and link named, and `lang` set;
- at 1280 px, a Tab walk where every stop must show a visible focus outline.

```
$ cd frontend && F9_BASE_URL=http://127.0.0.1:3014 EDGE_PATH=".../msedge.exe" node scripts/f9-screens.mjs
ok   ask-empty-1280.png (1280x900) | Tab: 7 stops, outline on all: true
ok   ask-empty-375.png (375x900)
ok   ask-loading-1280.png (1280x900)
ok   ask-loading-375.png (375x900)
ok   ask-answered-1280.png (1280x1324) | Tab: 7 stops, outline on all: true
ok   ask-answered-375.png (375x1691)
ok   ask-conflict-q10-1280.png (1280x2046) | Tab: 7 stops, outline on all: true
ok   ask-conflict-q10-375.png (375x3200)
ok   ask-refused-q13-1280.png (1280x900) | Tab: 6 stops, outline on all: true
ok   ask-refused-q13-375.png (375x1025)
ok   ask-conversation-1280.png (1280x2066) | Tab: 7 stops, outline on all: true
ok   ask-conversation-375.png (375x2485)
ok   history-1280.png (1280x3200) | Tab: 8 stops, outline on all: true
ok   history-375.png (375x3200)
ok   history-conversation-1280.png (1280x1867) | Tab: 8 stops, outline on all: true
ok   history-conversation-375.png (375x2190)
ok   corpus-1280.png (1280x900) | Tab: 8 stops, outline on all: true
ok   corpus-375.png (375x1174)
ok   corpus-document-superseded-1280.png (1280x3200) | Tab: 8 stops, outline on all: true
ok   corpus-document-superseded-375.png (375x3200)
ok   corpus-document-section-1280.png (1280x3200) | Tab: 7 stops, outline on all: true
ok   corpus-document-section-375.png (375x3200)
22/22 screenshots passed their checks
```

The passages-only and error states need the API in another state, so they ran separately
on the same build:

```
# API restarted with GENERATION_ENABLED=false (healthz: "generation":"disabled")
$ node scripts/f9-screens.mjs --only=ask-degraded
ok   ask-degraded-1280.png (1280x1795) | Tab: 7 stops, outline on all: true
ok   ask-degraded-375.png (375x2013)
# API stopped (the proxy answers "The service is unavailable. Try again shortly.")
$ node scripts/f9-screens.mjs --only=ask-error
(the 1280 line was cut from my captured output; the run's summary covers it)
ok   ask-error-375.png (375x969)
2/2 screenshots passed their checks
```

The API was then restarted with the normal `.env`.

**The checks caught a real bug.** On the first run, `history-1280` and `history-375`
failed with `horizontal scroll: 10246 > 1280`: a 1,000-character question with no spaces
(asked during the review) widened the page. Fixed with `overflow-wrap: anywhere` on list
items; the re-run passed.

**I looked at the screenshots by eye too:** answered, conflict, refused, passages only,
error, loading, the corpus page at 375 px, and keyboard focus. The automated checks don't
judge the visual result, so the remaining screenshots are there for you to check.

The 27 screenshots in `tickets/evidence/F9/`:
- `ask-empty`, `ask-loading`, `ask-answered`, `ask-conflict-q10`, `ask-refused-q13`,
  `ask-conversation`, `ask-degraded`, `ask-error`;
- `history`, `history-conversation`, `corpus`, `corpus-document-superseded`,
  `corpus-document-section`;
- each of those at `-1280` and `-375`, plus `keyboard-focus-1280` (the focus ring on an
  answer's `[1]`).

**The 13 questions after F9 are unchanged:**

```
$ cd backend && python -m app.eval
Q1 answered 0.723 · Q2 answered 0.733 · Q3 answered 0.582 · Q4 answered 0.666 · Q5 answered 0.557
Q6 answered 0.611 · Q7 answered 0.606 · Q8 answered 0.712 · Q9 answered 0.618 · Q10 answered 0.570
Q11 refused 0.438 · Q12 refused 0.462 · Q13 refused 0.275
eval 10/10 answered, 3/3 refused
```

Every status, score and top-three retrieval matches the run before F9. One thing differs:
in Q10's cited list, this run the model also cited records-retention §4.2. That is the
model's choice between runs; F9 changes no backend code.

`[F9 ui] tests 27/27 frontend + 129/129 backend ok | ruff ok | screens 26/26 + focus | eval 10/10 answered, 3/3 refused | next review addendum`
