"""
Unit tests for the pipeline orchestrator (end-to-end flow).

Mocks only LLM calls (stages 3-5); parser/splitter/assembler run for real.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from pathlib import Path

import pytest
import yaml

from pipeline.orchestrator import run_pipeline
from pipeline.analyzer import StructureResult, Character, Location
from pipeline.segmenter import Scene
from pipeline.extractor import Beat


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_STRUCTURE = StructureResult(
    synopsis="一个科学家发现宇宙的秘密",
    characters=[
        Character(name="林晓", aliases=["汪教授"], role="protagonist", description="天体物理学家"),
        Character(name="陈默", aliases=[], role="supporting", description="研究生"),
    ],
    locations=[
        Location(name="天文台", type="indoor", description="山顶观测站"),
        Location(name="海边", type="outdoor", description="小城海滩"),
    ],
)


def _mock_scenes(chapter_order: int, text_len: int) -> list[Scene]:
    return [
        Scene(
            location="天文台",
            time="night",
            type="interior",
            description="观测场景",
            text_segment=(0, text_len // 2),
            chapter_order=chapter_order,
        ),
        Scene(
            location="海边",
            time="dawn",
            type="exterior",
            description="散步场景",
            text_segment=(text_len // 2, text_len),
            chapter_order=chapter_order,
        ),
    ]


_MOCK_BEATS = [
    Beat(type="action", character_id="林晓", character_text="林晓", content="走进天文台", parenthetical=None, emotion="专注"),
    Beat(type="dialogue", character_id="林晓", character_text="林晓", content="今晚的星空格外明亮。", parenthetical="低声", emotion="感慨"),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_returns_valid_yaml(self, tmp_path: Path) -> None:
        """Full pipeline on a 3-chapter txt file produces valid YAML."""
        # Create a 3-chapter test file
        content = (
            "第1章 开始\n林晓走进天文台，望着星空。这是故事的开端。\n\n"
            "第2章 发展\n陈默递来一杯咖啡。两人讨论了宇宙的秘密。\n\n"
            "第3章 结局\n真相终于揭开。林晓独自站在海边，感慨万千。"
        )
        f = tmp_path / "novel.txt"
        f.write_text(content, encoding="utf-8")

        # Mock only LLM calls
        with patch("pipeline.orchestrator.analyze_structure", new_callable=AsyncMock) as mock_analyze, \
             patch("pipeline.orchestrator.segment_scenes", new_callable=AsyncMock) as mock_segment, \
             patch("pipeline.orchestrator.extract_beats", new_callable=AsyncMock) as mock_extract:

            mock_analyze.return_value = _MOCK_STRUCTURE
            mock_segment.side_effect = lambda ch, **kw: _mock_scenes(ch.order, len(ch.text))
            mock_extract.return_value = _MOCK_BEATS

            result = await run_pipeline(f, title="三体", author="刘慈欣")

        doc = yaml.safe_load(result)
        assert isinstance(doc, dict)
        assert doc["meta"]["title"] == "三体"
        assert doc["meta"]["author"] == "刘慈欣"

    @pytest.mark.asyncio
    async def test_characters_and_locations_in_output(self, tmp_path: Path) -> None:
        content = "第1章\n内容。\n\n第2章\n更多内容。\n\n第3章\n结尾。"
        f = tmp_path / "novel.txt"
        f.write_text(content, encoding="utf-8")

        with patch("pipeline.orchestrator.analyze_structure", new_callable=AsyncMock) as mock_analyze, \
             patch("pipeline.orchestrator.segment_scenes", new_callable=AsyncMock) as mock_segment, \
             patch("pipeline.orchestrator.extract_beats", new_callable=AsyncMock) as mock_extract:

            mock_analyze.return_value = _MOCK_STRUCTURE
            mock_segment.side_effect = lambda ch, **kw: _mock_scenes(ch.order, len(ch.text))
            mock_extract.return_value = []

            result = await run_pipeline(f)

        doc = yaml.safe_load(result)
        char_names = [c["name"] for c in doc["characters"]]
        assert "林晓" in char_names
        assert "陈默" in char_names

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, tmp_path: Path) -> None:
        content = "第1章\nA。\n\n第2章\nB。\n\n第3章\nC。"
        f = tmp_path / "novel.txt"
        f.write_text(content, encoding="utf-8")

        calls: list[tuple[str, int]] = []

        async def track_progress(stage: str, pct: int) -> None:
            calls.append((stage, pct))

        with patch("pipeline.orchestrator.analyze_structure", new_callable=AsyncMock) as mock_analyze, \
             patch("pipeline.orchestrator.segment_scenes", new_callable=AsyncMock) as mock_segment, \
             patch("pipeline.orchestrator.extract_beats", new_callable=AsyncMock) as mock_extract:

            mock_analyze.return_value = _MOCK_STRUCTURE
            mock_segment.return_value = []
            mock_extract.return_value = []

            await run_pipeline(f, progress_callback=track_progress)

        # Should have at least parser/splitter/analyzer/segmenter/assembler stages
        stage_names = [s for s, _ in calls]
        assert "parser" in stage_names
        assert "splitter" in stage_names
        assert "analyzer" in stage_names
        assert "segmenter" in stage_names
        assert "assembler" in stage_names

    @pytest.mark.asyncio
    async def test_handles_single_chapter_file(self, tmp_path: Path) -> None:
        """Single chapter file should still produce valid YAML (splitter returns full text)."""
        content = "这是很长的一段文字，没有章节标记，但足够长以通过检测。" * 20
        f = tmp_path / "novel.txt"
        f.write_text(content, encoding="utf-8")

        with patch("pipeline.orchestrator.analyze_structure", new_callable=AsyncMock) as mock_analyze, \
             patch("pipeline.orchestrator.segment_scenes", new_callable=AsyncMock) as mock_segment, \
             patch("pipeline.orchestrator.extract_beats", new_callable=AsyncMock) as mock_extract:

            mock_analyze.return_value = _MOCK_STRUCTURE
            mock_segment.return_value = _mock_scenes(1, len(content))
            mock_extract.return_value = _MOCK_BEATS

            result = await run_pipeline(f)

        doc = yaml.safe_load(result)
        assert doc["meta"]["source_chapters"] == 1
