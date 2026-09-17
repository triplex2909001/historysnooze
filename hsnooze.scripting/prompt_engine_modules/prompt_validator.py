"""
HistorySnooze Prompt Engine - Prompt Validation
Module: prompt_validator.py
Rule <= 150 lines compliant.
"""

import re
from typing import Any, Dict, List

from prompt_engine_modules.cultural_anchors import FORBIDDEN_TERMS
from prompt_engine_modules.tag_ops import extract_prompt_tags, strip_prompt_tags


def validate_prompt(prompt: str, max_length: int = 1500) -> Dict[str, Any]:
    """
    Validates a HistorySnooze prompt against syntax, format, style, and length constraints.
    Returns rich dictionary with boolean status, detected issues, tags, and stripped prompt.
    """
    issues: List[str] = []

    # 1. Single-line requirement
    if "\n" in prompt or "\r" in prompt:
        issues.append(
            "Prompt contains newline characters (must be strictly single-line)."
        )

    # 2. Bracket balance & syntax validation
    if prompt.count("[") != prompt.count("]"):
        issues.append("Prompt contains unbalanced square brackets.")

    bracket_blocks = re.findall(r"\[([^\]]*)\]", prompt)
    valid_types = {"CHARACTER", "SETTING", "PROP", "INGREDIENT"}
    for block in bracket_blocks:
        if ":" not in block:
            issues.append(
                f"Invalid bracketed tag format: '[{block}]' (missing colon separator)."
            )
            continue
        tag_type, tag_val = block.split(":", 1)
        tag_type_clean = tag_type.strip().upper()
        tag_val_clean = tag_val.strip()
        if tag_type_clean not in valid_types:
            issues.append(
                f"Unknown reference tag type: '[{tag_type_clean}]'. Permitted: {sorted(valid_types)}."
            )
        if not tag_val_clean:
            issues.append(
                f"Reference tag '[{tag_type_clean}:]' has an empty identifier."
            )
        elif not re.match(r"^[a-zA-Z0-9_.-]+$", tag_val_clean):
            issues.append(
                f"Reference tag value '{tag_val_clean}' contains invalid characters (must be alphanumeric, underscore, period, or hyphen)."
            )

    # 3. Format & Mandatory phrase checks
    p_lower = prompt.lower()
    if ".gif" in p_lower:
        issues.append("Prompt references forbidden .gif format (must be 100% .jpg).")
    if "full-bleed edge-to-edge painting" not in p_lower:
        issues.append("Missing mandatory anti-border full-bleed phrase.")
    if "illuminated manuscript" not in p_lower:
        issues.append("Missing signature illuminated manuscript style anchor.")

    # 4. Forbidden term enforcement
    for term in FORBIDDEN_TERMS:
        if term not in ["border", "frame", "margin", ".gif"]:
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, p_lower):
                issues.append(f"Contains forbidden negative term: '{term}'.")

    # 5. Length check (excluding beat filename prefix if present)
    clean_line = re.sub(r"^beat_P\d+_B\d+\.jpg:\s*", "", prompt)
    if len(clean_line) > max_length:
        issues.append(
            f"Prompt exceeds maximum character length of {max_length} ({len(clean_line)} characters)."
        )

    # Extracted metadata
    tags = extract_prompt_tags(prompt)
    stripped = strip_prompt_tags(clean_line)

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "prompt": prompt,
        "tags": tags,
        "stripped_prompt": stripped,
        "length": len(clean_line),
    }
