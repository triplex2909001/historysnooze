"""
HISTORYSNOOZE: MAIN JULIA DOMNA PRODUCER
Module: main_producer.py
SSOT-compliant with 01_STYLE_BIBLE through 06_PIPELINE_AUTOMATION_SPEC.
Rule <= 150 lines strictly enforced.
"""

import json
from pathlib import Path
import sys

_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from outline_data import JULIA_DOMNA_OUTLINE
from script_aggregator import get_full_script_markdown, ALL_PARTS
from prompt_builder import generate_combined_imageprompts_text
from metadata_builder import generate_metadata
from docx_generator import generate_outline_docx, generate_script_docx
from validator import validate_gk1_outline, validate_gk2_script, validate_gk3_prompts
from drive_sync import sync_all_artifacts_to_drive

OUTPUT_DIR = Path("/media/vpsg16gb/Media/historysnooze/output/Julia Domna - The Woman Who Ruled Rome from the Shadows")


def run_pipeline() -> None:
    """Execute end-to-end generation, audit, and cloud sync."""
    print("=== 1. AUDITING GATEKEEPER GATES ===")
    gk1_ok, gk1_errs = validate_gk1_outline()
    if not gk1_ok:
        raise ValueError(f"GK1 Failed: {gk1_errs}")
    print(" [PASS] Gatekeeper GK1: Outline validated.")

    gk2_ok, gk2_errs, word_counts = validate_gk2_script()
    total_words = sum(word_counts.values())
    print(f" Total Script Word Count: {total_words} words across 15 parts:")
    for p, w in word_counts.items():
        print(f"  - Part {p:02d}: {w} words ({len(ALL_PARTS[p])} paragraphs/beats)")

    if not gk2_ok:
        raise ValueError(f"GK2 Failed: {gk2_errs}")
    print(" [PASS] Gatekeeper GK2: Script validated.")

    gk3_ok, gk3_errs, prompt_count = validate_gk3_prompts()
    if not gk3_ok:
        raise ValueError(f"GK3 Failed: {gk3_errs}")
    print(f" [PASS] Gatekeeper GK3: {prompt_count} Visual Prompts validated.")

    print("\n=== 2. WRITING LOCAL ARTIFACTS ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. outline.json
    outline_path = OUTPUT_DIR / "outline.json"
    with open(outline_path, "w", encoding="utf-8") as f:
        json.dump(JULIA_DOMNA_OUTLINE, f, indent=2)
    print(f" - Written: {outline_path.name}")

    # 2. metadata.json
    meta_path = OUTPUT_DIR / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(generate_metadata(), f, indent=2)
    print(f" - Written: {meta_path.name}")

    # 3. script_full.md
    script_md_path = OUTPUT_DIR / "script_full.md"
    with open(script_md_path, "w", encoding="utf-8") as f:
        f.write(get_full_script_markdown() + "\n")
    print(f" - Written: {script_md_path.name}")

    # 4. combined_imageprompts.txt
    prompts_path = OUTPUT_DIR / "combined_imageprompts.txt"
    with open(prompts_path, "w", encoding="utf-8") as f:
        f.write(generate_combined_imageprompts_text())
    print(f" - Written: {prompts_path.name}")

    # 5. Outline - Julia Domna.docx
    outline_docx_path = OUTPUT_DIR / "Outline - Julia Domna.docx"
    generate_outline_docx(outline_docx_path)
    print(f" - Written: {outline_docx_path.name}")

    # 6. Script - Julia Domna.docx
    script_docx_path = OUTPUT_DIR / "Script - Julia Domna.docx"
    generate_script_docx(script_docx_path)
    print(f" - Written: {script_docx_path.name}")

    print("\n=== 3. SYNCING TO GOOGLE DRIVE & GOOGLE SHEETS ===")
    links = sync_all_artifacts_to_drive(OUTPUT_DIR)
    print(" Successfully synced all artifacts to Google Drive:")
    for fname, link in links.items():
        print(f"  - {fname}: {link}")

    print("\n=== PIPELINE COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    run_pipeline()
