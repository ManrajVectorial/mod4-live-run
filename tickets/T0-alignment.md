# T0 — Alignment: what I think we're building

*Written before any tickets, so it can be corrected cheaply. Sources: `docs/PRD.md` v1.0,
`docs/features.md` v1.0, `docs/project-brief.md`, `AGENTS.md`.*

## 1. The product

**Policy Assistant** is an internal web tool for Aldermere Bank operations and front-office
staff (about 1,400 people). It is not built for Compliance. A user asks a policy question in
their own words:

- **If the corpus can support an answer,** they get a plain-language answer citing the
  document, section and version it came from.
- **If it can't,** they get a refusal.

**It never tells staff what to do.** It says what the policy says, and points them to the team
that decides. Exceptions, judgement calls and conflicts between policies go to that team, not
to the tool. Which team a given refusal names is part of D5.

Every response is `answered`, `refused` or `degraded`.

- The **refusal is a rule**, run before any chat-model call.
- **`degraded`** means the chat model is off or failed, so the retrieved passages come back
  without a composed answer.

**The order:** the thin slice is F1–F5 (load, search, decide, answer, web page). F6–F8
(follow-ups, corpus browsing, history) are optional and dropped from the back.

## 2. Fixed: I may not change these

- **Protected files:** `backend/corpus/`, `docs/project-brief.md`, `docs/PRD.md`,
  `docs/features.md`, `AGENTS.md`, `CLAUDE.md`. Edits to the corpus, PRD and features are
  also denied in `.claude/settings.json`.
- **The agreed contract:** the PRD's 76 requirements, the API shapes (§5), the data model
  (§6), the Qdrant payload (§7) and the setting names (§8). Changing any of them needs your
  approval.
- **The stack:** Python 3.12 FastAPI, Qdrant, Postgres, Next.js, OpenRouter, GitHub Actions,
  Railway.
- **Rules (AGENTS.md):**
  - Stages run in order, and there is no code before the plan is approved.
  - Open decisions are yours.
  - Ask before adding an unlisted library, pushing to `main`, deploying, deleting data, or
    changing the API or data model.
  - Settings come from `.env` and are never committed. Nothing is hard-coded.
  - Tests are never weakened, skipped or deleted to get a pass.
  - No copyleft licences.
  - Only claim what I checked.

## 3. Where things live

| Path | What's there now |
|---|---|
| `backend/corpus/` | Five policy documents (four current, plus Travel and Expense v3.0, superseded), `MANIFEST.yaml`, `EVALUATION.md` (13 questions), `FICTION-AUDIT.md` |
| `docs/` | `project-brief.md`, `PRD.md`, `features.md` |
| `tickets/` | `01-requirements.md` (stage record), this file |
| `vectorforge-ticket-template.md` | Template for Linear tickets (Mavericks team, project test-live-demo) |
| `.claude/settings.json`, `AGENTS.md`, `CLAUDE.md`, `.gitignore` | Rules and locks |

- **No code exists yet:** no `backend/` app, no front end, no CI, no `.env`.
- **Git:** we work on `work/build`. `main` is protected (pull request required, 0 approvals,
  not enforced on admins) and has no required checks yet.
- **Repo:** https://github.com/ManrajVectorial/mod4-live-run

## 4. How to run it, as far as we know

**Nothing runs yet.** What is agreed so far:

- Settings come from a `.env` file using the PRD §8 names. The keys are `OPENROUTER_API_KEY`,
  `QDRANT_API_KEY` and `DATABASE_URL`.
- The API needs Postgres and Qdrant reachable, and refuses to start without
  `REFUSAL_THRESHOLD`.
- The order is: run ingestion, run the evaluation, start the API, start the web app.
- `/healthz` reports component status.

The commands, ports, module names, local Postgres and Qdrant setup, and Railway layout are all
**unknown until the plan**. I haven't checked that OpenRouter serves the embedding models we
will need.

## 5. Still open

The ten decisions, all unanswered:

| | Decision |
|---|---|
| D0 | Embedding model and dimensions |
| D1 | Chunk size and overlap |
| D2 | The refusal threshold, and how we pick it |
| D3 | How many passages to retrieve |
| D4 | Superseded policies: shown, hidden or flagged |
| D5 | What a refusal says |
| D6 | What happens when two policies conflict (worked example: Records Retention 7 years against Outsourcing 5) |
| D7 | How citations are grouped |
| D8 | How much conversation a follow-up sees |
| D9 | Whether a follow-up searches again, and on what |

**Also open:**

- PRD §12 item 7 now fails, because AGENTS.md changed. Unlocking the PRD to fix it needs
  your approval.
- The brief's Q1–Q4 belong to people outside the team.
- Items raised in `tickets/01-requirements.md`:
  - PR approvals
  - embeddings versus the kill switch
  - Compliance or Group Finance as the refusal contact
  - deferred feedback and re-indexing
  - history privacy
  - the health check gating deploys
  - the missing `ci/check_scope.py`
