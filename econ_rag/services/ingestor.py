"""PDF ingestion: extract, clean, split into section-aware chunks.

The lecture notes are LaTeX-generated, which gives us reliable structure to
exploit: a running header on every page after the first, a page number as the
last line, and numbered section headings. Chunking respects section boundaries
so that every chunk can carry an accurate "Lecture 4, §9 Fixed and Variable
Costs, p. 12" citation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from pypdf import PdfReader

from econ_rag.config import settings
from econ_rag.database import Chunk, Document, get_session
from econ_rag.taxonomy import topic_from_section

# "ECON 154 Lecture 4 Bates College" / "Economics 154 Lecture 1 Bates College"
RUNNING_HEADER = re.compile(
    r"^(ECON|Economics)\s*154\b.*Bates College\s*$", re.IGNORECASE
)
PAGE_NUMBER_ONLY = re.compile(r"^\s*\d{1,3}\s*$")
# "12 Section Title" or "16.4 Subsection Title" - LaTeX numbered headings.
SECTION_HEADING = re.compile(r"^(\d{1,2}(?:\.\d{1,2})?)\s+(\S.{2,90})$")
# A table-of-contents line ends with a page number: "5 Market Equilibrium 4"
TOC_LINE = re.compile(r"^\d{1,2}(?:\.\d{1,2})?\s+\S.*\s\d{1,3}\s*$")

# PDF text-extraction artifacts seen in these documents.
_CHAR_FIXES = [
    ("ﬀ", "ff"), ("ﬁ", "fi"), ("ﬂ", "fl"),
    ("ﬃ", "ffi"), ("ﬄ", "ffl"),
    ("−", "-"), ("–", "-"), ("—", "--"),
    ("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
    (" ", " "),
]
# LaTeX accent artifacts: "caf´ e" -> "café", "na¨ ıve" -> "naïve".
_ACCENTS = {
    ("´", "a"): "á", ("´", "e"): "é", ("´", "i"): "í",
    ("´", "o"): "ó", ("´", "u"): "ú",
    ("¨", "a"): "ä", ("¨", "e"): "ë", ("¨", "i"): "ï",
    ("¨", "o"): "ö", ("¨", "u"): "ü",
    ("`", "a"): "à", ("`", "e"): "è",
    ("^", "a"): "â", ("^", "e"): "ê", ("^", "o"): "ô",
    ("~", "n"): "ñ",
}
_ACCENT_RE = re.compile(r"([´¨`^~])\s*(?:ı|[aeiou])")


@dataclass
class Section:
    """A numbered section of a lecture with its accumulated text."""

    number: Optional[str]
    title: Optional[str]
    start_page: int
    lines: List[str] = field(default_factory=list)
    # Callout blocks ("Definition", "Real-World Example") are unnumbered and
    # carry no topic hint of their own, so they inherit the enclosing section's.
    parent_topic: Optional[str] = None
    parent_title: Optional[str] = None

    @property
    def text(self) -> str:
        return _join_lines(self.lines)


def _fix_chars(text: str) -> str:
    for bad, good in _CHAR_FIXES:
        text = text.replace(bad, good)

    def _accent(match: re.Match) -> str:
        mark = match.group(0)[0]
        letter = match.group(0)[-1]
        letter = "i" if letter == "ı" else letter
        return _ACCENTS.get((mark, letter), letter)

    return _ACCENT_RE.sub(_accent, text)


def _join_lines(lines: Iterable[str]) -> str:
    """Join wrapped lines into paragraphs, repairing hyphenated line breaks."""
    out: List[str] = []
    for line in lines:
        line = line.rstrip()
        if not line:
            if out and out[-1] != "\n":
                out.append("\n")
            continue
        if out and out[-1].endswith("-") and not out[-1].endswith("--"):
            out[-1] = out[-1][:-1] + line.lstrip()
        elif out and out[-1] != "\n":
            out[-1] = out[-1] + " " + line.lstrip()
        else:
            out.append(line)
    return re.sub(r"\n{2,}", "\n", "".join(
        part if part == "\n" else part + "\n" for part in out
    )).strip()


def _clean_page(raw: str) -> List[str]:
    """Strip running headers and standalone page numbers from a page."""
    lines = []
    for line in (raw or "").split("\n"):
        line = _fix_chars(line).rstrip()
        if RUNNING_HEADER.match(line):
            continue
        if PAGE_NUMBER_ONLY.match(line):
            continue
        lines.append(line)
    return lines


class DocumentIngestor:
    """Extract a PDF into topic-tagged, citable chunks."""

    def __init__(self, session=None):
        self.session = session or get_session()
        self._owns_session = session is None

    # ---------- extraction ----------

    def parse_pdf(self, file_path: str) -> tuple[str, List[Section], int]:
        """Return (document title, sections, page count)."""
        reader = PdfReader(file_path)
        sections: List[Section] = []
        current = Section(number=None, title="Front Matter", start_page=1)
        title_lines: List[str] = []
        saw_body_heading = False
        pending_heading = False
        in_front_matter = True
        last_numbered: Optional[Section] = None

        for page_index, page in enumerate(reader.pages):
            page_num = page_index + 1
            for line in _clean_page(page.extract_text() or ""):
                # A table-of-contents entry ends with its page number; a real
                # heading does not. Only front matter is treated this way, so a
                # body heading that happens to end in a digit is safe.
                if in_front_matter and TOC_LINE.match(line):
                    continue
                if page_index == 0 and len(title_lines) < 5 and not saw_body_heading:
                    if not SECTION_HEADING.match(line) and line.strip():
                        title_lines.append(line.strip())

                match = SECTION_HEADING.match(line)
                if match and self._is_real_heading(line, match):
                    saw_body_heading = True
                    in_front_matter = False
                    if current.lines:
                        sections.append(current)
                    heading_title = match.group(2).strip()
                    if heading_title.endswith("-"):
                        # Heading wrapped mid-word; the remainder opens the
                        # next line, which belongs to the title, not the body.
                        pending_heading = True
                    else:
                        pending_heading = False
                    current = Section(
                        number=match.group(1),
                        title=heading_title,
                        start_page=page_num,
                        parent_topic=topic_from_section(
                            f"{match.group(1)} {heading_title}"
                        ),
                        parent_title=heading_title,
                    )
                    last_numbered = current
                    continue

                if pending_heading:
                    pending_heading = False
                    head, _, rest = line.partition(" ")
                    current.title = (current.title or "")[:-1] + head
                    current.parent_title = current.title
                    current.parent_topic = topic_from_section(
                        f"{current.number or ''} {current.title}"
                    )
                    if last_numbered is current:
                        last_numbered = current
                    if rest.strip():
                        current.lines.append(rest.strip())
                    continue

                # Unnumbered but meaningful headings (e.g. "Learning Objectives").
                if self._is_unnumbered_heading(line):
                    saw_body_heading = True
                    if current.lines:
                        sections.append(current)
                    current = Section(
                        number=None,
                        title=line.strip(),
                        start_page=page_num,
                        parent_topic=last_numbered.parent_topic if last_numbered else None,
                        parent_title=last_numbered.parent_title if last_numbered else None,
                    )
                    continue

                current.lines.append(line)
                current.end_page = page_num  # type: ignore[attr-defined]

        if current.lines:
            sections.append(current)

        title = " ".join(title_lines[:4]).strip() or Path(file_path).stem
        return title, sections, len(reader.pages)

    @staticmethod
    def _is_real_heading(line: str, match: re.Match) -> bool:
        """Reject numbered list items ('1. How would...') and stray numbers."""
        title = match.group(2).strip()
        if not title or not title[0].isupper():
            return False
        if len(title.split()) > 12:
            return False
        if title.endswith((".", ",", ";", ":")) and not title.endswith("..."):
            return False
        # A numbered list item in these notes is written "1. Text", which the
        # heading regex would otherwise read as section "1" titled ". Text".
        return not re.match(r"^\d+\.\s", line)

    @staticmethod
    def _is_unnumbered_heading(line: str) -> bool:
        stripped = line.strip()
        return stripped in {
            "Learning Objectives",
            "Purpose of the Lecture",
            "Purpose and Learning Objectives",
            "Purpose of the First Class",
            "Contents",
            "Definition",
            "Economic Intuition",
            "Real-World Example",
            "Key Takeaway",
            "Common Misconceptions",
        }

    # ---------- chunking ----------

    def chunk_sections(
        self,
        sections: List[Section],
        chunk_size: int = None,
        overlap: int = None,
    ) -> List[dict]:
        """Split sections into overlapping word-windows, never crossing sections."""
        chunk_size = chunk_size or settings.CHUNK_SIZE
        overlap = overlap or settings.CHUNK_OVERLAP
        chunks: List[dict] = []

        for section in sections:
            text = section.text
            if len(text.split()) < 20:
                continue
            heading = (
                f"{section.number} {section.title}".strip()
                if section.number
                else (section.title or "")
            )
            cite_title = section.title
            if section.number is None and section.parent_title:
                cite_title = f"{section.parent_title} ({section.title})"
            words = text.split()
            step = max(1, chunk_size - overlap)
            for start in range(0, len(words), step):
                window = words[start : start + chunk_size]
                if len(window) < 25 and chunks:
                    break
                body = " ".join(window)
                chunks.append(
                    {
                        "content": f"[{heading}]\n{body}" if heading else body,
                        "raw": body,
                        "section_num": section.number,
                        "section_title": cite_title,
                        "page_num": section.start_page,
                        "word_count": len(window),
                        "topic": topic_from_section(
                            f"{section.number or ''} {section.title or ''}"
                        )
                        or section.parent_topic,
                    }
                )
                if start + chunk_size >= len(words):
                    break
        return chunks

    # ---------- persistence ----------

    def ingest_file(
        self,
        file_path: str,
        source_type: str = "lecture",
        sequence: Optional[int] = None,
        course: str = "ECON 154",
        replace: bool = True,
    ) -> int:
        """Ingest one file and return its document id."""
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)

        checksum = hashlib.sha256(path.read_bytes()).hexdigest()[:64]
        existing = (
            self.session.query(Document).filter(Document.name == path.name).first()
        )
        if existing:
            if not replace and existing.checksum == checksum:
                print(f"  = {path.name} already ingested (unchanged), skipping")
                return existing.id
            self.session.delete(existing)
            self.session.commit()

        if sequence is None:
            match = re.search(r"(\d+)", path.stem)
            sequence = int(match.group(1)) if match else None

        title, sections, total_pages = self.parse_pdf(str(path))
        document = Document(
            name=path.name,
            title=title,
            file_path=str(path),
            file_type=path.suffix.lstrip(".").lower() or "pdf",
            source_type=source_type,
            sequence=sequence,
            course=course,
            total_pages=total_pages,
            checksum=checksum,
            status="processing",
        )
        self.session.add(document)
        self.session.flush()

        rows = self.chunk_sections(sections)
        for i, row in enumerate(rows, start=1):
            self.session.add(
                Chunk(
                    document_id=document.id,
                    chunk_num=i,
                    content=row["content"],
                    section_num=row["section_num"],
                    section_title=row["section_title"],
                    page_num=row["page_num"],
                    word_count=row["word_count"],
                    topic=row["topic"],
                )
            )
        document.status = "complete"
        self.session.commit()
        print(
            f"  + {path.name}: {total_pages} pages, "
            f"{len(sections)} sections, {len(rows)} chunks"
        )
        return document.id

    def close(self) -> None:
        if self._owns_session:
            self.session.close()
