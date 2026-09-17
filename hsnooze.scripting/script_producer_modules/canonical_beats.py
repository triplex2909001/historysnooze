"""
HistorySnooze Script Producer - Canonical 150 Beats Assembler
Module: canonical_beats.py
Rule <= 150 lines compliant.
"""

from typing import List

from script_producer_modules.canonical_beats_p01_p03 import RAW_BEATS_P01_P03
from script_producer_modules.canonical_beats_p04_p06 import RAW_BEATS_P04_P06
from script_producer_modules.canonical_beats_p07_p09 import RAW_BEATS_P07_P09
from script_producer_modules.canonical_beats_p10_p12 import RAW_BEATS_P10_P12
from script_producer_modules.canonical_beats_p13_p15 import RAW_BEATS_P13_P15
from script_producer_modules.models import StoryBeat


def get_matsuo_basho_150_beats() -> List[StoryBeat]:
    """
    Returns the complete canonical 150-beat breakdown structure for Matsuo Basho
    (15 parts x 10 beats per part) per Milestone 2 specifications.
    """
    all_raw = (
        RAW_BEATS_P01_P03
        + RAW_BEATS_P04_P06
        + RAW_BEATS_P07_P09
        + RAW_BEATS_P10_P12
        + RAW_BEATS_P13_P15
    )

    beats: List[StoryBeat] = []
    for p_idx, b_idx, title, narr, scene, c_ref, s_ref, p_ref in all_raw:
        beat_id = f"beat_P{p_idx:02d}_B{b_idx:02d}.jpg"
        beats.append(
            StoryBeat(
                part_index=p_idx,
                beat_index=b_idx,
                beat_id=beat_id,
                title=title,
                narrative_text=narr,
                scene_description=scene,
                character_ref=c_ref,
                setting_ref=s_ref,
                prop_ref=p_ref,
            )
        )
    return beats


MATSUO_BASHO_150_BEATS = get_matsuo_basho_150_beats()
