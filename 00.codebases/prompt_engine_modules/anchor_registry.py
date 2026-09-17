"""
HistorySnooze Prompt Engine - Master Reference Anchor Registry
Module: anchor_registry.py
Rule <= 150 lines compliant.
"""

import re
from typing import Any, Dict, Optional

from prompt_engine_modules.anchor_characters import BASHO_CHARACTER_ANCHORS
from prompt_engine_modules.anchor_props import BASHO_PROPS_ANCHORS
from prompt_engine_modules.anchor_settings_part1 import BASHO_SETTINGS_PART1
from prompt_engine_modules.anchor_settings_part2 import BASHO_SETTINGS_PART2

# MASTER REFERENCE ANCHOR KIT REGISTRY (v2.0.0 - 25 Canonical Anchors)
MASTER_REFERENCE_ANCHORS: Dict[str, Dict[str, Any]] = {
    "matsuo_basho": {
        "characters": BASHO_CHARACTER_ANCHORS,
        "settings": {**BASHO_SETTINGS_PART1, **BASHO_SETTINGS_PART2},
        "props": BASHO_PROPS_ANCHORS,
        "ingredients": {},
    }
}


def get_reference_anchor_kit(character_name: str = "matsuo_basho") -> Dict[str, Any]:
    """Retrieves the Master Reference Anchor Kit dictionary for a given subject."""
    slug = re.sub(r"[^a-z0-9_]", "_", character_name.lower().strip())
    for key, kit in MASTER_REFERENCE_ANCHORS.items():
        if key in slug or slug in key:
            return kit
    return {}


def resolve_reference_anchor(
    tag_type: str, tag_value: str, character_name: str = "matsuo_basho"
) -> Optional[Dict[str, Any]]:
    """Resolves a reference tag by canonical ID, filename, or alias."""
    kit = get_reference_anchor_kit(character_name)
    if not kit:
        return None

    category_map = {
        "CHARACTER": "characters",
        "SETTING": "settings",
        "PROP": "props",
        "INGREDIENT": "ingredients",
    }
    cat_key = category_map.get(tag_type.upper())
    val_clean = tag_value.strip().lower()

    # If category matched, search within that category first
    if cat_key and cat_key in kit:
        cat_dict = kit[cat_key]
        for anchor_id, data in cat_dict.items():
            if (
                anchor_id.lower() == val_clean
                or anchor_id.lower().replace(".jpg", "") == val_clean
            ):
                return data
            if any(alias.lower() == val_clean for alias in data.get("aliases", [])):
                return data

    # Fallback search across all categories (e.g. INGREDIENT referencing a setting or prop)
    for category_dict in kit.values():
        if isinstance(category_dict, dict):
            for anchor_id, data in category_dict.items():
                if (
                    anchor_id.lower() == val_clean
                    or anchor_id.lower().replace(".jpg", "") == val_clean
                ):
                    return data
                if any(alias.lower() == val_clean for alias in data.get("aliases", [])):
                    return data

    return None
