# Project rules

These rules apply to every stage of the Policy Assistant build. They override any default
behaviour, skill or plugin workflow.

1. **Protected files.** Never edit `backend/corpus/`, `docs/project-brief.md`, `AGENTS.md` or
   `CLAUDE.md`. Once the requirements are approved, `docs/PRD.md` and `docs/features.md` are
   protected too. If one seems to need a change, stop and ask.
2. **Decisions are ours.** When something is left open, set out the options, the trade-off of
   each and a recommendation, then stop and wait. Never fill an open decision in yourself.
3. **Stages run in order:** requirements → design and planning → implementation → testing and
   review → deployment → verification. No code before the plan is approved. Each stage leaves
   its record in `tickets/`.
4. **Ask first** before adding a library the approved plan doesn't list, pushing to `main`,
   deploying, deleting data, or changing an agreed API or data model.
5. **Secrets and settings** come from environment variables, read from a `.env` file that is
   never committed. Never print, log or commit a key. No hard-coded model names, URLs or thresholds.
6. **Tests are honest.** Never weaken, skip or delete a test to get a pass. Never swallow an
   error silently.
7. **No copyleft licences:** GPL, AGPL, LGPL, SSPL or EUPL.
8. **Only claim what was checked.** Say "I haven't checked X" rather than guess.
