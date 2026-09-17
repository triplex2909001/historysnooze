"""
HistorySnooze: Master Atomic Pre-Production Pipeline Engine
Module: preproduction_pipeline.py
SSOT-compliant with 00_TONG_QUAN.md, 04_VISUAL_PROMPT_ENGINE.md, and Gatekeepers GK1-GK3.
Enforces simultaneous generation of 7 core assets inside 01. Preproduction and combined folder.
Rule <= 150 lines strictly enforced.
"""

import json
import os
import shutil
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import docx

_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from project_scaffolder import scaffold_project_directories
from prompt_engine import build_consistent_prompt, format_combined_prompts_file, validate_prompt


def generate_preproduction_bundle(
    idea_id: str,
    character_name: str,
    youtube_title: str,
    parts_data: List[List[Dict[str, str]]],
    outline_data: List[Dict[str, Any]],
    gdrive_folder_id: Optional[str] = None,
    output_base: Path = Path("/media/vpsg16gb/Media/historysnooze/output")
) -> Dict[str, Any]:
    """
    Executes atomic Pre-Production generation.
    Produces strictly 7 files inside 01. Preproduction, mirrors combined files to 02. Media Generation/combined, and syncs to Google Drive.
    """
    folder_name = f"{character_name} - {youtube_title}"
    project_root = output_base / folder_name

    # STEP 1: Scaffold all folders (01, 02 with audio/keyframes/combined, 03)
    dirs = scaffold_project_directories(project_root, gdrive_folder_id=gdrive_folder_id)
    preprod_dir = dirs["preproduction"]
    comb_dir = dirs["combined"]

    print(f"\n🚀 PRODUCING ATOMIC PRE-PRODUCTION BUNDLE FOR: {character_name}")
    print(f"📁 Target: {preprod_dir}")

    # Process Script & Prompts
    full_script_md = [f"# {youtube_title}\n## Full Canonical Script (15 Parts, 150 Beats)\n\n"]
    combined_voiceover_lines = []
    combined_prompts_dict = {}
    total_words = 0

    for p_idx, p_beats in enumerate(parts_data, 1):
        full_script_md.append(f"### Part {p_idx:02d}\n\n")
        for b_idx, beat in enumerate(p_beats, 1):
            narrative = beat["narrative"].strip()
            scene = beat["scene"].strip()
            total_words += len(narrative.split())

            full_script_md.append(f"{narrative}\n\n")
            combined_voiceover_lines.append(f"part_{p_idx:02d}_chunk_{b_idx:03d}: {narrative}")

            prompt_str = build_consistent_prompt(scene, character_name)
            is_valid, err = validate_prompt(prompt_str)
            if not is_valid:
                raise ValueError(f"GK3 Prompt Validation Failed at P{p_idx:02d}_B{b_idx:02d}: {err}")

            combined_prompts_dict[f"beat_P{p_idx:02d}_B{b_idx:02d}.jpg"] = prompt_str

    # 1. outline.json
    with open(preprod_dir / "outline.json", "w", encoding="utf-8") as f:
        json.dump(outline_data, f, indent=2, ensure_ascii=False)

    # 2. metadata.json
    metadata = {
        "idea_id": idea_id,
        "character": character_name,
        "youtube_title": youtube_title,
        "total_parts": 15,
        "total_beats": len(combined_prompts_dict),
        "total_words": total_words,
        "gdrive_folder_id": gdrive_folder_id,
        "generated_at": datetime.now().isoformat()
    }
    with open(preprod_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # 3. script_full.md
    with open(preprod_dir / "script_full.md", "w", encoding="utf-8") as f:
        f.write("".join(full_script_md))

    # 4. combined_voiceover.txt (in 01. Preproduction and 02. Media Generation/combined)
    voiceover_text = "\n\n".join(combined_voiceover_lines) + "\n"
    with open(preprod_dir / "combined_voiceover.txt", "w", encoding="utf-8") as f:
        f.write(voiceover_text)
    with open(comb_dir / "combined_voiceover.txt", "w", encoding="utf-8") as f:
        f.write(voiceover_text)

    # 5. combined_imageprompts.txt (in 01. Preproduction and 02. Media Generation/combined)
    prompts_content = format_combined_prompts_file(combined_prompts_dict)
    with open(preprod_dir / "combined_imageprompts.txt", "w", encoding="utf-8") as f:
        f.write(prompts_content)
    with open(comb_dir / "combined_imageprompts.txt", "w", encoding="utf-8") as f:
        f.write(prompts_content)

    # 6. Outline DOCX & 7. Script DOCX
    outline_doc = docx.Document()
    outline_doc.add_heading(f"Outline: {youtube_title}", level=0)
    for act in outline_data:
        outline_doc.add_heading(act.get("title", f"Act {act.get('act', '')}"), level=1)
        for part in act.get("parts", []):
            p_p = outline_doc.add_paragraph()
            p_p.add_run(f"Part {part.get('part', '')}: {part.get('title', '')}\n").bold = True
            p_p.add_run(f"Summary: {part.get('summary', '')}\n")
    outline_doc.save(preprod_dir / f"Outline - {character_name}.docx")

    script_doc = docx.Document()
    script_doc.add_heading(youtube_title, level=0)
    for p_idx, p_beats in enumerate(parts_data, 1):
        script_doc.add_heading(f"Part {p_idx:02d}", level=1)
        for beat in p_beats:
            script_doc.add_paragraph(beat["narrative"].strip())
    script_doc.save(preprod_dir / f"Script - {character_name}.docx")

    print(f"✅ Generated 7 Pre-Production files + combined mirror ({total_words} words, 150 beats).")

    # Sync to Google Drive
    if gdrive_folder_id:
        for s_name, loc_dir in [("01. Preproduction", preprod_dir), ("02. Media Generation/combined", comb_dir)]:
            cmd = ["rclone", "sync", str(loc_dir), f"hariinvpsg16gb,root_folder_id={gdrive_folder_id}:{s_name}", "--delete-excluded", "--transfers=8"]
            subprocess.run(cmd, check=True)
        print("✅ Synced 01. Preproduction and 02. Media Generation/combined to Google Drive!")

    return {"project_root": project_root, "preprod_dir": preprod_dir, "metadata": metadata}
