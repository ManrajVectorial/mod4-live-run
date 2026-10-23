"""Measure the follow-up evaluation set and choose the follow-up floor (D9 amendment).

    python -m app.followup_eval

For each two-turn case it prints the follow-up's gate score joined with the first question
(the D9 search) and on its own. The floor is the midpoint of the gap between the lowest
"answer" score on its own and the highest "refuse" score on its own. If those overlap there
is no floor, and F6 is cut (option C).
"""

import io
import re
import sys
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


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
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
