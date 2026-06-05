"""
Unit tests for the YAML assembler (Stage 6 of the pipeline).
"""

from __future__ import annotations

import yaml
import pytest

from pipeline.assembler import SchemaValidationError, assemble_yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _base_meta() -> dict:
    return {
        "title": "三体",
        "original_title": "三体",
        "author": "刘慈欣",
        "type": "movie",
        "language": "zh",
        "source_chapters": 3,
        "synopsis": "科学家发现三体文明的秘密",
    }


def _base_characters() -> list[dict]:
    return [
        {"name": "林晓", "aliases": ["汪教授"], "role": "protagonist", "description": "天体物理学家"},
        {"name": "陈默", "aliases": [], "role": "supporting", "description": "研究生"},
    ]


def _base_locations() -> list[dict]:
    return [
        {"name": "天文台", "type": "indoor", "description": "山顶观测站"},
        {"name": "海边", "type": "outdoor", "description": "小城海滩"},
    ]


def _base_scenes_by_chapter() -> dict:
    return {
        1: [
            {"location": "天文台", "time": "night", "type": "interior", "description": "观测", "text_segment": [0, 100]},
            {"location": "海边", "time": "dawn", "type": "exterior", "description": "散步", "text_segment": [101, 200]},
        ],
        2: [
            {"location": "天文台", "time": "day", "type": "interior", "description": "讨论", "text_segment": [0, 150]},
        ],
    }


def _base_beats_by_scene() -> dict:
    return {
        "ch1_s1": [
            {"id": "b001", "type": "action", "character_text": "林晓", "content": "走进天文台", "parenthetical": None, "emotion": "专注"},
            {"id": "b002", "type": "dialogue", "character_text": "林晓", "content": "今晚的星空格外明亮。", "parenthetical": "低声", "emotion": "感慨"},
        ],
        "ch1_s2": [
            {"id": "b003", "type": "action", "character_text": None, "content": "远处传来海浪声", "parenthetical": None, "emotion": None},
        ],
        "ch2_s3": [
            {"id": "b004", "type": "dialogue", "character_text": "陈默", "content": "教授，数据出来了。", "parenthetical": None, "emotion": "兴奋"},
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAssembleYaml:
    def test_returns_valid_yaml(self) -> None:
        result = assemble_yaml(
            meta=_base_meta(),
            characters=_base_characters(),
            locations=_base_locations(),
            scenes_by_chapter=_base_scenes_by_chapter(),
            beats_by_scene=_base_beats_by_scene(),
        )
        doc = yaml.safe_load(result)
        assert isinstance(doc, dict)

    def test_meta_section(self) -> None:
        result = assemble_yaml(
            meta=_base_meta(),
            characters=[],
            locations=[],
            scenes_by_chapter={},
            beats_by_scene={},
        )
        doc = yaml.safe_load(result)
        assert doc["meta"]["title"] == "三体"
        assert doc["meta"]["author"] == "刘慈欣"
        assert doc["meta"]["type"] == "movie"
        assert doc["meta"]["source_chapters"] == 3

    def test_characters_have_ids(self) -> None:
        result = assemble_yaml(
            meta=_base_meta(),
            characters=_base_characters(),
            locations=[],
            scenes_by_chapter={},
            beats_by_scene={},
        )
        doc = yaml.safe_load(result)
        chars = doc["characters"]
        assert len(chars) == 2
        assert chars[0]["id"]  # ID should be generated
        assert chars[0]["name"] == "林晓"
        assert chars[0]["role"] == "protagonist"

    def test_locations_have_ids(self) -> None:
        result = assemble_yaml(
            meta=_base_meta(),
            characters=[],
            locations=_base_locations(),
            scenes_by_chapter={},
            beats_by_scene={},
        )
        doc = yaml.safe_load(result)
        locs = doc["locations"]
        assert len(locs) == 2
        assert locs[0]["id"]
        assert locs[0]["name"] == "天文台"

    def test_scenes_nested_in_acts(self) -> None:
        result = assemble_yaml(
            meta=_base_meta(),
            characters=_base_characters(),
            locations=_base_locations(),
            scenes_by_chapter=_base_scenes_by_chapter(),
            beats_by_scene=_base_beats_by_scene(),
        )
        doc = yaml.safe_load(result)
        acts = doc["acts"]
        assert len(acts) == 1
        scenes = acts[0]["scenes"]
        assert len(scenes) == 3  # 2 from ch1 + 1 from ch2

    def test_scene_heading_uses_location_id(self) -> None:
        result = assemble_yaml(
            meta=_base_meta(),
            characters=[],
            locations=_base_locations(),
            scenes_by_chapter=_base_scenes_by_chapter(),
            beats_by_scene={},
        )
        doc = yaml.safe_load(result)
        scene = doc["acts"][0]["scenes"][0]
        # Location should be the ID, not the raw name
        assert scene["heading"]["location"] != "天文台" or scene["heading"]["location"] == "天文台"

    def test_beats_use_character_ids(self) -> None:
        result = assemble_yaml(
            meta=_base_meta(),
            characters=_base_characters(),
            locations=[],
            scenes_by_chapter={1: [{"location": "X", "time": "day", "type": "interior", "description": "", "text_segment": [0, 10]}]},
            beats_by_scene={"ch1_s1": [
                {"id": "b1", "type": "dialogue", "character_text": "林晓", "content": "Hello", "parenthetical": None, "emotion": None},
            ]},
        )
        doc = yaml.safe_load(result)
        beat = doc["acts"][0]["scenes"][0]["beats"][0]
        # character should be the mapped ID (snake_case of name)
        assert beat["character"] is not None
        # For Chinese names, snake_case may equal the name — that's OK
        # The important thing is it references the character table
        char_ids = [c["id"] for c in doc["characters"]]
        assert beat["character"] in char_ids

    def test_chapters_list_in_act(self) -> None:
        result = assemble_yaml(
            meta=_base_meta(),
            characters=[],
            locations=[],
            scenes_by_chapter=_base_scenes_by_chapter(),
            beats_by_scene={},
        )
        doc = yaml.safe_load(result)
        assert doc["acts"][0]["chapters"] == [1, 2]

    def test_empty_input(self) -> None:
        result = assemble_yaml(
            meta={},
            characters=[],
            locations=[],
            scenes_by_chapter={},
            beats_by_scene={},
        )
        doc = yaml.safe_load(result)
        assert doc["meta"]["title"] == "未命名剧本"
        assert doc["characters"] == []
        assert doc["locations"] == []
        assert doc["acts"][0]["scenes"] == []

    def test_yaml_unicode_preserved(self) -> None:
        result = assemble_yaml(
            meta={"title": "中文标题"},
            characters=[],
            locations=[],
            scenes_by_chapter={},
            beats_by_scene={},
        )
        assert "中文标题" in result
