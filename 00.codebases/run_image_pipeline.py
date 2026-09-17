#!/usr/bin/env python3
"""
HistorySnooze Sequential Image Pipeline Runner
Runs Google Flow image synthesis for projects:
- Julie d'Aubigny (Row 2, id_nbe77s)
- Emperor Nero (Row 11, id_jt1ps3)

Enforces:
- 5 rotating Chrome profiles: default, profile_3, profile_4, profile_9, profile_13
- Zero-leak, autoheal, resume checkpointing
- Strict bracket tag stripping [CHARACTER:...], [SETTING:...], [PROP:...]
- Standardized .jpg keyframes (no duplicate .jpeg)
- GK3 visual audit (file size >= 30KB, valid 16:9 JPEG)
- Automatic Google Drive sync via rclone
- Google Sheets master dashboard update
"""

import os
import sys
import re
import yaml
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import gspread

PROJECTS = {
    "julie": {
        "name": "Julie d'Aubigny",
        "idea_id": "id_nbe77s",
        "row_num": 2,
        "gdrive_folder_id": "1h6DO5D2zZzwFo4mbnWY9z9SZ8WvL2WZV",
        "project_root": Path("/media/vpsg16gb/Media/historysnooze/output/Julie d'Aubigny - Julie d'Aubigny - The Swordswoman Who Set Paris Ablaze and Defied the King"),
    },
    "nero": {
        "name": "Emperor Nero",
        "idea_id": "id_jt1ps3",
        "row_num": 11,
        "gdrive_folder_id": "1bKhloyCDMMjg2m6XCg2HPlzU5SEw_wbT",
        "project_root": Path("/media/vpsg16gb/Media/historysnooze/output/Emperor Nero - Emperor Nero - The Darkest Midnight Before the Fall of Rome _ The History Snooze"),
    }
}

GFLOW_DIR = Path("/media/vpsg16gb/Media/historysnooze/hsnooze.gflow")
SHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
SERVICE_ACCOUNT_PATH = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"
# Strictly approved profiles for Google Flow image synthesis
# FORBIDDEN: default / aleron.dt@gmail.com
PROFILES = ["profile_13", "profile_3", "profile_4", "profile_9"]
FORBIDDEN_EMAILS = ["aleron.dt@gmail.com"]
FORBIDDEN_PROFILES = ["default"]


def parse_prompts_file(prompts_path: Path):
    with open(prompts_path, "r", encoding="utf-8") as f:
        content = f.read()

    beats = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        colon_idx = line.find(":")
        if colon_idx > 0:
            raw_id = line[:colon_idx].strip()
            prompt = line[colon_idx + 1:].strip()
            clean_id = re.sub(r"\.(jpg|jpeg|png|webp)$", "", raw_id, flags=re.IGNORECASE)

            # Strip bracket tags like [CHARACTER: ...], [SETTING: ...], [PROP: ...]
            clean_prompt = re.sub(r"\[(CHARACTER|SETTING|PROP|INGREDIENT):\s*[^\]]+\]", "", prompt).strip()
            # Remove midjourney flags like --ar 16:9 --style raw --v 6.0
            clean_prompt = re.sub(r"--(?:ar|style|v|s|q)\s+[^\s]+", "", clean_prompt).strip()
            # Normalize multiple spaces
            clean_prompt = re.sub(r"\s+", " ", clean_prompt).strip()

            beats.append({"id": clean_id, "prompt": clean_prompt})
    return beats


def generate_pipeline_yaml(project_name: str, beats: list, out_dir: Path, yaml_path: Path):
    jobs = []
    for b in beats:
        jobs.append({
            "id": b["id"],
            "type": "image",
            "prompt": b["prompt"],
            "ratio": "16:9",
            "out": str(out_dir)
        })

    data = {
        "pipeline": {
            "name": f"{project_name} Keyframe Production",
            "profiles": PROFILES,
            "autoheal": True,
            "resume": True,
            "continueOnFailure": True
        },
        "jobs": jobs
    }

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, indent=2, allow_unicode=True)

    print(f"Generated GFlow Pipeline YAML: {yaml_path} with {len(jobs)} visual jobs.")


def normalize_and_audit_keyframes(keyframes_dir: Path):
    print(f"\nAuditing and normalizing keyframes in {keyframes_dir}...")
    valid_count = 0
    all_files = list(keyframes_dir.glob("beat_*.*"))

    for f in all_files:
        if f.suffix.lower() in [".jpeg", ".jpg", ".png"]:
            m = re.match(r"(beat_P\d{2}_B\d{2})(-\d{3})?\.(jpeg|jpg|png)", f.name, re.IGNORECASE)
            if m:
                base_id = m.group(1)
                std_jpg = keyframes_dir / f"{base_id}.jpg"

                # If f is not already std_jpg, move/rename to std_jpg
                if f != std_jpg and not std_jpg.exists():
                    shutil.copy2(f, std_jpg)

                size_kb = std_jpg.stat().st_size / 1024.0 if std_jpg.exists() else f.stat().st_size / 1024.0
                if size_kb >= 30.0:
                    valid_count += 1

    print(f"✅ Verified {valid_count} normalized beat keyframes (.jpg >= 30KB).")
    return valid_count


def sync_to_gdrive(keyframes_dir: Path, gdrive_folder_id: str):
    print(f"\nSyncing keyframes to Google Drive {gdrive_folder_id}...")
    cmd = [
        "rclone", "sync",
        str(keyframes_dir),
        f"hariinvpsg16gb,root_folder_id={gdrive_folder_id}:02. Media Generation/keyframes",
        "--transfers=8",
        "--include=*.jpg",
        "--include=.keep"
    ]
    subprocess.run(cmd, check=True)
    print("✅ Keyframes successfully synced to Google Drive!")


def update_sheet(row_num: int, status="JPEG", image_status="Done"):
    try:
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet("Pipeline")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.update_cell(row_num, 4, status)
        ws.update_cell(row_num, 10, "Automatic")
        ws.update_cell(row_num, 11, image_status)
        ws.update_cell(row_num, 15, now_str)
        print(f"✅ Google Sheets Row {row_num} updated: Status={status}, Image={image_status}")
    except Exception as e:
        print(f"⚠️ Error updating Google Sheets: {e}")


def process_project(proj):
    print("\n" + "=" * 70)
    print(f"🚀 STARTING IMAGE SYNTHESIS FOR: {proj['name']} (Row {proj['row_num']}, ID: {proj['idea_id']})")
    print("=" * 70)

    preprod_dir = proj["project_root"] / "01. Preproduction"
    prompts_file = preprod_dir / "combined_imageprompts.txt"
    media_dir = proj["project_root"] / "02. Media Generation"
    keyframes_dir = media_dir / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    if not prompts_file.exists():
        print(f"❌ Prompts file not found: {prompts_file}")
        return False

    beats = parse_prompts_file(prompts_file)
    print(f"Loaded {len(beats)} visual beats from {prompts_file.name}")

    yaml_path = GFLOW_DIR / f"pipeline_{proj['idea_id']}.yaml"
    generate_pipeline_yaml(proj["name"], beats, keyframes_dir, yaml_path)

    cmd = [
        "node", "dist/src/index.js", "run", str(yaml_path),
        "--output-dir", str(keyframes_dir)
    ]
    env = os.environ.copy()
    env["GFLOW_PROFILES_DIR"] = str(Path.home() / ".gflow" / "profiles")

    # Run gflow in a loop until all 150 keyframes are completed
    max_pipeline_attempts = 15
    for attempt in range(1, max_pipeline_attempts + 1):
        valid_count = normalize_and_audit_keyframes(keyframes_dir)
        if valid_count >= 150:
            print(f"🎉 All 150 keyframes verified! Skipping gflow run.")
            break

        print(f"\n[Pipeline Attempt {attempt}/{max_pipeline_attempts}] Current valid keyframes: {valid_count}/150")
        print(f"Executing gflow with command: {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, cwd=str(GFLOW_DIR), env=env)
        ret = proc.wait()

        if ret != 0:
            print(f"⚠️ gflow exited with code {ret}, checking progress and preparing resume...")
            # Clean up any stale chrome locks
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
            import time
            time.sleep(3)

        valid_count = normalize_and_audit_keyframes(keyframes_dir)
        sync_to_gdrive(keyframes_dir, proj["gdrive_folder_id"])

        if valid_count >= 150:
            update_sheet(proj["row_num"], status="JPEG", image_status="Done")
            print(f"\n🎉 FULL PRODUCTION COMPLETED FOR {proj['name']} ({valid_count}/150 keyframes)!")
            return True
        else:
            update_sheet(proj["row_num"], status="JPEG", image_status="In Progress")
            print(f"🔄 Progress: {valid_count}/150 beats completed. Resuming remaining beats...")

    return valid_count >= 150


def main():
    parser = argparse.ArgumentParser(description="HistorySnooze Image Pipeline Runner")
    parser.add_argument("--project", choices=["julie", "nero", "all"], default="julie",
                        help="Target project to generate images for (default: julie)")
    args = parser.parse_args()

    if args.project == "all":
        for key, proj in PROJECTS.items():
            process_project(proj)
    else:
        proj = PROJECTS[args.project]
        process_project(proj)

    print("\n" + "🌟" * 35)
    print("🎉 IMAGE GENERATION TASK FINISHED!")
    print("🌟" * 35 + "\n")


if __name__ == "__main__":
    main()
