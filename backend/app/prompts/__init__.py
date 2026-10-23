"""Versioned prompts (REQ-G3). The version lives in the prompt file itself, and
versions.json records the hash of each version's text, so a test fails if the text changes
without a new version."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent
ANSWER_PROMPT = PROMPTS_DIR / "answer.md"
REWRITE_PROMPT = PROMPTS_DIR / "rewrite.md"  # D9 amendment 2: follow-up rewriting


@dataclass(frozen=True)
class Prompt:
    version: str
    text: str


def _load(path: Path) -> Prompt:
    header, separator, text = path.read_text(encoding="utf-8").partition("\n---\n")
    if not separator or not header.startswith("version: "):
        raise ValueError(f"{path.name} must start with 'version: ...' and a '---' line")
    return Prompt(version=header.removeprefix("version: ").strip(), text=text.strip())


@cache
def load_answer_prompt() -> Prompt:
    return _load(ANSWER_PROMPT)


@cache
def load_rewrite_prompt() -> Prompt:
    return _load(REWRITE_PROMPT)
