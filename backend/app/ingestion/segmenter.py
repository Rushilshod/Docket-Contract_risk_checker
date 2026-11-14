"""
Stage 1b — Segmentation: split raw contract text into individual clauses.

Section 3: rule-based heading/section detection with spaCy sentence
boundaries doing the fine-grained split inside each section.
"""
import re
from dataclasses import dataclass
from typing import List


@dataclass
class RawClause:
    index: int
    heading: str | None
    text: str
    start_char: int
    end_char: int


def detect_section_headings(raw_text: str) -> List[tuple[int, str]]:
    """Very conservative heading detection for the minimal runtime pipeline."""
    pattern = re.compile(r"(?im)^(?:\d+[.)]\s*)?(?:ARTICLE|SECTION|CLAUSE|PART)\s*[IVXLC0-9.-]*\s*[:\-–—]?\s*[A-Z][A-Za-z0-9 &/()'-]*$")
    matches: list[tuple[int, str]] = []
    for match in pattern.finditer(raw_text):
        matches.append((match.start(), match.group(0).strip()))
    return matches


def segment_into_clauses(raw_text: str) -> List[RawClause]:
    """Fall back to sentence-level splitting when no heading boundary is detected."""
    text = (raw_text or "").strip()
    if not text:
        return []

    chunks = []
    if "\n" in text:
        blocks = [p.strip() for p in text.splitlines() if p.strip()]
    else:
        blocks = [text]

    for block in blocks:
        sentences = re.split(r"(?<=[.])\s+(?=[A-Z0-9])", block)
        for sentence in sentences:
            cleaned = sentence.strip()
            if cleaned:
                chunks.append(cleaned)

    if not chunks:
        chunks = [text]

    clauses: list[RawClause] = []
    cursor = 0
    for idx, chunk in enumerate(chunks):
        start = raw_text.find(chunk, cursor)
        if start == -1:
            start = cursor
        end = start + len(chunk)
        cursor = end
        clauses.append(
            RawClause(
                index=idx,
                heading=None,
                text=chunk,
                start_char=start,
                end_char=end,
            )
        )
    return clauses
