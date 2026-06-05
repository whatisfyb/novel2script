"""
Stage 1: File Parser — converts uploaded files to raw text.

Supported formats:
  - .txt  → chardet encoding detection → UTF-8 plain text
  - .md   → markdown parsing → preserves heading hierarchy as chapter hints
  - .docx → python-docx → paragraph extraction with Heading styles preserved
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import chardet

logger = logging.getLogger(__name__)
from docx import Document
from markdown import markdown


SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".docx"}

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_BLANK_LINE_RE = re.compile(r"\n{3,}")


@dataclass
class RawText:
    """Parsed file output — plain text with optional chapter markers."""

    content: str
    filename: str
    encoding: str
    chapter_hints: list[str] = field(default_factory=list)


def parse_file(path: str | Path) -> RawText:
    """
    Parse an uploaded file into raw text.

    Args:
        path: file path to the uploaded document (.txt, .md, or .docx)

    Returns:
        RawText object with extracted content and chapter heading hints.

    Raises:
        ValueError: if file format is not supported
        FileNotFoundError: if path does not exist
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = p.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {suffix}. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    if suffix == ".txt":
        return _parse_txt(p)
    if suffix in (".md", ".markdown"):
        return _parse_md(p)
    if suffix == ".docx":
        return _parse_docx(p)

    raise ValueError(f"Unhandled extension: {suffix}")


def _parse_txt(path: Path) -> RawText:
    """Read a .txt file with automatic encoding detection via chardet."""
    raw = path.read_bytes()
    detection = chardet.detect(raw)
    encoding = detection.get("encoding") or "utf-8"
    confidence = detection.get("confidence", 0) or 0
    if confidence < 0.1:
        logger.debug("Low encoding confidence (%.2f) for %s, using %s", confidence, path.name, encoding)
    # chardet may return 'GB2312' or 'GBK' — normalize to 'gbk'
    if encoding.lower().replace("-", "") in ("gb2312", "gbk", "gb18030"):
        encoding = "gbk"
    content = raw.decode(encoding, errors="replace")
    content = _normalize_whitespace(content)
    return RawText(
        content=content,
        filename=path.name,
        encoding=encoding,
        chapter_hints=[],
    )


def _parse_md(path: Path) -> RawText:
    """Read a .md file: keep content as plain text, extract headings as hints."""
    raw = path.read_bytes()
    detection = chardet.detect(raw)
    encoding = detection.get("encoding") or "utf-8"
    if encoding.lower().replace("-", "") in ("gb2312", "gbk", "gb18030"):
        encoding = "gbk"
    content = raw.decode(encoding, errors="replace")

    # Extract heading texts as chapter hints (preserves # hierarchy)
    hints = [m.group(2).strip() for m in _HEADING_RE.finditer(content)]

    content = _normalize_whitespace(content)
    return RawText(
        content=content,
        filename=path.name,
        encoding=encoding,
        chapter_hints=hints,
    )


def _parse_docx(path: Path) -> RawText:
    """Read a .docx file via python-docx, preserving heading style info."""
    doc = Document(str(path))
    lines: list[str] = []
    hints: list[str] = []

    for para in doc.paragraphs:
        text = para.text
        if not text.strip():
            continue
        style_name = (para.style.name or "").lower() if para.style else ""
        is_heading = style_name.startswith("heading")
        if is_heading:
            hints.append(text.strip())
        lines.append(text)

    content = _normalize_whitespace("\n".join(lines))
    return RawText(
        content=content,
        filename=path.name,
        encoding="utf-8",
        chapter_hints=hints,
    )


def _normalize_whitespace(text: str) -> str:
    """Collapse 3+ consecutive newlines to 2, strip trailing whitespace."""
    text = _BLANK_LINE_RE.sub("\n\n", text)
    return text.strip()
