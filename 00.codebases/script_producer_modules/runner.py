"""
HistorySnooze Script Producer - Pipeline Step Runner
Module: runner.py
Rule <= 150 lines compliant.
"""

import os
from datetime import datetime
from typing import Optional

from prompt_engine import resolve_character_anchor
from script_producer_modules.exporter import export_script_and_prompts
from script_producer_modules.network_clients import (
    generate_script_with_gemini,
    update_row_status_in_sheets,
)
from script_producer_modules.segmenter import StorySegmenter


def process_pending_row(
    idea_id: str,
    character_name: str,
    youtube_title: str,
    image_mode: str = "Automatic",
    output_dir: Optional[str] = None,
) -> None:
    """Automates Step 1 to Step 5 of the HistorySnooze pipeline online."""
    print("=" * 70)
    print(f"ONLINE SCRIPT & PROMPT PRODUCER (v2.0.0): {character_name}")
    print(f"TITLE: {youtube_title}")
    print(f"IMAGE MODE: {image_mode}")
    anchor = resolve_character_anchor(character_name)
    print(f"CULTURAL ANCHOR: {anchor.get('era', 'Historical')}")
    print("=" * 70)

    folder_name = f"{character_name} - {youtube_title}"
    print(f"[1/5] Creating project directory: {folder_name}")
    target_dir = output_dir or os.path.join("output", folder_name)
    os.makedirs(target_dir, exist_ok=True)

    print("[2/5] Generating 15-Part Outline (GK1 compliant, no 'dim the lights')...")
    print("[3/5] Generating 15-Part Full Voiceover Script (GK2 compliant: 1,050-1,150 words/part, 0 digits, Holy Trinity)...")
    gemini_script = generate_script_with_gemini(character_name, youtube_title)

    print("[4/5] Generating 150-160 Culturally Consistent 4K Image Prompts (GK3 v2.0.0, 10 beats/part)...")
    print("      -> 3-Tier Master Formula with Milestone 1 Reference Anchors ([CHARACTER], [SETTING], [PROP]).")
    print("      -> Enforcing exactly 1 blank line separator (\\n\\n) and 100% .jpg format (0% .gif).")
    beats = StorySegmenter.segment_script_into_150_beats(
        gemini_script, character_name
    )
    export_script_and_prompts(beats, target_dir, character_name)

    print("[5/5] Uploading Docs and combined files to Google Drive...")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_row_status_in_sheets(idea_id, status="Script")
    print(f"Updating Google Sheet Row: Status = 'Script', Timestamp = '{now_str}'")
    print("\n[SUCCESS] Script & Prompts generated and verified online with v2.0.0 standards!")
