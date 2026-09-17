"""
HISTORYSNOOZE: MASTER 3-TIER VISUAL PROMPT BUILDER
Module: prompt_builder.py
SSOT-compliant with 04_VISUAL_PROMPT_ENGINE.md & [QUY CHUẨN v1.5.0].
Rule <= 150 lines strictly enforced.
"""

from typing import Dict
from prompt_data_p01_p05 import TIER1_P01_P05
from prompt_data_p06_p10 import TIER1_P06_P10
from prompt_data_p11_p15 import TIER1_P11_P15

PERIOD_ANCHOR = (
    "late second-century and early third-century Imperial Rome and Roman Syria (Severan Dynasty), "
    "authentic classical Roman architecture, monumental marble colonnades, Corinthian columns, "
    "Roman fora, Syrian sun-temple courtyards, barrel-vaulted stone basilicas, terracotta-tiled porticos, "
    "authentic Roman stola, palla, and Syrian royal robes, flat medieval perspective, fine brown-ink outlines, "
    "strictly authentic classical Roman antiquity setting, no European medieval castle battlements, "
    "no Gothic turrets, no Western knights"
)

SIGNATURE_FRAME = (
    "late-15th-century illuminated manuscript style painting, tempera and shell-gold, "
    "flat medieval perspective, fine brown-ink outlines, full-bleed edge-to-edge painting extending "
    "to all four edges of the 16:9 canvas, zero margins, no outer paper, no parchment border, "
    "no decorative frame, no page border, wide cinematic 16:9 composition, ultra-high-resolution (4K)"
)


def get_all_tier1_beats() -> Dict[str, str]:
    """Merge all Tier 1 scene beats from all 15 parts."""
    beats = {}
    beats.update(TIER1_P01_P05)
    beats.update(TIER1_P06_P10)
    beats.update(TIER1_P11_P15)
    return beats


def build_3tier_prompt(part_num: int, beat_num: int) -> str:
    """Build single-line Master 3-Tier prompt for beat_PXX_BYY.jpg."""
    key = f"P{part_num:02d}_B{beat_num:02d}"
    all_tier1 = get_all_tier1_beats()
    tier1_scene = all_tier1.get(key, f"Julia Domna scene in Roman antiquity Part {part_num:02d} Beat {beat_num:02d}")
    return f"beat_{key}.jpg: {tier1_scene}, {PERIOD_ANCHOR}, {SIGNATURE_FRAME}"


def generate_combined_imageprompts_text() -> str:
    """
    Generate 150 prompts separated by exactly one blank line (\\n\\n).
    No line breaks within individual prompts.
    """
    prompts = []
    for p in range(1, 16):
        for b in range(1, 11):
            prompt_line = build_3tier_prompt(p, b)
            prompts.append(prompt_line)
    return "\n\n".join(prompts) + "\n"
