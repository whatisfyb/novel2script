"""
Unit tests for the structure analyzer (Stage 3 of the pipeline).

Mocks llm_complete to avoid real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pipeline.analyzer import Character, Location, StructureResult, analyze_structure
from pipeline.splitter import Chapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_LLM_RESPONSE = {
    "synopsis": "一个科学家发现宇宙的秘密",
    "characters": [
        {
            "name": "林晓",
            "aliases": ["汪教授", "老林"],
            "role": "protagonist",
            "description": "天体物理学家，执着于寻找真相",
        },
        {
            "name": "陈默",
            "aliases": [],
            "role": "supporting",
            "description": "林晓的研究生助手",
        },
    ],
    "locations": [
        {
            "name": "天文台",
            "type": "indoor",
            "description": "位于山顶的天文观测站",
        },
        {
            "name": "海边",
            "type": "outdoor",
            "description": "小城东侧的海滩",
        },
    ],
}


def _make_chapters() -> list[Chapter]:
    return [
        Chapter(title="第一章", text="林晓走进天文台，望着星空。" * 20, order=1),
        Chapter(title="第二章", text="陈默递来一杯咖啡。" * 15, order=2),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAnalyzeStructure:
    @pytest.mark.asyncio
    async def test_returns_structure_result(self) -> None:
        chapters = _make_chapters()
        with patch(
            "pipeline.analyzer.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_LLM_RESPONSE
            result = await analyze_structure(chapters)

        assert isinstance(result, StructureResult)
        assert result.synopsis == "一个科学家发现宇宙的秘密"

    @pytest.mark.asyncio
    async def test_parses_characters(self) -> None:
        chapters = _make_chapters()
        with patch(
            "pipeline.analyzer.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_LLM_RESPONSE
            result = await analyze_structure(chapters)

        assert len(result.characters) == 2
        assert isinstance(result.characters[0], Character)
        assert result.characters[0].name == "林晓"
        assert result.characters[0].role == "protagonist"
        assert "汪教授" in result.characters[0].aliases
        assert result.characters[1].name == "陈默"
        assert result.characters[1].role == "supporting"

    @pytest.mark.asyncio
    async def test_parses_locations(self) -> None:
        chapters = _make_chapters()
        with patch(
            "pipeline.analyzer.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_LLM_RESPONSE
            result = await analyze_structure(chapters)

        assert len(result.locations) == 2
        assert isinstance(result.locations[0], Location)
        assert result.locations[0].name == "天文台"
        assert result.locations[0].type == "indoor"

    @pytest.mark.asyncio
    async def test_truncates_chapter_text(self) -> None:
        """Chapters longer than 500 chars should be truncated in the prompt."""
        long_chapter = Chapter(title="长章", text="A" * 1000, order=1)
        with patch(
            "pipeline.analyzer.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_LLM_RESPONSE
            await analyze_structure([long_chapter])

        # Verify the prompt contains truncated text
        call_args = mock.call_args
        prompt = call_args[0][0]  # first positional arg
        assert "..." in prompt
        # The prompt should not contain the full 1000-char text
        assert "A" * 600 not in prompt

    @pytest.mark.asyncio
    async def test_handles_empty_characters_and_locations(self) -> None:
        chapters = _make_chapters()
        with patch(
            "pipeline.analyzer.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"synopsis": "empty story", "characters": [], "locations": []}
            result = await analyze_structure(chapters)

        assert result.synopsis == "empty story"
        assert result.characters == []
        assert result.locations == []

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self) -> None:
        """LLM response may omit optional fields like aliases, description."""
        chapters = _make_chapters()
        minimal_response = {
            "synopsis": "minimal",
            "characters": [{"name": "Bob", "role": "extra"}],
            "locations": [{"name": "Park", "type": "outdoor"}],
        }
        with patch(
            "pipeline.analyzer.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = minimal_response
            result = await analyze_structure(chapters)

        assert result.characters[0].aliases == []
        assert result.characters[0].description == ""
        assert result.locations[0].description == ""
