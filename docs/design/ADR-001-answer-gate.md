# ADR-001 — The answer gate: a deterministic rule before the model

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-23 |
| **Decided by** | Us (the product team), at design and planning |
| **Requirements** | REQ-R5, R6, R7, R8 (gate) · REQ-G1, G2, G4 (second layer) · NFR-2 |
| **Feature** | F3 — Decide whether to answer (MAV-796) |
| **Related decisions** | D2 (threshold value and how it is picked) is still open. This ADR fixes the mechanism, not the number |

## Context

The app has to decide, for every question, whether the policy corpus can support an answer at
all. The brief treats this as the product's defining behaviour:

- **The failure the product must not have** is a confident answer to a question the corpus
  cannot support (brief §5, S5).
- **Who decides:** "A model does not get to decide whether it knows something" (brief §9).
- **The model-off test:** turning the model off must leave a working policy search (brief §9).

The fixed evaluation set (`backend/corpus/EVALUATION.md`) has 13 questions:

- **Q1–Q10 must be answered.** This includes Q10, the Records Retention and Outsourcing
  conflict.
- **Q11–Q13 must be refused.** Two of these are hard:
  - Q11 (partner's flight) is *inferable, not stated*: a careful reader can reason to an answer
    from §2.1.
  - Q12 (client cryptocurrency) sits next to real KYC material.

The acceptance criteria (T1) require all 13 to pass on a single run, and refusals within 1.5 s
(NFR-2).

## Decision

**Option B: search, then a simple deterministic rule checks the matches before the chat model
is ever called.**

1. **Search.** Embed the question and retrieve the top passages with their similarity scores.
2. **Gate.** If the top score does not clear `REFUSAL_THRESHOLD`, the response is `refused`.
   No chat-model call is made.
3. **Answer.** Otherwise, if `GENERATION_ENABLED` is true, the chat model writes the answer from
   those passages only.
4. **Fall back.** If the model is off or fails, the response is `degraded` and carries the
   passages.

**Second layer.** This does not replace the gate:

- The answer must cite retrieved passages by marker (REQ-G4). An answer that cites nothing it
  was given comes back `degraded`, not `answered`.
- The prompt restricts the model to the supplied passages (REQ-G2).

**What stays open:**

- **D2:** the threshold value, how it is chosen, and what "clearing" means at the boundary.
  Picking it requires the recorded score spread over all 13 questions.

## Alternatives considered

### A — Search, then give everything to the model and let it decide

Retrieve the top passages, hand them all to the chat model with the question, and instruct it
to refuse if they don't support an answer.

**Rejected because:**
- **It hands the decision to the model.** The brief rules this out (§9).
- **It invites the Q11 failure.** A model reasons from §2.1 to a rule Aldermere never wrote,
  and states it as confidently as a real one.
- **Refusals aren't repeatable.** The same question can flip between runs, so a single-run pass
  on all 13 can't be relied on.
- **Refusals are slow.** Every refusal costs a model call, which puts the 1.5 s target (NFR-2)
  at risk.
- **It fails the model-off test.** Nothing decides when the model is off.

### C — The model answers first, then the answer is checked

Always generate. Then validate that the answer cites retrieved passages and that its claims
appear in them, and refuse if the check fails.

**Rejected because:**
- **Refusals are slow and costly.** Every question pays for a full model call and full answer
  latency, refusals included.
- **The check can't be both reliable and fair.** Checking "is this claim supported?" needs
  either a second model, which reintroduces A's problem, or strict text matching, which rejects
  good paraphrases.
- **Unsupported answers exist before they're caught.** Every one has to be caught reliably.
- **It fails the model-off test.** There is nothing to check when the model is off.

**Kept from C:** the citation check, as a second layer behind the gate (REQ-G4), not as the
gate itself.

## Consequences

**Positive**
- Refusals are deterministic and repeatable, and can be tested against `EVALUATION.md` with no
  model in the loop.
- Refusals are fast and cost nothing in chat-model calls, which makes NFR-2 achievable.
- The gate still works when the model is off, so the kill switch leaves a working search
  (REQ-G6).
- The decision to answer can be inspected: every response records the top score and the
  threshold in force (PRD §5.1 `meta`, §6 `messages`).

**Negative**
- **A similarity score is a blunt measure.** Q11 and Q12 may score close to answerable
  questions, and one threshold may not separate all 13 (the trigger below).
- **The gate depends on the embedding model.** Changing D0 changes every score, so D2 must be
  re-tuned.
- **The gate cannot catch an answer that clears the threshold but is still unsupported.** Only
  the citation check (REQ-G4) and the prompt (REQ-G2) stand behind it.
- **Without the embedding provider there is no gate.** Embeddings come from OpenRouter, so a
  full provider outage stops retrieval, and with it the gate. That is a D0 question, not one
  this ADR solves.

**Obligations**
- F2's evaluation run records the score for every one of the 13 questions. That spread is the
  evidence D2 is decided on.
- The threshold lives only in `REFUSAL_THRESHOLD`. It has no default in code (REQ-R7).

## When we'd revisit it

**Trigger: no threshold separates the questions the documents cover from the ones they don't.**
In practice that means the lowest top score among Q1–Q10 is not above the highest top score
among Q11–Q13 on the evaluation run.

**If that happens:**
1. Stop. Don't pick a number that fails some questions.
2. Record the score spread in the D2 decision record.
3. Bring the options back to us. Changing the mechanism means amending this ADR and, if a
   requirement changes, the protected PRD.

Fixing retrieval within this design (D0, D1, D3) comes before changing the gate. The corpus
and `EVALUATION.md` are never changed to make the numbers fit.

**Also revisit if:**
- D0 changes, since all scores move.
- The corpus gains documents, which changes the score spread.
- Answers that clear the gate start failing the citation check (REQ-G4) often enough to suggest
  the gate is letting through questions it shouldn't.
