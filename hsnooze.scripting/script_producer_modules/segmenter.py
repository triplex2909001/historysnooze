"""
HistorySnooze Script Producer - Story Segmenter
Module: segmenter.py
Rule <= 150 lines compliant.
"""

import re
from typing import Dict, List

from prompt_engine import build_consistent_prompt
from script_producer_modules.canonical_beats import get_matsuo_basho_150_beats
from script_producer_modules.models import PART_SETTINGS, StoryBeat
from script_producer_modules.text_segmenter import segment_part_text


class StorySegmenter:
    """Partitions 15-part voiceover scripts into exactly 10 narrative beats per part (150 total beats)."""

    TARGET_BEATS_PER_PART = 10

    @classmethod
    def segment_part_text(cls, part_index: int, part_text: str) -> List[str]:
        """Segments a single part's text into exactly TARGET_BEATS_PER_PART narrative paragraphs."""
        return segment_part_text(
            part_index, part_text, cls.TARGET_BEATS_PER_PART
        )

    @classmethod
    def segment_script_into_150_beats(
        cls, script_text: str = "", character_name: str = "matsuo_basho"
    ) -> List[StoryBeat]:
        """Segments a full 15-part script into 150 StoryBeat objects (10 beats per part)."""
        if not script_text or not script_text.strip():
            return get_matsuo_basho_150_beats()

        normalized_script = script_text.replace("\r\n", "\n").replace(
            "\r", "\n"
        )
        parts = re.findall(
            r"## Part (\d+):[^\n]*\n+(.*?)(?=\n+## Part |\Z)",
            normalized_script,
            re.DOTALL,
        )
        if len(parts) != 15:
            return get_matsuo_basho_150_beats()

        canonical_beats = get_matsuo_basho_150_beats()
        canonical_map = {
            (b.part_index, b.beat_index): b for b in canonical_beats
        }

        all_beats: List[StoryBeat] = []
        for part_num_str, p_text in parts:
            p_idx = int(part_num_str)
            segmented_paras = cls.segment_part_text(p_idx, p_text.strip())
            for b_idx in range(1, cls.TARGET_BEATS_PER_PART + 1):
                beat_id = f"beat_P{p_idx:02d}_B{b_idx:02d}.jpg"
                para_text = (
                    segmented_paras[b_idx - 1]
                    if b_idx - 1 < len(segmented_paras)
                    else f"Narrative beat {b_idx}"
                )
                canon = canonical_map.get((p_idx, b_idx))
                if canon:
                    all_beats.append(
                        StoryBeat(
                            part_index=p_idx,
                            beat_index=b_idx,
                            beat_id=beat_id,
                            title=canon.title,
                            narrative_text=para_text,
                            scene_description=canon.scene_description,
                            character_ref=canon.character_ref,
                            setting_ref=canon.setting_ref,
                            prop_ref=canon.prop_ref,
                            ingredient_ref=canon.ingredient_ref,
                        )
                    )
                else:
                    c_fallback = (
                        "ref_character_basho_young"
                        if p_idx in (1, 2)
                        else (
                            "ref_character_basho_traveler"
                            if 5 <= p_idx <= 11
                            else "ref_character_basho_elder"
                        )
                    )
                    all_beats.append(
                        StoryBeat(
                            part_index=p_idx,
                            beat_index=b_idx,
                            beat_id=beat_id,
                            title=f"Part {p_idx} Beat {b_idx}",
                            narrative_text=para_text,
                            scene_description=f"Matsuo Basho in contemplative scene during Part {p_idx} Beat {b_idx}, serene natural atmosphere",
                            character_ref=c_fallback,
                            setting_ref=PART_SETTINGS.get(
                                p_idx, "ref_setting_fukagawa_interior"
                            ),
                            prop_ref=(
                                "ref_props_travel_gear"
                                if 5 <= p_idx <= 11
                                else "ref_props_inkstone_brush"
                            ),
                        )
                    )
        return all_beats

    @classmethod
    def generate_part_prompts(
        cls, beats: List[StoryBeat], character_name: str = "matsuo_basho"
    ) -> Dict[str, str]:
        """Generates 3-tier visual prompts for a list of story beats using prompt_engine."""
        prompts: Dict[str, str] = {}
        for b in beats:
            prompts[b.beat_id] = build_consistent_prompt(
                b.scene_description,
                character_name=character_name,
                character_ref=b.character_ref,
                setting_ref=b.setting_ref,
                prop_ref=b.prop_ref,
                ingredient_ref=b.ingredient_ref,
            )
        return prompts
