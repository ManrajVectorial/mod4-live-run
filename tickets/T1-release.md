# T1 — Release: Policy Assistant, first release

**What this is:** the first release of Policy Assistant, merging `work/build` into `main`.
**Who merges:** the product owner. Use **"Create a merge commit"**, not squash or rebase.
The undo below reverts the merge commit, and a squash or rebase leaves none.
**What happens on merge:**
1. CI runs on `main`.
2. When its `gate` check is green, Railway builds and deploys `sample-api` and `sample-web`
   from `main` by itself.
3. There is no deploy workflow, no Railway token in CI, and nothing to run by hand.

## What's being released

An internal web tool for Aldermere Bank's operations and front-office staff. Someone asks a
policy question in their own words, and gets one of three things:
- **an answer** that says what the policy says, citing the document, section and version it
  came from;
- **a refusal** that says the policy documents don't cover it, cites nothing, and says who to
  ask;
- **passages only**, when the AI can't write an answer: the matching policy text, saying
  plainly that no answer was composed.

It never tells staff what to do or decides exceptions. Superseded policy is always labelled.
Where two current policies conflict (the records-retention and outsourcing case), it shows
both side by side and says to escalate to Group Legal and Group Operational Risk.

| Where | Address |
|---|---|
| Web page | https://sample-web-production-165b.up.railway.app |
| API | https://sample-api-production-5fad.up.railway.app |

On Railway, project `nus-module-4-live` (workspace CV Products), the services are:
- `sample-web` and `sample-api`, from GitHub `main`, waiting for CI;
- `sample-postgres` and `sample-qdrant`, on the private network only.

See [T1-deploy.md](T1-deploy.md).

## How we'll know within two minutes that it worked

The clock starts when Railway shows both new deployments as **Active**. Before that, CI on
`main` and the two builds take several minutes; that isn't the release failing.

```
API=https://sample-api-production-5fad.up.railway.app
WEB=https://sample-web-production-165b.up.railway.app

# 1. Both deployments are live, from the merge commit
gh run list --branch main --limit 1                      # CI on main: completed, success
railway deployment list --service sample-api --limit 1   # SUCCESS, commit = the merge commit
railway deployment list --service sample-web --limit 1   # SUCCESS, same commit

# 2. The API is healthy and has loaded the documents
curl -s $API/healthz
#   expect: "status":"ok", postgres/qdrant/generation "ok",
#           "index":{"status":"ready","passages":130}, "version": the merge commit's SHA
#   On a fresh deployment the index reads "indexing" for a few seconds first: that is
#   expected (it loaded in ~4 s locally). Ask again.

# 3. The web page is up and reaches the API
curl -s $WEB/healthz                                     # {"status":"ok","service":"policy-assistant-web"}
curl -s -X POST $WEB/api/ask -H 'content-type: application/json' \
  -d '{"question":"What is the approval threshold for a travel expense claim?"}' \
  | python -c "import json,sys; r=json.load(sys.stdin); print(r['status'], [(s['document_id'], s['section']) for s in r['sources']])"
#   expect: answered [('travel-expense-policy-v3.1', '4.2'), ...]

# 4. A question the documents don't cover is refused, citing nothing
curl -s -X POST $WEB/api/ask -H 'content-type: application/json' \
  -d '{"question":"How many days of paid parental leave am I entitled to?"}' \
  | python -c "import json,sys; r=json.load(sys.stdin); print(r['status'], r['sources'])"
#   expect: refused []
```

Then open the web page in a browser and ask the travel question once.

**Not part of the two minutes:** for the full check, run the 13 questions against the live
API. It takes about a minute and spends a little on the model:

```
cd backend && python -m app.eval --url https://sample-api-production-5fad.up.railway.app
#   expect: eval 10/10 answered, 3/3 refused
```

## How we'll know it didn't work

Any one of these means it failed:

- **CI on `main` is red.** Railway then doesn't deploy at all ("wait for CI"), and nothing
  changes for users. Fix forward on `work/build`, or undo the merge.
- **A deployment shows FAILED or CRASHED** in `railway deployment list`. For the API, read
  `railway logs --service sample-api`. Only error types are logged, never question text.
- **`/healthz` problems**, either of:
  - top-level `"degraded"` with a component `"unreachable"` for more than two minutes;
  - `"index":{"status":"failed",…}`.

  `"generation":"unreachable"` means OpenRouter is unreachable, or the key is wrong.
- **The answer check is wrong:** the travel question isn't `answered`, or doesn't cite
  §4.2 v3.1.
- **The refusal check is wrong:** the parental-leave question isn't `refused`, or cites
  anything.
- **The web page shows "The service is not configured" or "The service is unavailable".**
  The web can't reach the API: check `NEXT_PUBLIC_API_BASE_URL` on `sample-web`.

## How to undo it

### 1. Revert the merge on `main`, then deploy `main` again the same way

```
git fetch origin
git switch main
git pull --ff-only origin main
MERGE=$(git log --merges -1 --format=%H)     # the release's merge commit: check it first
git show --stat "$MERGE" | head -5
git revert -m 1 --no-edit "$MERGE"
git push origin main
```

- **Who may push to `main`:** pushing to `main` needs the product owner's say-so
  (AGENTS.md rule 4). Branch protection requires the `gate` check but isn't enforced for
  admins, so an admin can push the revert directly.
- **The pull-request route,** if you'd rather go through one:

  ```
  git switch -c revert-release
  git revert -m 1 --no-edit "$MERGE"
  git push -u origin revert-release
  gh pr create --base main --head revert-release --title "Revert the release" --body "Undo, per tickets/T1-release.md"
  gh pr merge revert-release --merge          # once its gate check is green
  ```

- **Deploying `main` again is the same as deploying the release.** There's nothing to run.
  The push to `main` runs CI, and when the gate is green Railway builds and deploys `main`.
  Watch it with:

  ```
  gh run watch "$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')"
  railway deployment list --service sample-api --limit 3
  railway deployment list --service sample-web --limit 3
  ```

**For this first release, the revert alone does not take it down.** Reverted, `main` is the
start commit again, with no app, so its build fails. Railway keeps the last good deployment
running, which is the release. To actually take it offline:

```
railway down --service sample-web --yes
railway down --service sample-api --yes
```

`railway down` removes the latest deployment, so the service stops serving. Postgres, Qdrant
and their data are untouched.

### 2. The Railway fallback: go back to the previous deployment

Use this if `main` can't be fixed quickly, or the revert's build fails, on a later release
when there is an earlier good deployment. The Railway CLI can only redeploy the *latest*
deployment, so `ci/railway_rollback.py` rolls back to the one before. It uses your Railway
login on this machine and never prints the token.

```
python ci/railway_rollback.py sample-api --dry-run   # shows which deployment it would go back to
python ci/railway_rollback.py sample-api
python ci/railway_rollback.py sample-web --dry-run
python ci/railway_rollback.py sample-web
```

**For this first release** there is no earlier good deployment. The script says so and
points to `railway down` above. I checked: its dry run on `sample-api` today prints "no
earlier live deployment to go back to". On `sample-qdrant` it finds the deployment before
the current one.

In the dashboard, the same fallback is: **the service → Deployments → the previous
deployment → ⋯ → Rollback.**

## What can't be undone

- **Questions people asked are kept.** Each question and answer is stored in Postgres
  (`sample-postgres`), and reverting or rolling back doesn't delete them. History is
  switched off (`HISTORY_ENABLED=false`), so nobody can read them through the tool, but
  they stay in the database. How long to keep them is brief Q2, which is unanswered.
- **Questions have been sent to the AI provider.** Every question went to OpenRouter and on
  to the model vendor, for searching (the embedding) and answering. That can't be recalled.
  I haven't checked the OpenRouter account's data-retention settings (review FND-10).
- **Model spending isn't refunded.** Every question costs a little at OpenRouter.
- **The database tables and the index stay.** The tables are created on first use, and the
  index of 130 passages is loaded on first start. A revert doesn't remove them. They're
  harmless and are reused next time.
- **The code stays public.** The repository is public, so the merge, and everything in it,
  stays visible in its history after a revert.
- **What people already read.** Anyone who used it has seen its answers, and anything
  shared outside the tool can't be taken back.

## What's in it, and what was left out

**In it: all nine features. None was cut.**

| | Feature | What it does |
|---|---|---|
| F1 | Load the documents | Indexes the five policy documents, superseded versions included and labelled. On a fresh deployment it loads them by itself at startup |
| F2 | Search the passages | Finds the passages closest to the question |
| F3 | Decide whether to answer | A fixed rule, before any AI call: answer only when the best current passage scores above 0.5092. Otherwise refuse, citing nothing |
| F4 | Write the answer | The AI answers from the cleared passages only, with numbered citations. If the AI fails or times out, the passages are shown instead |
| F5 | The web page | Ask a question, see the answer, refusal or passages |
| F6 | Follow-up questions | A follow-up is rewritten into a standalone question before searching, judged by the same rule |
| F7 | Browse the documents | `/corpus`, and each document section by section; citations link to their section |
| F8 | History | `/history`: past conversations as they were answered. **Built but switched off** (see below) |
| F9 | UI refresh | One design across every page; a conversation layout; distinct looks for answers, refusals, passages and errors; the conflict case side by side; works at 375 px and by keyboard |

**The top bar offers only pages we built.** I checked it against what is served:
- the product name links to `/`;
- **History** links to `/history`, and **Corpus** to `/corpus`;
- **Reset** clears the page.

All three pages answer 200, and there is no link to anything unbuilt. **History** is built
but switched off in this release, so its page says history is switched off rather than
listing conversations.

**Switched off: history (F8).** `/history` has no login, so anyone who can reach it would
see every stored question. It stays off (`HISTORY_ENABLED=false`) until brief Q3 is
answered: who may see a user's question.

**Left out on purpose** (T1, "What we're not building"):
- editing or authoring policy;
- deciding exceptions;
- anything customer-facing;
- case-management or CRM integration;
- answers from anything but the approved documents;
- non-English documents;
- authentication or per-user history;
- automatic re-indexing;
- in-product feedback;
- thresholds tuned beyond D2.

**Known gaps going out** (each decided in [T1-review.md](T1-review.md)):
- **If OpenRouter as a whole is down, nothing is shown, not even passages** (FND-29). The
  search itself needs the provider. Waiting on your choice of fix.
- **The refusal threshold is tuned on only 13 questions** (FND-37, accepted by the product
  owner).
- **A question asked in the first seconds of a fresh deployment, while it is still loading
  the documents, is refused as "not covered"** (T1-deploy.md).
- **Speed on the deployed service isn't measured yet** (NFR-1, NFR-2). The 13-question check
  above gives the first numbers.
- **The deferred review findings** are listed with their reasons in the review.

## Links

- [T1.md](T1.md): what we're building, the criteria, F1–F9
- [T1-plan.md](T1-plan.md): the approved plan and decisions D0–D9
- [T1-review.md](T1-review.md): the review, the F9 addendum and every finding's decision
- [T1-deploy.md](T1-deploy.md): the Railway setup
