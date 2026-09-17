"""
HistorySnooze Prompt Engine - Prompt Generation & File Formatting
Module: prompt_builder.py
Rule <= 150 lines compliant.
"""

import re
from typing import Dict, List, Optional, Union

from prompt_engine_modules.anchor_registry import get_reference_anchor_kit
from prompt_engine_modules.cultural_anchors import (
    SIGNATURE_FRAME_TAIL,
    resolve_character_anchor,
)
from prompt_engine_modules.tag_ops import build_tag_header


def build_consistent_prompt(
    scene_description: str,
    character_name: str = "default",
    *,
    character_ref: Optional[Union[str, List[str]]] = None,
    setting_ref: Optional[Union[str, List[str]]] = None,
    prop_ref: Optional[Union[str, List[str]]] = None,
    ingredient_ref: Optional[Union[str, List[str]]] = None,
    tags: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> str:
    """
    Builds a single-line culturally consistent prompt.
    If reference tags are provided, prepends [CHARACTER: ...] [SETTING: ...] etc.
    """
    tag_header = build_tag_header(
        character_ref=character_ref,
        setting_ref=setting_ref,
        prop_ref=prop_ref,
        ingredient_ref=ingredient_ref,
        tags=tags,
    )

    anchor = resolve_character_anchor(character_name)
    parts = [
        scene_description.rstrip(",. "),
        anchor["period_anchor"],
        anchor["style_fusion"],
        anchor["negative_constraints"],
        SIGNATURE_FRAME_TAIL,
    ]
    raw_prompt = ", ".join(p.strip() for p in parts if p.strip())
    single_line_prompt = re.sub(r"\s+", " ", raw_prompt).strip()

    if tag_header:
        return f"{tag_header} {single_line_prompt}"
    return single_line_prompt


def format_combined_prompts_file(prompts_dict: Dict[str, str]) -> str:
    """Formats prompts into standard file syntax separated by double newlines."""
    lines = []
    for beat_name, prompt_text in prompts_dict.items():
        if not beat_name.endswith(".jpg"):
            if "." in beat_name:
                beat_name = re.sub(r"\.[a-zA-Z0-9]+$", ".jpg", beat_name)
            else:
                beat_name = f"{beat_name}.jpg"
        lines.append(f"{beat_name}: {prompt_text}")
    return "\n\n".join(lines) + "\n"


def generate_reference_prompts(
    character_name: str = "matsuo_basho",
) -> Dict[str, str]:
    """Generates the full dictionary of reference image prompts for a subject."""
    kit = get_reference_anchor_kit(character_name)
    prompts: Dict[str, str] = {}
    for cat_name in ["characters", "settings", "props", "ingredients"]:
        items = kit.get(cat_name, {})
        for _item_id, item_data in items.items():
            fname = item_data["file_name"]
            prompts[fname] = build_consistent_prompt(
                item_data["description"], character_name
            )
    return prompts


def format_reference_prompts_file(character_name: str = "matsuo_basho") -> str:
    """Formats reference prompts into standard reference_imageprompts.txt syntax."""
    prompts = generate_reference_prompts(character_name)
    return format_combined_prompts_file(prompts)
