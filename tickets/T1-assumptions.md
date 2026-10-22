# T1 — Assumptions

These are the simplest options, taken on instruction for every acceptance question that
isn't one of D0–D9 (2026-10-23). The acceptance criteria themselves live only in
[T1.md](T1.md).

| # | Question | Assumption |
|---|---|---|
| A1 | Where is it judged | Each feature locally. T1's criteria re-run on Railway at the verification stage |
| A2 | Who signs off | You, recorded in `tickets/` |
| A3 | When is a feature done | When it's merged to `main` with its checks passing. The build is done when deployed and verified |
| A4 | Automated or manual | Automated tests wherever possible. REQ-G8 and G11 are checked by me, recorded in `tickets/`, and reviewed by you |
| A5 | Evaluation runs | One full run of all thirteen on the final configuration |
| A6 | Flaky result | A failure on that run is a failure. Rerunning until it passes doesn't count |
| A7 | Required checks on `main` | Tests, security scan and licence check, required from the first pull request that adds CI |
| A8 | PRD §12 item 7 | The PRD isn't edited. The protected-files check runs against `6961c35` (the approved state) |
| A9 | S1–S5 | Not part of acceptance. They're measured after release |
| A10 | Feedback (S4), scheduled re-indexing | Outside "done" for this build |
| A11 | Cost budget | None |
| A12 | F1 environment | Local Qdrant. Railway at the deployment stage |
| A13 | Passage count | Checked only for being the same on a repeat run, not for an exact number |
| A14 | Front-matter test (REQ-I2) | Modified copies of corpus files in test fixtures, outside `backend/corpus/` |
| A15 | Partial failure (REQ-I9) | Proved by simulating an embedding failure halfway through a run |
| A16 | Evaluation results file | One file, overwritten on each run. The final run is committed |
| A17 | Wrong answers or refusals among the 13 | None allowed |
| A18 | NFR-1 and NFR-2 timing | On Railway, one warm run (the first request is excluded). A slow run counts as a fail |
| A19 | NFR-3 dependency outage | Shown locally only |
| A20 | NFR-4 logs | Our application logs and Railway's logs for our service. OpenRouter's side is out of our control |
| A21 | Question text to OpenRouter | Acceptable for this build. Brief Q3 still blocks release |
| A22 | `MAX_QUESTION_CHARS` | Value set in the plan |
| A23 | "States the expected fact" (G11) | Same meaning as `EVALUATION.md`, not the same wording |
| A24 | "Tells the user what to do" (G8) | The answer contains advice in its own voice ("you should", "I recommend", "I suggest"). Restating what the policy requires is not advice |
| A25 | Degraded answers among Q1–Q10 | None allowed |
| A26 | Token counts (NFR-5) | Checked at planning to see whether OpenRouter reports them. Raised with you if not |
| A27 | Browsers | Current desktop Chrome, plus Chrome at 375 px wide |
| A28 | Accessibility | REQ-U13 plus labelled form controls. No further standard |
| A29 | REQ-U6 notice text | Drafted by me in the plan, approved by you |
| A30 | "Unmistakably different" refusal (U4) | Judged by you, by looking |
| A31 | Page tests | A recorded manual check. No browser-automation library |
| A32 | Extra follow-up questions | None beyond `features.md` |
| A33 | F8 and brief Q3 | F8 is not started until Q3 is answered |
| A34 | Dropping F6–F8 | Your call, with no set date |
| A35 | Deployment | Once, at the deployment stage, not per feature. I ask you first (rule 4) |
| A36 | PR approval | 0 required approvals governs. Your sign-off in `tickets/` is the named human approval |
| A37 | Security scan pass | No high or critical findings |
| A38 | Repository layout for "Files" in F1–F8 | Python app in `backend/app/` with tests in `backend/tests/`; Next.js in `frontend/`. The plan may change this |
| A39 | Check commands in F1–F8 | Use `features.md`'s placeholder module names and ports (`app.ingest`, `app.evaluate`, `:8000`, `:3000`). Replaced by the plan's real ones |
