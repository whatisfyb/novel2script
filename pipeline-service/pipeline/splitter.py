"""
Stage 2: Chapter Splitter — splits raw text into chapters.

Regex patterns:
  - Chinese: "第X章 / 第X回 / 第X节 / 第X卷" (Arabic or Chinese numerals)
  - English: "Chapter N", "CHAPTER N", "Ch. N"
  - Markdown hints (from Stage 1) take priority when present

Caller is responsible for LLM fallback when this returns < 2 chapters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Chinese chapter heading prefix: "第1章", "第一章", "第十回", "第三节", "第五卷"
_CHINESE_NUMERALS = "零一二三四五六七八九十百千〇两"
_CN_CHAPTER_RE = re.compile(
    rf"^第[0-9{_CHINESE_NUMERALS}]+[章回节卷部]",
    re.MULTILINE,
)

# English: "Chapter 1", "CHAPTER 12", "Ch. 3"
_EN_CHAPTER_RE = re.compile(
    r"^(?:chapter|ch\.?)\s+[0-9a-z]+",
    re.IGNORECASE | re.MULTILINE,
)

# Plain numeric heading: "1. Title", "1) Title"
_PLAIN_HEADING_RE = re.compile(r"^[0-9]{1,3}\s*[、.)]\s*.+$", re.MULTILINE)

MIN_CHAPTERS_FOR_ACCEPT = 2


@dataclass
class Chapter:
    """A single chapter extracted from the novel."""

    title: str
    text: str
    order: int  # 1-based chapter number


def split_chapters(
    text: str,
    hints: list[str] | None = None,
) -> list[Chapter]:
    """
    Split raw text into individual chapters.

    Args:
        text: the full novel text
        hints: optional heading hints from the file parser (Stage 1)

    Returns:
        List of Chapter objects, ordered by appearance.

    Raises:
        ValueError: if text is empty
    """
    if not text or not text.strip():
        raise ValueError("Cannot split empty text")

    # 1) markdown hints (most reliable — structural)
    if hints and len(hints) >= MIN_CHAPTERS_FOR_ACCEPT:
        chapters = _split_by_hints(text, hints)
        if len(chapters) >= MIN_CHAPTERS_FOR_ACCEPT:
            return chapters

    # 2) Chinese pattern
    chapters = _split_by_regex(text, _CN_CHAPTER_RE)
    if len(chapters) >= MIN_CHAPTERS_FOR_ACCEPT:
        return chapters

    # 3) English pattern
    chapters = _split_by_regex(text, _EN_CHAPTER_RE)
    if len(chapters) >= MIN_CHAPTERS_FOR_ACCEPT:
        return chapters

    # 4) Plain numeric heading fallback
    chapters = _split_by_regex(text, _PLAIN_HEADING_RE)
    if len(chapters) >= MIN_CHAPTERS_FOR_ACCEPT:
        return chapters

    # Not enough structure — return a single chapter containing the full text
    return [Chapter(title="全文", text=text.strip(), order=1)]


def _split_by_regex(text: str, pattern: re.Pattern) -> list[Chapter]:
    """Find heading prefixes via regex, then extract title + body between them."""
    matches = list(pattern.finditer(text))
    if not matches:
        return []

    # Build (match_start, title) pairs
    boundaries: list[tuple[int, str]] = []
    for m in matches:
        line_end = text.find("\n", m.start())
        if line_end < 0:
            line_end = len(text)
        title = text[m.start():line_end].strip()
        boundaries.append((m.start(), title))

    # Build chapters: body is the text between heading line end and next heading start
    chapters: list[Chapter] = []
    for i, (pos, title) in enumerate(boundaries):
        heading_line_end = text.find("\n", pos)
        body_start = (heading_line_end + 1) if heading_line_end >= 0 else len(text)
        body_end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        body = text[body_start:body_end].strip()
        if not body:
            continue
        chapters.append(Chapter(title=title, text=body, order=len(chapters) + 1))
    return chapters


def _split_by_hints(text: str, hints: list[str]) -> list[Chapter]:
    """Split text by matching heading hints found in the body."""
    positions: list[tuple[int, str]] = []
    cursor = 0
    for hint in hints:
        hint_clean = hint.strip()
        if not hint_clean:
            continue
        idx = text.find(hint_clean, cursor)
        if idx < 0:
            continue
        positions.append((idx, hint_clean))
        cursor = idx + len(hint_clean)

    if not positions:
        return []

    chapters: list[Chapter] = []
    for i, (pos, title) in enumerate(positions):
        line_end = text.find("\n", pos)
        body_start = (line_end + 1) if line_end >= 0 else len(text)
        body_end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        body = text[body_start:body_end].strip()
        if not body:
            continue
        chapters.append(Chapter(title=title, text=body, order=len(chapters) + 1))
    return chapters
