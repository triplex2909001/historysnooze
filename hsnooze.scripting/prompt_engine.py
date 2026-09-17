"""
HistorySnooze Director - Prompt Engine Facade Module
Module: prompt_engine.py
Version: 2.0.0 (Refactored to modular architecture)
Compliant with 04_VISUAL_PROMPT_ENGINE.md, PROJECT.md, and Gatekeeper GK3.
Rule <= 150 lines strictly enforced.
"""

import sys
from pathlib import Path

# Ensure package directory is on sys.path for direct imports
_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from prompt_engine_modules import (
    CULTURAL_ANCHORS,
    FORBIDDEN_TERMS,
    MASTER_REFERENCE_ANCHORS,
    SIGNATURE_FRAME_TAIL,
    TAG_REGEX,
    VALID_TAG_TYPES,
    build_consistent_prompt,
    build_tag_header,
    extract_prompt_tags,
    format_bracket_tag,
    format_combined_prompts_file,
    format_reference_prompts_file,
    generate_reference_prompts,
    get_reference_anchor_kit,
    resolve_character_anchor,
    resolve_reference_anchor,
    strip_prompt_tags,
    validate_prompt,
)

__all__ = [
    "MASTER_REFERENCE_ANCHORS",
    "CULTURAL_ANCHORS",
    "SIGNATURE_FRAME_TAIL",
    "FORBIDDEN_TERMS",
    "VALID_TAG_TYPES",
    "TAG_REGEX",
    "resolve_character_anchor",
    "get_reference_anchor_kit",
    "resolve_reference_anchor",
    "format_bracket_tag",
    "build_tag_header",
    "extract_prompt_tags",
    "strip_prompt_tags",
    "build_consistent_prompt",
    "generate_reference_prompts",
    "format_reference_prompts_file",
    "validate_prompt",
    "format_combined_prompts_file",
]
