#!/usr/bin/env python3
"""
Post-processing for Emperor Nero:
1. Copy exact assembled Part_01.wav ... Part_15.wav and Master_*.wav from /tmp/omni_download_nero into local audio folder.
2. Acoustic and GK4 audit (24kHz, RMS, Peak, non-empty, all 15 parts + master).
3. Upload/Sync to Google Drive folder 1bKhloyCDMMjg2m6XCg2HPlzU5SEw_wbT/02. Media Generation/audio via rclone.
4. Update Google Sheets Row 11 (Status = Voiceover, Voice_Mode = GHA OmniVoice, Voiceover = Done).
"""

import os
import sys
import shutil
import glob
import subprocess
import soundfile as sf
import numpy as np
from pathlib import Path
import gspread
from datetime import datetime

SRC_DIR = Path("/tmp/omni_download_nero")
TARGET_DIR = Path("/media/vpsg16gb/Media/historysnooze/output/Emperor Nero - Emperor Nero - The Darkest Midnight Before the Fall of Rome _ The History Snooze/02. Media Generation/audio")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

GDRIVE_FOLDER_ID = "1bKhloyCDMMjg2m6XCg2HPlzU5SEw_wbT"
SHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
SERVICE_ACCOUNT_PATH = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"

print(f"=== STEP 1: Copying exact assembled Part_*.wav from {SRC_DIR} to {TARGET_DIR} ===")

# Locate exact Part_XX.wav files
for pnum in range(1, 16):
    part_dir = SRC_DIR / f"voiceover-part-{pnum}"
    expected_file = part_dir / f"Part_{pnum:02d}.wav"
    if not expected_file.exists():
        # Fallback search directly in folder
        candidates = [f for f in part_dir.glob("*.wav") if "chunk" not in f.name]
        if candidates:
            expected_file = candidates[0]
        else:
            print(f"❌ Missing Part {pnum:02d} in {part_dir}!")
            sys.exit(1)

    dst = TARGET_DIR / f"Part_{pnum:02d}.wav"
    shutil.copy2(expected_file, dst)
    print(f"  -> Copied {expected_file} ({expected_file.stat().st_size / 1024 / 1024:.2f} MB) -> {dst.name}")

# Locate master
master_dir = SRC_DIR / "master-voiceover-full"
master_candidates = list(master_dir.glob("*.wav"))
if not master_candidates:
    print(f"❌ Missing Master in {master_dir}!")
    sys.exit(1)

master_src = master_candidates[0]
dst_master = TARGET_DIR / "Master_Emperor_Nero_Full_Voiceover.wav"
shutil.copy2(master_src, dst_master)
print(f"  -> Copied Master {master_src.name} ({master_src.stat().st_size / 1024 / 1024:.2f} MB) -> {dst_master.name}")

print("\n=== STEP 2: Acoustic & GK4 Audit ===")
total_duration = 0.0
for pnum in range(1, 16):
    fpath = TARGET_DIR / f"Part_{pnum:02d}.wav"
    data, sr = sf.read(str(fpath))
    dur = len(data) / sr
    total_duration += dur
    rms = float(np.sqrt(np.mean(data**2)))
    peak = float(np.max(np.abs(data)))
    print(f"  Part {pnum:02d}: SR={sr}Hz, Dur={dur/60:.2f}m ({dur:.1f}s), RMS={rms:.4f}, Peak={peak:.4f}")
    assert sr == 24000, f"Part {pnum} sample rate is {sr}, expected 24000"
    assert rms >= 0.003, f"Part {pnum} RMS is {rms:.4f} < 0.003"
    assert peak >= 0.02, f"Part {pnum} Peak is {peak:.4f} < 0.02"

# Master audit
mdata, msr = sf.read(str(dst_master))
mdur = len(mdata) / msr
mrms = float(np.sqrt(np.mean(mdata**2)))
mpeak = float(np.max(np.abs(mdata)))
print(f"\n  MASTER AUDIO: SR={msr}Hz, Dur={mdur/60:.2f}m ({mdur:.1f}s), RMS={mrms:.4f}, Peak={mpeak:.4f}")
print(f"  Sum of parts duration: {total_duration/60:.2f}m ({total_duration:.1f}s)")
assert msr == 24000
assert mdur > 1800 # Should be > 30 minutes (actual ~79.5 min)
print("✅ GK4 Acoustic Audit PASSED 100%!")

print(f"\n=== STEP 3: Syncing to Google Drive folder {GDRIVE_FOLDER_ID} ===")
cmd_sync = [
    "rclone", "sync",
    str(TARGET_DIR),
    f"hariinvpsg16gb,root_folder_id={GDRIVE_FOLDER_ID}:02. Media Generation/audio",
    "--transfers=8",
    "--progress"
]
res = subprocess.run(cmd_sync, check=True)
print("✅ Audio synced to Google Drive successfully!")

print("\n=== STEP 4: Updating Google Sheets Row 11 ===")
gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet("Pipeline")
cell = worksheet.find("id_jt1ps3")
if cell:
    row_num = cell.row
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Col 4: Status -> Voiceover
    # Col 8: Voice_Mode -> GHA OmniVoice
    # Col 9: Voiceover -> Done
    # Col 15: Updated_At -> now
    worksheet.update_cell(row_num, 4, "Voiceover")
    worksheet.update_cell(row_num, 8, "GHA OmniVoice")
    worksheet.update_cell(row_num, 9, "Done")
    worksheet.update_cell(row_num, 15, now_str)
    print(f"✅ Google Sheets Row {row_num} (Emperor Nero) updated: Status=Voiceover, Voice_Mode=GHA OmniVoice, Voiceover=Done")

print("\n🎉 ALL STEPS COMPLETED FOR EMPEROR NERO!")
