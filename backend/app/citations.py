"""Citation markers in a composed answer (REQ-G4)."""

import re

MARKER = re.compile(r"\[(\d+)\]")


def cited_markers(answer: str) -> list[int]:
    """Markers in order of first appearance, without repeats."""
    seen: list[int] = []
    for match in MARKER.finditer(answer):
        number = int(match.group(1))
        if number not in seen:
            seen.append(number)
    return seen


def valid_citations(answer: str, passage_count: int) -> bool:
    """At least one marker, and every marker points at a passage that was sent."""
    markers = cited_markers(answer)
    return bool(markers) and all(1 <= m <= passage_count for m in markers)
