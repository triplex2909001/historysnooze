"""
HistorySnooze Script Producer - Script & Prompts Exporter
Module: exporter.py
Rule <= 150 lines compliant.
"""

import os
from typing import Any, Dict, List

from prompt_engine import format_combined_prompts_file
from script_producer_modules.models import StoryBeat
from script_producer_modules.segmenter import StorySegmenter


def export_script_and_prompts(
    all_beats: List[StoryBeat],
    output_dir: str,
    character_name: str = "matsuo_basho",
) -> Dict[str, Any]:
    """
    Exports combined_imageprompts.txt and individual Part_01_prompts.txt..Part_15_prompts.txt
    into output_dir using prompt_engine formatting.
    """
    os.makedirs(output_dir, exist_ok=True)
    all_prompts = StorySegmenter.generate_part_prompts(
        all_beats, character_name
    )

    # 1. Combined file
    combined_content = format_combined_prompts_file(all_prompts)
    combined_path = os.path.join(output_dir, "combined_imageprompts.txt")
    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(combined_content)

    # 2. Individual Part files
    part_paths: Dict[int, str] = {}
    for part_idx in range(1, 16):
        part_beats = [b for b in all_beats if b.part_index == part_idx]
        part_prompts = StorySegmenter.generate_part_prompts(
            part_beats, character_name
        )
        part_content = format_combined_prompts_file(part_prompts)
        part_file = os.path.join(output_dir, f"Part_{part_idx:02d}_prompts.txt")
        with open(part_file, "w", encoding="utf-8") as f:
            f.write(part_content)
        part_paths[part_idx] = part_file

    return {"combined": combined_path, "parts": part_paths}
