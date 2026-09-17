"""
HistorySnooze Prompt Engine - Structured Tag Operations
Module: tag_ops.py
Rule <= 150 lines compliant.
"""

import re
from typing import Dict, List, Optional, Union

from prompt_engine_modules.cultural_anchors import TAG_REGEX


def format_bracket_tag(tag_type: str, tag_value: str) -> str:
    """Formats a single bracketed tag: [TYPE: value]."""
    clean_type = tag_type.strip().upper()
    clean_val = tag_value.strip()
    return f"[{clean_type}: {clean_val}]"


def build_tag_header(
    character_ref: Optional[Union[str, List[str]]] = None,
    setting_ref: Optional[Union[str, List[str]]] = None,
    prop_ref: Optional[Union[str, List[str]]] = None,
    ingredient_ref: Optional[Union[str, List[str]]] = None,
    tags: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> str:
    """
    Builds a space-separated tag header adhering to canonical ordering:
    [CHARACTER: ...] [SETTING: ...] [PROP: ...] [INGREDIENT: ...]
    """
    tag_entries: List[str] = []
    pairs = [
        ("CHARACTER", character_ref),
        ("SETTING", setting_ref),
        ("PROP", prop_ref),
        ("INGREDIENT", ingredient_ref),
    ]
    for t_type, t_val in pairs:
        if t_val:
            if isinstance(t_val, str):
                tag_entries.append(format_bracket_tag(t_type, t_val))
            elif isinstance(t_val, (list, tuple)):
                for item in t_val:
                    if item and isinstance(item, str):
                        tag_entries.append(format_bracket_tag(t_type, item))

    if tags:
        canonical_order = ["CHARACTER", "SETTING", "PROP", "INGREDIENT"]
        normalized_tags: Dict[str, List[str]] = {}
        for k, v in tags.items():
            norm_k = k.strip().upper()
            vals = [v] if isinstance(v, str) else list(v)
            normalized_tags.setdefault(norm_k, []).extend([x for x in vals if x])

        for c_type in canonical_order:
            if c_type in normalized_tags and not any(
                p[0] == c_type and p[1] for p in pairs
            ):
                for val in normalized_tags[c_type]:
                    tag_entries.append(format_bracket_tag(c_type, val))

        for k, v_list in normalized_tags.items():
            if k not in canonical_order:
                for val in v_list:
                    tag_entries.append(format_bracket_tag(k, val))

    return " ".join(tag_entries)


def extract_prompt_tags(prompt: str) -> Dict[str, List[str]]:
    """Extracts structured reference tags from a prompt string."""
    result: Dict[str, List[str]] = {
        "CHARACTER": [],
        "SETTING": [],
        "PROP": [],
        "INGREDIENT": [],
    }
    for match in TAG_REGEX.finditer(prompt):
        tag_type = match.group(1).upper()
        tag_val = match.group(2).strip()
        result.setdefault(tag_type, []).append(tag_val)
    return result


def strip_prompt_tags(prompt: str) -> str:
    """Removes all [TYPE: value] tags and collapses whitespace."""
    cleaned = TAG_REGEX.sub("", prompt)
    return re.sub(r"\s+", " ", cleaned).strip()
