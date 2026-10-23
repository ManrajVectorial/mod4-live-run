# T1 review — work/build against main

**Date:** 2026-10-23
**Scope:** everything on `work/build` (`fa1434d`) that is not on `main` (`b056bc6`, the start
commit). That is 111 files. The corpus is excluded, since it was supplied and is protected.
**Fixes made:** FND-1 and FND-9 (high), on the product owner's instruction "fix every high
finding". FND-29 (high) is not fixed: it waits on a design decision. Every finding has a
**Decision** line, and the full list is in "Decisions" at the end.
**How to read it:** findings are numbered FND-1 onwards across the five passes. Each gives
where it is, how serious it is (high, medium or low) and what I'd do. "Checked" means I ran it
or read it in this review. "By reading" means I read the code but didn't reproduce the
behaviour. Anything I didn't look at is marked "I haven't checked".

## Results before the review

### Whole test suite

```
$ cd backend && ruff check . && ruff format --check .
All checks passed!
62 files already formatted
$ cd backend && bandit -q -r app
(no findings, exit 0)
$ cd backend && python -m pytest -q
123 passed, 5 warnings in 15.11s        (a second run: 123 passed, 3 warnings; see FND-20)
$ python -m pytest -q -p no:cacheprovider ci/tests
41 passed in 12.20s
$ python ci/check_scope.py --base plan-approved
Scope check passed: no protected file has changed since refs/tags/plan-approved.
$ python ci/check_licences.py --node-modules frontend/node_modules
Checked 77 packages.
Licence check passed: no copyleft or unknown licences.
$ cd frontend && npm run typecheck && npm test
ℹ tests 12  ℹ pass 12  ℹ fail 0
```

I didn't rebuild the frontend in this review, because a rebuild would have replaced the
running server's files. `npm run build` passed in CI on `fa1434d` (run 39887215629, all five
jobs green).

### The 13 questions, against the local API (127.0.0.1:8014)

```
$ cd backend && python -m app.eval
Q    status    top score  first source                       question
Q1   answered  0.723      travel-expense-policy-v3.1 §4.2    What is the approval threshold for a travel expense claim?
Q2   answered  0.733      travel-expense-policy-v3.1 §4.2    Does a claim of exactly £75 need approval?
Q3   answered  0.582      travel-expense-policy-v3.1 §5.2    Can I fly business class on a six-hour flight?
Q4   answered  0.666      travel-expense-policy-v3.1 §6.2    What is the accommodation cap for a night in Singapore?
Q5   answered  0.557      client-onboarding-kyc-v2.4 §6.1    How often do we refresh KYC for a high-risk client?
Q6   answered  0.611      client-onboarding-kyc-v2.4 §6.4    What happens if a KYC refresh is more than 90 days overdue?
Q7   answered  0.606      client-onboarding-kyc-v2.4 §4.2    At what ownership percentage do we identify beneficial owners under enhanced due diligence?
Q8   answered  0.712      records-retention-v4.0 §4.2        How long do we keep client correspondence?
Q9   answered  0.618      outsourcing-third-party-v1.8 §4.1  Who can approve a critical outsourcing arrangement?
Q10  answered  0.570      outsourcing-third-party-v1.8 §6.4  A provider holds our client correspondence. How long can they keep it after we terminate?
Q11  refused   0.438      —                                  Can I expense my partner's flight if they travel with me?
Q12  refused   0.462      —                                  What is our policy on cryptocurrency held by clients?
Q13  refused   0.275      —                                  How many days of paid parental leave am I entitled to?

eval 10/10 answered, 3/3 refused
```

The full table, with the cited sections, is in `eval-results.md` (rewritten by this run).

### Do the functions and libraries we call exist in the installed versions?

I checked this once for the whole codebase, and each pass below draws on it.

- **Backend.** Installed: Python 3.12.1, fastapi 0.161.1, starlette 1.9.0, uvicorn 0.54.0,
  pydantic 2.14.1, pydantic-settings 2.16.1, sqlalchemy 2.1.6, pg8000 1.31.5,
  qdrant-client 1.20.0, openai 3.37.0, pyyaml 6.0.3, python-dotenv 1.2.4. Each direct pin
  matches `T1-plan.md` §2.
  - A script imported every name the app uses and inspected the signature of every call
    whose keywords we pass. That covered 88 names and parameters, and none is missing.
  - The checked calls include `QdrantClient.query_points`, `scroll`, `upsert`, `delete`,
    `collection_exists`, `get_collection`, `create_collection` and `get_collections`, and the
    `OpenAI(default_headers=, max_retries=, timeout=)` constructor.
  - They also include `chat.completions.create(extra_body=, max_tokens=, temperature=)`,
    `embeddings.create`, `pg8000.dbapi.connect(timeout=)`, `datetime.UTC`, `asyncio.to_thread`
    and the `SettingsConfigDict` keys.
  - `openai.APITimeoutError` is a subclass of `APIConnectionError`, as `generation.py:103`
    assumes. `asyncio.TimeoutError is TimeoutError` holds, which `health.py:134` relies on.
    `uvicorn --factory` exists.
- **Frontend.** Installed: Node 24.20.0, next 16.4.2, react and react-dom 19.3.1,
  typescript 5.9.3.
  - `next/navigation` exports `useSearchParams`, and React has `Suspense`, `useState` and
    `useEffect`.
  - Node has `Response.json`, `--env-file-if-exists` and type stripping for `node --test`.
  - The config keys `agentRules`, `output`, `poweredByHeader` and `images.unoptimized` are in
    Next's `config-shared.d.ts`. `tsc --noEmit` also passes on the typed config object.

## 1. Correctness: does it do what T1.md says?

**T1 acceptance criteria, checked live today:**

| Criterion | What I checked | Result |
|---|---|---|
| Normal | Q1 answered, citing Travel and Expense Policy §4.2, v3.1 | holds |
| Edge (£75) | Asked "exactly £75", "£74.99" and "£75.01" through the API | holds: "a claim of exactly £75 requires line-manager approval… thresholds are inclusive [1]", £74.99 is "automatically approved", and £75.01 needs approval. But see FND-2 |
| Error (model unavailable) | `GENERATION_TIMEOUT_SECONDS=0.01`, first question | holds: HTTP 200, `degraded/provider_timeout`, 5 passages |
| Error, on a follow-up | The same, on "And for Singapore?" | **fails: FND-1** |
| Not allowed | Q13 (parental leave): `refused`, `sources` empty, who-to-ask text names HR | holds |
| All 13 on one run | Above | 10/10 answered, 3/3 refused |

**Boundaries and empty input, checked through the API:**
- `"   "` → 422 `question_blank`.
- 1001 characters → 422 `question_too_long`.
- 1000 characters → accepted (then refused at score 0.196).
- A score equal to the threshold is refused: `refusal.py:14` uses `>`, which matches ADR-001's
  "strictly above".
- Citation markers must be in `1..n` (`citations.py:21`).
- A follow-up's earlier-version markers start after the cleared passages (`ask.py:177`), so
  they can't collide.

**FND-1 — A follow-up asked while the chat model is down is refused as "not covered" instead
of showing passages.** High.
- **Where:** `backend/app/ask.py:111-121` and `129-132`.
- **Checked:** asked "What is the accommodation cap for a night in London?" (answered), then
  "And for Singapore?" with `GENERATION_TIMEOUT_SECONDS=0.01`.
- **What happened:**
  - The log reads `rewrite failed (RewriteFailed: APITimeoutError); searching as asked`.
  - The bare follow-up scores 0.3447, below the threshold.
  - The response is `refused` with no sources.
- **Why it matters:** the staff member is told the policy doesn't cover something it does.
  That breaks T1's Error criterion ("still shows the relevant policy passages"). It is also
  the failure the brief says the product must not have.
- **What I'd do:**
  - When the rewrite fails because the provider erred or timed out (not because the reply
    wasn't a question), don't apply the refusal rule to the unrewritten follow-up.
  - Instead, return `degraded` with passages retrieved some other way, for example on the
    previous question joined to the follow-up (the original D9).
  - This changes D9 amendment 2's fallback, so it is your decision.
- **Decision:** **Fixed** in this commit (product owner: fix every high finding). With the provider down, a follow-up is searched joined with the question before it, judged by the same rule and threshold, and returns `degraded` with passages, never "not covered" for that reason. An unusable reply still falls back to the question as asked. Evidence below, under "Fixes".

**FND-2 — The £75 Edge criterion is only ever checked by reading the model's answer.**
Medium.
- **Where:** `backend/app/eval.py:89-95`. Every backend test uses a fake model.
- **The gap:**
  - The eval passes Q2 when it is `answered` and cites §4.2.
  - It would still pass if the model wrote "a claim of exactly £75 does not need approval".
  - Today's answer is correct (checked above), but nothing would catch a regression.
- **What I'd do:** add an answer-content check for Q2 to the eval, for example that the
  answer says exactly £75 requires approval. Whether a phrase match is enough, or a reviewed
  judgement is needed, is for you to decide.
- **Decision:** Deferred (accepted recommendation): today's live answer is correct; the content check needs a choice between a phrase match and a reviewed judgement, so it belongs to the next testing pass.

**FND-3 — The model answers the rewritten question, which is never shown or stored.**
Medium.
- **Where:**
  - `ask.py:148` passes `search_text`, not the question as asked, to the generator.
  - `ask.py:191-224` and `db.py:51-67` store neither the rewritten text nor the rewrite
    prompt version (`rewrite-v2`).
- **Why it matters:**
  - If a rewrite drifts, the answer is to a question the person didn't ask, and nothing on
    screen shows it.
  - Afterwards the record can't show what was searched, or which rewrite prompt produced it.
  - Answers are meant to be traceable (brief §7, REQ-G3).
- **What I'd do:** store the search text and the rewrite prompt version with each assistant
  message, and consider showing "Searched for: …". Both change the agreed data model or the
  API, so they need your approval (rule 4).
- **Decision:** Deferred (accepted recommendation): storing the search text and rewrite version changes the agreed data model, which needs approval (rule 4).

**FND-4 — Citation anchors repeat across turns, so `[n]` can jump to the wrong answer's
source.** Low.
- **Where:** `frontend/components/Citation.tsx:10` (`id="source-N"`) and
  `frontend/components/Result.tsx:28` (`href="#source-N"`).
- **Checked:** rendered `/history?c=f5e8f6c1…` (two answered turns) with headless Edge. The
  page has two elements with `id="source-2"`, so the second answer's `[2]` jumps to the first
  answer's source. The ask page renders the same components.
- **What I'd do:** prefix the id with the message ID.
- **Decision:** Deferred (accepted recommendation): it only misdirects a scroll in multi-turn conversations; a one-line fix with the next frontend change.
- **Update (F9, `c9773c7`):** fixed. Citation anchors carry the message ID; see the F9 addendum.

**FND-5 — The question-length message is off by one, and length is counted before
trimming.** Low.
- **Where:** `ask.py:85-89`.
- **What happens:**
  - A 1000-character question is accepted, but the error says "Keep the question under 1000
    characters".
  - `len(question)` is taken before `strip()`, so surrounding spaces count towards the limit.
- **What I'd do:** say "1000 characters or fewer", and measure after stripping.
- **Decision:** Deferred (accepted recommendation): wording only, with no wrong answer or refusal; fix with the next API change.

**FND-6 — A request body that isn't valid UTF-8 gets "Enter a question."** Low.
- **Where:** `main.py:231-236`, pinned by `tests/test_api_ask.py:95`.
- **Checked:** my shell sent "£" as the Latin-1 byte `a3` and got back 422 `question_blank`,
  "Enter a question."
- **Why it matters:** the agreed behaviour is a 422, but the message misleads anyone who did
  type a question.
- **What I'd do:** use a distinct message. That changes the agreed API error, so it needs
  your approval.
- **Decision:** Accepted (accepted recommendation): the 422 is the agreed contract, pinned by a test, and only a client sending non-UTF-8 sees it.

**FND-7 — Superseded sources in history lose "replaced by vX".** Low.
- **Where:** `backend/app/history.py`, `_source()`.
- **Why:** the citation snapshot (PRD §6) has no `superseded_by`. This is already recorded in
  `T1-F8-history.md`.
- **What I'd do:** add the column only if you approve a data-model change.
- **Decision:** Accepted (accepted recommendation): U17 still holds ("Superseded" is shown), and the fuller label needs a data-model change.

**FND-8 — The 5-message follow-up context can start with an answer whose question was
dropped.** Low.
- **Where:** `db.py:132-142` and `conversation.py:26-29`.
- **Why:** D8 counts questions and answers separately, and 5 is odd. From the third exchange
  on, the oldest message the models see is an answer with no question.
- **What I'd do:** count whole exchanges, or use an even number. Either changes D8, so it is
  your decision.
- **Decision:** Accepted (accepted recommendation): D8 is a decided value, and the follow-up set passes 6/6 with it.

**FND-37 — The refusal threshold is tuned on only 13 questions.** Raised and decided by the
product owner on 2026-10-23; it isn't one of the 36 I found.
- **Where:** `REFUSAL_THRESHOLD=0.5092` (D2), set at the midpoint of the gap in the 13-question
  set. `T1-plan.md` already records that 4 of 26 rephrased variants land on the wrong side.
- **Decision:** **Accepted by the product owner:** a known limitation. Doing better needs more
  test questions.

## 2. Security and privacy

**Checked and found clean:**
- **Secrets in git history:**
  - `.env` was never committed, in any branch.
  - I searched the full history of every branch (`git log --all -p`) for the real
    `OPENROUTER_API_KEY`, `POSTGRES_PASSWORD` and `DATABASE_URL` password values. Each was
    found 0 times. I compared the values in a script and never printed them.
  - There are no key-shaped strings (`sk-…`, `AKIA…`, PEM blocks). The only "secrets" in
    history are the fake ones in tests.
- **Secrets in code:** settings are `SecretStr` (`settings.py:31, 58, 60`). `SettingsError`
  names variables, never values. The health probe never reads or logs the `/key` response.
- **Question text in logs:**
  - The live API log (`.api.log`, 124 lines at `LOG_LEVEL=INFO`, including today's eval run)
    contains no question text and no SQL. `test_logging.py` covers DEBUG with a marker
    question.
  - The openai, httpx and httpx2 loggers are held at WARNING (`logging.py:10`).
  - The Next proxy logs only error names (`route.ts:19, 41`).
- **The web page:** no `dangerouslySetInnerHTML` or `innerHTML`, and React escapes answer
  and passage text.
- **The proxy:** two path-traversal attempts through it (`/api/..%2fopenapi.json` and
  `/api/a/%2e%2e/%2e%2e/openapi.json`) both returned 404.
- **Deployment surfaces:** CORS is off unless origins are listed, the container runs as a
  non-root user (`Dockerfile:18-19`), and Compose binds to 127.0.0.1 only.
- **Known vulnerabilities:** `npm audit` reports 0, with and without dev dependencies.
  **I haven't checked the Python packages for known vulnerabilities.** No audit tool is
  installed, and adding one (for example pip-audit) needs your approval.

**Where the question text goes:**
1. **Postgres:** stored in plain text, permanently. Today: 230 questions in 204
   conversations, the oldest from 00:07 UTC (`messages.content`).
2. **OpenRouter, then the model vendor:**
   - the question, or its rewrite, is embedded (`embeddings.py:26`);
   - on a follow-up, the question plus the last 5 messages go to the rewrite call
     (`rewrite.py:50-63`);
   - the rewrite plus the passages plus the same context go to the answer call
     (`generation.py:89-102`).
3. **Back out over HTTP:**
   - to anyone who calls `GET /api/conversations` or `/api/conversations/{id}`;
   - to anyone who opens `/history`.
4. **Not** written to logs, and not put in any URL.

**FND-9 — Every stored question is readable, unauthenticated, by anyone who can reach the
API or the web page.** High.
- **Where:** `main.py:212-225` and `frontend/app/history/page.tsx`.
- **Why it matters:** brief Q3 (who may see a user's question) is unanswered, and F8 is
  recorded as blocked for release on it.
- **What I'd do:** don't deploy with these routes reachable until Q3 is answered. If a deploy
  has to happen first, add a setting that switches the history routes off.
- **Decision:** **Fixed** in this commit. A required `HISTORY_ENABLED` setting: when false, the history routes don't exist (404 `not_found`) and `/history` says history is switched off; questions are still recorded (REQ-C1). It is true only in the local `.env`; keep it false in any deployment until brief Q3 is answered. Authentication stays out of T1's scope. Evidence below, under "Fixes".

**FND-10 — Question text and conversation context go to a third party, whose handling I
haven't checked.** Medium.
- **Where:** see "Where the question text goes", point 2.
- **What I haven't checked:** the OpenRouter account's data-retention and training settings,
  and which upstream vendors it routes to.
- **What I'd do:** confirm both and record them with brief Q3. This one isn't mine to decide.
- **Decision:** Deferred (accepted recommendation): it belongs with brief Q3, which is owned outside the team; nothing is deployed yet.

**FND-11 — Questions are kept forever, with no retention or deletion.** Medium.
- **Where:** `db.py`. There is no delete path and no expiry.
- **Why:** brief Q2 (retention) is open.
- **What I'd do:** a retention decision from the owner of Q2, then a scheduled purge.
- **Decision:** Deferred (accepted recommendation): retention is brief Q2, owned outside the team; nothing is deployed yet.

**FND-12 — `/api/ask` has no rate limit or per-client cap.** Medium.
- **Where:** `main.py:227`.
- **Why it matters:** each ask makes up to 3 paid provider calls (embedding, rewrite, answer).
  An unauthenticated caller can run up cost, and the 40-thread pool can be exhausted.
- **What I'd do:** a limit at the platform edge or in the proxy. A library for it would need
  your approval.
- **Decision:** Deferred (accepted recommendation): to the deployment stage, where the platform's own limits can be used before any new library is considered.

**FND-13 — The API publishes its docs.** Low.
- **Where:** `main.py:141`, which uses FastAPI's defaults.
- **Checked:** `/docs`, `/redoc` and `/openapi.json` all return 200.
- **What I'd do:** turn them off outside development, through a setting.
- **Decision:** Deferred (accepted recommendation): a deployment-stage setting; the docs show nothing a public repo doesn't already.

**FND-14 — No security headers on the web page.** Low.
- **Where:** `frontend/next.config.ts`.
- **Checked:** `curl -I` on `/` shows no CSP, frame-ancestors or X-Frame-Options, nosniff or
  HSTS header.
- **What I'd do:** add `headers()` to `next.config.ts`.
- **Decision:** Deferred (accepted recommendation): set at the deployment stage, together with the frontend's start command (FND-23).

**FND-15 — The repository is public, and history keeps three stray files.** Low.
- **Where:** commit `6eb8b85`.
- **Checked:**
  - `gh repo view` reports `ManrajVectorial/mod4-live-run` as `PUBLIC`.
  - `.api.log`, `.eval-run2.txt` and `backend/corpus.zip` are untracked now, but still in
    history.
  - They hold a 7-line API log, eval output (the published eval questions) and a copy of the
    corpus. None of it is a secret or a real user's question.
- **What I'd do:** leave history as it is, since rewriting a pushed public branch is
  destructive. Keep staging explicit paths, as now.
- **Decision:** Accepted (accepted recommendation): nothing sensitive is in those files, and rewriting a pushed public history is destructive.

**FND-16 — Citations are checked for shape, not support.** Low.
- **Where:** `citations.py:18-21`.
- **The gap:** a `[1]` that points at a real passage passes even if passage 1 doesn't support
  the sentence. A question written to steer the model (prompt injection) could exploit that.
  The refusal rule still runs first, so it can't make an unsupported question answerable.
- **What I'd do:** keep this as an open risk, and spot-check answers in the eval (see FND-2).
- **Decision:** Accepted (accepted recommendation): an inherent residual risk; the refusal rule still runs first, and FND-2's content check will spot-check answers.

## 3. Maintainability

**Errors swallowed silently:** none found. I checked each broad `except`:
- `health.py:137` logs the type and reports `unreachable`.
- `ingest.py:54` re-raises as `IngestError` with the type.
- `followup_eval.py:75` records an error row, and the run then fails.
- `ask.py:114` logs a warning and falls back.
- `eval.py`'s HTTP errors show up as error rows.
- In the frontend, `.catch(() => null)` on `response.json()` (`api.ts:19`, `corpus.ts:20`)
  still leads to a shown error message, never a blank result.

**FND-17 — An unexpected error leaves no trace you can follow.** Medium.
- **Where:** `main.py:177-181`, and `ask.py:230`, which logs only on success.
- **Checked:** with Qdrant, the provider or Postgres down, the only log line is
  `unhandled error: ResponseHandlingException` (or `APIConnectionError`, or `InterfaceError`).
  It has no request ID, no code location and no `ask` line.
- **Why it matters:** NFR-5 ("every `/api/ask` call logs one line") isn't met on error
  paths, and a production 500 is hard to diagnose.
- **What I'd do:**
  - Create the request ID in the route and log it on every path.
  - Add the failing module and line from the traceback, without its local values, which can
    hold the question.
- **Decision:** Deferred (accepted recommendation): diagnostics only, with no wrong output; fix before deployment, since NFR-5 applies there.

**FND-18 — Small duplications.** Low.
- **Where:**
  - the OpenAI client is built three times (`embeddings.py:16`, `generation.py:77`,
    `rewrite.py:38`);
  - the reasoning switch twice (`generation.py:94`, `rewrite.py:55`);
  - the `conversation_not_found` error three times (`ask.py:80`, `ask.py:228`, `main.py:224`);
  - the turn-list markup twice (`frontend/app/page.tsx:45-54`,
    `frontend/app/history/page.tsx:85-94`);
  - the date formatters twice (`present.ts:90`, `history/page.tsx:13`).
- **What I'd do:** one small shared helper for each.
- **Decision:** Accepted (accepted recommendation): each copy is short and readable; merge them when that code is next touched.

**FND-19 — Some values are typed into code instead of read from settings.** Low.
- **Where:**
  - the rewriter's `temperature=0` (`rewrite.py:60`) ignores `CHAT_TEMPERATURE`, which is
    deliberate and commented;
  - the rewriter reuses `CHAT_MAX_TOKENS` (600) for a one-line reply (`main.py:101`);
  - the scroll page size of 256 appears twice (`vector_store.py:81`, `corpus_index.py:38`);
  - the OpenRouter-specific `/key` path is fixed in code (`health.py:75`).
- **Rule 5:** none is a model name or threshold. The `/key` path is part of a URL.
- **What I'd do:** move them into named settings or constants. Whether the rewriter gets its
  own settings is your decision.
- **Decision:** Accepted (accepted recommendation): none is a model name or threshold, and the rewriter's temperature 0 is deliberate and commented.

**FND-20 — Some tests reach the network, so the warning count varies.** Low.
- **Where:** constructing a `QdrantClient` checks the server version over the network
  (`qdrant_client/qdrant_remote.py:266-277`). This happens at `create_app` (probes) and in
  `test_healthz.py` and `test_conversation.py`.
- **Checked:** two runs gave 5 and 3 warnings: "Failed to obtain server version".
- **What I'd do:** pass `check_compatibility=False` in tests, or inject the client.
- **Decision:** Deferred (accepted recommendation): test hygiene; the network call only adds a warning and can't make a test pass falsely.

**FND-21 — No type checker runs on the backend.** Low.
- **Where:** `backend/requirements-dev.txt` and `.github/workflows/ci.yml`. The frontend
  does run `tsc`.
- **What I haven't checked:** the editor's Pyright reported errors in `main.py` during F8,
  including an argument count on `run_in_threadpool`. Some of these were clearly stale (it
  said `app.rewrite` didn't exist). I haven't checked whether any are real.
- **What I'd do:** add a type checker to CI. That is a new library, so it needs your
  approval.
- **Decision:** Deferred (accepted recommendation): a type checker is a new library and needs approval (rule 4).

**FND-22 — Builds aren't fully reproducible.** Low.
- **Where:**
  - `requirements.txt` pins direct dependencies only, with no lock and no hashes, so 44 of
    the 58 installed packages float;
  - `Dockerfile:2` uses `python:3.12-slim` by tag, not by digest;
  - locally we run 3.12.1, while CI takes the latest 3.12.
- **What I'd do:** a constraints file from `pip freeze`, which needs no new library, and a
  digest-pinned base image.
- **Decision:** Deferred (accepted recommendation): to the deployment stage, when the image is first built for release.

**FND-23 — `npm start` doesn't match `output: "standalone"`.** Low.
- **Where:** `frontend/package.json:12` and `next.config.ts:5`.
- **Checked:** Next prints `"next start" does not work with "output: standalone"`
  (`.web.log`), although it still serves.
- **What I'd do:** settle the frontend's start command at the deployment stage.
- **Decision:** Deferred (accepted recommendation): the frontend's deploy command is settled at the deployment stage.

**FND-24 — T1.md is out of date.** Low.
- **Where:** `tickets/T1.md:3` (still "todo"), lines 86-99 (the D0–D9 table is blank, while
  the decisions are in `T1-plan.md`) and line 101 (Evidence is empty).
- **What I'd do:** fill in the decisions and the evidence links, and set its status once
  you accept this review.
- **Decision:** Deferred (accepted recommendation): T1.md is updated at the verification stage, once the decisions on this review are final.

## 4. Licences and origin

**Rule 7 result:** no package carries GPL, AGPL, LGPL, SSPL or EUPL, either by my listing
below or by `ci/check_licences.py`. Every direct dependency matches `T1-plan.md` §2 in name
and version.

**Backend: every package in `backend/.venv`** (58, from `pip-licenses --with-system`).

All of them come from PyPI. No custom index is configured: `pip config get global.index-url`
reports "No such key". Packages marked "dev" come from `requirements-dev.txt`. The rest are
runtime packages.

| Package | Version | Licence | Why it's here | Source URL |
|---|---|---|---|---|
| fastapi | 0.161.1 | MIT | direct | github.com/fastapi/fastapi |
| uvicorn | 0.54.0 | BSD-3-Clause | direct | uvicorn.dev |
| pydantic-settings | 2.16.1 | MIT | direct | github.com/pydantic/pydantic-settings |
| SQLAlchemy | 2.1.6 | MIT | direct | sqlalchemy.org |
| pg8000 | 1.31.5 | BSD | direct | codeberg.org/tlocke/pg8000 |
| qdrant-client | 1.20.0 | Apache-2.0 | direct | github.com/qdrant/qdrant-client |
| openai | 3.37.0 | Apache-2.0 | direct | github.com/openai/openai-python |
| PyYAML | 6.0.3 | MIT | direct | pyyaml.org |
| python-dotenv | 1.2.4 | BSD-3-Clause | direct (pydantic-settings reads `.env` with it) | github.com/theskumar/python-dotenv |
| pytest | 9.1.1 | MIT | dev | docs.pytest.org |
| httpx | 0.28.1 | BSD | dev (also used by qdrant-client) | github.com/encode/httpx |
| ruff | 0.17.2 | MIT | dev | docs.astral.sh/ruff |
| bandit | 1.9.4 | Apache-2.0 | dev | bandit.readthedocs.io |
| pip-licenses | 5.5.5 | MIT | dev | (PyPI) |
| starlette | 1.9.0 | BSD-3-Clause | fastapi | github.com/Kludex/starlette |
| pydantic | 2.14.1 | MIT | fastapi, pydantic-settings | github.com/pydantic/pydantic |
| pydantic_core | 2.50.1 | MIT | pydantic | github.com/pydantic |
| annotated-types | 0.8.0 | MIT | pydantic | github.com/annotated-types/annotated-types |
| typing-inspection | 0.4.4 | MIT | pydantic | github.com/pydantic/typing-inspection |
| typing_extensions | 4.16.0 | PSF-2.0 | several | github.com/python/typing_extensions |
| annotated-doc | 0.0.5 | MIT | fastapi | github.com/fastapi/annotated-doc |
| opentelemetry-api | 1.45.1 | Apache-2.0 | fastapi | github.com/open-telemetry/opentelemetry-python |
| anyio | 4.15.1 | MIT | starlette, httpx | anyio.readthedocs.io |
| sniffio | 1.3.1 | Apache-2.0 / MIT | anyio | github.com/python-trio/sniffio |
| idna | 3.20 | BSD-3-Clause | httpx | github.com/kjd/idna |
| h11 | 0.16.0 | MIT | uvicorn, httpcore | github.com/python-hyper/h11 |
| click | 8.5.0 | BSD-3-Clause | uvicorn | github.com/pallets/click |
| colorama | 0.4.6 | BSD | click (Windows) | github.com/tartley/colorama |
| httpcore | 1.0.9 | BSD-3-Clause | httpx | encode.io/httpcore |
| httpx2 | 2.16.0 | BSD-3-Clause | openai | github.com/pydantic/httpx2 |
| httpcore2 | 2.16.0 | BSD-3-Clause | httpx2 | github.com/pydantic/httpx2 |
| truststore | 0.10.5 | MIT | httpx2, httpcore2 | github.com/sethmlarson/truststore |
| jiter | 0.17.0 | MIT | openai | github.com/pydantic/jiter |
| h2 | 4.4.1 | MIT | httpx[http2] (qdrant-client) | github.com/python-hyper/h2 |
| hpack | 4.2.0 | MIT | h2 | github.com/python-hyper/hpack |
| hyperframe | 6.1.0 | MIT | h2 | github.com/python-hyper/hyperframe |
| grpcio | 1.84.1 | Apache-2.0 | qdrant-client (unused: we use REST) | grpc.io |
| protobuf | 7.36.2 | BSD-3-Clause | qdrant-client | developers.google.com/protocol-buffers |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | qdrant-client | numpy.org |
| portalocker | 4.4.1 | BSD-3-Clause | qdrant-client | github.com/wolph/portalocker |
| urllib3 | 2.8.0 | MIT | qdrant-client | github.com/urllib3/urllib3 |
| certifi | 2026.10.19 | **MPL-2.0** | httpx | github.com/certifi/python-certifi |
| scramp | 1.4.18 | MIT-0 | pg8000 | codeberg.org/tlocke/scramp |
| asn1crypto | 1.5.1 | MIT | scramp | github.com/wbond/asn1crypto |
| python-dateutil | 3.0.0 | Apache-2.0 / BSD | pg8000 | github.com/dateutil/dateutil |
| six | 1.17.0 | MIT | python-dateutil | github.com/benjaminp/six |
| tzdata | 2026.5 | Apache-2.0 | (time zones) | github.com/python/tzdata |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | pytest | github.com/pypa/packaging |
| iniconfig | 2.3.1 | MIT | pytest | github.com/pytest-dev/iniconfig |
| pluggy | 1.7.0 | MIT | pytest | github.com/pytest-dev/pluggy |
| Pygments | 2.21.0 | BSD-2-Clause | pytest, rich | pygments.org |
| stevedore | 5.9.1 | Apache-2.0 | bandit | docs.openstack.org/stevedore |
| rich | 15.0.0 | MIT | bandit | github.com/Textualize/rich |
| markdown-it-py | 4.2.0 | MIT | rich | github.com/executablebooks/markdown-it-py |
| mdurl | 0.1.2 | MIT | markdown-it-py | github.com/executablebooks/mdurl |
| prettytable | 3.18.0 | BSD-3-Clause | pip-licenses | (PyPI) |
| wcwidth | 0.9.3 | MIT | prettytable | (PyPI) |
| pip | 26.2.2 | MIT | the venv itself | (PyPI) |

I traced "Why it's here" with `pip show` for grpcio, numpy, protobuf, opentelemetry-api,
portalocker and truststore. The rest come from each package's published dependencies, and I
haven't traced every edge with `pip show`.

**Frontend: every package in `frontend/package-lock.json`** (31 entries; 23 are installed on
this machine, the other 8 are other platforms' optional binaries).

Every registry package is from `registry.npmjs.org` and carries a sha512 `integrity` hash in
the lockfile.

| Package | Version | Licence | Kind |
|---|---|---|---|
| next | 16.4.2 | MIT | runtime, direct |
| react | 19.3.1 | MIT | runtime, direct |
| react-dom | 19.3.1 | MIT | runtime, direct |
| @next/env | 16.4.2 | MIT | runtime (next) |
| @next/swc-* (win32-x64 installed; 8 other platforms listed, not installed) | 16.4.2 | MIT | optional (next) |
| @swc/helpers | 0.5.23 | Apache-2.0 | runtime (next) |
| tslib | 2.8.1 | 0BSD | runtime (@swc/helpers) |
| styled-jsx | 5.1.6 | MIT | runtime (next) |
| client-only | 0.0.1 | MIT | runtime (styled-jsx) |
| postcss | 8.5.23 | MIT | runtime (next) |
| nanoid | 3.3.20 | MIT | runtime (postcss) |
| picocolors | 1.1.1 | ISC | runtime (postcss) |
| source-map-js | 1.2.2 | BSD-3-Clause | runtime (postcss) |
| caniuse-lite | 1.0.30001819 | **CC-BY-4.0** | runtime (next) |
| baseline-browser-mapping | 2.11.31 | Apache-2.0 | runtime (next) |
| scheduler | 0.28.0 | MIT | runtime (react-dom) |
| sharp | 0.0.0-policy-assistant-stub | MIT (ours) | link to `frontend/vendor/no-sharp` (override) |
| typescript | 5.9.3 | Apache-2.0 | dev, direct |
| @types/node | 26.6.5 | MIT | dev, direct |
| @types/react | 19.3.0 | MIT | dev, direct |
| @types/react-dom | 19.3.0 | MIT | dev, direct |
| csstype | 3.2.3 | MIT | dev (@types/react) |
| undici-types | 8.9.0 | MIT | dev (@types/node) |

The licences come from the lockfile, or from each installed `package.json` where the
lockfile had none. The "Kind" column is the lockfile's `dev` and `optional` flags; the parent
package in brackets is from each package's published dependencies.

**Not libraries, but they run with the product:**
- `qdrant/qdrant:v1.20.0`: its SBOM (`/qdrant/qdrant.spdx.json`, 782 packages) declares
  qdrant itself Apache-2.0. Three entries are dual-licensed with a GPL or LGPL option
  ("Apache-2.0 OR GPL-2.0", "MIT OR Apache-2.0 OR LGPL-2.1-or-later"), and each also offers
  a permissive option.
- `postgres:16.15`: it has no licence labels. **I haven't checked its licences.**

**Anything copied in:**
- I searched every tracked file outside the corpus and the lockfile for copyright lines,
  "copied from", "adapted from", SPDX tags, "licensed under" and "(c) YEAR". There were none.
- No fonts, images or other binary assets are tracked. No external URLs appear in the
  frontend code.
- `frontend/vendor/no-sharp` (2 files) is ours, recorded in `T1-plan.md` §2.
- The corpus was supplied with the brief.
- That search is all I can show. It can't prove that no snippet was copied without a notice.

**FND-25 — `certifi` is MPL-2.0.** Low.
- **Where:** a dependency of httpx and qdrant-client.
- **Why it's flagged:** MPL-2.0 is a weak, file-level copyleft. It isn't on rule 7's list,
  and the CI check passes it, but nobody has decided on it explicitly.
- **What I'd do:** record a decision that MPL-2.0 is acceptable. The obligation only applies
  if certifi's own files are modified.
- **Decision:** Accepted (accepted recommendation): MPL-2.0 is not on rule 7's list, and we don't modify certifi, so its file-level terms never bite.

**FND-26 — `caniuse-lite` is CC-BY-4.0, which requires attribution.** Low.
- **Where:** a dependency of next.
- **What I haven't checked:** whether any of its data ends up in the shipped bundle, or is
  only used at build time.
- **What I'd do:** check, and add an attribution notice if it ships.
- **Decision:** Deferred (accepted recommendation): check whether it ships in the bundle at the deployment stage, and add attribution if it does.

**FND-27 — The CI licence check misses some of what runs.** Low.
- **Where:** `ci/check_licences.py:39` runs `pip-licenses` without `--with-system`.
- **What it misses:**
  - `pip`, `pip-licenses`, `prettytable` and `wcwidth`. I checked them by hand: MIT, MIT,
    BSD-3-Clause and MIT.
  - The Docker images, which it never looks at.
- **What I'd do:** add `--with-system`, and record the image licences in the plan.
- **Decision:** Deferred (accepted recommendation): a small CI change; the missing packages were checked by hand in this review, all permissive.

**FND-28 — The lockfile records the `sharp` stub at an odd path.** Low.
- **Where:** `frontend/package-lock.json`, entry `node_modules/sharp`, whose `resolved` is
  `node_modules/next/vendor/no-sharp`.
- **Checked:** a clean `npm ci` in a scratch copy still links `sharp` to `vendor/no-sharp`
  and installs the stub, so it is harmless.
- **What I'd do:** nothing now. Recheck whenever npm is upgraded.
- **Decision:** Accepted (accepted recommendation): harmless, verified with a clean `npm ci`.

## 5. Production readiness

**What I checked:** an in-process copy of the app with the real `.env`, breaking one
dependency at a time and asking Q1. The shared containers were left running.

| Broken | Response | Time | Passages shown? | `/healthz` | Log |
|---|---|---|---|---|---|
| nothing (baseline) | 200 `answered` | 3571 ms | n/a (2 sources) | ok | — |
| chat model times out (`GENERATION_TIMEOUT_SECONDS=0.01`) | 200 `degraded`, `provider_timeout` | 1465 ms | **yes, 5** | ok | `generation timed out (APITimeoutError)` |
| the same, on a follow-up | 200 **`refused`** | — | **no** | ok | `rewrite failed (RewriteFailed: APITimeoutError); searching as asked` (FND-1) |
| Qdrant down (`QDRANT_URL` → port 1) | 500 `internal_error` "Something went wrong. Try again shortly." | 3344 ms | no | degraded, qdrant `unreachable` | `unhandled error: ResponseHandlingException` |
| provider unreachable (`OPENROUTER_BASE_URL` → port 1) | 500 `internal_error` | 2458 ms | **no** | degraded, generation `unreachable` | `unhandled error: APIConnectionError` |
| Postgres down (`DATABASE_URL` → port 1) | 500 `internal_error` | 5275 ms | no | degraded, postgres `unreachable` | `unhandled error: InterfaceError` |

**What this shows:**
- A failure is always visible. No path returns a blank result or a fake answer, and
  `/healthz` names the broken component.
- The fallback to passages works only when the chat model alone fails on a first question.
- The web page shows the 500's message through the proxy (`api.ts:21-23`).

**FND-29 — When the provider is down, nothing falls back to the passages.** High.
- **Where:** `retrieval.py:47` and `embeddings.py:26`. Embeddings come from the same provider
  as the chat model.
- **Checked:** with OpenRouter unreachable, the result is a 500 with no passages.
- **Why it matters:** T1's Error criterion holds only when the chat model alone fails. The
  likeliest real outage, the whole provider, gives no passages. T1.md's playback notes
  recorded this as a D0 question, and it is still open.
- **What I'd do:** decide D0's outage plan. The options are:
  - a second embedding provider;
  - cached question embeddings;
  - a keyword-search fallback, which shows passages without the refusal score and would need
    its own rule.

  Each is a design decision for you.
- **Decision:** **Not fixed: waiting for your decision.** Each fix is a design choice (rule 2), and I couldn't ask in-session. The options are under "FND-29 options" below. I recommend A, a second route to the same embedding model.

**FND-29 options** (each keeps the refusal rule as it is unless it says otherwise):

| | Option | What it takes | Trade-off |
|---|---|---|---|
| A (recommended) | If OpenRouter's embedding call fails, call the same model (`text-embedding-3-small`, 1,536 dimensions) directly at OpenAI | Two new settings (`EMBEDDING_FALLBACK_BASE_URL`, `EMBEDDING_FALLBACK_API_KEY`) and an OpenAI API key, a new provider account. No new library | Same vectors, so the same threshold applies. Covers an OpenRouter outage, not an OpenAI one. I can't verify it live without the key |
| B | If embedding fails, rank passages by word overlap in plain Python and show them as `degraded` | A second refusal rule with its own threshold, tuned on the same 13 questions. ADR-001 changes | No new account, but an untested gate: parental-leave or crypto questions could show loosely matching passages instead of a refusal |
| C | Return a clear "policy search is unavailable" message instead of the generic 500 | An agreed-API change (a 503 with its own code) | Honest, but T1's Error criterion still fails in a full outage, so FND-29 would be accepted rather than fixed |

**FND-30 — When Qdrant is down, the person sees only "Something went wrong".** Medium.
- **Where:** `ask.py:121` (retrieval isn't guarded) and `main.py:177-181`.
- **What happens:** search can't run, so the 500 is the right outcome, but nothing says the
  policy search is down.
- **Monitoring:** `/healthz` always returns 200 by design (PRD §5.6), so Railway's health
  check (`railway.json`) can't see a degraded service. Monitoring would have to read the
  body.
- **What I'd do:** catch retrieval failures and return a clear 503 with its own code. That
  changes the agreed API, so it needs your approval.
- **Decision:** Deferred (accepted recommendation): a clearer 503 changes the agreed API (rule 4); `/healthz` already names the broken component.

**FND-31 — When Postgres is down, the answer is generated, paid for, then thrown away.**
Medium.
- **Where:** `ask.py:225`. The exchange is recorded after generation, and the failure only
  shows up at that point.
- **Checked:** a 500 after 5275 ms. The model was called first.
- **What I'd do:** check the store before calling the model, or return the answer and log
  that the record failed. REQ-C1 requires every call to be recorded, so you'd choose between
  them.
- **Decision:** Deferred (accepted recommendation): either fix changes how REQ-C1 is met, so it needs your choice; it costs one wasted model call per request during a Postgres outage.

**FND-32 — No overall deadline on a request.** Medium.
- **Where:**
  - The API's `QdrantClient` has no timeout setting (`main.py:63`), so it gets httpx's 5 s
    per phase. I read that in `qdrant_remote.py:221` and `httpx/_config.py:246`.
  - The rest stacks up: embedding 5 s, rewrite 6 s, answer 6 s.
  - The Next proxy's `fetch` has no timeout at all (`route.ts:34`).
- **Why it matters:** in the worst case one ask can take more than 20 s, and a hung API holds
  the proxy indefinitely. That is by reading; I didn't reproduce a hang.
- **What I'd do:** add a `QDRANT_TIMEOUT_SECONDS` setting, and `AbortSignal.timeout` in the
  proxy, read from a setting.
- **Decision:** Deferred (accepted recommendation): timeouts are set at the deployment stage, where the real latencies are measured (NFR-1).

**FND-33 — The history list reads every message, every time.** Low.
- **Where:** `history.py:27-38`.
- **Why it matters:** with no pagination (PRD §5.4 [ASSUMED]), each call grows with the
  whole history. That's fine at 230 questions, not at 1,400 staff.
- **What I'd do:** aggregate in SQL, and add pagination. That is an API change, so it needs
  your approval.
- **Decision:** Deferred (accepted recommendation): fine at today's volume, and pagination changes the agreed API.

**FND-34 — Two asks into the same conversation at once can fail.** Low.
- **Where:** `db.py:164-167`, which takes the next `seq` from `max(seq) + 1`.
- **What happens:** both requests pick the same `seq`, the unique constraint rejects one, and
  that request gets a 500. The web page blocks double-submits, so it's unlikely. By reading,
  not reproduced.
- **What I'd do:** lock the conversation row (`SELECT … FOR UPDATE`) while recording.
- **Decision:** Accepted (accepted recommendation): the page blocks double-submits, so it needs two clients on one conversation at once.

**FND-35 — A re-index isn't atomic.** Low.
- **Where:** `vector_store.py:77-86`, which upserts, then deletes stale points.
- **What happens:** during an ingest, searches see a mix of old and new passages. A Qdrant
  failure part-way leaves the mix in place. REQ-I9's "nothing written" holds for embedding
  failures only. By reading, not reproduced.
- **What I'd do:** ingest into a fresh collection and switch an alias over at the end.
- **Decision:** Deferred (accepted recommendation): re-indexing is manual and rare (scheduled re-indexing is out of scope); fix before the first production re-index.

**FND-36 — The rewrite call's cost isn't logged.** Low.
- **Where:** `rewrite.py:76` returns only text, and `ask.py:231-240` logs the answer call's
  tokens only.
- **Why it matters:** every follow-up makes an uncounted model call, so cost reporting (brief
  §9) is short.
- **What I'd do:** return and log the rewrite's token counts.
- **Decision:** Deferred (accepted recommendation): cost reporting only; add it with FND-17's logging change.

**What I haven't checked in this pass:**
- NFR-1 and NFR-2 latency on a deployed service, since nothing is deployed.
- NFR-3's 1-second `/healthz` timing. I didn't re-time it in this review; `test_healthz.py`
  covers it in the suite.
- Behaviour under concurrent load.
- Postgres or Qdrant failing mid-request rather than at connect.

## Fixes (2026-10-23)

**FND-1, the follow-up asked while the model is down:**
- **Changes:**
  - `RewriteFailed` now carries `provider` (`"timeout"`, `"error"` or `None`), in
    `app/rewrite.py`.
  - In `app/ask.py`, a provider failure searches the follow-up joined with the previous
    question (the original D9) under the same rule and threshold. If that clears, it returns
    `degraded` (`provider_timeout` or `provider_error`) with passages, without calling the
    model again.
  - An unusable reply still searches as asked, as before.
- **Tests first:**
  - In `test_rewriter.py`: provider timeout and error told apart from an unusable reply.
  - In `test_conversation.py`: model down on a follow-up gives passages, not a refusal (both
    reasons), and the joined follow-up is still judged by the rule.
  - Shown failing: `4 failed, 16 passed`, with `TypeError: RewriteFailed() takes no keyword
    arguments`. After the code: `20 passed`.
- **Live, with `GENERATION_TIMEOUT_SECONDS=0.01` and a real London question first:**

  ```
  FND-1 model down, follow-up 'And for Singapore?': degraded {'reason': 'provider_timeout'} top 0.7471 sources [('travel-expense-policy-v3.1', '6.2'), ('travel-expense-policy-v3.0', '6.1')]
  FND-1 model down, follow-up 'How many days of paid parental leave am I entitled to?': refused None top 0.3312 sources []
    log: ask request_id=3083fbc37967 rewrite failed (RewriteFailed: APITimeoutError); model down; searching joined with the previous question
  ```

  Before the fix, the same Singapore follow-up came back `refused` at 0.3447.
- **Residual risk:** with the model down, an off-topic follow-up joined with an on-topic
  question can clear the rule and show the earlier topic's passages, as `degraded`, never as
  an answer. That is the joined-search weakness D9 measured at F6, now confined to outages.

**FND-9, history open to anyone:**
- **Changes:**
  - A `HISTORY_ENABLED` setting, required at startup with no default in code (settings, and
    `create_app`'s required list).
  - The history routes are registered only when it is true.
  - `/history` shows "History is switched off on this service…" when the API answers the
    routes' absence with `not_found` (`lib/present.ts` `historyNotFound`; `lib/corpus.ts`
    passes the error code through).
  - `.env.example` documents it. It is `true` only in my local `.env`.
- **Not in PRD §8:** the setting isn't in PRD §8's list, which is locked, so the setting list
  there is now one short. I haven't changed the PRD (rule 1).
- **Tests first:**
  - Backend, in `test_api_conversations.py`: switched off, no stored question is exposed and
    every exchange is still recorded; the API won't start without the setting. Shown
    failing: `2 failed, 6 passed` (`assert 200 == 404`, and `DID NOT RAISE SettingsError`).
    After the code: `8 passed`.
  - Frontend, in `present.test.ts`: switched off says so. Shown failing: `does not provide
    an export named 'historyNotFound'`. After the code: 13/13.
- **Live:**

  ```
  FND-9 HISTORY_ENABLED=false: 404 not_found | 404 not_found
  FND-9 HISTORY_ENABLED=true (local .env): 200
  ```

**After both fixes, the whole suite:**

```
$ cd backend && ruff check . && ruff format --check . && bandit -q -r app && python -m pytest -q
All checks passed!  62 files already formatted  (bandit: no findings)
129 passed, 3 warnings in 8.94s
$ python -m pytest -q -p no:cacheprovider ci/tests
41 passed in 13.11s
$ python ci/check_scope.py --base plan-approved
Scope check passed: no protected file has changed since refs/tags/plan-approved.
$ python ci/check_licences.py --node-modules frontend/node_modules
Checked 77 packages.  Licence check passed: no copyleft or unknown licences.
$ cd frontend && npm run typecheck && npm test && npm run build
typecheck ok · ℹ tests 13  ℹ pass 13  ℹ fail 0 · ✓ Compiled successfully (/history built)
```

The 13 questions and the follow-up set, against the restarted API on 8014:

```
$ cd backend && python -m app.eval
Q1 answered 0.723 · Q2 answered 0.733 · Q3 answered 0.582 · Q4 answered 0.666 · Q5 answered 0.557
Q6 answered 0.611 · Q7 answered 0.606 · Q8 answered 0.712 · Q9 answered 0.618 · Q10 answered 0.570
Q11 refused 0.438 · Q12 refused 0.462 · Q13 refused 0.275
eval 10/10 answered, 3/3 refused
$ cd backend && python -m app.followup_eval
C1 answered 0.7182 · C2 answered 0.6657 · C3 answered 0.5374 · C4 refused 0.4690 · C5 refused 0.2750 · C6 refused 0.4825
followups 6/6 passed
```

## Decisions

**Findings per pass:**

| Pass | Findings | Count |
|---|---|---|
| 1. Correctness | FND-1 to FND-8, plus FND-37 (raised by the product owner) | 9 |
| 2. Security and privacy | FND-9 to FND-16 | 8 |
| 3. Maintainability | FND-17 to FND-24 | 8 |
| 4. Licences and origin | FND-25 to FND-28 | 4 |
| 5. Production readiness | FND-29 to FND-36 | 8 |
| **Total** | | **37** |

**Outcome:**
- 2 fixed (FND-1, FND-9).
- 1 waiting for your decision (FND-29).
- 1 accepted by the product owner (FND-37).
- 33 decided as accepted recommendations: 10 accepted, 23 deferred.

| Finding | Pass | Severity | Decision | Reason |
|---|---|---|---|---|
| FND-1 | 1. Correctness | High | Fixed | Fixed in this commit; evidence under "Fixes" |
| FND-2 | 1. Correctness | Medium | Deferred (accepted recommendation) | today's live answer is correct; the content check needs a choice between a phrase match and a reviewed judgement, so it belongs to the next testing pass |
| FND-3 | 1. Correctness | Medium | Deferred (accepted recommendation) | storing the search text and rewrite version changes the agreed data model, which needs approval (rule 4) |
| FND-4 | 1. Correctness | Low | Deferred (accepted recommendation) | it only misdirects a scroll in multi-turn conversations; a one-line fix with the next frontend change |
| FND-5 | 1. Correctness | Low | Deferred (accepted recommendation) | wording only, with no wrong answer or refusal; fix with the next API change |
| FND-6 | 1. Correctness | Low | Accepted (accepted recommendation) | the 422 is the agreed contract, pinned by a test, and only a client sending non-UTF-8 sees it |
| FND-7 | 1. Correctness | Low | Accepted (accepted recommendation) | U17 still holds ("Superseded" is shown), and the fuller label needs a data-model change |
| FND-8 | 1. Correctness | Low | Accepted (accepted recommendation) | D8 is a decided value, and the follow-up set passes 6/6 with it |
| FND-9 | 2. Security and privacy | High | Fixed | Fixed in this commit; evidence under "Fixes" |
| FND-10 | 2. Security and privacy | Medium | Deferred (accepted recommendation) | it belongs with brief Q3, which is owned outside the team; nothing is deployed yet |
| FND-11 | 2. Security and privacy | Medium | Deferred (accepted recommendation) | retention is brief Q2, owned outside the team; nothing is deployed yet |
| FND-12 | 2. Security and privacy | Medium | Deferred (accepted recommendation) | to the deployment stage, where the platform's own limits can be used before any new library is considered |
| FND-13 | 2. Security and privacy | Low | Deferred (accepted recommendation) | a deployment-stage setting; the docs show nothing a public repo doesn't already |
| FND-14 | 2. Security and privacy | Low | Deferred (accepted recommendation) | set at the deployment stage, together with the frontend's start command (FND-23) |
| FND-15 | 2. Security and privacy | Low | Accepted (accepted recommendation) | nothing sensitive is in those files, and rewriting a pushed public history is destructive |
| FND-16 | 2. Security and privacy | Low | Accepted (accepted recommendation) | an inherent residual risk; the refusal rule still runs first, and FND-2's content check will spot-check answers |
| FND-17 | 3. Maintainability | Medium | Deferred (accepted recommendation) | diagnostics only, with no wrong output; fix before deployment, since NFR-5 applies there |
| FND-18 | 3. Maintainability | Low | Accepted (accepted recommendation) | each copy is short and readable; merge them when that code is next touched |
| FND-19 | 3. Maintainability | Low | Accepted (accepted recommendation) | none is a model name or threshold, and the rewriter's temperature 0 is deliberate and commented |
| FND-20 | 3. Maintainability | Low | Deferred (accepted recommendation) | test hygiene; the network call only adds a warning and can't make a test pass falsely |
| FND-21 | 3. Maintainability | Low | Deferred (accepted recommendation) | a type checker is a new library and needs approval (rule 4) |
| FND-22 | 3. Maintainability | Low | Deferred (accepted recommendation) | to the deployment stage, when the image is first built for release |
| FND-23 | 3. Maintainability | Low | Deferred (accepted recommendation) | the frontend's deploy command is settled at the deployment stage |
| FND-24 | 3. Maintainability | Low | Deferred (accepted recommendation) | T1.md is updated at the verification stage, once the decisions on this review are final |
| FND-25 | 4. Licences and origin | Low | Accepted (accepted recommendation) | MPL-2.0 is not on rule 7's list, and we don't modify certifi, so its file-level terms never bite |
| FND-26 | 4. Licences and origin | Low | Deferred (accepted recommendation) | check whether it ships in the bundle at the deployment stage, and add attribution if it does |
| FND-27 | 4. Licences and origin | Low | Deferred (accepted recommendation) | a small CI change; the missing packages were checked by hand in this review, all permissive |
| FND-28 | 4. Licences and origin | Low | Accepted (accepted recommendation) | harmless, verified with a clean `npm ci` |
| FND-29 | 5. Production readiness | High | Waiting for product owner | Every fix is a design choice (rule 2); options A, B or C, A recommended |
| FND-30 | 5. Production readiness | Medium | Deferred (accepted recommendation) | a clearer 503 changes the agreed API (rule 4); `/healthz` already names the broken component |
| FND-31 | 5. Production readiness | Medium | Deferred (accepted recommendation) | either fix changes how REQ-C1 is met, so it needs your choice; it costs one wasted model call per request during a Postgres outage |
| FND-32 | 5. Production readiness | Medium | Deferred (accepted recommendation) | timeouts are set at the deployment stage, where the real latencies are measured (NFR-1) |
| FND-33 | 5. Production readiness | Low | Deferred (accepted recommendation) | fine at today's volume, and pagination changes the agreed API |
| FND-34 | 5. Production readiness | Low | Accepted (accepted recommendation) | the page blocks double-submits, so it needs two clients on one conversation at once |
| FND-35 | 5. Production readiness | Low | Deferred (accepted recommendation) | re-indexing is manual and rare (scheduled re-indexing is out of scope); fix before the first production re-index |
| FND-36 | 5. Production readiness | Low | Deferred (accepted recommendation) | cost reporting only; add it with FND-17's logging change |
| FND-37 | 1. Correctness | (not rated) | Accepted (product owner) | Known limitation: doing better needs more test questions |

## F9 addendum (2026-10-23)

**Scope:** the F9 diff only, `8daf059..c9773c7`: 18 files outside the screenshots, all
under `frontend/` and `tickets/`. Findings continue from FND-37. The same five passes.
There are **no high findings**, so nothing needed fixing now. Each finding has its
decision.

**What I checked before the passes:**
- **Existence in the installed versions:**
  - `usePathname`, `useParams` and `useSearchParams` in next 16.4.2 (`next/navigation`);
  - the `Viewport` type export, through `tsc --noEmit`, which passed;
  - Node 24.20.0's global `WebSocket`;
  - Edge's DevTools methods (`Emulation.setDeviceMetricsOverride`,
    `Page.captureScreenshot` with `captureBeyondViewport`, `Input.insertText`,
    `Input.dispatchKeyEvent`). All of these ran without error in the screenshot runs.
- **Nothing outside the frontend changed:**
  - `git diff --stat` of `frontend/package.json`, `package-lock.json`,
    `backend/requirements.txt` and `backend/app` is empty;
  - the licence check passes (77 packages);
  - backend 129 tests and CI-script 41 tests pass;
  - the scope check passes.
- **No new risk surfaces:**
  - no `dangerouslySetInnerHTML` or `innerHTML`;
  - no `@import` or `url()` in the stylesheet, and no external URL in the frontend code,
    so the pages fetch nothing from outside;
  - fonts are system fonts only.
- **Class names:** every class used in the TSX has a rule in `globals.css`, except
  `result--answer`. That one is deliberate: the base `.result` is the answer look, and the
  class is a hook for the screenshot script.

### F9: 1. Correctness

The criteria were checked through the 22 + 4 screenshot checks, the keyboard-focus
screenshot and 27 frontend tests (see `T1-F9-ui.md`). I looked at 8 of the screenshots by
eye.

**FND-38 — The conflict notice is found at its first occurrence, not its last.** Low.
- **Where:** `frontend/lib/present.ts`, `conflictView` (`indexOf(CONFLICT_LEAD)`).
- **The risk:** if the model's own text ever contained the exact phrase "These two current
  policies conflict:", the answer would be split in the wrong place. The backend always
  appends the notice at the end (`ask.py`, `f"{result.text}\n\n{note}"`).
- **What I'd do:** use `lastIndexOf`.
- **Decision:** Deferred (accepted recommendation): Q10 renders correctly today (screenshot
  `ask-conflict-q10`); a one-word fix for the next frontend change.

**FND-39 — The passages-only result says "No answer was composed" twice.** Low.
- **Where:** `components/Result.tsx` (`Degraded`): the heading, then `degradedMessage`.
- **What I'd do:** reword the heading, for example "Policy passages only".
- **Decision:** Accepted (accepted recommendation): U5 requires the message to say it; the
  repeat is redundant, not wrong.

**FND-40 — Next's built-in 404 page isn't on the new design, and the skip link has no
target there.** Low.
- **Checked:** `curl /no-such-page` returns 404 with Next's own inline-styled `h1` and
  `0` elements with `id="main"`, while the layout's "Skip to content" link points at
  `#main`.
- **What I'd do:** add `app/not-found.tsx` on the shared design.
- **Decision:** Deferred (accepted recommendation): it isn't one of the four pages F9
  names; add it with the next frontend change.

**FND-41 — The card's marker number carries an `aria-label` that screen readers
ignore.** Low.
- **Where:** `components/Citation.tsx`, `<span className="card__marker" aria-label=…>`. An
  `aria-label` on a plain span is not announced.
- **What I'd do:** replace it with visually hidden text, as the answer's markers already
  have.
- **Decision:** Deferred (accepted recommendation): the card's visible text (document,
  section, version) already identifies it; fix with FND-40.

### F9: 2. Security and privacy

No question text is added to any log, URL or request by F9. The pages call only the same
same-origin `/api/*` routes as before.

**FND-42 — The screenshot script opens Edge's DevTools port while it runs.** Low.
- **Where:** `frontend/scripts/f9-screens.mjs`, `--remote-debugging-port`
  (`F9_DEBUG_PORT`, otherwise 9333).
- **The risk:** while it runs, any process on the machine could drive that headless
  browser through `127.0.0.1`.
- **Decision:** Accepted (accepted recommendation): it's a developer tool. The browser uses
  a fresh temporary profile with no credentials, and it is killed at the end; it never
  runs in CI or production.

**FND-43 — The committed screenshots show stored questions, in a public repository.** Low.
- **Where:** `tickets/evidence/F9/history-*.png` and `history-conversation-*.png`.
- **Checked:** by eye, the history screenshot shows only test and eval questions asked
  during this build, including the 1,000-character "xxxx…" one. No real user's question
  is in the local store.
- **Decision:** Accepted (accepted recommendation): nothing sensitive. Any future
  screenshot must be taken against a store with no real questions in it.

### F9: 3. Maintainability

**FND-44 — The screenshot and accessibility checks don't run in CI.** Medium.
- **Where:** `frontend/scripts/f9-screens.mjs` needs Edge plus the API and web servers
  with a live provider. CI runs only the unit tests, the typecheck and the build.
- **The gap:** a layout regression like the history overflow these checks caught would
  pass CI.
- **What I'd do:** a CI job that starts both servers with generation off, then runs the
  script on the pages and states that don't need the model.
- **Decision:** Deferred (accepted recommendation): it needs services in CI and a browser
  on the runner, which is deployment-stage work; until then the script is run by hand
  before each release, as here.

**FND-45 — The frontend reads structure out of backend wording.** Low.
- **Where:** `refusalView` splits the D5 text at "Who to ask:", and `conflictView` looks
  for the D6 lead. Both are in `lib/present.ts`.
- **The guard:** `lib/views.test.ts` reads `backend/app/text/refusal.md` and
  `conflict.md`, so a wording change fails the tests.
- **Decision:** Accepted (accepted recommendation): the agreed API has no separate fields
  for these, and adding them would change it (rule 4); the tests guard the coupling.

**FND-46 — The test fixtures are duplicated.** Low.
- **Where:** `lib/present.test.ts` and `lib/views.test.ts` each build their own `Source`
  and `AskResponse`.
- **Decision:** Accepted (accepted recommendation): each file stays readable on its own;
  merge them if a third file needs them.

**FND-47 — The screenshot script holds some values in code.** Low.
- **Where:** `f9-screens.mjs`: the DevTools port fallback (9333), the 3,200 px height cap
  and the eval questions it asks.
- **Rule 5:** the base URL and Edge's path come from the environment, as rule 5 needs.
- **Decision:** Accepted (accepted recommendation): test fixtures and a local port, not a
  model name, URL or threshold.

### F9: 4. Licences and origin

- **No new packages:** the diff of `package.json` and `package-lock.json` is empty. All
  CSS is hand-written. No fonts, images or icon sets are added; the icons are inline SVG.
- **Fonts:** Segoe UI and the system fallbacks belong to the viewer's machine and aren't
  shipped.
- **Screenshots:** they show the corpus, which was supplied with the brief.

**FND-48 — The check icon's path matches a common icon set.** Low.
- **Where:** `components/Icon.tsx`, `check: "M20 6 9 17l-5-5"`.
- **What I know:** I wrote it from memory. As far as I know it is the same path as the
  check icon in Lucide (ISC) and Feather (MIT). I haven't checked against their source.
  The other paths are my own drawings of simple shapes.
- **What I'd do:** redraw it, or keep it with a one-line ISC notice. Both licences are
  permissive, so rule 7 isn't breached either way.
- **Decision:** Deferred (accepted recommendation): redraw it at the next frontend change.

### F9: 5. Production readiness

The states were checked live:
- **Passages only:** with the API restarted as `GENERATION_ENABLED=false`, the page shows
  `degraded` with the passages.
- **Error:** with the API stopped, the proxy's "The service is unavailable. Try again
  shortly." is shown as an error with what to try and a Try again button.
- **Loading:** shown while the question is pending, with the box and button disabled.

**FND-49 — Only checked in headless Edge.** Low.
- **What I haven't checked:**
  - Firefox and Safari;
  - a screen reader;
  - automated contrast beyond the token pairs (for example text over the
    semi-transparent brand mark).
- **Decision:** Deferred (accepted recommendation): to the verification stage, on the
  browsers the bank actually uses.

**FND-50 — The "Searching the policy documents" state never times out on its own.** Low.
- **Where:** `lib/api.ts`: the browser's `fetch` has no time limit, and neither does the
  proxy (FND-32).
- **What happens:** if the API hangs, the loading state stays up rather than turning into
  an error. By reading, not reproduced.
- **What I'd do:** an `AbortSignal.timeout` read from a setting, together with FND-32.
- **Decision:** Deferred (accepted recommendation): fix with FND-32 at the deployment
  stage.

### F9 addendum summary

| Pass | Findings | Count |
|---|---|---|
| 1. Correctness | FND-38 to FND-41 | 4 |
| 2. Security and privacy | FND-42, FND-43 | 2 |
| 3. Maintainability | FND-44 to FND-47 | 4 |
| 4. Licences and origin | FND-48 | 1 |
| 5. Production readiness | FND-49, FND-50 | 2 |
| **Total** | | **13** (0 high, 1 medium, 12 low) |

**Decisions:** 6 accepted (FND-39, 42, 43, 45, 46, 47) and 7 deferred (FND-38, 40, 41, 44,
48, 49, 50), all as accepted recommendations. F9 also fixes **FND-4** from the main review:
citation anchors now carry the message ID (test: "citation anchors are unique per answer").
