# Policy Assistant — Features

| | |
|---|---|
| **Status** | **Draft v0.1, awaiting approval.** Once approved, this file is protected (AGENTS.md rule 1) |
| **Source** | `docs/PRD.md` §4 and §9 |

Eight features, in build order:

- **F1–F5 are the thin slice** (brief §10): one question, one cited answer or a refusal.
- **F6–F8 are optional.** If time runs short they are dropped from the back: F8 first, then
  F7, then F6.

Every requirement in PRD §4 and §9 belongs to exactly one feature (see the check at the end).

The commands in "Done when" use module names and ports that the plan has not fixed yet
(`app.ingest`, `app.evaluate`, API on `:8000`, web on `:3000`) **[ASSUMED]**. The plan will
replace them with the real ones, without changing what each line checks.

---

## F1 — Load the documents

Read the five MANIFEST documents, split them into passages, embed them, and store them in
Qdrant with their status.

| | |
|---|---|
| **Requirements** | REQ-I1, I2, I3, I4, I5, I6, I7, I8, I9, I10, I11 |
| **Decisions** | D0 (embedding model and dimensions), D1 (chunk size and overlap) |
| **Done when** | `python -m app.ingest && python -m app.ingest`, then a Qdrant point count on `$QDRANT_COLLECTION`: the total is the same after both runs, the count filtered to `status = superseded` is above zero, and `git status --porcelain backend/corpus` prints nothing |

## F2 — Search them

Embed a question and return the top-K passages with scores, plus the thirteen-question
evaluation command.

| | |
|---|---|
| **Requirements** | REQ-R1, R2, R3, R4 |
| **Decisions** | D0, D3 (top-K), D4 (superseded handling) |
| **Done when** | `python -m app.evaluate` writes a thirteen-row results table under `tickets/`, and the Q1 row shows `travel-expense-policy-v3.1` §4.2 in the top three |

## F3 — Decide whether to answer

Add the refusal rule and the `/api/ask` endpoint. Before F4 exists, a question that clears
the threshold comes back `degraded` (`generation_disabled`). Every exchange is recorded in
Postgres.

| | |
|---|---|
| **Requirements** | REQ-R5, R6, R7, R8 · REQ-C1, C2 · REQ-A2, A3, A4, A5 · NFR-2, NFR-3, NFR-4, NFR-6 |
| **Decisions** | D2 (refusal threshold), D5 (what a refusal says) |
| **Done when** | With the API running, `curl -s -w ' %{time_total}s\n' -H 'Content-Type: application/json' -d '{"question":"How many days of paid parental leave am I entitled to?"}' localhost:8000/api/ask` prints `"status":"refused"` in under 1.5 s, and the same call with Q1 prints `"status":"degraded"` with a source at `travel-expense-policy-v3.1` §4.2 |

## F4 — Write the answer

Add the chat model: a cited answer from the retrieved passages only, the kill switch,
citation validation, and the prompt version and model recorded on every answer.

| | |
|---|---|
| **Requirements** | REQ-A1 · REQ-G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11 · NFR-1, NFR-5 |
| **Decisions** | D3, D4, D6 (conflicting policies), D7 (citation grouping) |
| **Done when** | With `GENERATION_ENABLED=true`, `curl -s -H 'Content-Type: application/json' -d '{"question":"Does a claim of exactly £75 need approval?"}' localhost:8000/api/ask` prints `"status":"answered"`, an answer saying yes, a source at v3.1 §4.2, and non-null `prompt_version` and `model`. The same call with `GENERATION_ENABLED=false` prints `"status":"degraded"` |

## F5 — The web page

The ask page at `/`: question box, answer with expandable citations, a distinct refusal, a
distinct degraded state, the standing notice and the indexed date. The top bar has the name
and Reset. Light theme.

| | |
|---|---|
| **Requirements** | REQ-U1, U2, U3, U4, U5, U6, U7, U8, U9, U10, U11, U12, U13 · REQ-A10 |
| **Decisions** | D4, D5, D7 |
| **Done when** | With API and web running, open `http://localhost:3000`, ask Q1 and see an answer with an expandable T&E v3.1 §4.2 citation, the notice and the indexed date; ask Q11 and see a refusal that looks clearly different; the top bar shows only "Policy Assistant" and Reset |

---

*Optional from here. Drop from the back if time runs short.*

## F6 — Follow-up questions

Continue a conversation: context per D8, retrieval per D9, the refusal rule on every turn,
and Reset starting afresh.

| | |
|---|---|
| **Requirements** | REQ-C3, C4, C5, C6 |
| **Decisions** | D8 (context a follow-up sees), D9 (whether and on what a follow-up searches) |
| **Done when** | `curl` Q1 to `/api/ask` and keep its `conversation_id`; sending `"And does a claim of exactly that amount need it?"` with that ID prints `"status":"answered"` citing v3.1 §4.2, then `"Can I expense my partner's flight?"` with the same ID prints `"status":"refused"` |

## F7 — Browse the documents

`/corpus` and `/corpus/[id]`, with superseded documents labelled, citations linking to their
section, and a Corpus link in the top bar.

| | |
|---|---|
| **Requirements** | REQ-B1, B2, B3, B4, B5 · REQ-A6, A7 · REQ-U14 |
| **Decisions** | D4 |
| **Done when** | Open `http://localhost:3000/corpus` and see five documents with v3.0 labelled superseded; open `/corpus/travel-expense-policy-v3.0` and see a banner linking to v3.1; click a citation on `/` and land on its section |

## F8 — History

`/history`: past conversations newest first, each reopening with the citations stored at
answer time, and a History link in the top bar.

| | |
|---|---|
| **Requirements** | REQ-C7, C8 · REQ-A8, A9 · REQ-U15 |
| **Decisions** | None of D0–D9. **Blocked for release by brief Q3** (who may see a question): with no authentication, `/history` shows every user's questions |
| **Done when** | After the F6 run, `curl -s localhost:8000/api/conversations` lists that conversation first, and opening it at `http://localhost:3000/history` shows the same answers and citations as were shown originally |

---

## Coverage check

| Group | IDs | Feature |
|---|---|---|
| Ingestion | REQ-I1 – I11 | F1 |
| Retrieval | REQ-R1 – R4 | F2 |
| Refusal | REQ-R5 – R8 | F3 |
| Generation | REQ-G1 – G11 | F4 |
| Conversation | REQ-C1, C2 | F3 |
| | REQ-C3 – C6 | F6 |
| | REQ-C7, C8 | F8 |
| Browsing | REQ-B1 – B5 | F7 |
| API | REQ-A1 | F4 |
| | REQ-A2 – A5 | F3 |
| | REQ-A6, A7 | F7 |
| | REQ-A8, A9 | F8 |
| | REQ-A10 | F5 |
| Interface | REQ-U1 – U13 | F5 |
| | REQ-U14 | F7 |
| | REQ-U15 | F8 |
| Non-functional | NFR-2, 3, 4, 6 | F3 |
| | NFR-1, 5 | F4 |

There are 74 requirements: 11 I, 8 R, 11 G, 8 C, 5 B, 10 A, 15 U and 6 NFR. Each appears
exactly once.
