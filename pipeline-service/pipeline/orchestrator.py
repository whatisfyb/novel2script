"""
Pipeline Orchestrator — coordinates all 6 stages end-to-end.

Stage flow:
  1. File Parser    → RawText
  2. Chapter Splitter → [Chapter]
  3. Structure Analyzer → StructureResult (characters, locations, synopsis)
  4. Scene Segmenter (per chapter, parallel) → {chapter_order: [Scene]}
  5. Beat Extractor (per scene, parallel) → {scene_key: [Beat]}
  6. YAML Assembler → YAML string

Chapters 4+5 run in parallel via asyncio.gather for throughput.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from pipeline.parser import parse_file
from pipeline.splitter import split_chapters
from pipeline.analyzer import analyze_structure
from pipeline.segmenter import segment_scenes
from pipeline.extractor import extract_beats
from pipeline.assembler import assemble_yaml

logger = logging.getLogger(__name__)


async def run_pipeline(
    file_path: str | Path,
    *,
    title: str = "",
    author: str = "",
    script_type: str = "movie",
    language: str = "zh",
    progress_callback: Any = None,
    stream_callback: Any = None,
) -> str:
    """
    Run the full 6-stage pipeline on an uploaded file.

    Args:
        file_path: path to the uploaded novel file (.txt, .md, .docx)
        title: screenplay title (defaults to filename)
        author: original author name
        script_type: movie / tv / short_video / stage
        language: zh / en / bilingual
        progress_callback: optional async callable(stage_name, progress_pct)

    Returns:
        Final YAML string.
    """
    async def _notify(stage: str, pct: int) -> None:
        if progress_callback:
            try:
                await progress_callback(stage, pct)
            except Exception as e:
                logger.warning("Progress callback failed: %s", e)

    # ---- Stage 1: File Parser ----
    await _notify("parser", 0)
    logger.info("Stage 1: Parsing file %s", file_path)
    raw_text = parse_file(file_path)
    await _notify("parser", 100)

    # ---- Stage 2: Chapter Splitter ----
    await _notify("splitter", 0)
    logger.info("Stage 2: Splitting chapters (hints=%d)", len(raw_text.chapter_hints))
    chapters = split_chapters(raw_text.content, hints=raw_text.chapter_hints)
    logger.info("  → %d chapters found", len(chapters))
    await _notify("splitter", 100)

    # ---- Stage 3: Structure Analyzer (LLM) ----
    await _notify("analyzer", 0)
    logger.info("Stage 3: Analyzing structure")

    async def _on_analyze_chunk(chunk: str) -> None:
        if stream_callback:
            await stream_callback(chunk)

    structure = await analyze_structure(chapters, on_stream=_on_analyze_chunk)
    logger.info("  → synopsis: %s...", structure.synopsis[:50])
    logger.info("  → %d characters, %d locations", len(structure.characters), len(structure.locations))
    await _notify("analyzer", 100)

    # ---- Stage 4+5: Segment + Extract (parallel per chapter) ----
    await _notify("segmenter", 0)
    logger.info("Stage 4+5: Segmenting scenes and extracting beats")

    scenes_by_chapter: dict[int, list] = {}
    beats_by_scene: dict[str, list] = {}

    total_chapters = len(chapters)
    completed = [0]  # mutable counter for cross-task chapter tracking

    # Run chapters in parallel (max 3 concurrent to avoid LLM rate limits)
    sem = asyncio.Semaphore(3)

    async def _process_chapter(chapter) -> None:
        async with sem:
            # Stage 4: segment
            scenes = await segment_scenes(
                chapter,
                characters=structure.characters,
                locations=structure.locations,
            )
            scenes_by_chapter[chapter.order] = scenes
            logger.info("  Chapter %d: %d scenes", chapter.order, len(scenes))

            # Stage 5: extract beats per scene (also parallel)
            async def _process_scene(scene, idx: int) -> None:
                scene_key = f"ch{chapter.order}_s{idx}"
                start, end = scene.text_segment
                scene_text = chapter.text[start:end] if end > 0 else chapter.text

                async def _on_extract_chunk(chunk: str) -> None:
                    pass  # streaming beats works; callback placeholder

                beats = await extract_beats(
                    scene_text,
                    characters=structure.characters,
                    on_stream=_on_extract_chunk,
                )
                beats_by_scene[scene_key] = beats
                logger.info("    Scene %s: %d beats", scene_key, len(beats))

            await asyncio.gather(
                *[_process_scene(s, i + 1) for i, s in enumerate(scenes)]
            )

            # Report progress after each chapter completes
            completed[0] += 1
            progress_pct = completed[0] * 100 // total_chapters
            await _notify("segmenter", progress_pct)

    results = await asyncio.gather(
        *[_process_chapter(ch) for ch in chapters],
        return_exceptions=True,
    )
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error("Chapter %d failed: %s", chapters[i].order, r)
    total_scenes = sum(len(v) for v in scenes_by_chapter.values())
    total_beats = sum(len(v) for v in beats_by_scene.values())
    logger.info("  → %d scenes, %d beats total", total_scenes, total_beats)
    await _notify("segmenter", 100)

    # ---- Stage 6: YAML Assembler ----
    await _notify("assembler", 0)
    logger.info("Stage 6: Assembling YAML")

    # Convert dataclass objects to dicts for the assembler
    scenes_as_dicts = {
        ch_order: [
            {
                "location": s.location,
                "time": s.time,
                "type": s.type,
                "description": s.description,
                "text_segment": list(s.text_segment),
            }
            for s in scene_list
        ]
        for ch_order, scene_list in scenes_by_chapter.items()
    }

    beats_as_dicts = {
        key: [
            {
                "id": b.id,
                "type": b.type,
                "character_id": b.character_id,
                "character_text": b.character_text,
                "content": b.content,
                "parenthetical": b.parenthetical,
                "emotion": b.emotion,
            }
            for b in beat_list
        ]
        for key, beat_list in beats_by_scene.items()
    }

    yaml_str = assemble_yaml(
        meta={
            "title": title or raw_text.filename,
            "original_title": title or raw_text.filename,
            "author": author,
            "type": script_type,
            "language": language,
            "source_chapters": len(chapters),
            "synopsis": structure.synopsis,
        },
        characters=[
            {"name": c.name, "aliases": c.aliases, "role": c.role, "description": c.description}
            for c in structure.characters
        ],
        locations=[
            {"name": l.name, "type": l.type, "description": l.description}
            for l in structure.locations
        ],
        scenes_by_chapter=scenes_as_dicts,
        beats_by_scene=beats_as_dicts,
    )
    await _notify("assembler", 100)

    logger.info("Pipeline complete. YAML length: %d chars", len(yaml_str))
    return yaml_str
