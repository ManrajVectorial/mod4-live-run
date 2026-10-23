"""Load the policy documents listed in MANIFEST.yaml (REQ-I1, I2). Read only (REQ-I10)."""

from dataclasses import dataclass
from pathlib import Path

import yaml

MANIFEST = "MANIFEST.yaml"
CHECKED_FIELDS = ("id", "version", "status", "effective")


class CorpusError(RuntimeError):
    """The corpus can't be loaded as listed. The message names the file."""


@dataclass(frozen=True)
class Document:
    document_id: str  # unique: "{id}-v{version}" (the MANIFEST id is shared across versions)
    policy_id: str
    title: str
    version: str
    status: str
    effective: str
    supersedes: str | None
    superseded_by: str | None
    superseded_on: str | None
    owner: str
    source_file: str
    body: str


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def _split_front_matter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise CorpusError(f"{path.name}: no front matter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise CorpusError(f"{path.name}: front matter is not closed")
    front = yaml.safe_load(text[4:end]) or {}
    return front, text[end + len("\n---\n") :]


def load_corpus(corpus_dir: Path) -> list[Document]:
    manifest_path = corpus_dir / MANIFEST
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CorpusError(f"{MANIFEST}: cannot read ({type(exc).__name__})") from exc

    documents = []
    for entry in manifest.get("documents", []):
        path = corpus_dir / entry["file"]
        try:
            front, body = _split_front_matter(path)
        except OSError as exc:
            raise CorpusError(f"{entry['file']}: cannot read ({type(exc).__name__})") from exc
        for field in CHECKED_FIELDS:
            if _text(front.get(field)) != _text(entry.get(field)):
                raise CorpusError(
                    f"{entry['file']}: front matter {field!r} does not match {MANIFEST}"
                )
        documents.append(
            Document(
                document_id=f"{entry['id']}-v{entry['version']}",
                policy_id=entry["id"],
                title=entry["title"],
                version=str(entry["version"]),
                status=entry["status"],
                effective=str(entry["effective"]),
                supersedes=_text(entry.get("supersedes")),
                superseded_by=_text(entry.get("superseded_by")),
                superseded_on=_text(entry.get("superseded_on")),
                owner=entry["owner"],
                source_file=entry["file"],
                body=body,
            )
        )
    return documents
