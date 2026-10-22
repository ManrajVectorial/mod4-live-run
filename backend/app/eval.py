"""Ask the 13 EVALUATION.md questions through the API and print one row each.

    python -m app.eval                  # the API at EVAL_API_BASE_URL (local, from .env)
    python -m app.eval --url URL        # any other deployment

Exits non-zero if any question could not be asked, so a broken run never looks clean.
The top-three retrieval columns (REQ-R4) are added at F2 by calling the search code directly.
"""

import argparse
import io
import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.settings import SettingsError, load_settings

QUESTION_HEADING = re.compile(r"^### (Q\d+) — (?:⭐ )?(.+?)\s*$")


@dataclass(frozen=True)
class Question:
    qid: str
    text: str


@dataclass(frozen=True)
class Row:
    qid: str
    status: str
    top_score: str
    source: str
    question: str


Ask = Callable[[str, str, float], dict]


def load_questions(evaluation_file: Path) -> list[Question]:
    questions = []
    for line in evaluation_file.read_text(encoding="utf-8").splitlines():
        match = QUESTION_HEADING.match(line)
        if match:
            questions.append(Question(qid=match.group(1), text=match.group(2)))
    return questions


def ask_api(base_url: str, question: str, timeout: float) -> dict:
    url = base_url.rstrip("/") + "/api/ask"
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError("the API URL must start with http:// or https://")
    body = json.dumps({"question": question}).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310 - scheme checked above
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def to_row(question: Question, response: dict) -> Row:
    meta = response.get("meta") or {}
    score = meta.get("top_score")
    sources = response.get("sources") or []
    first = sources[0] if isinstance(sources, list) and sources else None
    source = f"{first.get('document_id')} §{first.get('section')}" if first else "—"
    return Row(
        qid=question.qid,
        status=str(response.get("status", "—")),
        top_score=f"{score:.3f}" if isinstance(score, int | float) else "—",
        source=source,
        question=question.text,
    )


def run(questions: list[Question], base_url: str, timeout: float, ask: Ask = ask_api) -> list[Row]:
    rows = []
    for question in questions:
        try:
            rows.append(to_row(question, ask(base_url, question.text, timeout)))
        except urllib.error.HTTPError as exc:
            rows.append(Row(question.qid, f"error: HTTP {exc.code}", "—", "—", question.text))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            rows.append(Row(question.qid, f"error: {type(exc).__name__}", "—", "—", question.text))
    return rows


def format_rows(rows: list[Row]) -> str:
    header = Row("Q", "status", "top score", "first source", "question")
    lines = [header, *rows]
    columns = ("qid", "status", "top_score", "source")
    widths = [max(len(getattr(r, col)) for r in lines) for col in columns]
    out = []
    for r in lines:
        cells = [getattr(r, col).ljust(w) for col, w in zip(columns, widths, strict=True)]
        out.append("  ".join([*cells, r.question]))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the 13 EVALUATION.md questions via the API.")
    parser.add_argument("--url", help="API base URL (default: EVAL_API_BASE_URL)")
    args = parser.parse_args(argv)
    # The questions contain "£"; Windows consoles default to a code page that can't print it.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")

    try:
        settings = load_settings()
    except SettingsError as exc:
        print(exc, file=sys.stderr)
        return 2
    base_url = args.url or settings.eval_api_base_url
    timeout = settings.eval_timeout_seconds
    corpus_dir = settings.corpus_dir
    if base_url is None or timeout is None or corpus_dir is None:
        missing = [
            name
            for name, value in (
                ("EVAL_API_BASE_URL (or --url)", base_url),
                ("EVAL_TIMEOUT_SECONDS", timeout),
                ("CORPUS_DIR", corpus_dir),
            )
            if value is None
        ]
        print("Missing settings: " + ", ".join(missing), file=sys.stderr)
        return 2

    questions = load_questions(corpus_dir / "EVALUATION.md")
    rows = run(questions, base_url, timeout)
    print(f"{len(rows)} questions against {base_url}")
    print(format_rows(rows))
    failed = [r for r in rows if r.status.startswith("error")]
    if failed:
        print(f"{len(failed)} of {len(rows)} questions could not be asked.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
