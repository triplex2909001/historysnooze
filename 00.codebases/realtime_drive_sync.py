#!/usr/bin/env python3
"""
HistorySnooze Real-time Immediate Google Drive Keyframe Syncer
Watches local keyframes directory and uploads each newly generated keyframe
to Google Drive immediately upon completion without waiting for the full batch.
"""

import os
import sys
import time
import re
import shutil
import subprocess
from pathlib import Path

KEYFRAMES_DIR = Path("/media/vpsg16gb/Media/historysnooze/output/Julie d'Aubigny - Julie d'Aubigny - The Swordswoman Who Set Paris Ablaze and Defied the King/02. Media Generation/keyframes")
GDRIVE_FOLDER_ID = "1h6DO5D2zZzwFo4mbnWY9z9SZ8WvL2WZV"
RCLONE_REMOTE = "hariinvpsg16gb"

def main():
    print(f"📡 Real-time GDrive Keyframe Watcher started for:\n📁 {KEYFRAMES_DIR}")
    print(f"☁️ Target GDrive ID: {GDRIVE_FOLDER_ID}")

    uploaded_files = set()

    # First, populate uploaded_files by listing what's already on GDrive
    try:
        res = subprocess.run(
            ["rclone", "lsf", f"{RCLONE_REMOTE},root_folder_id={GDRIVE_FOLDER_ID}:02. Media Generation/keyframes"],
            capture_output=True, text=True, check=True
        )
        for name in res.stdout.splitlines():
            name = name.strip()
            if name:
                uploaded_files.add(name)
        print(f"ℹ️ Found {len(uploaded_files)} files already on GDrive.")
    except Exception as e:
        print(f"⚠️ Initial GDrive listing notice: {e}")

    while True:
        try:
                # 0. Unpack any .zip files from Google Flow
                for zf in KEYFRAMES_DIR.glob("beat_*.zip"):
                    m = re.match(r"(beat_P\d{2}_B\d{2})\.zip", zf.name, re.IGNORECASE)
                    if m:
                        base_id = m.group(1)
                        std_jpg = KEYFRAMES_DIR / f"{base_id}.jpg"
                        try:
                            import zipfile
                            with zipfile.ZipFile(zf, 'r') as z:
                                imgs = [n for n in z.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png'))]
                                if imgs:
                                    imgs.sort(key=lambda x: z.getinfo(x).file_size, reverse=True)
                                    img_data = z.read(imgs[0])
                                    with open(std_jpg, 'wb') as out_f:
                                        out_f.write(img_data)
                                    print(f"📦 Unpacked {zf.name} -> {std_jpg.name} ({len(img_data)//1024} KB)", flush=True)
                            # Remove zip after successful extraction
                            zf.unlink(missing_ok=True)
                        except Exception as ez:
                            print(f"⚠️ Error unpacking {zf.name}: {ez}", flush=True)

                all_files = list(KEYFRAMES_DIR.glob("beat_*.*"))

                for f in all_files:
                    # 1. Normalize .jpeg to .jpg
                    if f.suffix.lower() in [".jpeg", ".jpg", ".png"]:
                        m = re.match(r"(beat_P\d{2}_B\d{2})(-\d{3})?\.(jpeg|jpg|png)", f.name, re.IGNORECASE)
                        if m:
                            base_id = m.group(1)
                            std_jpg = KEYFRAMES_DIR / f"{base_id}.jpg"

                            # If f is not std_jpg, copy to std_jpg
                            if f != std_jpg and not std_jpg.exists():
                                shutil.copy2(f, std_jpg)
                                print(f"🔄 Normalized {f.name} -> {std_jpg.name}", flush=True)

                            # Target file to upload is std_jpg
                            target_upload = std_jpg if std_jpg.exists() else f

                            # Check size and upload status
                            if target_upload.name not in uploaded_files and target_upload.stat().st_size >= 30000:
                                # Run rclone copyto
                                gdrive_dest = f"{RCLONE_REMOTE},root_folder_id={GDRIVE_FOLDER_ID}:02. Media Generation/keyframes/{target_upload.name}"
                                cmd = ["rclone", "copyto", str(target_upload), gdrive_dest]
                                ret = subprocess.run(cmd, capture_output=True, text=True)
                                if ret.returncode == 0:
                                    uploaded_files.add(target_upload.name)
                                    print(f"🚀 [INSTANT SYNC] Uploaded {target_upload.name} ({target_upload.stat().st_size // 1024} KB) to Google Drive!", flush=True)
                                else:
                                    print(f"⚠️ Failed to upload {target_upload.name}: {ret.stderr}", flush=True)

                    # Note: No .json metadata uploaded to keyframes folder on GDrive per user instruction


        except Exception as e:
            print(f"⚠️ Error in sync loop: {e}", flush=True)

        time.sleep(5)

if __name__ == "__main__":
    main()
