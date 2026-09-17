#!/usr/bin/env python3
"""
Sync Emperor Nero Preproduction assets to Google Drive and update Google Sheets Row 11.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import gspread

GDRIVE_FOLDER_ID = "1bKhloyCDMMjg2m6XCg2HPlzU5SEw_wbT"
PROJECT_ROOT = Path("/media/vpsg16gb/Media/historysnooze/output/Emperor Nero - Emperor Nero - The Darkest Midnight Before the Fall of Rome _ The History Snooze")
PREPROD_DIR = PROJECT_ROOT / "01. Preproduction"

print(f"Uploading Preproduction assets to GDrive folder {GDRIVE_FOLDER_ID} via rclone...")
cmd_preprod = [
    "rclone", "copy",
    str(PREPROD_DIR),
    f"hariinvpsg16gb,root_folder_id={GDRIVE_FOLDER_ID}:01. Preproduction",
    "--transfers=8"
]
subprocess.run(cmd_preprod, check=True)
print("✅ Preproduction files uploaded to GDrive successfully!")

# Query GDrive file IDs
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

GDRIVE_URL = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
outline_url = f"https://docs.google.com/document/d/{outline_id}/edit?usp=drivesdk" if outline_id else GDRIVE_URL
script_url = f"https://docs.google.com/document/d/{script_id}/edit?usp=drivesdk" if script_id else GDRIVE_URL

# Update Google Sheets Row 11
SHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
SERVICE_ACCOUNT_PATH = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"

gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet("Pipeline")

cell = worksheet.find("id_jt1ps3")
if cell:
    row_num = cell.row
    # Col D (4): Status -> 'Script'
    # Col E (5): GDrive -> GDRIVE_URL
    # Col F (6): Outline -> outline_url
    # Col G (7): Script -> script_url
    # Col I (9): Voiceover -> ''
    # Col K (11): Image -> ''
    # Col O (15): Updated_At -> current timestamp
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    worksheet.update_cell(row_num, 4, "Script")
    worksheet.update_cell(row_num, 5, GDRIVE_URL)
    worksheet.update_cell(row_num, 6, outline_url)
    worksheet.update_cell(row_num, 7, script_url)
    worksheet.update_cell(row_num, 9, "")
    worksheet.update_cell(row_num, 11, "")
    worksheet.update_cell(row_num, 15, now_str)

    print("=" * 60)
    print(f"✅ GOOGLE SHEET ROW {row_num} (EMPEROR NERO) RESET TO REAL SCRIPT!")
    print(f"   - Status: Script")
    print(f"   - Col E (GDrive): {GDRIVE_URL}")
    print(f"   - Col F (Outline): {outline_url}")
    print(f"   - Col G (Script): {script_url}")
    print(f"   - Voiceover & Image: Reset to empty (ready for cloud runner)")
    print("=" * 60)
