"""
HistorySnooze Script Producer Package
Exposes story beats, segmenter, exporter, network clients, and runner.
Rule <= 150 lines compliant.
"""

from script_producer_modules.canonical_beats import (
    MATSUO_BASHO_150_BEATS,
    get_matsuo_basho_150_beats,
)
from script_producer_modules.exporter import export_script_and_prompts
from script_producer_modules.models import (
    CONTEXTUAL_PROP_MAP,
    PART_SETTINGS,
    StoryBeat,
)
from script_producer_modules.network_clients import (
    call_gemini_api,
    fetch_pending_rows_from_sheets,
    generate_script_with_gemini,
    update_row_status_in_sheets,
)
from script_producer_modules.runner import process_pending_row
from script_producer_modules.segmenter import StorySegmenter
from script_producer_modules.text_segmenter import segment_part_text

__all__ = [
    "StoryBeat",
    "PART_SETTINGS",
    "CONTEXTUAL_PROP_MAP",
    "get_matsuo_basho_150_beats",
    "MATSUO_BASHO_150_BEATS",
    "StorySegmenter",
    "segment_part_text",
    "export_script_and_prompts",
    "process_pending_row",
    "call_gemini_api",
    "generate_script_with_gemini",
    "fetch_pending_rows_from_sheets",
    "update_row_status_in_sheets",
]
