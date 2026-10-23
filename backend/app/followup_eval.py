"""The follow-up evaluation set: F6's check (D9 amendment 2).

    python -m app.followup_eval            # run every case through the API (the F6 check)
    python -m app.followup_eval --scores   # the D9 option-B measurement, kept for the record

Each case asks the first question, then the follow-up in the same conversation. A case passes
when an "answer" follow-up comes back answered and a "refuse" follow-up comes back refused.
Exits non-zero if any case fails, so a failed check never looks clean.
"""

import argparse
import io
import re
import sys
import urllib.error
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.settings import REPO_ROOT, SettingsError, load_settings

FOLLOWUPS_FILE = REPO_ROOT / "backend" / "eval" / "followups.md"
HEADING = re.compile(r"^### (C\d+) — (answer|refuse)\s*$")


@dataclass(frozen=True)
class FollowupCase:
    cid: str
    expect: str  # "answer" or "refuse"
    first: str
    followup: str


def load_cases(path: Path) -> list[FollowupCase]:
    cases, current = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if match := HEADING.match(line):
            current = {"cid": match.group(1), "expect": match.group(2)}
        elif current is not None and line.startswith("First: "):
            current["first"] = line.removeprefix("First: ").strip()
        elif current is not None and line.startswith("Follow-up: "):
            current["followup"] = line.removeprefix("Follow-up: ").strip()
            cases.append(FollowupCase(**current))
            current = None
    return cases


def choose_floor(cases: list[FollowupCase], alone: dict[str, float]) -> float | None:
    """Midpoint of the gap between answerable and must-refuse follow-ups on their own."""
    answer = [alone[c.cid] for c in cases if c.expect == "answer" and c.cid in alone]
    refuse = [alone[c.cid] for c in cases if c.expect == "refuse" and c.cid in alone]
    if not answer or not refuse or min(answer) <= max(refuse):
        return None
    return (min(answer) + max(refuse)) / 2


@dataclass(frozen=True)
class CaseRow:
    cid: str
    expect: str
    followup: str
    status: str
    top_score: str
    outcome: str


def run_cases(
    cases: list[FollowupCase], base_url: str, timeout: float, ask: Callable
) -> list[CaseRow]:
    rows = []
    for c in cases:
        try:
            first = ask(base_url, c.first, timeout)
            body = ask(base_url, c.followup, timeout, conversation_id=first["conversation_id"])
        except (urllib.error.URLError, TimeoutError, ValueError, OSError, KeyError) as exc:
            rows.append(
                CaseRow(c.cid, c.expect, c.followup, f"error: {type(exc).__name__}", "—", "FAIL")
            )
            continue
        status = str(body.get("status"))
        score = (body.get("meta") or {}).get("top_score")
        wanted = "answered" if c.expect == "answer" else "refused"
        rows.append(
            CaseRow(
                c.cid,
                c.expect,
                c.followup,
                status,
                f"{score:.4f}" if isinstance(score, int | float) else "—",
                "PASS" if status == wanted else "FAIL",
            )
        )
    return rows


def run_through_api(url: str | None) -> int:
    from app.eval import ask_api

    settings = load_settings()
    base_url = url or settings.eval_api_base_url
    if base_url is None or settings.eval_timeout_seconds is None:
        print(
            "Missing settings: EVAL_API_BASE_URL (or --url), EVAL_TIMEOUT_SECONDS", file=sys.stderr
        )
        return 2
    rows = run_cases(load_cases(FOLLOWUPS_FILE), base_url, settings.eval_timeout_seconds, ask_api)
    print(f"Follow-up set against {base_url}")
    print("| case | expect | follow-up | status | top score (rewritten) | outcome |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r.cid} | {r.expect} | {r.followup} | {r.status} | {r.top_score} | {r.outcome} |")
    passed = sum(r.outcome == "PASS" for r in rows)
    print(f"followups {passed}/{len(rows)} passed")
    return 0 if passed == len(rows) else 1


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run the follow-up evaluation set.")
    parser.add_argument("--url", help="API base URL (default: EVAL_API_BASE_URL)")
    parser.add_argument("--scores", action="store_true", help="the D9 option-B score measurement")
    args = parser.parse_args()
    if not args.scores:
        try:
            return run_through_api(args.url)
        except SettingsError as exc:
            print(exc, file=sys.stderr)
            return 2
    from app.main import build_services  # the real retriever, from .env settings

    try:
        settings = load_settings()
        retriever = build_services(settings).retriever
    except SettingsError as exc:
        print(exc, file=sys.stderr)
        return 2
    threshold = settings.refusal_threshold
    cases = load_cases(FOLLOWUPS_FILE)
    alone: dict[str, float] = {}
    print("| case | expect | follow-up | joined (D9) | alone |")
    print("|---|---|---|---|---|")
    for c in cases:
        joined = retriever.retrieve(f"{c.first} {c.followup}").top_current_score or 0.0
        alone[c.cid] = retriever.retrieve(c.followup).top_current_score or 0.0
        print(f"| {c.cid} | {c.expect} | {c.followup} | {joined:.4f} | {alone[c.cid]:.4f} |")
    floor = choose_floor(cases, alone)
    print(f"\nREFUSAL_THRESHOLD={threshold}")
    if floor is None:
        print("No floor separates the cases on their own scores: cut F6 (option C).")
        return 1
    print(f"Follow-up floor (midpoint of the gap): {floor:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
