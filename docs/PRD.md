# Policy Assistant — Product Requirements (PRD)

| | |
|---|---|
| **Status** | **v1.0, reviewed and approved 2026-10-23. Protected** (AGENTS.md rule 1; Edit denied in `.claude/settings.json`) |
| **Source** | `docs/project-brief.md` v1.0, `backend/corpus/MANIFEST.yaml`, `backend/corpus/EVALUATION.md` |
| **Features** | `docs/features.md` assigns every requirement here to exactly one feature |
| **Stack** | Python 3.12 FastAPI API · Qdrant (vector search) · Postgres · Next.js front end · OpenRouter (chat and embedding models) · GitHub Actions · Railway |

Anything marked **[ASSUMED]** is a choice made while drafting that the brief and corpus do not
settle. Each one should be confirmed or corrected at review. Nothing in §10 is decided.

---

## §1 What we're building

A staff member asks a policy question in their own words. The system:

1. **Searches the policy passages.** It embeds the question and retrieves the most similar
   passages from the indexed corpus.
2. **Checks whether there is enough.** A deterministic rule compares the best retrieval score
   with a threshold. A model does not get to decide whether the corpus supports an answer
   (brief §9).
3. **Answers with citations, or refuses.**
   - If there is enough, a chat model composes a plain-language answer from those passages
     only, and every answer cites the policy sections it drew on.
   - If there isn't, the system refuses and makes no chat-model call.
   - If the chat model is switched off or fails, the system returns the retrieved passages
     without a composed answer: less useful, still honest, still working (brief §9).

**The product says what the policy says, never what someone should do.** It does not judge
exceptions, give advice or pick which of two conflicting policies wins.

Every response is exactly one of three statuses:

| Status | Meaning |
|---|---|
| `answered` | Retrieval cleared the threshold and the model composed a cited answer |
| `refused` | Retrieval did not clear the threshold. No chat-model call was made |
| `degraded` | Retrieval cleared the threshold, but no composed answer is returned, because generation is switched off, the provider failed, or the model's output failed citation validation. The retrieved passages are returned instead |

```
question ─▶ embed ─▶ Qdrant top-K ─▶ refusal rule ──┬─ below threshold ─▶ refused
                                                    └─ clears ─▶ GENERATION_ENABLED? ─┬─ no ──▶ degraded (passages)
                                                                                      └─ yes ─▶ chat model ─┬─ ok ───▶ answered (cited)
                                                                                                            └─ fail ─▶ degraded (passages)
every response ─▶ Postgres (conversation, messages, citations)
```

---

## §2 Screens

| Route | When | Purpose |
|---|---|---|
| `/` | Slice (F5) | **Ask page.** One question box; the answer, refusal or degraded result; citations underneath |
| `/history` | Later (F8, optional) | Past conversations and what was answered |
| `/corpus` | Later (F7, optional) | The indexed documents, current and superseded |
| `/corpus/[id]` | Later (F7, optional) | One document, section by section |

- **Top bar** on every page: the product name ("Policy Assistant") and a **Reset** button.
- **History** and **Corpus** links appear in the top bar only once those pages exist.
- **Light theme only.** No dark-mode variant.
- The ask page is the brief's "one screen that does one thing" (brief §11). It has no
  settings and no dashboard.
- `[id]` is the document's unique key `{policy id}-v{version}`, for example
  `travel-expense-policy-v3.1`. The MANIFEST `id` alone is not unique, because two travel
  versions share it. **[ASSUMED]**

---

## §3 Users and outcome

**Users:** operations and front-office staff at Aldermere Bank, roughly 1,400 people, who
hit a policy question in the middle of other work. Examples are a settlements analyst
mid-investigation, a relationship manager with a client on the phone, and an onboarding
officer checking a document set. The policy question is never the job (brief §2).

**Not users:** compliance and risk officers. They need the source documents, not an answer.
They benefit through fewer interruptions.

**The problem:** policy lives in four places, none of them definitive. Staff can't tell
which answer is current. In a supplied sample, 9 of 50 answers cited a superseded version
(brief §3). The cost is wrongness, not slowness.

**The outcome:** a cited, current answer in under a minute, with the source section visible
without leaving the page. Answers stay consistent, traceable and current because they are
derived from the documents (brief §4).

**Success measures** (brief §5, fictional supplied targets, measured 30 days after release):

| | Measure | Target |
|---|---|---|
| S1 | Median time to a usable answer | < 2 min |
| S2 | Answers citing a current policy version | > 95% |
| S3 | Questions reaching the Compliance mailbox | < 250 / month |
| S4 | Answers rated unhelpful | < 15% |
| S5 | Out-of-scope questions correctly declined | > 90% |

S5 is the one to defend hardest: **a confident answer to a question the corpus cannot support
is the failure this product must not have.**

---

## §4 Requirements

Each requirement is a single sentence that either passes or fails. Feature assignment is in
`docs/features.md`.

### Ingestion (REQ-I)

| ID | Requirement |
|---|---|
| REQ-I1 | Ingestion indexes exactly the files listed under `documents:` in `MANIFEST.yaml` (five), and no other file in `backend/corpus/` (`EVALUATION.md`, `FICTION-AUDIT.md` and `MANIFEST.yaml` are never indexed) |
| REQ-I2 | Ingestion stops with an error naming the file if a document's front matter (`id`, `version`, `status`, `effective`) disagrees with its MANIFEST entry |
| REQ-I3 | Every passage is cut exactly as D1 decides |
| REQ-I4 | Every passage records the number and title of the section it came from (for example, `4.2` and `Approval thresholds`) |
| REQ-I5 | Every passage is stored in Qdrant with every payload field listed in §7 |
| REQ-I6 | Passages are embedded with `EMBEDDING_MODEL`, and ingestion stops with an error if the returned vector length differs from `EMBEDDING_DIMENSIONS` |
| REQ-I7 | Superseded documents are indexed, not excluded, and each of their passages carries `status: superseded`, `superseded_by` and `superseded_on` (MANIFEST `superseded_version`) |
| REQ-I8 | Running ingestion twice on an unchanged corpus leaves the same passage IDs and the same passage count (no duplicates) |
| REQ-I9 | If ingestion fails part-way, the previously indexed passages stay searchable and unchanged **[ASSUMED]** |
| REQ-I10 | Ingestion never writes to, renames or deletes anything under `backend/corpus/` |
| REQ-I11 | Every passage records the time its ingestion run completed (`indexed_at`), so the indexed date can be shown with every answer (brief §8) |

### Retrieval and the refusal rule (REQ-R)

| ID | Requirement |
|---|---|
| REQ-R1 | A question is embedded with the same `EMBEDDING_MODEL` as the passages, and the `RETRIEVAL_TOP_K` passages with the highest cosine similarity are returned |
| REQ-R2 | Retrieved passages come back in descending score order, with each one's score and full §7 payload, and ties are broken by `passage_id` so the same question always returns the same order |
| REQ-R3 | Every retrieved passage carries its document `status`, and superseded passages are handled exactly as D4 decides |
| REQ-R4 | An evaluation command runs all thirteen `EVALUATION.md` questions and writes a results table (top score, whether the expected section is in the top three, outcome) to a file under `tickets/` |
| REQ-R5 | A question whose top retrieval score does not clear `REFUSAL_THRESHOLD`, as D2 defines clearing it, gets `status: refused` |
| REQ-R6 | The refusal rule runs before any chat-model call, and a refused request makes zero chat-model calls **[ASSUMED: "model call" means the chat model; embedding the question is necessarily a model call and comes first]** |
| REQ-R7 | `REFUSAL_THRESHOLD` has no default in code, and the API refuses to start if it is unset or not a number |
| REQ-R8 | At the chosen threshold, Q11–Q13 are refused and Q1–Q10 are not refused with the expected section in the top three. Any shortfall is recorded, with the score distribution, in the D2 decision record |

### Generation (REQ-G)

| ID | Requirement |
|---|---|
| REQ-G1 | The chat model is called only when the refusal rule has passed and `GENERATION_ENABLED` is true |
| REQ-G2 | The prompt sent to the chat model contains only the system prompt, the retrieved passages, the question and the conversation context allowed by D8. It contains no other source of policy |
| REQ-G3 | The system prompt lives in a versioned file in the repository, and its `prompt_version` identifier changes whenever the prompt text changes (a test fails if the text changes but the version does not) |
| REQ-G4 | An answer must cite at least one retrieved passage by marker, and an answer that cites nothing, or cites a marker not in the retrieved set, is returned as `degraded` with reason `invalid_citations`, not as `answered` **[ASSUMED]** |
| REQ-G5 | Every `answered` response records the `prompt_version` and the `model` that produced it, in the response and in Postgres |
| REQ-G6 | With `GENERATION_ENABLED=false`, a question that clears the threshold returns `status: degraded`, reason `generation_disabled`, with the retrieved passages and zero chat-model calls |
| REQ-G7 | A chat-provider error or a response slower than `GENERATION_TIMEOUT_SECONDS` returns `status: degraded` with the retrieved passages, and logs the error type (never silently) |
| REQ-G8 | No answer to Q1–Q10 tells the user what to do. Each states what the policy says, checked by reading the ten evaluation answers and recording the check in `tickets/` |
| REQ-G9 | An answer that draws on a superseded passage states that passage's version and status, as D4 decides |
| REQ-G10 | The response to Q10, the known conflict, behaves exactly as D6 decides |
| REQ-G11 | Each answer to Q1–Q10 states the expected fact in `EVALUATION.md` (including "yes" for exactly £75, Q2), checked and recorded in `tickets/` |

### Conversation (REQ-C)

| ID | Requirement |
|---|---|
| REQ-C1 | Every `/api/ask` call stores the question and the response (any status) as two messages, with the response's citations, in Postgres |
| REQ-C2 | An `/api/ask` call without `conversation_id` creates a new conversation and returns its ID |
| REQ-C3 | An `/api/ask` call with a known `conversation_id` appends to that conversation. An unknown one returns 404 |
| REQ-C4 | A follow-up question gives the chat model exactly the earlier context D8 allows, and no more |
| REQ-C5 | A follow-up question is retrieved as D9 decides, and the refusal rule applies to every follow-up, however the earlier turns went |
| REQ-C6 | After Reset, the next question starts a new conversation and none of the earlier conversation reaches the model |
| REQ-C7 | `/history` lists stored conversations newest first, each with its first question, its time and the status of each answer |
| REQ-C8 | Opening a past conversation shows each response with the citations stored when it was answered, not a fresh retrieval |

### Corpus browsing (REQ-B)

| ID | Requirement |
|---|---|
| REQ-B1 | `/corpus` lists all five indexed documents with title, version, status, effective date and owner, and labels the superseded one as superseded |
| REQ-B2 | `/corpus/[id]` shows the whole document section by section, in document order |
| REQ-B3 | A superseded document's page shows a superseded banner linking to the current version |
| REQ-B4 | Each citation on the ask page links to its section on `/corpus/[id]` |
| REQ-B5 | An unknown `[id]` shows a not-found page, not an error page |

### API (REQ-A)

| ID | Requirement |
|---|---|
| REQ-A1 | `POST /api/ask` returns exactly the §5.1 shape for all three statuses |
| REQ-A2 | Every `/api/ask` success response has `status` equal to `answered`, `refused` or `degraded` |
| REQ-A3 | A blank question, or one longer than `MAX_QUESTION_CHARS`, returns 422 before any retrieval |
| REQ-A4 | Every non-2xx response uses the §5.7 error shape and contains no stack trace |
| REQ-A5 | `GET /healthz` returns the §5.6 shape |
| REQ-A6 | `GET /api/corpus` returns the §5.2 shape |
| REQ-A7 | `GET /api/corpus/{document_id}` returns the §5.3 shape, or 404 for an unknown ID |
| REQ-A8 | `GET /api/conversations` returns the §5.4 shape |
| REQ-A9 | `GET /api/conversations/{id}` returns the §5.5 shape, or 404 for an unknown ID |
| REQ-A10 | The API accepts browser requests only from origins listed in `CORS_ALLOWED_ORIGINS` |

### Interface (REQ-U)

| ID | Requirement |
|---|---|
| REQ-U1 | `/` shows a labelled question box and an Ask button, and pressing Enter submits **[ASSUMED]** |
| REQ-U2 | An `answered` response shows the answer with its citations under it |
| REQ-U3 | Each citation can be expanded in place to show the passage text, without leaving the page (brief §4, A3) |
| REQ-U4 | A `refused` response looks unmistakably different from an answer and shows the D5 refusal text |
| REQ-U5 | A `degraded` response says that no answer was composed, and shows the retrieved passages as sources |
| REQ-U6 | Every `answered` and `degraded` response shows a notice that this is what the policy says, not a decision, and that exceptions go to a person (brief §8) |
| REQ-U7 | Every `answered` and `degraded` response shows the date the corpus was indexed |
| REQ-U8 | Beyond the label REQ-U17 requires, superseded citations are shown, hidden or flagged as D4 decides |
| REQ-U9 | The top bar shows "Policy Assistant" and a Reset button, and Reset clears the page |
| REQ-U10 | Until F7 and F8 are built, the top bar shows no History or Corpus link |
| REQ-U11 | Every page uses the light theme, whatever the operating system's colour setting |
| REQ-U12 | While a question is pending, the Ask button is disabled and a loading state shows, and a failed request shows an error message (never a blank result) |
| REQ-U13 | The ask page works at 375 px wide with no horizontal scrolling **[ASSUMED]** |
| REQ-U14 | Once `/corpus` exists, the top bar shows a Corpus link |
| REQ-U15 | Once `/history` exists, the top bar shows a History link |
| REQ-U16 | Every citation, wherever it appears (answered and degraded results, history, corpus links), shows the document title, the section number and title, and the document version |
| REQ-U17 | Superseded text is never presented as current: every passage or citation from a superseded document carries a visible "Superseded" label, and no answer states anything from a superseded passage without saying it is superseded |

---

## §5 The API

All endpoints are JSON. All IDs are UUIDs unless stated. Times are ISO 8601 UTC. The path
prefix `/api` is **[ASSUMED]**.

### §5.1 `POST /api/ask`

Request:

```json
{
  "question": "What is the approval threshold for a travel expense claim?",
  "conversation_id": null
}
```

`conversation_id` is optional. Leave it out or send `null` to start a new conversation.

**Response 200: answered**

```json
{
  "status": "answered",
  "conversation_id": "7f1c2a9e-0b7d-4a51-9b1e-3d6f0f2c8a11",
  "message_id": "c2b0e5d4-1f3a-4e8b-a7d2-5e9c1b0f6a22",
  "answer": "Under the Travel and Expense Policy, a single claim of £75 or more needs line-manager approval before it is reimbursed [1].",
  "refusal": null,
  "degraded": null,
  "sources": [
    {
      "marker": 1,
      "passage_id": "travel-expense-policy-v3.1:4.2:0",
      "document_id": "travel-expense-policy-v3.1",
      "policy_id": "travel-expense-policy",
      "title": "Travel and Expense Policy",
      "version": "3.1",
      "status": "current",
      "effective": "2026-04-01",
      "superseded_by": null,
      "section": "4.2",
      "section_title": "Approval thresholds",
      "text": "The following thresholds apply to a single claim: …",
      "score": <number>
    }
  ],
  "meta": {
    "prompt_version": "answer-v1",
    "model": "<value of CHAT_MODEL as reported by the provider>",
    "top_score": <number>,
    "threshold": <REFUSAL_THRESHOLD>,
    "retrieved": <int>,
    "corpus_indexed_at": "2026-10-23T09:00:00Z",
    "latency_ms": 2140
  },
  "created_at": "2026-10-23T10:15:02Z"
}
```

- For `answered`, `sources` holds only the passages the answer cites, and `marker` matches
  the `[n]` in `answer` **[ASSUMED]**.
- The list is flat. D7 decides how citations are grouped for display. If D7 needs grouping
  inside the API, this shape changes before approval.
- `<number>`, `<int>` and `<REFUSAL_THRESHOLD>` stand for values that depend on D0–D3. Those decisions are ours, at the planning stage, so no example here carries a number for them.

**Response 200: refused**

```json
{
  "status": "refused",
  "conversation_id": "…",
  "message_id": "…",
  "answer": null,
  "refusal": {
    "reason": "below_threshold",
    "message": "<D5 refusal text>"
  },
  "degraded": null,
  "sources": "<per D5: empty, or the nearest passages>",
  "meta": {
    "prompt_version": null,
    "model": null,
    "top_score": <number>,
    "threshold": <REFUSAL_THRESHOLD>,
    "retrieved": <int>,
    "corpus_indexed_at": "2026-10-23T09:00:00Z",
    "latency_ms": 410
  },
  "created_at": "…"
}
```

Whether `sources` is empty on a refusal, or shows the nearest passages, is part of D5.
The field is always present.

**Response 200: degraded**

```json
{
  "status": "degraded",
  "conversation_id": "…",
  "message_id": "…",
  "answer": null,
  "refusal": null,
  "degraded": {
    "reason": "generation_disabled"
  },
  "sources": [ { "marker": 1, "passage_id": "…", "…": "same fields as above" } ],
  "meta": {
    "prompt_version": null,
    "model": null,
    "top_score": <number>,
    "threshold": <REFUSAL_THRESHOLD>,
    "retrieved": <int>,
    "corpus_indexed_at": "…",
    "latency_ms": 380
  },
  "created_at": "…"
}
```

- `degraded.reason` is one of `generation_disabled`, `provider_error`, `provider_timeout` or
  `invalid_citations`.
- For `degraded`, `sources` holds every retrieved passage at or above the threshold
  **[ASSUMED]**.
- For `provider_error`, `provider_timeout` and `invalid_citations`, `meta.prompt_version` and
  `meta.model` record what was attempted **[ASSUMED]**.

**Errors:** 404 for an unknown `conversation_id`, 422 for a blank or over-long question
(§5.7 shape).

### §5.2 `GET /api/corpus`

```json
{
  "documents": [
    {
      "document_id": "travel-expense-policy-v3.1",
      "policy_id": "travel-expense-policy",
      "title": "Travel and Expense Policy",
      "version": "3.1",
      "status": "current",
      "effective": "2026-04-01",
      "owner": "Group Finance",
      "supersedes": "3.0",
      "superseded_by": null,
      "superseded_on": null,
      "passage_count": <int>,
      "indexed_at": "2026-10-23T09:00:00Z"
    }
  ]
}
```

### §5.3 `GET /api/corpus/{document_id}`

```json
{
  "document": { "…": "same fields as one item of §5.2" },
  "current_document_id": "travel-expense-policy-v3.1",
  "sections": [
    {
      "section": "4.2",
      "section_title": "Approval thresholds",
      "heading_path": ["4. Approval", "4.2 Approval thresholds"],
      "passages": [
        { "passage_id": "travel-expense-policy-v3.1:4.2:0", "text": "…" }
      ]
    }
  ]
}
```

`current_document_id` is the current version of the same policy. For a current document it
equals its own `document_id`. Returns 404 for an unknown ID.

### §5.4 `GET /api/conversations`

```json
{
  "conversations": [
    {
      "conversation_id": "…",
      "created_at": "…",
      "updated_at": "…",
      "first_question": "What is the approval threshold for a travel expense claim?",
      "message_count": 4,
      "statuses": ["answered", "refused"]
    }
  ]
}
```

The list is newest first. `statuses` lists each answer's status, in order. Pagination is
not specified for this build **[ASSUMED]**.

### §5.5 `GET /api/conversations/{id}`

```json
{
  "conversation_id": "…",
  "created_at": "…",
  "messages": [
    { "message_id": "…", "role": "user", "content": "What is the approval threshold…?", "created_at": "…" },
    {
      "message_id": "…",
      "role": "assistant",
      "status": "answered",
      "answer": "…",
      "refusal": null,
      "degraded": null,
      "sources": [ { "…": "as stored at answer time" } ],
      "meta": { "prompt_version": "answer-v1", "model": "…", "top_score": <number>, "threshold": <REFUSAL_THRESHOLD>, "retrieved": <int>, "corpus_indexed_at": "…", "latency_ms": 2140 },
      "created_at": "…"
    }
  ]
}
```

Returns 404 for an unknown ID.

### §5.6 `GET /healthz`

Always `200` while the process is running, even when a dependency is down:

```json
{
  "status": "ok",
  "components": {
    "postgres": "ok",
    "qdrant": "unreachable",
    "generation": "disabled"
  },
  "version": "<git commit SHA>"
}
```

- Top-level `status` is `ok` when every component is `ok` (or `generation` is `disabled`),
  and `degraded` otherwise.
- Component values are `ok`, `unreachable` and, for `generation` only, `disabled`.
- `healthz` does not call the chat model **[ASSUMED]**. `generation` reports only the
  `GENERATION_ENABLED` setting.

### §5.7 Error shape

Every non-2xx response:

```json
{ "error": { "code": "question_blank", "message": "Enter a question." } }
```

The error codes are `question_blank`, `question_too_long`, `conversation_not_found`,
`document_not_found` and `internal_error`.

---

## §6 Postgres data model

```
conversations 1 ──< messages 1 ──< citations
```

**`conversations`**

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `created_at` | timestamptz not null | |
| `updated_at` | timestamptz not null | Set on every new message |

**`messages`**

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `conversation_id` | uuid FK → conversations, not null | |
| `seq` | int not null | Order within the conversation. Unique with `conversation_id` |
| `role` | text not null | `user` or `assistant` |
| `content` | text | The question for `user`, the composed answer for `answered`, otherwise null |
| `status` | text | `answered`, `refused` or `degraded` on assistant rows, null on user rows |
| `refusal_reason` | text | |
| `refusal_message` | text | The D5 text as shown |
| `degraded_reason` | text | |
| `prompt_version` | text | Required when `status = answered` (check constraint) |
| `model` | text | Required when `status = answered` (check constraint) |
| `top_score` | real | |
| `threshold` | real | The threshold in force when answered |
| `retrieved` | int | |
| `corpus_indexed_at` | timestamptz | |
| `latency_ms` | int | |
| `created_at` | timestamptz not null | |

**`citations`** (one row per source returned with an assistant message)

| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `message_id` | uuid FK → messages, not null | |
| `marker` | int not null | Matches `[n]` in the answer |
| `passage_id` | text not null | |
| `document_id` | text not null | For example `travel-expense-policy-v3.1` |
| `policy_id` | text not null | |
| `title` | text not null | |
| `version` | text not null | Supports S2: which version each answer used |
| `status` | text not null | Document status **at answer time** |
| `section` | text not null | |
| `section_title` | text not null | |
| `score` | real not null | |
| `text` | text not null | The passage text as shown, kept so history survives a re-index |

There is no feedback table in this build; see §11.

---

## §7 What's stored with every passage in Qdrant

The collection is named by `QDRANT_COLLECTION`. The vector size is `EMBEDDING_DIMENSIONS`
(D0). Distance is cosine **[ASSUMED]**. Point IDs are a UUIDv5 of `passage_id`, so
re-ingestion is idempotent **[ASSUMED]**.

| Payload field | Example | Source |
|---|---|---|
| `passage_id` | `travel-expense-policy-v3.1:4.2:0` | `{document_id}:{section}:{chunk index}` |
| `document_id` | `travel-expense-policy-v3.1` | `{id}-v{version}` |
| `policy_id` | `travel-expense-policy` | Front matter `id` |
| `title` | `Travel and Expense Policy` | Front matter |
| `version` | `3.1` | Front matter |
| `status` | `current` or `superseded` | Front matter (REQ-I7) |
| `effective` | `2026-04-01` | Front matter |
| `supersedes` | `3.0` or null | Front matter |
| `superseded_by` | `3.1` or null | Front matter |
| `superseded_on` | `2026-04-01` or null | Front matter |
| `owner` | `Group Finance` | Front matter |
| `source_file` | `travel-expense-policy-v3.1.md` | MANIFEST |
| `section` | `4.2` | Heading |
| `section_title` | `Approval thresholds` | Heading |
| `heading_path` | `["4. Approval", "4.2 Approval thresholds"]` | Headings |
| `chunk_index` | `0` | Position within the section |
| `order` | `17` | Position within the document, for `/corpus/[id]` |
| `text` | passage text | |
| `content_hash` | SHA-256 of `text` | |
| `embedding_model` | value of `EMBEDDING_MODEL` | |
| `indexed_at` | `2026-10-23T09:00:00Z` | Ingestion run (REQ-I11) |

---

## §8 Settings

Every setting is an environment variable, read from a `.env` file locally (never committed)
and from Railway variables when deployed. No values appear here or in code. Required
settings have no code default: the service refuses to start without them, and names the
missing variable without printing any value.

**API**

| Variable | Purpose | Secret |
|---|---|---|
| `OPENROUTER_API_KEY` | Chat and embedding provider key | **yes** |
| `OPENROUTER_BASE_URL` | Provider endpoint | |
| `CHAT_MODEL` | Model that composes answers | |
| `CHAT_TEMPERATURE` | Sampling temperature **[ASSUMED needed]** | |
| `CHAT_MAX_TOKENS` | Answer length cap **[ASSUMED needed]** | |
| `GENERATION_ENABLED` | Kill switch (`true` / `false`) | |
| `GENERATION_TIMEOUT_SECONDS` | Chat-call timeout before `degraded` | |
| `EMBEDDING_MODEL` | D0 | |
| `EMBEDDING_DIMENSIONS` | D0 | |
| `CHUNK_SIZE` | D1 | |
| `CHUNK_OVERLAP` | D1 | |
| `REFUSAL_THRESHOLD` | D2 | |
| `RETRIEVAL_TOP_K` | D3 | |
| *(named when D8 is decided)* | D8: how much conversation a follow-up sees | |
| `MAX_QUESTION_CHARS` | REQ-A3 | |
| `QDRANT_URL` | Vector store | |
| `QDRANT_API_KEY` | Vector store key | **yes** |
| `QDRANT_COLLECTION` | Collection name | |
| `DATABASE_URL` | Postgres connection string (contains a password) | **yes** |
| `CORPUS_DIR` | Path to the corpus for ingestion | |
| `CORS_ALLOWED_ORIGINS` | REQ-A10 | |
| `LOG_LEVEL` | | |

**Front end**

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Where the browser sends API calls **[ASSUMED: the browser calls the API directly, not through a Next.js proxy]** |

D4, D5, D6 and D9 may add settings once decided. `PORT` is supplied by Railway.
`prompt_version` is not a setting: it lives with the prompt file in the repository (REQ-G3).

---

## §9 Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | On the deployed service, the median `/api/ask` latency for Q1–Q10 is at most 5 s, and none exceeds 8 s **[ASSUMED: how "about 5 seconds" is measured]** |
| NFR-2 | On the deployed service, each of Q11–Q13 returns `refused` within 1.5 s |
| NFR-3 | `GET /healthz` returns 200 within 1 s while Postgres is stopped, and again while Qdrant is stopped, and reports the stopped component as `unreachable` |
| NFR-4 | No log line at any level contains question text or answer text (a test submits a unique marker question and searches the captured logs for it) |
| NFR-5 | Every `/api/ask` call logs one line with request ID, status, top score, latency, and the chat model's token counts when it was called (brief §9: latency, cost, refusal rate) |
| NFR-6 | No secret listed in §8 appears in any log line, response body or committed file |

---

## §10 Open decisions

**None of these is decided.** Each is decided by us at the design and planning stage, and its
record goes in `tickets/`.

| ID | Decision | What depends on it | Evidence to hand |
|---|---|---|---|
| **D0** | Embedding model and dimensions | Ingestion, retrieval, the Qdrant vector size, every score that D2 is tuned on (changing D0 means re-indexing and re-tuning D2) | Stack fixes OpenRouter as provider. *If the embedding provider is down, retrieval is down too, which limits what the kill switch can keep working (brief §8 constraint).* |
| **D1** | Chunk size and overlap | REQ-I3, passage boundaries, score distribution | Sections run from one line to a large table (for example T&E §4.2, KYC §6.4). This also covers whether a passage may cross a numbered section and whether a table may be split |
| **D2** | The refusal threshold, and how we pick it | REQ-R5, R8, S5 | `EVALUATION.md` requires a recorded score distribution over all thirteen. Q11 is "inferable, not absent" and Q12 has adjacent KYC material, so both may score moderately. This also covers what "clearing" means at the boundary. The brief (§9) says "nothing above threshold" refuses |
| **D3** | How many passages to retrieve (top-K) | Prompt size, latency, whether Q10's two sections both arrive | Q8 and Q10 each expect two sections |
| **D4** | Superseded policies: shown, hidden or flagged | Retrieval, answer wording, citation display, `/corpus` | T&E v3.0 says £50, v3.1 says £75. v3.0 still governs expenses incurred before 1 April 2026 (its own banner). REQ-I7 requires it to be indexed either way. Whatever D4 decides, REQ-U17 holds: superseded text is never presented as current |
| **D5** | What a refusal says | REQ-U4, the refusal payload, whether nearest passages are shown | The brief §12 example points at **Compliance**. MANIFEST and `EVALUATION.md` Q11 point at **Group Finance**. These differ |
| **D6** | What happens when two policies conflict | REQ-G10, Q10 | The known clash, worked through below. Brief Q4 says "resist the temptation to answer it in code" |
| **D7** | How citations are grouped | `sources` shape, ask-page layout | Brief §10: the "clickable, deduplicated citation panel" is outside the slice |
| **D8** | How much conversation a follow-up sees | REQ-C4, prompt size | — |
| **D9** | Whether a follow-up searches again, and on what | REQ-C5 | Rewriting a follow-up with the chat model before retrieval would put a chat-model call ahead of the refusal rule, which conflicts with REQ-R6 |

### D6 worked example: the clash we already know about (undecided)

| | Records Retention and Data Handling v4.0 | Outsourcing and Third-Party Risk v1.8 |
|---|---|---|
| **Section** | §4.1 General table, client correspondence | §6.4 Return and destruction on exit |
| **Requires** | Keep client correspondence **7 years** | Provider destroys all copies **within 5 years** |
| **Clock starts** | End of the client relationship | Termination of the outsourcing arrangement |
| **Status** | Current (effective 2026-02-01) | Current (effective 2026-03-01) |
| **Related text** | §4.4: records held by a third party remain the Bank's and are subject to §4.1 | Note to §6.4: where the two cannot both be satisfied, "escalate to Group Legal and Group Operational Risk jointly. Do not resolve the conflict locally" |

**Where they collide.** A provider holds the only copy of a client's correspondence, and the
arrangement ends. Outsourcing requires that copy destroyed within five years. Records
Retention requires it kept for seven years after the client relationship ends, which may be
later still. Both cannot be met. This is `EVALUATION.md` Q10 and MANIFEST `known_conflict`.

**Traps to avoid.**
- Records Retention §4.3 ("the longer period applies") governs a record that falls into two
  categories *within that policy*. It is not a rule for choosing between two policies.
- The two clocks start at different events, so "7 is longer than 5" is not the whole clash.

**What D6 must settle, at planning:** what the response does when retrieved passages from two
current policies conflict, as in this case. No option is chosen here.

**Open questions owned outside the team** (brief §6, not ours to decide, but they block release):

| | Question | Owner | Touches |
|---|---|---|---|
| Q1 | Who owns the corpus once live | COO | Re-indexing |
| Q2 | Must every answer be retained for audit | Compliance | §6 retention |
| Q3 | Who may see a user's question, and for how long it is kept | Privacy | REQ-C1 stores question text. `/history` (F8) has no authentication, so it would show every user's questions |
| Q4 | Conflicting policy: refuse or show both | Compliance | D6 |

---

## §11 Out of scope

From the brief (§7):

| | Why |
|---|---|
| Editing or authoring policy | The assistant reads. Policy Office writes |
| Deciding whether an exception is permitted | Judgement stays with humans, by design |
| Customer-facing use of any kind | Internal staff tool only |
| Integrating with case management or the CRM | Later, if the product earns it |
| Answering from anything other than the approved corpus | No web search, no general knowledge |
| Non-English policy documents | The policy set is English-only |

From the thin slice (brief §10), and so outside this build unless added: tuned confidence
thresholds beyond D2, automatic re-indexing on change, authentication and per-user history.

**Not covered by F1–F8 although the brief lists them as in scope** (brief §7). These are
treated as deferred **[ASSUMED]** and need confirming:

- "Staff can say whether an answer helped" (feedback, success measure S4)
- Scheduled re-indexing (brief §8). F1 provides a re-runnable ingestion command only

---

## §12 Definition of done

The build is done when all of the following are true:

1. Every requirement assigned to a built feature passes, shown by an automated test or, where
   the requirement says so, a recorded check in `tickets/`.
2. D0–D9 are each decided by us and recorded in `tickets/` with the options and the
   reasoning. D2 includes the thirteen-question score distribution.
3. The evaluation results table (REQ-R4) for the deployed configuration is committed under
   `tickets/`.
4. GitHub Actions runs tests, a security scan and a dependency-licence check (no GPL, AGPL,
   LGPL, SSPL or EUPL) on every push, and all pass on the merged commit.
5. `main` is deployed on Railway. `/healthz` returns 200 there, and the brief §12 day-one
   scenario passes on the deployed URL: Q1 answered citing T&E v3.1 §4.2, and Q11 refused.
6. NFR-1 to NFR-6 pass against the deployed service.
7. Nothing under `backend/corpus/`, `docs/project-brief.md`, `AGENTS.md` or `CLAUDE.md` has
   changed since the first commit (`git diff b056bc6 -- <those paths>` is empty).
8. Each stage (requirements, design and planning, implementation, testing and review,
   deployment, verification) has its record in `tickets/`.
