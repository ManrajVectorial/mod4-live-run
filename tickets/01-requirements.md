# Stage 01 — Requirements

| | |
|---|---|
| **Status** | Drafted, **awaiting approval** |
| **Date** | 2026-10-23 |
| **Branch** | `work/build` |

## Read

`docs/project-brief.md`; every corpus document (T&E v3.1 and v3.0, KYC v2.4, Records Retention
v4.0, Outsourcing v1.8); `MANIFEST.yaml`; `EVALUATION.md`; `FICTION-AUDIT.md`.

## Produced

- `docs/PRD.md` v0.1: §1–§12, with 74 requirements (68 REQ and 6 NFR)
- `docs/features.md` v0.1: F1–F8, with every requirement assigned to exactly one feature,
  checked mechanically by diffing the ID lists

## Not decided (PRD §10)

D0–D9 are all open. Brief Q1–Q4 are open and owned outside the team.

## Raised for review

1. **Approval on PRs.** Brief §11 says nothing merges without "a named human approving".
   `main` protection is set to 0 approvals, as instructed.
2. **Kill switch and embeddings.** Embeddings come from OpenRouter, so with the provider down
   retrieval is down too, and the kill switch can't keep search working (PRD §10 D0).
3. **Refusal contact.** The brief points refusals at Compliance. MANIFEST and EVALUATION point
   at Group Finance (D5).
4. **Missing features.** Feedback (S4) and scheduled re-indexing are in the brief's scope but
   in no feature. They are marked deferred [ASSUMED] (PRD §11).
5. **History privacy.** `/history` without authentication shows every user's questions
   (brief Q3, F8).
6. **Health check.** `/healthz` stays 200 when dependencies are down, as required. As the
   deploy health check, that won't stop a deploy whose database is broken (brief §11).
7. **Missing script.** MANIFEST mentions `ci/check_scope.py`, which does not exist yet.

## Approval

- [ ] PRD approved, after which `docs/PRD.md` is protected
- [ ] Features approved, after which `docs/features.md` is protected
