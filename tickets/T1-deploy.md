# T1 — Deployment setup (Railway)

**Status:** set up, not deployed. `main` has no app until the release PR is merged.
**Date:** 2026-10-23
**How it deploys:** Railway from GitHub. The repo connected, so the fallback (me deploying
from this machine) is not needed. Railway deploys `sample-api` and `sample-web` itself when
`main` changes, and only once the commit's CI is green ("wait for CI"). There is no deploy
workflow and no Railway token in CI.

## The project

- **Project:** `nus-module-4-live`, workspace **CV Products**, environment `production`. It
  didn't exist, so I created it there, not in the personal workspace. This folder is linked
  to it.
- **Only these four services were created or changed.** No other project or service was
  touched; the separate `nus-module-4` project is untouched.

| Service | What it is | Source | Network |
|---|---|---|---|
| `sample-postgres` | Railway Postgres (template image `postgres-ssl:18`), volume `/var/lib/postgresql/data` | Railway template | private only |
| `sample-qdrant` | `qdrant/qdrant:v1.20.0` (the version tested locally), volume `/qdrant/storage`, API key `QDRANT__SERVICE__API_KEY` generated on this machine and set from stdin, never shown; `QDRANT__SERVICE__HOST=::` so it listens on the private network's IPv6 | image | private only |
| `sample-api` | GitHub `ManrajVectorial/mod4-live-run`, branch `main`, root directory `/backend`, wait for CI on | GitHub | public: https://sample-api-production-5fad.up.railway.app |
| `sample-web` | the same repo and branch, root directory `/frontend`, wait for CI on | GitHub | public: https://sample-web-production-165b.up.railway.app |

### How each setting was made

- **CLI:** the project, the Postgres and Qdrant services, the volume, the variables and the
  domains.
- **Railway's public API, with the same CLI login:**
  - The CLI's `railway add --repo` answered "repo not found". Railway's GitHub app can see
    the repo (it is among the 27 repos the app lists), so the problem was the CLI's lookup,
    not GitHub access.
  - So `sample-api` and `sample-web` were created empty through the API, given their root
    directories, then connected to the repo.
  - The API was also used to rename "Postgres" to `sample-postgres` (the CLI's `--service`
    name was ignored) and to set `checkSuites: true` ("wait for CI") on both deployment
    triggers.
  - The token is read from the CLI's config file and never printed.

## Variables

### sample-api

Values are as stored, unrendered. Secrets are references or hidden.

| Variable | Value | From |
|---|---|---|
| `DATABASE_URL` | `postgresql+pg8000://${{sample-postgres.PGUSER}}:${{sample-postgres.PGPASSWORD}}@${{sample-postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{sample-postgres.PGDATABASE}}` | reference, private network |
| `QDRANT_URL` | `http://${{sample-qdrant.RAILWAY_PRIVATE_DOMAIN}}:6333` | reference, private network |
| `QDRANT_API_KEY` | `${{sample-qdrant.QDRANT__SERVICE__API_KEY}}` | reference |
| `OPENROUTER_API_KEY` | hidden; copied from `.env` on stdin, checked equal to `.env` without printing it | `.env` |
| `CORS_ALLOWED_ORIGINS` | `https://${{sample-web.RAILWAY_PUBLIC_DOMAIN}}` | reference |
| `GENERATION_ENABLED` | `true` | product owner |
| `HISTORY_ENABLED` | `false` | T1-review FND-9: off in any deployment until brief Q3 is answered |
| `CHAT_MODEL` | `anthropic/claude-haiku-5.5` | plan |
| `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` | `openai/text-embedding-3-small`, `1536` | plan, D0 |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | `1200`, `0` | D1 |
| `REFUSAL_THRESHOLD` | `0.5092` | D2 |
| `RETRIEVAL_TOP_K` | `5` | D3 |
| `CONVERSATION_CONTEXT_MESSAGES` | `5` | D8 |
| `CHAT_TEMPERATURE`, `CHAT_MAX_TOKENS`, `CHAT_REASONING_ENABLED`, `GENERATION_TIMEOUT_SECONDS`, `EMBEDDING_TIMEOUT_SECONDS`, `MAX_QUESTION_CHARS`, `HEALTHZ_TIMEOUT_SECONDS`, `QDRANT_COLLECTION`, `LOG_LEVEL`, `OPENROUTER_BASE_URL` | `0`, `600`, `false`, `6`, `5`, `1000`, `0.8`, `policy_passages`, `INFO`, `https://openrouter.ai/api/v1` | `.env`, as tested locally |
| `PORT` | `8080` | the domain's target port |

`CORPUS_DIR` comes from the Dockerfile (`/srv/backend/corpus`).

### sample-web

- `NEXT_PUBLIC_API_BASE_URL = https://${{sample-api.RAILWAY_PUBLIC_DOMAIN}}`
- `NEXT_TELEMETRY_DISABLED = 1`
- `PORT = 8080`

### Names that differ from the request

- **`ALLOWED_ORIGINS` and `API_URL`:** the code reads `CORS_ALLOWED_ORIGINS` and
  `NEXT_PUBLIC_API_BASE_URL` (PRD §8, locked). Variables named as requested would be
  ignored, so the values went under the names the code reads.

## Loading the documents on an empty index

- **Behaviour:** `uvicorn --factory app.main:serve` (the Dockerfile's command now) starts
  the API and checks Qdrant in a background thread.
  - If the collection is missing or empty, it runs the F1 ingest.
  - `/healthz` answers 200 throughout. It gains an `index` field
    (`{"status": "checking|indexing|ready|failed|not_checked", "passages": N}`), and the
    top-level status is `degraded` until the index is ready.
- **Change to the API:** this changes the agreed `/healthz` shape (PRD §5.6, locked), at
  the product owner's request. The PRD itself was not edited (rule 1).
- **Tests first** (`tests/test_index_bootstrap.py`, 7 tests). They failed first with
  `ModuleNotFoundError: No module named 'app.index_bootstrap'`. They cover:
  - an empty index is loaded and counted;
  - a full index is not loaded again;
  - a failure is reported and logged by type only;
  - a missing collection counts as empty;
  - `/healthz` gives 200 and "indexing", then "ready" with its count;
  - "not_checked" when there is no bootstrap;
  - the Dockerfile starts `serve`.
  - `test_healthz.py`'s exact-body test now includes the `index` field.
- **Live, against local Qdrant and OpenRouter with a scratch collection** (deleted
  afterwards):

  ```
  log: app.index index: empty; loading the documents in the background
    0.9s HTTP 200 status=degraded index={'status': 'indexing', 'passages': 0}
    2.5s HTTP 200 status=degraded index={'status': 'indexing', 'passages': 0}
  log: app.index index: loaded 130 passages
    4.2s HTTP 200 status=ok index={'status': 'ready', 'passages': 130}
  ```

  The local API, restarted through `serve` against the real index:
  `index: 130 passages already indexed`, and `/healthz` reports
  `"index":{"status":"ready","passages":130}`.
- **Risk:** a question asked during the few seconds of indexing finds nothing and is
  refused as "not covered". A 503 "still indexing" answer would change the agreed API, so
  it isn't done; it's listed below for a decision.

## Web health check

`frontend/app/healthz/route.ts` is new. It answers `{"status": "ok", "service":
"policy-assistant-web"}` without calling the API. Its test, `lib/healthz.test.ts`, failed
first (`Cannot find module …/app/healthz/route.ts`) and passes now.

## CI on main

`.github/workflows/ci.yml` now also runs on pushes to `main`. Before, it ran only on pull
requests and on pushes to `work/build`, so a merge commit on `main` had no gate check for
"wait for CI" to wait on. The scope job compares against the `plan-approved` tag, so it
works on `main` too.

## State now

The latest deployment of each service:

```
sample-postgres: SUCCESS  (ghcr.io/railwayapp-templates/postgres-ssl:18)
sample-qdrant:   SUCCESS  (qdrant/qdrant:v1.20.0) — log: "listening on: [::]:6333"
sample-api:      FAILED   (commit b056bc6, main's start commit: no backend/ yet)
sample-web:      FAILED   (commit b056bc6: no frontend/ yet)
```

Connecting the repo made Railway build `main` straight away. It failed because `main` is
still the start commit, so nothing is deployed. The first real deployment is the merge of
the release PR.

## Open: build and health-check config (railway.json)

- **What Railway said:** it refused to set `/backend/railway.json` and
  `/frontend/railway.json` as the services' config files: "Config as Code
  (railway.json/railway.toml) is deprecated. Use Infrastructure as Code (.railway/railway.ts)
  instead."
- **Where that leaves the files:** `backend/railway.json` (Dockerfile, `/healthz`) and the
  new `frontend/railway.json` (Railpack, `npm ci && npm run build`, `npm start`, `/healthz`)
  are committed. I haven't checked whether Railway reads them by itself from a service's root
  directory.
- **Why I couldn't check:** web fetch of Railway's docs wasn't permitted, and nothing can be
  tested until `main` has the app.
- **Decision:** waiting for the product owner; the options are in the hand-off.

## Not checked

- That Qdrant enforces its API key (only reachable from inside the private network).
- That the API reaches Postgres and Qdrant over the private network. That happens at the
  first real deployment.
- Postgres 18 on Railway against the app (local tests use Postgres 16).
- How Railway's "wait for CI" behaves when a commit has no check suites.
