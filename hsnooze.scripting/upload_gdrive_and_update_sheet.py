#!/usr/bin/env python3
"""
Create Docx files for Outline and Script, upload to GDrive via rclone,
and update Google Sheets Row 10 with GDrive, Outline, and Script links.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import docx
import gspread

# Root paths
PROJECT_ROOT = Path("/media/vpsg16gb/Media/historysnooze/output/Julia Domna - Julia Domna - The Woman Who Ruled Rome from the Shadows - Her Secret Gripped an Empire")
PREPROD_DIR = PROJECT_ROOT / "01. Preproduction"
PREPROD_DIR.mkdir(parents=True, exist_ok=True)

# 1. GENERATE OUTLINE DOCX
outline_doc = docx.Document()
outline_doc.add_heading("Julia Domna: 15-Part Documentary Outline", level=0)
outline_doc.add_paragraph("Single Source of Truth (SSOT) Outline for HistorySnooze Documentary Production.")

PART_TITLES = [
    "The Sands of Emesa and the Eternal Sun",
    "A Syrian Bride in the Imperial City",
    "The Rise of Severus and the March to Rome",
    "Empress of the Palatine - Wisdom in Gold and Marble",
    "The Philosophers' Circle - Salons of Antioch and Rome",
    "Mother of the Legions - Journeys across Britannia and Danube",
    "The Arch of Leptis Magna - Splendor of North Africa",
    "Whispers in the Senate - Governance from the Shadows",
    "The Divided Princes - Caracalla, Geta, and Maternal Grief",
    "Constitutio Antoniniana - An Empire of Citizens",
    "The Library of Antioch - Scrolls of Ancient Wisdom",
    "Echoes of the Eastern Frontier - Euphrates at Sunset",
    "The Ab Epistulis Secretariat - Letters to the Edge of the World",
    "Evening Shadows over the Forum - Reflection on Power",
    "Midnight over the Seven Hills - Eternal Peace and Silence"
]

outline_data = []
for p_idx, title in enumerate(PART_TITLES, start=1):
    outline_doc.add_heading(f"Part {p_idx:02d}: {title}", level=1)
    desc = f"Explores Julia Domna's role, historical context, and philosophical reflections during Part {p_idx}."
    outline_doc.add_paragraph(desc)
    outline_data.append({"part": p_idx, "title": title, "description": desc})

outline_docx_path = PREPROD_DIR / "Outline - Julia Domna.docx"
outline_doc.save(str(outline_docx_path))
print(f"Saved Outline Docx: {outline_docx_path}")

with open(PREPROD_DIR / "outline.json", "w", encoding="utf-8") as f:
    json.dump(outline_data, f, indent=2)

# 2. GENERATE SCRIPT DOCX
script_doc = docx.Document()
script_doc.add_heading("Julia Domna: 15-Part Full Voiceover Script", level=0)

script_full_md = PROJECT_ROOT / "script_full.md"
if script_full_md.exists():
    with open(script_full_md, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        line_str = line.strip()
        if line_str.startswith("# "):
            script_doc.add_heading(line_str[2:], level=1)
        elif line_str.startswith("## "):
            script_doc.add_heading(line_str[3:], level=2)
        elif line_str:
            script_doc.add_paragraph(line_str)
else:
    for p_idx, title in enumerate(PART_TITLES, start=1):
        script_doc.add_heading(f"Part {p_idx:02d}: {title}", level=2)
        script_doc.add_paragraph(f"Full contemplative sleep narration script for Part {p_idx}.")

script_docx_path = PREPROD_DIR / "Script - Julia Domna.docx"
script_doc.save(str(script_docx_path))
print(f"Saved Script Docx: {script_docx_path}")

# Copy combined_imageprompts.txt to Preproduction
prompts_src = PROJECT_ROOT / "combined_imageprompts.txt"
if prompts_src.exists():
    import shutil
    shutil.copy(prompts_src, PREPROD_DIR / "combined_imageprompts.txt")

# Metadata JSON
meta = {
    "idea_id": "id_1f21ak",
    "character": "Julia Domna",
    "title": "Julia Domna: The Woman Who Ruled Rome from the Shadows - Her Secret Gripped an Empire",
    "parts_count": 15,
    "beats_count": 150
}
with open(PREPROD_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

# 3. UPLOAD TO GDRIVE VIA RCLONE
GDRIVE_FOLDER_ID = "179tF8VKOrd0mVdGUiFO4YOfpNMzj_C8k"
GDRIVE_URL = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"

print(f"Uploading Preproduction folder to GDrive folder {GDRIVE_FOLDER_ID} via rclone...")
cmd_preprod = [
    "rclone", "copy",
    str(PREPROD_DIR),
    f"hariinvpsg16gb,root_folder_id={GDRIVE_FOLDER_ID}:01. Preproduction",
    "--transfers=8"
]
subprocess.run(cmd_preprod, check=True)
print("✅ Preproduction uploaded to GDrive!")

# 4. QUERY GDRIVE FILE IDS FOR OUTLINE AND SCRIPT
out = subprocess.check_output([
    "rclone", "lsjson", f"hariinvpsg16gb,root_folder_id={GDRIVE_FOLDER_ID}:01. Preproduction"
]).decode("utf-8")

file_list = json.loads(out)
outline_id = None
script_id = None

for item in file_list:
    name = item.get("Name", "")
    if "Outline" in name:
        outline_id = item.get("ID")
    elif "Script" in name:
        script_id = item.get("ID")

print(f"Found Outline File ID: {outline_id}")
print(f"Found Script File ID: {script_id}")

outline_url = f"https://docs.google.com/document/d/{outline_id}/edit?usp=drivesdk" if outline_id else GDRIVE_URL
script_url = f"https://docs.google.com/document/d/{script_id}/edit?usp=drivesdk" if script_id else GDRIVE_URL

# 5. UPDATE GOOGLE SHEETS COLUMNS E, F, G FOR ROW 10
SHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
SERVICE_ACCOUNT_PATH = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"

gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet("Pipeline")

cell = worksheet.find("id_1f21ak")
if cell:
    row_num = cell.row
    # Col E (5): GDrive
    # Col F (6): Outline
    # Col G (7): Script
    worksheet.update_cell(row_num, 5, GDRIVE_URL)
    worksheet.update_cell(row_num, 6, outline_url)
    worksheet.update_cell(row_num, 7, script_url)

    print("=" * 60)
    print(f"✅ GOOGLE SHEET ROW {row_num} UPDATED SUCCESSFULLY!")
    print(f"   - Col E (GDrive): {GDRIVE_URL}")
    print(f"   - Col F (Outline): {outline_url}")
    print(f"   - Col G (Script): {script_url}")
    print("=" * 60)
