# T1-F4 — Write the answer

**Status:** done (2026-10-23)
**Parent:** [T1](T1.md)
**Depends on:** F3
**Decisions it waits on:** D3, D4, D6, D7

Add the chat model: a cited answer from the retrieved passages only, the kill switch,
citation validation, and the prompt version and model recorded on every answer.

## Requirements

REQ-A1 · REQ-G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11 · NFR-1, NFR-5

## Done when (from `features.md`)

With `GENERATION_ENABLED=true`, `curl -s -H 'Content-Type: application/json' -d '{"question":"Does a claim of exactly £75 need approval?"}' localhost:8000/api/ask` prints `"status":"answered"`, an answer saying yes, a source at v3.1 §4.2, and non-null `prompt_version` and `model`. The same call with `GENERATION_ENABLED=false` prints `"status":"degraded"`

## Command that checks it

```
cd backend && python -m pytest tests/test_generation.py tests/test_api_ask.py && python -m app.evaluate
```

Then run the Done-when line above. The G8 and G11 checks are recorded below by me and
reviewed by you (A4).

## Files it will touch

- `backend/app/generation.py`: new. OpenRouter chat client, timeout, kill switch
  (G1, G6, G7)
- `backend/app/prompts/answer.md`: new. Versioned system prompt (G2, G3)
- `backend/app/citations.py`: new. Validates markers against the retrieved passages (G4)
- `backend/app/main.py`: changed. Adds the `answered` path to `/api/ask` (A1)
- `backend/app/db/`: changed only to write `prompt_version` and `model` (G5). No schema
  change
- `backend/app/logging.py`: changed. Adds token counts (NFR-5)
- `backend/tests/test_generation.py`: new. `test_api_ask.py`: extended
- `tickets/eval-results.md`: updated

## Not in it

- Any web page (F5)
- Follow-up context (F6)
- Choosing D6 or D7

## Evidence

**Done-when, real API with `anthropic/claude-haiku-5.5` through OpenRouter.** The body is sent
from a UTF-8 file, because Git Bash on Windows mangles a `£` in a `curl -d` argument:

```
$ GENERATION_ENABLED=true  curl -s -H "Content-Type: application/json" --data-binary @q2.json localhost:8000/api/ask
  # q2.json: {"question":"Does a claim of exactly £75 need approval?"}
status: answered | degraded: None
answer: Yes. A claim of £75 or more requires line-manager approval before reimbursement, and thresholds are inclusive, so a claim of exactly £75 requires line-manager approval [1]. Claims below £75 are automatically approved on submission [1].
sources: [(1, 'travel-expense-policy-v3.1', '4.2', 'current'), (4, 'travel-expense-policy-v3.0', '4.1', 'superseded'), (5, 'travel-expense-policy-v3.0', '4.3', 'superseded')]
prompt_version: answer-v1 | model: anthropic/claude-haiku-5.5

$ GENERATION_ENABLED=false (same call)
status: degraded | degraded: {'reason': 'generation_disabled'}
answer: None
sources: [(1, ...v3.1 §4.2), (2, ...v3.1 §4.1), (3, ...v3.1 §4.5), (4, ...v3.0 §4.1 superseded), (5, ...v3.0 §4.3 superseded)]
prompt_version: None | model: None
```

**The 13 questions through the local API** (`python -m app.eval`). Two consecutive full runs
both gave `eval 10/10 answered, 3/3 refused`. Run 2:

| Q | top score | API status | cited | outcome |
|---|---|---|---|---|
| Q1 | 0.723 | answered | travel-expense-policy-v3.1 §4.2, travel-expense-policy-v3.0 §4.1 | PASS |
| Q2 | 0.733 | answered | travel-expense-policy-v3.1 §4.2, travel-expense-policy-v3.1 §4.1, travel-expense-policy-v3.0 §4.1, travel-expense-policy-v3.0 §4.3 | PASS |
| Q3 | 0.582 | answered | travel-expense-policy-v3.1 §5.2, travel-expense-policy-v3.0 §5.2 | PASS |
| Q4 | 0.664 | answered | travel-expense-policy-v3.1 §6.2, travel-expense-policy-v3.0 §6.1 | PASS |
| Q5 | 0.557 | answered | client-onboarding-kyc-v2.4 §6.1 | PASS |
| Q6 | 0.611 | answered | client-onboarding-kyc-v2.4 §6.4 | PASS |
| Q7 | 0.606 | answered | client-onboarding-kyc-v2.4 §4.2, client-onboarding-kyc-v2.4 §4.1 | PASS |
| Q8 | 0.712 | answered | records-retention-v4.0 §4.2, records-retention-v4.0 §4.1, outsourcing-third-party-v1.8 §6.4 | PASS |
| Q9 | 0.618 | answered | outsourcing-third-party-v1.8 §4.1 | PASS |
| Q10 | 0.570 | answered | records-retention-v4.0 §4.2, outsourcing-third-party-v1.8 §6.4, records-retention-v4.0 §4.1 | PASS |
| Q11 | 0.438 | refused | — | PASS |
| Q12 | 0.462 | refused | — | PASS |
| Q13 | 0.275 | refused | — | PASS |

**REQ-G8 and G11 check** (by me, for your review; A4). I read all ten answers.
- **G11:** each states the expected fact from `EVALUATION.md`.
  - Q1: £75 or more, inclusive. Q2: "Yes", because the thresholds are inclusive.
  - Q3: business class isn't listed for 4 to 8 hours.
  - Q4: £300 per night, including taxes. Q5: every 12 months, from the date the last review
    was completed.
  - Q6: suspended; only Financial Crime Compliance can lift it. Q7: 10%, against 25% for
    standard due diligence.
  - Q8: 7 years from the end of the relationship. Q9: all four approvers.
  - Q10: both sides, said to conflict, with the escalation route.
- **G8:** none tells the reader what to do. A pattern search found no "you should", "I
  recommend", "I suggest", "make sure" or "consider". Q10's "must be escalated" restates
  Outsourcing §6.4's own instruction.
- **D6:** fired for Q10, and for Q8 too, because both conflicting passages were retrieved
  there. In both, the model's own sentence about the conflict is followed by the fixed notice,
  so the conflict is stated twice. That is redundant but accurate.

**Local timing (not NFR-1 itself, which is measured on Railway):** answers took 2.0 to 3.9 s,
median 2.6 s. Refusals took 0.86 to 0.96 s.

**The Q11 rephrasing from F3** ("Can I claim travel costs for a family member who joins me
on business travel?") scores 0.5365, which clears the gate. The model replied `NOT STATED`,
as the prompt instructs when the passages don't state an answer, so citation validation
returned `degraded` (`invalid_citations`). No answer was invented. But it isn't a refusal:
the user sees two travel passages and no who-to-ask list. That risk stays open.

**Problems found and fixed during F4:**
1. **Empty answers.** `anthropic/claude-haiku-5.5` is a reasoning model. With my first
   `CHAT_MAX_TOKENS=400`, it spent all 400 tokens on hidden reasoning and returned an empty
   answer (`finish_reason=length`), so answerable questions came back `degraded`. I measured
   three options on Q3:
   - 2000 tokens with reasoning on: 3.1 to 4.6 s;
   - effort "low": 5.0 to 5.5 s;
   - reasoning off: 1.9 to 2.0 s, with correct, cited answers.

   I chose reasoning off, through a new setting `CHAT_REASONING_ENABLED=false` (OpenRouter's
   `reasoning: {enabled: false}`), with `CHAT_MAX_TOKENS=600`. A completion cut off at the
   limit is now a `provider_error`, never shown as an answer.
2. **Crash on the first question.** My edit failed to add `chat_reasoning_enabled` to the
   settings `build_services` requires, so the real app hit a `KeyError` on every question.
   No unit test built the real services. Added `test_build_services.py`.
3. **Malformed body.** A body that isn't UTF-8 JSON got a framework 400 instead of the agreed
   422 `question_blank`. `/api/ask` now parses the body itself, with a test.
4. **Question text could reach the logs.** openai 3.x sends requests through `httpx2` and
   `httpcore2`, which my quiet-logger list missed; at DEBUG they could log the request body,
   which contains the question. Both are now held at WARNING. The logger test also passed
   when it shouldn't have, because pytest's handlers made `basicConfig` do nothing. It now
   sets the root logger to DEBUG explicitly and failed before the fix.

**Tests:** 88 backend tests passed, including:
- `test_generation.py` (11): G1–G10 and NFR-5;
- `test_openrouter_generator.py` (4);
- `test_build_services.py` (7);
- the strengthened logging test and the malformed-body test.

The one pytest warning is qdrant-client failing to read the server version when the
`build_services` test points a client at a closed local port. It is harmless.

**Simplest options taken where the plan was silent:**
- `CHAT_TEMPERATURE=0`, so answers are as repeatable as possible.
- `GENERATION_TIMEOUT_SECONDS=6`, to stay under NFR-1's 8-second ceiling.
- `CHAT_MAX_TOKENS=600` and `CHAT_REASONING_ENABLED=false`, as above.
- **G9:** superseded text never reaches the model (D4), so no answer draws on it. Superseded
  passages of a cited policy appear only as labelled sources after the cited ones.
- **G4:** when the passages don't state an answer, the prompt has the model reply `NOT STATED`.
  That carries no citation, so it becomes `degraded` (`invalid_citations`) rather than a
  refusal, because only the rule may refuse (ADR-001).
- **D6:** the conflict notice is fixed text from `app/text/conflict.md`, added after the
  model's answer. Both sides are always cited, whatever the model cited.
- **Prompt version:** `answer-v1`, held in `app/prompts/answer.md`. `versions.json` holds its
  SHA-256, and a test fails if the text changes without a new version.
