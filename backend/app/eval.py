"""Ask the 13 EVALUATION.md questions and write the results table (REQ-R4).

    python -m app.eval                  # the API at EVAL_API_BASE_URL (local, from .env)
    python -m app.eval --url URL        # any other deployment

Two sources per question:
- status, top score and cited sources come from the API (POST /api/ask);
- the top three retrieved sections come from calling the search code directly, because the
  API returns no sources for a refusal and only cited ones for an answer (plan, Task 0).

Prints one row per question, writes tickets/eval-results.md, and exits non-zero if any
question could not be asked, so a broken run never looks clean.
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
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from qdrant_client import QdrantClient

from app.embeddings import OpenRouterEmbedder
from app.retrieval import Hit, Retriever
from app.settings import REPO_ROOT, SettingsError, load_settings, require

QUESTION_HEADING = re.compile(r"^### (Q\d+) — (?:⭐ )?(.+?)\s*$")
RESULTS_FILE = REPO_ROOT / "tickets" / "eval-results.md"

TE, KYC = "travel-expense-policy-v3.1", "client-onboarding-kyc-v2.4"
RR, OUT = "records-retention-v4.0", "outsourcing-third-party-v1.8"

# Expected sections, transcribed from EVALUATION.md (which stays read only). Each question
# lists groups that must ALL be found; any (document, section) inside a group counts.
# Q8 accepts §4.1 or §4.2; Q10 needs both conflicting policies. Q11–Q13 must refuse.
EXPECTED: dict[str, list[set[tuple[str, str]]]] = {
    "Q1": [{(TE, "4.2")}],
    "Q2": [{(TE, "4.2")}],
    "Q3": [{(TE, "5.2")}],
    "Q4": [{(TE, "6.2")}],
    "Q5": [{(KYC, "6.1")}],
    "Q6": [{(KYC, "6.4")}],
    "Q7": [{(KYC, "4.2")}],
    "Q8": [{(RR, "4.1"), (RR, "4.2")}],
    "Q9": [{(OUT, "4.1")}],
    "Q10": [{(OUT, "6.4")}, {(RR, "4.1")}],
    "Q11": [],
    "Q12": [],
    "Q13": [],
}


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
    cited: tuple[tuple[str, str], ...] = ()


Ask = Callable[[str, str, float], dict]


def found(groups: list[set[tuple[str, str]]], sections: set[tuple[str, str]]) -> bool:
    return all(group & sections for group in groups)


def top_three_hits(retriever: Retriever, question: str) -> list[Hit]:
    return retriever.retrieve(question).current[:3]


def outcome(qid: str, row: Row | None) -> str:
    if row is None or row.status.startswith("error"):
        return "—"
    groups = EXPECTED[qid]
    if not groups:
        return "PASS" if row.status == "refused" else "FAIL"
    return "PASS" if row.status == "answered" and found(groups, set(row.cited)) else "FAIL"


def results_table(
    questions: list[Question], hits: dict[str, list[Hit]], api_rows: list[Row] | None
) -> str:
    by_q = {r.qid: r for r in api_rows or []}
    lines = [
        "| Q | top score | expected in top 3 | top 3 retrieved | API status | cited | outcome |",
        "|---|---|---|---|---|---|---|",
    ]
    for q in questions:
        top = hits.get(q.qid, [])
        sections = {(h.payload["document_id"], h.payload["section"]) for h in top}
        expected = (
            "must refuse"
            if not EXPECTED[q.qid]
            else ("yes" if found(EXPECTED[q.qid], sections) else "NO")
        )
        listed = ", ".join(
            f"{h.payload['document_id']} §{h.payload['section']} ({h.score:.3f})" for h in top
        )
        row = by_q.get(q.qid)
        cited = ", ".join(f"{d} §{s}" for d, s in row.cited) if row and row.cited else "—"
        lines.append(
            f"| {q.qid} | {f'{top[0].score:.3f}' if top else '—'} | {expected} | {listed or '—'} "
            f"| {row.status if row else '—'} | {cited} | {outcome(q.qid, row)} |"
        )
    return "\n".join(lines)


def summary(api_rows: list[Row]) -> tuple[int, int]:
    """(answerable questions answered with the expected section, of 10; refused, of 3)."""
    answered = sum(outcome(r.qid, r) == "PASS" for r in api_rows if EXPECTED[r.qid])
    refused = sum(outcome(r.qid, r) == "PASS" for r in api_rows if not EXPECTED[r.qid])
    return answered, refused


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
    sources = sources if isinstance(sources, list) else []
    first = sources[0] if sources else None
    source = f"{first.get('document_id')} §{first.get('section')}" if first else "—"
    return Row(
        qid=question.qid,
        status=str(response.get("status", "—")),
        top_score=f"{score:.3f}" if isinstance(score, int | float) else "—",
        source=source,
        question=question.text,
        cited=tuple((str(s.get("document_id")), str(s.get("section"))) for s in sources),
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
        cfg = require(
            settings,
            "eval_timeout_seconds",
            "corpus_dir",
            "qdrant_url",
            "qdrant_collection",
            "openrouter_api_key",
            "openrouter_base_url",
            "embedding_model",
            "embedding_timeout_seconds",
            "retrieval_top_k",
        )
    except SettingsError as exc:
        print(exc, file=sys.stderr)
        return 2
    base_url = args.url or settings.eval_api_base_url
    if base_url is None:
        print("Missing settings: EVAL_API_BASE_URL (or --url)", file=sys.stderr)
        return 2

    questions = load_questions(cfg["corpus_dir"] / "EVALUATION.md")
    qdrant_key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
    retriever = Retriever(
        client=QdrantClient(url=cfg["qdrant_url"], api_key=qdrant_key),
        collection=cfg["qdrant_collection"],
        embedder=OpenRouterEmbedder(
            api_key=cfg["openrouter_api_key"].get_secret_value(),
            base_url=cfg["openrouter_base_url"],
            model=cfg["embedding_model"],
            timeout=cfg["embedding_timeout_seconds"],
        ),
        top_k=cfg["retrieval_top_k"],
    )
    hits = {q.qid: top_three_hits(retriever, q.text) for q in questions}
    rows = run(questions, base_url, cfg["eval_timeout_seconds"])
    table = results_table(questions, hits, rows)
    answered, refused = summary(rows)
    failed = [r for r in rows if r.status.startswith("error")]

    print(f"{len(rows)} questions against {base_url}")
    print(format_rows(rows))
    print()
    print(table)
    eval_line = (
        "eval --"
        if len(failed) == len(rows)
        else f"eval {answered}/10 answered, {refused}/3 refused"
    )
    print(eval_line)
    RESULTS_FILE.write_text(
        "# Evaluation results\n\n"
        f"Generated by `python -m app.eval` at {datetime.now(UTC).isoformat(timespec='seconds')} "
        f"against `{base_url}`. Overwritten on every run (T1-assumptions A16).\n\n"
        '"top score" and "top 3 retrieved" are current passages from the search code; '
        '"API status" and "cited" come from `POST /api/ask`. A PASS for Q1–Q10 means '
        "answered and citing the expected section; for Q11–Q13 it means refused.\n\n"
        f"{table}\n\n**{eval_line}**\n",
        encoding="utf-8",
    )
    if failed:
        print(f"{len(failed)} of {len(rows)} questions could not be asked.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
