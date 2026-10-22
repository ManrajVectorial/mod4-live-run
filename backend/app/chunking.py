"""Cut a document into passages as D1 decides (REQ-I3, I4).

- One passage per numbered section: every "## N." or "### N.N" heading starts a section,
  and a passage never crosses into the next one. The preamble before the first numbered
  heading (title, owner line, superseded banner) is not a section and is not indexed; the
  document's status travels in the payload instead.
- A Markdown table is never split. A section longer than CHUNK_SIZE characters is split at
  paragraph boundaries; a single paragraph or table longer than the cap stays whole.
- No overlap (D1).
"""

import re
from dataclasses import dataclass

from app.corpus import Document

HEADING = re.compile(r"^(#{2,3}) (\d+(?:\.\d+)?)\.? (.+?)\s*$")
RULE = re.compile(r"^-{3,}\s*$")


@dataclass(frozen=True)
class Passage:
    passage_id: str
    document: Document
    section: str
    section_title: str
    heading_path: tuple[str, ...]
    chunk_index: int
    order: int
    text: str

    @property
    def embedding_text(self) -> str:
        """What gets embedded: the section heading, then the passage (D1)."""
        return f"{self.section} {self.section_title}\n{self.text}"


def _blocks(lines: list[str]) -> list[str]:
    """Paragraphs and tables: runs of non-blank lines. Table rows are never blank, so a
    table is always one block."""
    blocks, current = [], []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def _pack(blocks: list[str], chunk_size: int) -> list[str]:
    chunks, current = [], ""
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if current and len(candidate) > chunk_size:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def split_passages(document: Document, chunk_size: int, chunk_overlap: int) -> list[Passage]:
    if chunk_overlap != 0:
        raise ValueError("CHUNK_OVERLAP must be 0: D1 decided no overlap")
    if chunk_size <= 0:
        raise ValueError("CHUNK_SIZE must be positive")

    sections: list[tuple[str, str, tuple[str, ...], list[str]]] = []
    parent: str | None = None
    for line in document.body.splitlines():
        match = HEADING.match(line)
        if match:
            level, number, title = match.groups()
            heading = f"{number}. {title}" if level == "##" else f"{number} {title}"
            if level == "##":
                parent = heading
                path: tuple[str, ...] = (heading,)
            else:
                path = (parent, heading) if parent else (heading,)
            sections.append((number, title, path, []))
        elif sections and not RULE.match(line):
            sections[-1][3].append(line)

    passages, order = [], 0
    for number, title, path, lines in sections:
        for index, chunk in enumerate(_pack(_blocks(lines), chunk_size)):
            passages.append(
                Passage(
                    passage_id=f"{document.document_id}:{number}:{index}",
                    document=document,
                    section=number,
                    section_title=title,
                    heading_path=path,
                    chunk_index=index,
                    order=order,
                    text=chunk,
                )
            )
            order += 1
    return passages
