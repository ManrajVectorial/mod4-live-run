# Stage 01 — Requirements

| | |
|---|---|
| **Status** | **Approved 2026-10-23.** `docs/PRD.md` and `docs/features.md` are v1.0 and protected |
| **Branch** | `work/build` |

## Read

`docs/project-brief.md`; every corpus document (T&E v3.1 and v3.0, KYC v2.4, Records Retention
v4.0, Outsourcing v1.8); `MANIFEST.yaml`; `EVALUATION.md`; `FICTION-AUDIT.md`.

## Produced

- `docs/PRD.md` v1.0: §1–§12, with 76 requirements (70 REQ and 6 NFR)
- `docs/features.md` v1.0: F1–F8, with every requirement assigned to exactly one feature,
  checked mechanically by diffing the ID lists

## Changes at review (v0.1 → v1.0)

**Values removed from §10 decisions**, so they stay ours for planning:

- REQ-I3 and I4 no longer say passages never cross a section or split a table. I3 now says
  "cut as D1 decides". I4 now requires the section number and title. Both questions moved
  into D1.
- REQ-R5 no longer assumes the boundary is inclusive. What "clearing" the threshold means
  moved into D2, noting that the brief says "nothing above threshold".
- In the §5 examples, the threshold (0.55), the scores (0.81, 0.31), the retrieved count (5)
  and the passage count (42) are now placeholders.
- The refused example's `sources` now reads "per D5" instead of `[]`.
- §8 `CONVERSATION_CONTEXT_TURNS` is now "named when D8 is decided", because the name
  presumed that D8 counts in turns.

**Added:**

- **REQ-U16:** every citation shows the document, the section and the version (F5)
- **REQ-U17:** superseded text is never presented as current (F5). D4 now notes that it holds
  whatever D4 decides
- **§10, D6 worked example:** Records Retention §4.1 (7 years from end of relationship)
  against Outsourcing §6.4 (destroy within 5 years of termination). Still undecided

**Adjusted to avoid overlap:**

- REQ-U2 is now "answer with its citations under it". The document, section and version
  detail moved to U16
- REQ-U8 is now "beyond U17's label, per D4"

**Kept:** all other [ASSUMED] items, as instructed.

## Not decided

D0–D9 are all open. Brief Q1–Q4 are open and owned outside the team.

## Raised at review, still open

1. **Approval on PRs.** Brief §11 says nothing merges without "a named human approving".
   `main` is set to 0 approvals.
2. **Kill switch and embeddings.** With the embedding provider down, retrieval is down too
   (D0).
3. **Refusal contact.** The brief points refusals at Compliance. MANIFEST and EVALUATION point
   at Group Finance (D5).
4. **Missing features.** Feedback (S4) and scheduled re-indexing are deferred [ASSUMED].
5. **History privacy.** `/history` without authentication exposes every user's questions
   (brief Q3, F8).
6. **Health check.** `/healthz` always returns 200, so as the deploy health check it won't
   stop a deploy whose database is broken.
7. **Missing script.** MANIFEST mentions `ci/check_scope.py`, which does not exist.

## Locks applied

- AGENTS.md rule 1 now names `docs/PRD.md` and `docs/features.md`. Edited on the user's
  explicit instruction
- `.claude/settings.json` adds the deny rules `Edit(/docs/PRD.md)` and
  `Edit(/docs/features.md)`

## Approval

- [x] PRD approved, 2026-10-23
- [x] Features approved, 2026-10-23
