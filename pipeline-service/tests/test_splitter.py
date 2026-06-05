"""
Unit tests for the chapter splitter (Stage 2 of the pipeline).
"""

from __future__ import annotations

import pytest

from pipeline.splitter import Chapter, split_chapters


# ---------- Chinese patterns ----------

class TestChinesePatterns:
    def test_arabic_numerals(self) -> None:
        text = (
            "第1章 开始\n"
            "林晓走进实验室。\n\n"
            "第2章 重逢\n"
            "他已经离开了三年。\n\n"
            "第3章 真相\n"
            "宇宙的秘密即将揭开。"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3
        assert chapters[0].order == 1
        assert "第1章" in chapters[0].title
        assert "林晓走进实验室" in chapters[0].text
        assert "已经离开了三年" in chapters[1].text
        assert "宇宙的秘密" in chapters[2].text

    def test_chinese_numerals(self) -> None:
        text = (
            "第一章 序\n甲乙丙\n\n"
            "第二章\n内容\n\n"
            "第三章\n内容"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3
        assert "第一章" in chapters[0].title

    def test_chinese_variant_hui(self) -> None:
        # 第X回 is a common Chinese pattern in classical novels
        text = (
            "第一回\n甲\n\n第二回\n乙\n\n第三回\n丙"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3

    def test_chinese_variant_jie(self) -> None:
        text = (
            "第一节\n甲\n\n第二节\n乙\n\n第三节\n丙"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3

    def test_chinese_with_colon_subtitle(self) -> None:
        text = (
            "第一章：相遇\ncontent1\n\n"
            "第二章：重逢\ncontent2\n\n"
            "第三章：真相\ncontent3"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3
        assert "第一章" in chapters[0].title

    def test_skips_empty_chapter_body(self) -> None:
        text = (
            "第一章\n内容A\n\n"
            "第二章\n\n\n"  # empty body
            "第三章\n内容C"
        )
        chapters = split_chapters(text)
        # Only 2 chapters with non-empty bodies
        assert len(chapters) == 2
        assert "内容A" in chapters[0].text
        assert "内容C" in chapters[1].text


# ---------- English patterns ----------

class TestEnglishPatterns:
    def test_chapter_n(self) -> None:
        text = (
            "Chapter 1\nIt was a dark night.\n\n"
            "Chapter 2\nThe wind howled.\n\n"
            "Chapter 3\nThen it happened."
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3
        assert "Chapter 1" in chapters[0].title
        assert "dark night" in chapters[0].text

    def test_chapter_with_subtitle(self) -> None:
        text = (
            "Chapter 1: The Beginning\nfoo\n\n"
            "Chapter 2: The Middle\nbar\n\n"
            "Chapter 3: The End\nbaz"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3

    def test_chapter_lowercase(self) -> None:
        text = (
            "chapter 1\nfoo\n\n"
            "chapter 2\nbar\n\n"
            "chapter 3\nbaz"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3


# ---------- Markdown hints ----------

class TestMarkdownHints:
    def test_hints_take_priority(self) -> None:
        text = (
            "some intro text\n\n"
            "Act 1\n"
            "content1\n\n"
            "Act 2\n"
            "content2\n\n"
            "Act 3\n"
            "content3"
        )
        chapters = split_chapters(text, hints=["Act 1", "Act 2", "Act 3"])
        assert len(chapters) == 3
        assert chapters[0].title == "Act 1"
        assert "content1" in chapters[0].text
        assert "content2" in chapters[1].text
        assert "content3" in chapters[2].text

    def test_hints_filtered_when_not_in_text(self) -> None:
        text = "no headings here at all\njust plain prose"
        chapters = split_chapters(text, hints=["Nonexistent"])
        # Falls back to single-chapter full text
        assert len(chapters) == 1
        assert chapters[0].title == "全文"


# ---------- Plain numeric fallback ----------

class TestPlainNumericFallback:
    def test_numeric_with_dot(self) -> None:
        text = (
            "1. The Start\nfoo\n\n"
            "2. The Middle\nbar\n\n"
            "3. The End\nbaz"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3

    def test_numeric_with_paren(self) -> None:
        text = (
            "1) First\nfoo\n\n"
            "2) Second\nbar\n\n"
            "3) Third\nbaz"
        )
        chapters = split_chapters(text)
        assert len(chapters) == 3


# ---------- Edge cases ----------

class TestEdgeCases:
    def test_empty_text_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            split_chapters("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            split_chapters("   \n\n   ")

    def test_no_structure_returns_single_chapter(self) -> None:
        text = "Just some prose without any chapter headings whatsoever at all."
        chapters = split_chapters(text)
        assert len(chapters) == 1
        assert chapters[0].title == "全文"
        assert chapters[0].order == 1

    def test_only_one_chapter_heading_returns_single(self) -> None:
        # Only 1 chapter heading — not enough to split confidently
        text = "第1章 开始\nsome content"
        chapters = split_chapters(text)
        assert len(chapters) == 1

    def test_chapter_dataclass_immutable_order(self) -> None:
        ch = Chapter(title="t", text="body", order=1)
        assert ch.title == "t"
        assert ch.text == "body"
        assert ch.order == 1
