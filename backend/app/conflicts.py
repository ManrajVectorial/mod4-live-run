"""Known policy conflicts (D6). Spotted only from MANIFEST.yaml `known_conflict` entries,
never by the model; the response shows both sides and says to escalate."""

import re
from functools import cache
from pathlib import Path

import yaml

from app.retrieval import Hit

CONFLICT_TEXT = Path(__file__).parent / "text" / "conflict.md"
SECTION_NUMBER = re.compile(r"^(\d+(?:\.\d+)?)")

Conflict = set[tuple[str, str]]  # {(policy_id, section), ...}


def known_conflicts(corpus_dir: Path) -> list[Conflict]:
    manifest = yaml.safe_load((corpus_dir / "MANIFEST.yaml").read_text(encoding="utf-8"))
    entries = manifest.get("known_conflict")
    entries = [entries] if isinstance(entries, dict) else (entries or [])
    conflicts = []
    for entry in entries:
        sides = set()
        for doc in entry.get("documents", []):
            match = SECTION_NUMBER.match(str(doc["section"]))
            if match:
                sides.add((doc["id"], match.group(1)))
        if len(sides) >= 2:
            conflicts.append(sides)
    return conflicts


def find_conflict(hits: list[Hit], conflicts: list[Conflict]) -> list[Hit] | None:
    """The hits that make up a known conflict, if every side of it was retrieved."""
    for conflict in conflicts:
        sides = []
        for policy_id, section in sorted(conflict):
            match = next(
                (
                    h
                    for h in hits
                    if (h.payload["policy_id"], h.payload["section"]) == (policy_id, section)
                ),
                None,
            )
            if match is None:
                break
            sides.append(match)
        else:
            return sides
    return None


@cache
def _template() -> str:
    return CONFLICT_TEXT.read_text(encoding="utf-8").strip()


def conflict_note(sides: list[Hit], markers: dict[str, int]) -> str:
    def label(hit: Hit) -> str:
        p = hit.payload
        return f"{p['title']} v{p['version']} §{p['section']} [{markers[p['passage_id']]}]"

    return _template().format(first=label(sides[0]), second=label(sides[1]))
