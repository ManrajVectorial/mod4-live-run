"""Roll a Railway service back to the deployment that was live before the current one.

    python ci/railway_rollback.py sample-api --dry-run   # show what it would roll back to
    python ci/railway_rollback.py sample-api             # roll back

The release fallback in tickets/T1-release.md. The Railway CLI can only redeploy the latest
deployment, so the rollback itself uses Railway's API with the CLI's own login on this
machine (`railway login`). The token is read from the CLI's config and never printed. Run it
from the repo, which `railway link` ties to the project.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request

API = "https://backboard.railway.com/graphql/v2"
LIVE, SUPERSEDED = (
    "SUCCESS",
    "REMOVED",
)  # a deployment that went live, then was replaced


def pick_previous(deployments: list[dict]) -> dict | None:
    """The newest once-live deployment older than the one live now, or None."""
    newest_first = sorted(deployments, key=lambda d: d["createdAt"], reverse=True)
    live = next((d for d in newest_first if d["status"] == LIVE), None)
    if live is None:
        return None
    older = [d for d in newest_first if d["createdAt"] < live["createdAt"]]
    return next((d for d in older if d["status"] == SUPERSEDED), None)


def railway(*args: str) -> str:
    exe = shutil.which("railway.cmd") or shutil.which("railway")
    if exe is None:
        sys.exit("The Railway CLI isn't installed or on PATH.")
    result = subprocess.run([exe, *args], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"railway {' '.join(args)} failed: {result.stderr.strip()[-300:]}")
    return result.stdout


def rollback(deployment_id: str) -> dict:
    config = os.path.expanduser("~/.railway/config.json")
    with open(config, encoding="utf-8") as f:
        token = json.load(f)["user"]["token"]
    query = "mutation($id: String!) { deploymentRollback(id: $id) }"
    request = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": {"id": deployment_id}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "policy-assistant-rollback",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        return json.load(response)


def describe(d: dict) -> str:
    commit = ((d.get("meta") or {}).get("commitHash") or "")[:7]
    return f"{d['id']} ({d['status']}, {d['createdAt'][:19]}, commit {commit or 'n/a'})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Roll a Railway service back one deployment."
    )
    parser.add_argument("service", help="e.g. sample-api or sample-web")
    parser.add_argument(
        "--dry-run", action="store_true", help="show the target, change nothing"
    )
    args = parser.parse_args(argv)

    deployments = json.loads(
        railway("deployment", "list", "--service", args.service, "--json")
    )
    target = pick_previous(deployments)
    if target is None:
        print(
            f"{args.service}: no earlier live deployment to go back to. On the first release, "
            f"take the service offline instead: railway down --service {args.service}"
        )
        return 1
    print(f"{args.service}: rolling back to {describe(target)}")
    if args.dry_run:
        print("dry run: nothing changed")
        return 0
    body = rollback(target["id"])
    if body.get("errors"):
        print(
            "Railway refused:", "; ".join(e.get("message", "") for e in body["errors"])
        )
        return 1
    print(
        "rollback requested; watch it with: railway deployment list --service",
        args.service,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
