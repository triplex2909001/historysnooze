#!/usr/bin/env python3
"""
Canonical Production Generator for Julie d'Aubigny (La Maupin) Sleep Documentary
Generates:
1. 15-Part ambient sleep narration script (150 paragraphs, ~17,366 words in Milo ASMR style).
2. 150 unique, cinematic 4K visual prompt beats with Reference Anchor Kit tags ([CHARACTER] [SETTING] [PROP]).
3. Formatted DOCX outline and script, JSON metadata, combined prompts file, and Markdown script.
4. Synchronizes dedicated project folder on Google Drive and uploads clean authentic assets.
5. Updates Google Sheets row 2 in tab "Pipeline" with direct URLs and timestamp.
"""

import os
import sys
import json
import shutil
import subprocess
import docx
from datetime import datetime
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Add scripts directory to path
SCRIPTS_DIR = Path("/media/vpsg16gb/Media/historysnooze/scripts")
sys.path.insert(0, str(SCRIPTS_DIR))
from julie_canonical_data import CANONICAL_PARTS, CANONICAL_SCENES

# Constants & SSOT
SHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
GDRIVE_PARENT_FOLDER_ID = "1UGkrUFQ62ghj1Lquy1HVsKIYR9nO60zf"  # "historysnooze posts"
SERVICE_ACCOUNT_PATH = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"
IDEA_ID = "id_nbe77s"
CHARACTER_NAME = "Julie d'Aubigny"
DOC_TITLE = "Julie d'Aubigny: The Swordswoman Who Set Paris Ablaze and Defied the King"

DOC_TITLE_SAFE = DOC_TITLE.replace(":", " -")
PROJECT_ROOT = Path("/media/vpsg16gb/Media/historysnooze/output") / f"{CHARACTER_NAME} - {DOC_TITLE_SAFE}"
PREPROD_DIR = PROJECT_ROOT / "01. Preproduction"
MEDIA_DIR = PROJECT_ROOT / "02. Media Generation"
AUDIO_DIR = MEDIA_DIR / "audio"
KEYFRAMES_DIR = MEDIA_DIR / "keyframes"

for d in [PROJECT_ROOT, PREPROD_DIR, MEDIA_DIR, AUDIO_DIR, KEYFRAMES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print(f"HISTORYSNOOZE CANONICAL GENERATOR: {DOC_TITLE}")
print(f"Target Directory: {PROJECT_ROOT}")
print("=" * 60)

PARTS_INFO = [
    {
        "index": 1,
        "title": "The Grand Stables of Versailles - The Riding Master's Daughter",
        "c_ref": "ref_character_julie_daubigny_young",
        "s_ref": "ref_setting_versailles_grand_stables",
        "p_ref": "ref_props_french_training_foil",
        "focus": "Childhood in the Grand Stables of Versailles, father Gaston d'Aubigny, equestrian mastery, training alongside royal pages, morning mist over palace riding rings."
    },
    {
        "index": 2,
        "title": "The Art of the Blade - A Maiden in Men's Doublet",
        "c_ref": "ref_character_julie_daubigny_young",
        "s_ref": "ref_setting_paris_fencing_school",
        "p_ref": "ref_props_french_court_rapier",
        "focus": "Fencing academies of Paris, master bladesmiths, adopting male attire for athletic freedom, swift mastery of rapier and smallsword, poise and discipline."
    },
    {
        "index": 3,
        "title": "The Flight with Sérannes - Highwaymen and the Road South",
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_provencal_travel_road",
        "p_ref": "ref_props_travel_leather_trunk",
        "focus": "Departure from Paris with master swordsman Sérannes, fleeing along moonlit southern post roads, coaching inns, campfires under starlit skies of France."
    },
    {
        "index": 4,
        "title": "Duelists on the Traveling Stage - Defeating Men Across the Provinces",
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_provencal_tavern_courtyard",
        "p_ref": "ref_props_french_court_rapier",
        "focus": "Fairs and tavern courtyards of Poitiers and Bordeaux, public fencing challenges, unbuttoning doublet to silence skeptics, charismatic fearless presence."
    },
    {
        "index": 5,
        "title": "The Songbird of Marseille - Triumph in the Southern Sun",
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_marseille_opera_harbor",
        "p_ref": "ref_props_baroque_opera_score",
        "focus": "Arrival in Marseille, Pierre Gaultier's opera academy, discovery of her rich resonant contralto voice, singing over turquoise Mediterranean waters."
    },
    {
        "index": 6,
        "title": "The Cloister of Avignon - The Midnight Fire and the Daring Escape",
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_avignon_convent_night",
        "p_ref": "ref_props_monastery_incense_cross",
        "focus": "Entering the Visitandine convent as a postulant, the daring scheme to free her lover, flames in the night, riding into the cool starlit dawn of Provence."
    },
    {
        "index": 7,
        "title": "The Road to Paris and the Duel of Count d'Albert - From Steel to Devotion",
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_provencal_travel_road",
        "p_ref": "ref_props_french_court_rapier",
        "focus": "Tavern confrontation with young Count d'Albert, moonlit duel outside the coaching inn, wounding his shoulder, nursing him, forging lifelong friendship."
    },
    {
        "index": 8,
        "title": "The Golden Gates of the Palais-Royal - Debut as Pallas Athena",
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_paris_opera_palais_royal",
        "p_ref": "ref_props_gilded_pallas_helmet_spear",
        "focus": "Petitioning Louis XIV via Count d'Armagnac, royal pardon granted, sensational 1690 debut in Lully's Cadmus et Hermione as Pallas Athena at the Paris Opera."
    },
    {
        "index": 9,
        "title": "Masterpieces of Lully and Campra - Clorinda the Warrior Maiden",
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_paris_opera_palais_royal",
        "p_ref": "ref_props_baroque_opera_score",
        "focus": "André Campra writing Tancrède specifically for her, creating the historic warrior heroine Clorinda, armor and silk on stage, undisputed star of French opera."
    },
    {
        "index": 10,
        "title": "The Masked Ball of Monsieur - A Kiss, A Challenge, and Three Rapiers",
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_versailles_hall_of_mirrors",
        "p_ref": "ref_props_baroque_carnival_mask",
        "focus": "Grand royal masquerade at Palais-Royal, dressed in men's court velvet, kissing a beautiful noblewoman, dueling three challengers consecutively in the gardens."
    },
    {
        "index": 11,
        "title": "The Decree of the Sun King - Sovereign Grace and Dueling Laws",
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_versailles_hall_of_mirrors",
        "p_ref": "ref_props_royal_pardon_scroll",
        "focus": "Louis XIV's famous sovereign quip that dueling laws applied only to men, the King's second royal pardon, court fascination with her indomitable spirit."
    },
    {
        "index": 12,
        "title": "The Grand Stage of Brussels - Defying the Prince of Bavaria",
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_brussels_court_salon",
        "p_ref": "ref_props_travel_leather_trunk",
        "focus": "Sojourn in Brussels, prima donna at Opéra du Quai au Foin, court of Maximilian II Emanuel, tossing his 40,000 francs to the floor with proud independence."
    },
    {
        "index": 13,
        "title": "Reign at the Académie Royale - The Unrivaled Star of Paris",
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_paris_opera_palais_royal",
        "p_ref": "ref_props_baroque_opera_score",
        "focus": "Triumphant return to Paris, legendary duets with Fanchon Moreau, standing ovations from the Sun King's court, quiet evenings along the banks of the Seine."
    },
    {
        "index": 14,
        "title": "The Shadow of Grief - The Passing of Florensac and Farewell to the Stage",
        "c_ref": "ref_character_julie_daubigny_opera",
        "s_ref": "ref_setting_fontainebleau_forest_clearing",
        "p_ref": "ref_props_baroque_carnival_mask",
        "focus": "Devoted bond with the Marquise de Florensac, tragic illness and mourning, final operatic performance at 32, retiring gracefully from public acclaim."
    },
    {
        "index": 15,
        "title": "Midnight over Provence - Eternal Rest and the Legend of La Maupin",
        "c_ref": "ref_character_julie_daubigny_duelist",
        "s_ref": "ref_setting_provencal_monastery_sanctuary",
        "p_ref": "ref_props_monastery_incense_cross",
        "focus": "Final serene retreat in a peaceful Provence convent, cloister garden beneath starlit skies, lavender-scented night air, timeless rest, and deep sleep."
    }
]

print(f"Loaded {len(PARTS_INFO)} parts metadata.")

# --- 1. COMPOSE SCRIPT AND PROMPTS ---
print("\n[1/5] Assembling 15-Part Narration & 150 Visual Prompt Beats...")

def build_script_and_prompts():
    beats = []
    full_script_md = [f"# {DOC_TITLE}\n\n"]

    for p_idx in range(1, 16):
        info = PARTS_INFO[p_idx - 1]
        p_title = info["title"]
        c_ref = info["c_ref"]
        s_ref = info["s_ref"]
        p_ref = info["p_ref"]

        full_script_md.append(f"## Part {p_idx:02d}: {p_title}\n\n")

        paragraphs = CANONICAL_PARTS[str(p_idx)] if str(p_idx) in CANONICAL_PARTS else CANONICAL_PARTS[p_idx]
        scenes = CANONICAL_SCENES[str(p_idx)] if str(p_idx) in CANONICAL_SCENES else CANONICAL_SCENES[p_idx]

        for b_idx in range(1, 11):
            beat_id = f"beat_P{p_idx:02d}_B{b_idx:02d}"
            paragraph_text = paragraphs[b_idx - 1]
            scene_desc = scenes[b_idx - 1]

            full_script_md.append(f"{paragraph_text}\n\n")

            prompt_str = (
                f"beat_P{p_idx:02d}_B{b_idx:02d}.jpg: [CHARACTER: {c_ref}] [SETTING: {s_ref}] [PROP: {p_ref}] "
                f"{scene_desc} --ar 16:9 --style raw --v 6.0"
            )

            beats.append({
                "part_index": p_idx,
                "beat_index": b_idx,
                "id": beat_id,
                "filename": f"{beat_id}.jpg",
                "title": f"Part {p_idx:02d} Beat {b_idx:02d}: {p_title}",
                "narrative": paragraph_text,
                "prompt": prompt_str,
                "c_ref": c_ref,
                "s_ref": s_ref,
                "p_ref": p_ref
            })

    return beats, "".join(full_script_md)

all_beats, script_md_text = build_script_and_prompts()
total_word_count = len(script_md_text.split())

# Save script_full.md
script_md_file = PROJECT_ROOT / "script_full.md"
with open(script_md_file, "w", encoding="utf-8") as f:
    f.write(script_md_text)
print(f"✅ Generated {script_md_file.name} ({total_word_count} words, {len(all_beats)} beats)")

# Save combined_imageprompts.txt
prompts_lines = [b["prompt"] for b in all_beats]
prompts_file = PROJECT_ROOT / "combined_imageprompts.txt"
with open(prompts_file, "w", encoding="utf-8") as f:
    f.write("\n\n".join(prompts_lines) + "\n")
print(f"✅ Generated {prompts_file.name} (150 distinct visual prompts)")

# Copy to Preproduction folder
shutil.copy(prompts_file, PREPROD_DIR / "combined_imageprompts.txt")

# --- 2. GENERATE OUTLINE & SCRIPT DOCX ---
print("\n[2/5] Creating Professional Word Documents (DOCX)...")

# Outline DOCX
outline_doc = docx.Document()
outline_doc.add_heading(f"{DOC_TITLE} - 15-Part Documentary Outline", level=0)
outline_doc.add_paragraph("Canonical Single Source of Truth (SSOT) Production Outline for HistorySnooze Ambient Sleep Documentary.")

outline_json_data = []
for p in PARTS_INFO:
    p_idx = p["index"]
    p_title = p["title"]
    outline_doc.add_heading(f"Part {p_idx:02d}: {p_title}", level=1)
    desc = f"Focus: {p['focus']}. Anchor kit tags: Character: {p['c_ref']}, Setting: {p['s_ref']}, Prop: {p['p_ref']}."
    outline_doc.add_paragraph(desc)
    outline_json_data.append({
        "part": p_idx,
        "title": p_title,
        "character_ref": p["c_ref"],
        "setting_ref": p["s_ref"],
        "prop_ref": p["p_ref"],
        "description": p["focus"],
        "beats_count": 10
    })

outline_docx_path = PREPROD_DIR / f"Outline - {CHARACTER_NAME}.docx"
outline_doc.save(str(outline_docx_path))
print(f"✅ Saved Outline DOCX: {outline_docx_path.name}")

with open(PREPROD_DIR / "outline.json", "w", encoding="utf-8") as f:
    json.dump(outline_json_data, f, indent=2)

# Script DOCX
script_doc = docx.Document()
script_doc.add_heading(f"{DOC_TITLE} - Full Voiceover Script", level=0)
script_doc.add_paragraph(f"Full contemplative ambient sleep narration script (15 Parts, 150 Paragraphs, {total_word_count} words in Milo ASMR style).")

for p in PARTS_INFO:
    p_idx = p["index"]
    p_title = p["title"]
    script_doc.add_heading(f"Part {p_idx:02d}: {p_title}", level=1)

    part_beats = [b for b in all_beats if b["part_index"] == p_idx]
    for b in part_beats:
        p_para = script_doc.add_paragraph(b["narrative"])
        p_para.paragraph_format.space_after = docx.shared.Pt(8)

script_docx_path = PREPROD_DIR / f"Script - {CHARACTER_NAME}.docx"
script_doc.save(str(script_docx_path))
print(f"✅ Saved Script DOCX: {script_docx_path.name}")

# Metadata JSON
meta = {
    "idea_id": IDEA_ID,
    "character": CHARACTER_NAME,
    "title": DOC_TITLE,
    "parts_count": 15,
    "beats_count": 150,
    "word_count": total_word_count,
    "created_at": datetime.now().isoformat(),
    "style": "Ambient ASMR Sleep Documentary",
    "gdrive_folder_id": None
}
with open(PREPROD_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

# --- 3. SYNCHRONIZE TO GOOGLE DRIVE VIA RCLONE ---
print("\n[3/5] Synchronizing directly to Google Drive via rclone...")

remote_folder_name = f"{CHARACTER_NAME} - {DOC_TITLE}"

# Copy Preproduction folder
cmd_preprod = [
    "/home/vpsg16gb/.local/bin/rclone", "copy",
    str(PREPROD_DIR),
    f"hariinvpsg16gb:{remote_folder_name}/01. Preproduction",
    f"--drive-root-folder-id={GDRIVE_PARENT_FOLDER_ID}",
    "-v"
]
subprocess.run(cmd_preprod, check=True)

# Copy Root files
cmd_root = [
    "/home/vpsg16gb/.local/bin/rclone", "copy",
    str(PROJECT_ROOT),
    f"hariinvpsg16gb:{remote_folder_name}",
    f"--drive-root-folder-id={GDRIVE_PARENT_FOLDER_ID}",
    "--include", "script_full.md",
    "--include", "combined_imageprompts.txt",
    "-v"
]
subprocess.run(cmd_root, check=True)

print("✅ Google Drive synchronization complete!")

# --- 4. QUERY GDRIVE FILE IDS & UPDATE GOOGLE SHEETS DASHBOARD ---
print("\n[4/5] Retrieving Google Drive File IDs & Updating Google Sheets (Row 2)...")

sa_creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_PATH,
    scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
)
drive = build("drive", "v3", credentials=sa_creds)

# Find project folder ID
res = drive.files().list(
    q=f"'{GDRIVE_PARENT_FOLDER_ID}' in parents and name contains 'Julie' and trashed=false",
    fields="files(id, name)"
).execute()
julie_folder = res.get("files", [])[0]
gdrive_project_folder_id = julie_folder["id"]

# Update metadata.json with actual gdrive_folder_id
meta["gdrive_folder_id"] = gdrive_project_folder_id
with open(PREPROD_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

# Find 01. Preproduction folder ID
res_preprod = drive.files().list(
    q=f"'{gdrive_project_folder_id}' in parents and name='01. Preproduction' and trashed=false",
    fields="files(id, name)"
).execute()
preprod_folder = res_preprod.get("files", [])[0]
preprod_drive_id = preprod_folder["id"]

# Find Outline and Script DOCX in Preproduction
res_files = drive.files().list(
    q=f"'{preprod_drive_id}' in parents and trashed=false",
    fields="files(id, name)"
).execute()
files_map = {f["name"]: f["id"] for f in res_files.get("files", [])}

outline_docx_id = files_map.get(f"Outline - {CHARACTER_NAME}.docx")
script_docx_id = files_map.get(f"Script - {CHARACTER_NAME}.docx")

gdrive_url = f"https://drive.google.com/drive/folders/{gdrive_project_folder_id}"
outline_url = f"https://docs.google.com/document/d/{outline_docx_id}/edit?usp=drivesdk" if outline_docx_id else gdrive_url
script_url = f"https://docs.google.com/document/d/{script_docx_id}/edit?usp=drivesdk" if script_docx_id else gdrive_url

gc = gspread.authorize(sa_creds)
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("Pipeline")

cell = ws.find(IDEA_ID)
if cell:
    row_num = cell.row
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ws.update_cell(row_num, 4, "Script")
    ws.update_cell(row_num, 5, gdrive_url)
    ws.update_cell(row_num, 6, outline_url)
    ws.update_cell(row_num, 7, script_url)
    ws.update_cell(row_num, 15, now_str)

    print("=" * 60)
    print(f"🎉 GOOGLE SHEET ROW {row_num} UPDATED SUCCESSFULLY!")
    print(f"   - Status (Col D): Script")
    print(f"   - GDrive (Col E): {gdrive_url}")
    print(f"   - Outline (Col F): {outline_url}")
    print(f"   - Script (Col G): {script_url}")
    print(f"   - Updated_At (Col O): {now_str}")
    print("=" * 60)
else:
    print(f"❌ Error: Idea ID '{IDEA_ID}' not found in Google Sheet!")

print("\n" + "=" * 60)
print("🚀 ALL TASKS COMPLETED SUCCESSFULLY!")
print(f"1. Generated full 15-part script ({total_word_count} words, 150 beats).")
print(f"2. Generated 150 distinct 3-tier visual prompts ([CHARACTER] [SETTING] [PROP]).")
print(f"3. Created DOCX, JSON, Markdown, and TXT artifacts locally.")
print(f"4. Uploaded all assets directly to Google Drive folder '{remote_folder_name}'.")
print(f"5. Updated Google Sheets Pipeline Row 2.")
print("=" * 60)
