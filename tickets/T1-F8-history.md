# T1-F8 — History *(optional)*

**Status:** done (2026-10-23), built on the product owner's instruction "Finish F7 and F8". You can look at it in a browser at http://127.0.0.1:3014/history
**Optional:** no. Every feature ships (product owner, 2026-10-23)
**Blocked by:** brief Q3 (who may see a user's question) **for release, still open.** `/history` has no
authentication, so anyone who can reach the page sees every stored question. Built, not cleared to
release until Q3 is answered (A33)
**Parent:** [T1](T1.md)
**Depends on:** F6
**Decisions it waits on:** none of D0–D9

`/history`: past conversations newest first, each reopening with the citations stored at
answer time, and a History link in the top bar.

## Requirements

REQ-C7, C8 · REQ-A8, A9 · REQ-U15

## Done when (from `features.md`)

After the F6 run, `curl -s localhost:8000/api/conversations` lists that conversation first, and opening it at `http://localhost:3000/history` shows the same answers and citations as were shown originally

## Command that checks it

```
cd backend && python -m pytest tests/test_api_conversations.py
cd frontend && npm run build && npm run dev
```

Then the manual check in the Done-when line, recorded below.

## Files it will touch

- `backend/app/main.py`: changed. Adds `GET /api/conversations` and
  `GET /api/conversations/{id}` (A8, A9)
- `backend/tests/test_api_conversations.py`: new
- `frontend/app/history/page.tsx`: new (C7, C8)
- `frontend/app/layout.tsx`: changed. Adds the History link (U15)

## Not in it

- Authentication or per-user filtering
- Retention or deletion policy (brief Q2 and Q3, owned outside the team)
- Re-running retrieval for past answers: C8 shows the stored citations

## Notes (simplest option taken where the plan was open)

- **Ports.** The Done-when line says 8000 and 3000. Locally the API runs on 8014 and the web page on
  3014 (product owner), so the check used those.
- **Stored sources.** A citation snapshot (PRD §6) keeps no `effective` or `superseded_by`, so
  history sources hold only the stored fields. A superseded snapshot still shows the plain
  "Superseded" label (U17), without "replaced by v…". Adding the two columns would change the agreed
  data model (rule 4), so it was not done.
- **Opening one conversation** is `/history?c=<conversation_id>` on the same page, rather than a
  new route.
- **Files beyond the list above:** `backend/app/history.py` (the two queries), `frontend/lib/history.ts`,
  `frontend/lib/present.ts` (history types, `historyTurns`, the History link in `TOP_BAR_LINKS`) and
  `frontend/lib/corpus.ts` (its fetch helper takes a not-found message). The History link is in
  `TOP_BAR_LINKS`, shown by `components/TopBar.tsx`, not in `layout.tsx`, which F7 had already set up.
- **List size.** No pagination (PRD §5.4 [ASSUMED]).

## Evidence

Tests written first and shown failing:

```
$ cd backend && .venv/Scripts/python -m pytest -q tests/test_api_conversations.py
6 failed in 1.56s
$ cd frontend && npm test        # against the committed present.ts
SyntaxError: The requested module './present.ts' does not provide an export named 'historyTurns'
ℹ tests 1  ℹ pass 0  ℹ fail 1
```

After the code:

```
$ cd backend && .venv/Scripts/python -m pytest -q tests/test_api_conversations.py
6 passed in 1.16s
$ cd backend && ruff check . && ruff format --check . && bandit -q -r app && python -m pytest -q
All checks passed!  62 files already formatted  (bandit: no findings)
123 passed, 3 warnings in 8.15s
$ python -m pytest -q -p no:cacheprovider ci/tests
41 passed in 12.41s
$ python ci/check_scope.py --base plan-approved
Scope check passed: no protected file has changed since refs/tags/plan-approved.
$ cd frontend && npm run typecheck && npm test && npm run build
ℹ tests 12  ℹ pass 12  ℹ fail 0
Route (app) … ○ /history
```

Done-when, against the local API (8014) and web page (3014). The script replays the F6 follow-up
set (`backend/eval/followups.md`), keeps what each response showed, then reads it back from history:

```
$ cd backend && PYTHONPATH=. .venv/Scripts/python f8_check.py      # scratch script, not committed
C1 answered
C2 answered
C3 answered
C4 refused
C5 refused
C6 refused
top of /api/conversations: 45e3ad2e-47d2-4d11-b671-4012c0accab6 == last F6 conversation: True
  first_question: What happens if a KYC refresh is more than 90 days overdue? | message_count: 4 | statuses: ['answered', 'refused']
history matches what was shown: 6/6 conversations (status, answer, refusal, sources)
```

The page itself, rendered by headless Edge (`msedge --headless=new --dump-dom`) and reduced to its text:

```
/history -> History | What happens if a KYC refresh is more than 90 days overdue? | 23 Oct 2026, 01:57 UTC · 2 answers (answered, refused) | Can I fly business class on a six-hour flight? | …

/history?c=45e3ad2e-47d2-4d11-b671-4012c0accab6 -> ← All conversations | Past conversation | Shown as it was answered at the time. | You asked: | What happens if a KYC refresh is more than 90 days overdue? | What the policy says | If a KYC refresh is more than 90 days overdue, the relationship is suspended pending completion | [1] | . Under this section, only Financial Crime Compliance may lift such a suspension | [1] | . | Sources | [1] | Client Onboarding and KYC Refresh Policy, §6.4 Overdue refresh, v2.4 | … | Open this section in the document | … | You asked: | What is our policy on cryptocurrency held by clients? | Not covered by the policy documents | The policy documents don't cover this, so there is no policy answer to give. Who to ask: expenses → Group Finance; leave, pay and benefits → HR; anything else → Compliance. |
```

I checked the page as rendered text, not by eye in a browser.

The 13 questions after F8 (`cd backend && python -m app.eval`, full table in `eval-results.md`):

```
eval 10/10 answered, 3/3 refused
```

The follow-up set after F8 (`cd backend && python -m app.followup_eval`):

```
| C1 | answer | And does a claim of exactly that amount need it? | answered | 0.7182 | PASS |
| C2 | answer | And for Singapore? | answered | 0.6642 | PASS |
| C3 | answer | And for a standard-risk client? | answered | 0.5374 | PASS |
| C4 | refuse | Can I expense my partner's flight? | refused | 0.4229 | PASS |
| C5 | refuse | How many days of paid parental leave am I entitled to? | refused | 0.2750 | PASS |
| C6 | refuse | What is our policy on cryptocurrency held by clients? | refused | 0.4825 | PASS |
followups 6/6 passed
```

C1 and C4 score a little differently from the F6 run (0.7225 and 0.4690). The rewrite is not
exactly repeatable even at temperature 0, so the rewritten wording, and with it the score, can
shift between runs. No case changed side of the threshold.

`[F8 history] tests 123/123 + 12/12 ok | ruff ok | eval 10/10 answered, 3/3 refused | followups 6/6 | next push`

## Change after review (2026-10-23, T1-review FND-9)

- **History now has a switch.** `HISTORY_ENABLED` is required at startup.
- **When it's false:**
  - `/api/conversations` and `/api/conversations/{id}` don't exist (404 `not_found`);
  - `/history` says history is switched off;
  - every exchange is still recorded.
- **Where it's on:** only in the local `.env`. Keep it false in any deployment until brief Q3
  is answered.
- **The PRD:** the setting isn't in PRD §8 (locked).
- **Evidence:** in `T1-review.md`, under "Fixes".
