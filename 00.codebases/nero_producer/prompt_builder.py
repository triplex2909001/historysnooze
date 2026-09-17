"""
HistorySnooze: Master 3-Tier Visual Prompt Builder for Emperor Nero
Module: prompt_builder.py
SSOT-compliant with 04_VISUAL_PROMPT_ENGINE.md & Gatekeeper GK3.
Rule <= 150 lines strictly enforced.
"""

import re
from typing import List, Dict

from nero_parts_p01_p03 import P01_BEATS, P02_BEATS, P03_BEATS
from nero_parts_p04_p06 import P04_BEATS, P05_BEATS, P06_BEATS
from nero_parts_p07_p09 import P07_BEATS, P08_BEATS, P09_BEATS
from nero_parts_p10_p12 import P10_BEATS, P11_BEATS, P12_BEATS
from nero_parts_p13_p15 import P13_BEATS, P14_BEATS, P15_BEATS

ALL_PARTS = [
    P01_BEATS, P02_BEATS, P03_BEATS,
    P04_BEATS, P05_BEATS, P06_BEATS,
    P07_BEATS, P08_BEATS, P09_BEATS,
    P10_BEATS, P11_BEATS, P12_BEATS,
    P13_BEATS, P14_BEATS, P15_BEATS
]

PERIOD_ANCHOR = (
    "first-century Imperial Rome (Julio-Claudian Dynasty), authentic classical Roman architecture, "
    "monumental marble colonnades, Corinthian columns, Roman fora, Domus Aurea frescoed ceilings and octagonal halls, "
    "barrel-vaulted stone basilicas, terracotta-tiled porticos, authentic Roman togas, tunics, and gold laurel wreaths, "
    "flat medieval perspective, fine brown-ink outlines, strictly authentic classical Roman antiquity setting, "
    "no European medieval castle battlements, no Gothic turrets, no Western knights"
)

SIGNATURE_FRAME = (
    "late-15th-century illuminated manuscript style painting, tempera and shell-gold, "
    "flat medieval perspective, fine brown-ink outlines, full-bleed edge-to-edge painting extending "
    "to all four edges of the 16:9 canvas, zero margins, no outer paper, no parchment border, "
    "no decorative frame, no page border, wide cinematic 16:9 composition, ultra-high-resolution (4K)"
)


def clean_scene_description(raw_scene: str) -> str:
    """Cleans up raw narrative scene description into Tier 1 format."""
    s = raw_scene.strip()
    s = re.sub(r",?\s*4K documentary keyframe\.?", "", s, flags=re.IGNORECASE)
    s = re.sub(r",?\s*dramatic cinematic framing\.?", "", s, flags=re.IGNORECASE)
    return s.rstrip("., ")


def build_3tier_nero_prompt(part_num: int, beat_num: int) -> str:
    """Builds single-line Master 3-Tier prompt for beat_PXX_BYY.jpg."""
    part_beats = ALL_PARTS[part_num - 1]
    beat = part_beats[beat_num - 1]
    scene = clean_scene_description(beat["scene"])
    return f"beat_P{part_num:02d}_B{beat_num:02d}.jpg: {scene}, {PERIOD_ANCHOR}, {SIGNATURE_FRAME}"


def generate_nero_combined_imageprompts() -> str:
    """
    Generates 150 single-line prompts separated by double newlines (\\n\\n).
    No line breaks within individual prompts.
    """
    prompts = []
    for p in range(1, 16):
        for b in range(1, 11):
            prompts.append(build_3tier_nero_prompt(p, b))
    return "\n\n".join(prompts) + "\n"
