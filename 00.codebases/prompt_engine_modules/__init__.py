"""
HistorySnooze Prompt Engine Package
Exposes canonical visual prompt engine API and anchor registries.
Rule <= 150 lines compliant.
"""

from prompt_engine_modules.anchor_registry import (
    MASTER_REFERENCE_ANCHORS,
    get_reference_anchor_kit,
    resolve_reference_anchor,
)
from prompt_engine_modules.cultural_anchors import (
    CULTURAL_ANCHORS,
    FORBIDDEN_TERMS,
    SIGNATURE_FRAME_TAIL,
    TAG_REGEX,
    VALID_TAG_TYPES,
    resolve_character_anchor,
)
from prompt_engine_modules.prompt_builder import (
    build_consistent_prompt,
    format_combined_prompts_file,
    format_reference_prompts_file,
    generate_reference_prompts,
)
from prompt_engine_modules.prompt_validator import validate_prompt
from prompt_engine_modules.tag_ops import (
    build_tag_header,
    extract_prompt_tags,
    format_bracket_tag,
    strip_prompt_tags,
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
