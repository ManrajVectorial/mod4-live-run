# T1 — Plan

**Status:** approved (release manager, 2026-10-23 07:05 UTC+08:00)
**Date:** 2026-10-23
**Inputs:** `docs/PRD.md` v1.0, `docs/features.md` v1.0, `tickets/T1.md` (criteria),
`tickets/T1-assumptions.md`, `docs/design/ADR-001-answer-gate.md`. No code before approval.

## 1. Decisions

| | Value | Reason (one sentence) |
|---|---|---|
| D0 | OpenAI `text-embedding-3-small`, 1,536 dimensions, via OpenRouter. Before F1 I check that OpenRouter serves it | It finds the right policy text well at low cost, and stays with the provider we already agreed, so nothing new needs approving. |
| D1 | One passage per numbered section. Tables kept whole, no overlap. A long section splits at paragraph boundaries, and the section heading is prefixed to each passage before embedding. **Size cap set at F1** from the measured section lengths | Cutting along the policy's own sections means every answer can point to the exact section it came from, which is what staff need to trust it. |
| D2 | **Method:** run all 13 questions, record every top score, and set the threshold at the midpoint of the gap between the lowest score among Q1–Q10 and the highest among Q11–Q13. A score clears only if strictly above the threshold. Rephrased variants are tested in a separate file, never in `EVALUATION.md`. **Number:** filled in at F3 from the measured scores. **If no threshold cleanly separates the 13:** we don't pick a number that fails any question. I stop and record the scores, then try improving the search within the agreed design (chunking, heading prefix, number of passages) and re-run. If there is still no clean gap, I bring you the options and you decide (ADR-001). The corpus and `EVALUATION.md` are never changed to make it pass | The cut-off is set from measured results on the bank's own test questions, not from guesswork, so we can show an auditor exactly why the assistant answers some questions and declines others. |
| D3 | 5 passages | Five passages are enough to bring in both policies when a question spans two, without slowing answers down. |
| D4 | Only current versions go to the model. A retrieved superseded passage appears only as a labelled "earlier version" note | Staff always get the current rule, and can still see what changed, which tackles the brief's core problem of answers quoting out-of-date policy. |
| D5 | The refusal says the policy documents don't cover this, cites no policy, and gives a fixed who-to-ask list: expenses → Group Finance; leave, pay and benefits → HR; anything else → Compliance | Staff need somewhere to go, not just a no. |
| D6 | Show both policies with their sections, say plainly that they conflict, and tell the reader to escalate to Group Legal and Group Operational Risk. Conflicts are spotted only from `known_conflict` in `MANIFEST.yaml` (read-only), never by the model | Which policy wins is the policy owner's call, not the app's. |
| D7 | Flat numbered list in marker order, each entry showing document, section and version | Every source is shown plainly with its document, section and version, and a fancier layout can wait until users ask for it. |
| D8 | The last 5 messages, counting questions and answers separately (`CONVERSATION_CONTEXT_MESSAGES`) | Staff often refer back more than one turn. |
| D9 | Search again every turn, on the new question joined with the one before it (`FOLLOWUP_QUERY_QUESTIONS`). The refusal rule judges the joined text. **Measured at F6.** If the partner-flight check fails there, that is a planned stop | A short follow-up like "and for Singapore?" finds nothing on its own, and limiting it to the one question before keeps old topics from slipping into new answers. |

**Chat model** (set by the product owner, 2026-10-23, after Task 0):
`anthropic/claude-haiku-5.5` through OpenRouter, in `CHAT_MODEL`. Embeddings stay as D0
decided. On 2026-10-23 I checked that OpenRouter lists both `anthropic/claude-haiku-5.5` and
`openai/text-embedding-3-small`, and that the key in `.env` authenticates.
`GENERATION_ENABLED` is now `true`.

## 2. Allowed libraries (pinned; nothing else without asking)

Versions are the latest releases on PyPI and npm, checked 2026-10-23.

| Backend | Version | Licence | | Dev / frontend | Version | Licence |
|---|---|---|---|---|---|---|
| fastapi | 0.161.1 | MIT | | pytest | 9.1.1 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause | | httpx | 0.28.1 | BSD-3-Clause |
| pydantic-settings | 2.16.1 | MIT | | ruff | 0.17.2 | MIT |
| sqlalchemy | 2.1.6 | MIT | | bandit | 1.9.4 | Apache-2.0 |
| pg8000 (not psycopg, which is LGPL) | 1.31.5 | BSD-3-Clause | | pip-licenses | 5.5.5 | MIT |
| qdrant-client | 1.20.0 | Apache-2.0 | | next | 16.4.2 | MIT |
| openai (pointed at OpenRouter) | 3.37.0 | Apache-2.0 | | react, react-dom | 19.3.1 | MIT |
| pyyaml | 6.0.3 | MIT | | typescript | 5.9.3 | Apache-2.0 |
| python-dotenv | 1.2.4 | BSD-3-Clause | | @types/react, @types/react-dom | 19.3.0 | MIT |
| | | | | @types/node | 26.6.5 | MIT |

- **TypeScript:** pinned to 5.9.3, not 7.0.2. I haven't checked whether Next 16 supports
  TypeScript 7.
- **The `@types` packages** were added with your approval on 2026-10-23.
- **Frontend lint** is `tsc --noEmit`. There is no eslint.
- **Python:** 3.12 is run through the launcher, `py -3.12` (3.12.1 is installed).
- **Not libraries:** the Docker images `postgres` (PostgreSQL Licence) and `qdrant/qdrant`
  (Apache-2.0).
- **Transitive dependencies** are covered by the licence check, which fails on GPL, AGPL, LGPL,
  SSPL or EUPL.
- **`sharp` is replaced** (approved by the product owner, 2026-10-23, during Task 0). Next 16
  pulls in `sharp` as an optional dependency for image optimisation, and its native library
  (`@img/sharp-*`, libvips) is LGPL-3.0-or-later. An npm `overrides` entry in
  `frontend/package.json` points `sharp` at an empty stand-in, `frontend/vendor/no-sharp` (MIT,
  ours), which throws if anything ever loads it. Image optimisation is off
  (`images.unoptimized` in `next.config.ts`). We don't use the Image component. Re-enabling
  image optimisation needs approval.

## 3. Tasks in order

| # | Task | Ticket |
|---|---|---|
| 0 | **Skeletons and checks** (details below) | this plan |
| 1–5 | **Core:** F1 ingest → F2 search → F3 decide → F4 answer → F5 web page | MAV-794 to MAV-798 |
| 6–8 | **Optional, cut from the back:** F6 follow-ups → F7 corpus → F8 history (F8 also waits on brief Q3) | MAV-799 to MAV-801 |

**Task 0 delivers:**
- A FastAPI app with `/healthz`. It reports Postgres, Qdrant and the model, and answers while
  they're down. "Model" means `GENERATION_ENABLED`; it doesn't call the model (PRD §5.6).
- A Next.js page with the top bar: "Policy Assistant" and Reset.
- Docker Compose for Postgres and Qdrant.
- `.env.example`, plus a git-ignored `.env` that all keys and settings are read from.
- Test fakes for embeddings and chat, so no test touches the network.
- `python -m app.evaluate`, which runs the 13 questions. Status, answers and top score come
  from the running API. The top three sections (REQ-R4) come from calling the search code
  directly, so the agreed API doesn't change.
- One GitHub Actions job, `gate`, on every pull request: tests, lint, security scan, licence
  check and protected-files check.

**Why this order:**
- **Checks first,** so every later change is tested and licence- and scope-checked from the
  first pull request.
- **Each feature needs the one before it.** Passages before search, search before the gate,
  the gate before generation, and the API before the page.
- **F2 produces the score spread that D2 is set from in F3.** That's where the riskiest
  unknown is settled, before anything is built on top of it.
- **F6–F8 come last** because they're the ones we can cut.
- **Workflow:** one pull request per task, from `work/build` to `main`. You merge it after
  `gate` passes and you sign off in the ticket.

## 4. Files

| Path | What it does |
|---|---|
| `docker-compose.yml` | Local Postgres and Qdrant |
| `.env.example` | Every PRD §8 name plus D8 and D9 settings, no values. `.env` is already git-ignored |
| `.github/workflows/gate.yml` | The single `gate` job |
| `ci/check_scope.py` | Fails if a pull request changes `backend/corpus/`, `docs/project-brief.md`, `docs/PRD.md`, `docs/features.md`, `AGENTS.md` or `CLAUDE.md` (the script `MANIFEST.yaml` already names) |
| `ci/check_licences.py` | Runs pip-licenses, and reads every `node_modules/*/package.json` licence. Fails on a banned licence |
| `backend/pyproject.toml` | Python 3.12 project, the pins above, ruff and pytest config |
| `backend/app/settings.py` | Settings from the environment and `.env`. Refuses to start without required ones, and never prints values |
| `backend/app/main.py` | FastAPI app: `/healthz` (Task 0), `/api/ask` (F3–F6), `/api/corpus` (F7), `/api/conversations` (F8) |
| `backend/app/schemas.py` | PRD §5 response shapes |
| `backend/app/db.py` | SQLAlchemy models for PRD §6. Tables created with `create_all` (no migration tool) |
| `backend/app/corpus.py`, `chunking.py`, `embeddings.py`, `vector_store.py`, `ingest.py` | F1 |
| `backend/app/retrieval.py` | F2 |
| `backend/app/refusal.py`, `backend/app/text/refusal.md` | F3: the gate, and the D5 refusal text with the who-to-ask list |
| `backend/app/generation.py`, `citations.py`, `conflicts.py`, `backend/app/prompts/answer.md` | F4: chat client and kill switch, marker validation, the D6 conflict notice from `known_conflict`, and the versioned prompt |
| `backend/app/conversation.py` | F6: D8 context, D9 joined query |
| `backend/app/logging.py` | Structured logs without question text or secrets |
| `backend/app/evaluate.py` | The 13-question run. Writes `tickets/eval-results.md` |
| `backend/tests/` and `backend/tests/fakes.py`, `fixtures/` | Tests, the network-free fakes, and modified corpus copies kept outside `backend/corpus/` |
| `frontend/package.json`, `tsconfig.json`, `next.config.ts` | Next.js app with the pins above |
| `frontend/app/layout.tsx`, `page.tsx`, `corpus/…`, `history/…` | Top bar and pages (Task 0, F5, F7, F8) |
| `frontend/components/`, `frontend/lib/api.ts` | Citation, refusal, degraded result, notice, and the API client |
| `tickets/eval-results.md` | Generated evaluation table, committed at each feature's sign-off |

## 5. Deliberately not doing

- Authentication or per-user history
- Feedback (S4)
- Scheduled or change-triggered re-indexing
- A database migration tool
- Browser-automation tests
- Dark theme
- Grouped or deduplicated citations
- Query rewriting by the model
- Resolving conflicts in code
- Deploying before the deployment stage
- Editing the corpus, the PRD or features to make anything pass

## 6. Riskiest part

**The risk:** no single threshold separates Q1–Q10 from Q11–Q13 on one run (D2, ADR-001).
Q11 is inferable from §2.1, and Q12 sits next to KYC material.

**If it fails:**
1. Stop and record the score spread.
2. Try fixing retrieval within the design: chunking, the heading prefix, top-K.
3. Bring you options.

The corpus and `EVALUATION.md` are never changed.

**Second risk:** the D9 joined query makes the F6 partner-flight check answer instead of
refuse. That would be a planned stop at F6.

## 7. When I stop and ask

- A test fails twice and I don't know why
- I need a library that isn't listed above
- The plan turns out to be wrong
- F5 is done
- Before pushing to `main`, deploying, deleting data, or changing an agreed API or data model
  (AGENTS.md rule 4)

## 8. Approval

| Decision | By | When |
|---|---|---|
| D0–D9 values (D2 method only) | Product owner | 2026-10-23 |
| D2 threshold number | Product owner | At F3, from measured scores |
| D1 size cap | Product owner | At F1, from measured section lengths |
| Chat model `anthropic/claude-haiku-5.5` via OpenRouter | Product owner | 2026-10-23 |
| This plan and the library list | Release manager | **Approved 2026-10-23 07:05 UTC+08:00** |
| `gate` made a required check on `main` | Product owner (repo admin) | After Task 0 merges |
| Each feature done | Product owner | At each feature's sign-off in its ticket |
| Deployment to Railway | Product owner | At the deployment stage |
