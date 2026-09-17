"""
HISTORYSNOOZE: ONLINE SCRIPT & PROMPT PRODUCER (Facade)
Module: online_script_producer.py
Version: 2.1.0 (Refactored to modular architecture)
Compliant with 04_VISUAL_PROMPT_ENGINE.md, PROJECT.md, and Gatekeeper GK3.
Rule <= 150 lines strictly enforced.
"""

import argparse
import sys
from pathlib import Path

# Ensure package directory is on sys.path for direct imports
_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from script_producer_modules import (
    CONTEXTUAL_PROP_MAP,
    MATSUO_BASHO_150_BEATS,
    PART_SETTINGS,
    StoryBeat,
    StorySegmenter,
    export_script_and_prompts,
    get_matsuo_basho_150_beats,
    process_pending_row,
)

__all__ = [
    "StoryBeat",
    "PART_SETTINGS",
    "CONTEXTUAL_PROP_MAP",
    "StorySegmenter",
    "get_matsuo_basho_150_beats",
    "MATSUO_BASHO_150_BEATS",
    "export_script_and_prompts",
    "process_pending_row",
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Online Script Producer v2.1.0"
    )
    parser.add_argument("--idea-id", type=str, required=True)
    parser.add_argument("--character", type=str, required=True)
    parser.add_argument("--title", type=str, required=True)
    parser.add_argument("--image-mode", type=str, default="Automatic")
    args = parser.parse_args()

    process_pending_row(
        args.idea_id, args.character, args.title, args.image_mode
    )
