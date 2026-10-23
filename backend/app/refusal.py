"""The answer gate (ADR-001; REQ-R5, R6). A rule, not a model.

A question is answerable only when the best current passage scores strictly above
REFUSAL_THRESHOLD (D2). Otherwise the response is refused before any chat-model call.
"""

from functools import cache
from pathlib import Path

REFUSAL_TEXT = Path(__file__).parent / "text" / "refusal.md"


def clears(top_score: float | None, threshold: float) -> bool:
    return top_score is not None and top_score > threshold


@cache
def refusal_message() -> str:
    """D5: not covered, cites no policy, and a fixed who-to-ask list."""
    return REFUSAL_TEXT.read_text(encoding="utf-8").strip()
