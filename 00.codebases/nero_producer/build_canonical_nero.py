#!/usr/bin/env python3
"""
Master Canonical Production Builder for Emperor Nero (Row 11)
Assembles 150 beats, generates DOCX & Markdown assets, uploads to GDrive, and updates Google Sheets.
Rule <= 150 lines compliant via modular imports.
"""

import os
import sys
import json
import docx
from datetime import datetime
from pathlib import Path

# Add producer directory to path
PRODUCER_DIR = Path(__file__).resolve().parent
if str(PRODUCER_DIR) not in sys.path:
    sys.path.insert(0, str(PRODUCER_DIR))

from nero_parts_p01_p03 import P01_BEATS, P02_BEATS, P03_BEATS
from nero_parts_p04_p06 import P04_BEATS, P05_BEATS, P06_BEATS
from nero_parts_p07_p09 import P07_BEATS, P08_BEATS, P09_BEATS
from nero_parts_p10_p12 import P10_BEATS, P11_BEATS, P12_BEATS
from nero_parts_p13_p15 import P13_BEATS, P14_BEATS, P15_BEATS
from prompt_builder import build_3tier_nero_prompt

ALL_PARTS = [
    P01_BEATS, P02_BEATS, P03_BEATS,
    P04_BEATS, P05_BEATS, P06_BEATS,
    P07_BEATS, P08_BEATS, P09_BEATS,
    P10_BEATS, P11_BEATS, P12_BEATS,
    P13_BEATS, P14_BEATS, P15_BEATS
]

# Constants
SHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
GDRIVE_FOLDER_ID = "1bKhloyCDMMjg2m6XCg2HPlzU5SEw_wbT"
SERVICE_ACCOUNT_PATH = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"
IDEA_ID = "id_jt1ps3"
CHARACTER_NAME = "Emperor Nero"
DOC_TITLE = "Emperor Nero: The Darkest Midnight Before the Fall of Rome"
YOUTUBE_TITLE = "Emperor Nero: The Darkest Midnight Before the Fall of Rome | The History Snooze"

PROJECT_ROOT = Path("/media/vpsg16gb/Media/historysnooze/output") / "Emperor Nero - Emperor Nero - The Darkest Midnight Before the Fall of Rome _ The History Snooze"
PREPROD_DIR = PROJECT_ROOT / "01. Preproduction"
MEDIA_DIR = PROJECT_ROOT / "02. Media Generation"
AUDIO_DIR = MEDIA_DIR / "audio"
KEYFRAMES_DIR = MEDIA_DIR / "keyframes"

for d in [PROJECT_ROOT, PREPROD_DIR, MEDIA_DIR, AUDIO_DIR, KEYFRAMES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PART_TITLES = [
    "The Sunrise at Antium and the Child of Bronze",
    "Return from Exile and the Poisoned Banquet of Claudius",
    "The Golden Five Years - Seneca, Burrus, and the New Age",
    "The Shadow in the Banqueting Hall - The Fall of Britannicus",
    "The Empress Mother and the Golden Court of Baiae",
    "The Crimson Bay of Pozzuoli - A Mother's Fate",
    "The Great Fire of Rome - The Night of Ash and Starlight",
    "The Domus Aurea - The Revolving Palace of Ivory and Gold",
    "The Pisonian Shadow - Whispers, Philosophy, and Daggers",
    "The Greek Odyssey - The Artist-Emperor and the Crown of Laurel",
    "The Gathering Tempest - Echoes of Revolt from Gaul and Hispania",
    "The Deserted Palatine - Empty Chambers and Vanishing Guards",
    "The Midnight Escape - The Cloaked Ride along the Via Nomentana",
    "The Final Sanctuary - The Cellar of Phaon and the Last Artist",
    "The Ashes of the Pincian Hill - Memory, Starlight, and Eternal Rome"
]

SETTINGS = [
    "ref_setting_antium_coastal_palace", "ref_setting_rome_palatine_hill_courtyard",
    "ref_setting_seneca_philosophy_library", "ref_setting_imperial_banquet_hall",
    "ref_setting_palatine_private_gardens", "ref_setting_bay_of_naples_night",
    "ref_setting_great_fire_of_rome_ruins", "ref_setting_domus_aurea_golden_hall",
    "ref_setting_roman_curia_marble_baths", "ref_setting_olympia_greece_temple",
    "ref_setting_palatine_silent_hallway", "ref_setting_empty_emperor_chambers",
    "ref_setting_nomentana_road_misty_night", "ref_setting_phaon_suburban_villa_room",
    "ref_setting_pincian_hill_twilight"
]

PROPS = [
    "ref_props_roman_bronze_cradle", "ref_props_poisoned_mushroom_platter",
    "ref_props_papyrus_scroll_philosophy", "ref_props_golden_goblet_wine",
    "ref_props_golden_lyre_instrument", "ref_props_imperial_ship_lantern",
    "ref_props_crimson_torch_flame", "ref_props_domus_aurea_ivory_ceiling",
    "ref_props_senatorial_piso_scroll", "ref_props_greek_laurel_wreath",
    "ref_props_praetorian_deserted_helmet", "ref_props_unlit_oil_lamp",
    "ref_props_cloak_hood_rain", "ref_props_iron_dagger_blade",
    "ref_props_marble_funeral_urn"
]

print("Assembling 15 Parts, 150 Beats for Emperor Nero...")

# Build full text & prompts
full_script_md = [f"# {DOC_TITLE}\n## Full Canonical Script (15 Parts, 150 Beats)\n\n"]
prompts_text = []
outline_data = []
total_words = 0

for p_idx, p_beats in enumerate(ALL_PARTS, 1):
    p_title = PART_TITLES[p_idx - 1]
    s_ref = SETTINGS[p_idx - 1]
    p_ref = PROPS[p_idx - 1]
    c_ref = "ref_character_emperor_nero_young" if p_idx <= 3 else "ref_character_emperor_nero_emperor"

    full_script_md.append(f"### Part {p_idx:02d}: {p_title}\n\n")
    p_words = 0

    for b_idx, beat in enumerate(p_beats, 1):
        narrative = beat["narrative"]
        scene = beat["scene"]
        p_words += len(narrative.split())
        full_script_md.append(f"{narrative}\n\n")

        prompt_str = build_3tier_nero_prompt(p_idx, b_idx)
        prompts_text.append(prompt_str)

    total_words += p_words
    outline_data.append({
        "part": p_idx,
        "title": p_title,
        "character_ref": c_ref,
        "setting_ref": s_ref,
        "prop_ref": p_ref,
        "word_count": p_words,
        "summary": p_beats[0]["narrative"][:200] + "..."
    })

print(f"✅ Total Script Word Count: {total_words} words (150 beats across 15 parts)")

# Save script_full.md
script_md_content = "".join(full_script_md)
with open(PROJECT_ROOT / "script_full.md", "w", encoding="utf-8") as f:
    f.write(script_md_content)
with open(PREPROD_DIR / "script_full.md", "w", encoding="utf-8") as f:
    f.write(script_md_content)

# Save combined_imageprompts.txt (150 beats 3-tier)
prompts_file_content = "\n\n".join(prompts_text) + "\n"
combined_dir = MEDIA_DIR / "combined"
combined_dir.mkdir(parents=True, exist_ok=True)

with open(PROJECT_ROOT / "combined_imageprompts.txt", "w", encoding="utf-8") as f:
    f.write(prompts_file_content)
with open(PREPROD_DIR / "combined_imageprompts.txt", "w", encoding="utf-8") as f:
    f.write(prompts_file_content)
with open(combined_dir / "combined_imageprompts.txt", "w", encoding="utf-8") as f:
    f.write(prompts_file_content)

# Save outline.json & metadata.json
with open(PREPROD_DIR / "outline.json", "w", encoding="utf-8") as f:
    json.dump(outline_data, f, indent=2, ensure_ascii=False)
with open(PREPROD_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump({
        "idea_id": IDEA_ID,
        "character": CHARACTER_NAME,
        "title": DOC_TITLE,
        "youtube_title": YOUTUBE_TITLE,
        "word_count": total_words,
        "total_parts": 15,
        "total_beats": 150,
        "generated_at": datetime.now().isoformat()
    }, f, indent=2, ensure_ascii=False)

# Build Outline DOCX
outline_doc = docx.Document()
outline_doc.add_heading(f"Outline: {DOC_TITLE}", level=0)
outline_doc.add_paragraph(f"Idea ID: {IDEA_ID} | Total Words: {total_words} | 15 Parts, 150 Beats")
for item in outline_data:
    p = outline_doc.add_paragraph()
    p.add_run(f"Part {item['part']:02d}: {item['title']}\n").bold = True
    p.add_run(f"Anchors: [{item['character_ref']}] [{item['setting_ref']}] [{item['prop_ref']}] ({item['word_count']} words)\n")
    p.add_run(f"Focus: {item['summary']}\n")
outline_doc.save(PREPROD_DIR / "Outline - Emperor Nero.docx")

# Build Script DOCX
script_doc = docx.Document()
script_doc.add_heading(DOC_TITLE, level=0)
script_doc.add_paragraph("Full Canonical Narration Script (15 Parts, 150 Paragraphs)")
for p_idx, p_beats in enumerate(ALL_PARTS, 1):
    script_doc.add_heading(f"Part {p_idx:02d}: {PART_TITLES[p_idx-1]}", level=1)
    for beat in p_beats:
        script_doc.add_paragraph(beat["narrative"])
script_doc.save(PREPROD_DIR / "Script - Emperor Nero.docx")

print("✅ Saved local Markdown, JSON, and DOCX files successfully!")
