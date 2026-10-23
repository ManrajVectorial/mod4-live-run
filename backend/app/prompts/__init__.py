"""Versioned prompts (REQ-G3). The version lives in the prompt file itself, and
versions.json records the hash of each version's text, so a test fails if the text changes
without a new version."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent
ANSWER_PROMPT = PROMPTS_DIR / "answer.md"


@dataclass(frozen=True)
class Prompt:
    version: str
    text: str


@cache
def load_answer_prompt() -> Prompt:
    header, separator, text = ANSWER_PROMPT.read_text(encoding="utf-8").partition("\n---\n")
    if not separator or not header.startswith("version: "):
        raise ValueError(f"{ANSWER_PROMPT.name} must start with 'version: ...' and a '---' line")
    return Prompt(version=header.removeprefix("version: ").strip(), text=text.strip())
