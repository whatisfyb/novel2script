"""
Unit tests for the scene segmenter (Stage 4) and beat extractor (Stage 5).

Mocks llm_complete to avoid real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pipeline.segmenter import Scene, segment_scenes
from pipeline.extractor import Beat, extract_beats
from pipeline.analyzer import Character, Location
from pipeline.splitter import Chapter


# ---------------------------------------------------------------------------
# Stage 4: Scene Segmenter tests
# ---------------------------------------------------------------------------


_MOCK_SEGMENT_RESPONSE = {
    "scenes": [
        {
            "location": "天文台",
            "time": "night",
            "type": "interior",
            "description": "林晓独自在天文台观测",
            "text_segment": [0, 100],
        },
        {
            "location": "海边",
            "time": "dawn",
            "type": "exterior",
            "description": "林晓和陈默在海滩散步",
            "text_segment": [101, 200],
        },
    ]
}


class TestSegmentScenes:
    @pytest.mark.asyncio
    async def test_returns_scene_list(self) -> None:
        chapter = Chapter(title="第一章", text="内容" * 50, order=1)
        with patch(
            "pipeline.segmenter.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_SEGMENT_RESPONSE
            scenes = await segment_scenes(chapter)

        assert len(scenes) == 2
        assert isinstance(scenes[0], Scene)

    @pytest.mark.asyncio
    async def test_parses_scene_fields(self) -> None:
        chapter = Chapter(title="第一章", text="内容" * 50, order=1)
        with patch(
            "pipeline.segmenter.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_SEGMENT_RESPONSE
            scenes = await segment_scenes(chapter)

        s = scenes[0]
        assert s.location == "天文台"
        assert s.time == "night"
        assert s.type == "interior"
        assert s.text_segment == (0, 100)
        assert s.chapter_order == 1

    @pytest.mark.asyncio
    async def test_includes_character_and_location_context(self) -> None:
        chapter = Chapter(title="第一章", text="text", order=1)
        chars = [Character(name="林晓", role="protagonist")]
        locs = [Location(name="天文台", type="indoor")]
        with patch(
            "pipeline.segmenter.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"scenes": []}
            await segment_scenes(chapter, characters=chars, locations=locs)

        call_args = mock.call_args
        prompt = call_args[0][0]
        assert "林晓" in prompt
        assert "天文台" in prompt

    @pytest.mark.asyncio
    async def test_handles_empty_scenes(self) -> None:
        chapter = Chapter(title="第一章", text="text", order=1)
        with patch(
            "pipeline.segmenter.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"scenes": []}
            scenes = await segment_scenes(chapter)

        assert scenes == []

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self) -> None:
        chapter = Chapter(title="第一章", text="text", order=1)
        with patch(
            "pipeline.segmenter.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {
                "scenes": [
                    {"location": "X", "text_segment": [0, 10]},
                ]
            }
            scenes = await segment_scenes(chapter)

        assert scenes[0].time == "continuous"
        assert scenes[0].type == "interior"
        assert scenes[0].description == ""


# ---------------------------------------------------------------------------
# Stage 5: Beat Extractor tests
# ---------------------------------------------------------------------------


_MOCK_BEATS_RESPONSE = {
    "beats": [
        {
            "type": "action",
            "character_id": "林晓",
            "character_text": "林晓",
            "content": "走进天文台",
            "parenthetical": None,
            "emotion": "专注",
        },
        {
            "type": "dialogue",
            "character_id": "林晓",
            "character_text": "林晓",
            "content": "今晚的星空格外明亮。",
            "parenthetical": "低声",
            "emotion": "感慨",
        },
        {
            "type": "action",
            "character_id": None,
            "character_text": None,
            "content": "远处传来海浪声",
            "parenthetical": None,
            "emotion": None,
        },
    ]
}


class TestExtractBeats:
    @pytest.mark.asyncio
    async def test_returns_beat_list(self) -> None:
        with patch(
            "pipeline.extractor.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_BEATS_RESPONSE
            beats = await extract_beats("scene text")

        assert len(beats) == 3
        assert isinstance(beats[0], Beat)

    @pytest.mark.asyncio
    async def test_parses_beat_fields(self) -> None:
        with patch(
            "pipeline.extractor.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_BEATS_RESPONSE
            beats = await extract_beats("scene text")

        b = beats[0]
        assert b.type == "action"
        assert b.character_id == "林晓"
        assert b.content == "走进天文台"
        assert b.emotion == "专注"
        assert b.id is not None  # auto-generated

    @pytest.mark.asyncio
    async def test_dialogue_beat_with_parenthetical(self) -> None:
        with patch(
            "pipeline.extractor.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_BEATS_RESPONSE
            beats = await extract_beats("scene text")

        b = beats[1]
        assert b.type == "dialogue"
        assert b.parenthetical == "低声"
        assert b.content == "今晚的星空格外明亮。"

    @pytest.mark.asyncio
    async def test_non_character_beat(self) -> None:
        with patch(
            "pipeline.extractor.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = _MOCK_BEATS_RESPONSE
            beats = await extract_beats("scene text")

        b = beats[2]
        assert b.character_id is None
        assert b.character_text is None

    @pytest.mark.asyncio
    async def test_includes_character_context(self) -> None:
        chars = [Character(name="林晓", role="protagonist")]
        with patch(
            "pipeline.extractor.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"beats": []}
            await extract_beats("text", characters=chars)

        call_args = mock.call_args
        prompt = call_args[0][0]
        assert "林晓" in prompt

    @pytest.mark.asyncio
    async def test_empty_beats(self) -> None:
        with patch(
            "pipeline.extractor.llm_complete", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"beats": []}
            beats = await extract_beats("text")

        assert beats == []
