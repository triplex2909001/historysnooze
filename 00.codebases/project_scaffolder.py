"""
HistorySnooze: Master Project Scaffolder & Hierarchy Initializer
Module: project_scaffolder.py
SSOT-compliant with ARCHITECTURE.md, 00_TONG_QUAN.md, and Gatekeepers GK0-GK4.
Rule <= 150 lines strictly enforced.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Optional


def scaffold_project_directories(
    project_root: Path,
    gdrive_folder_id: Optional[str] = None,
    rclone_remote: str = "hariinvpsg16gb"
) -> Dict[str, Path]:
    """
    Scaffolds the mandatory folder hierarchy for a HistorySnooze episode
    on local VPS and ensures identical structure on Google Drive:
    ├── 01. Preproduction/
    ├── 02. Media Generation/
    │   ├── audio/
    │   ├── keyframes/
    │   └── combined/
    └── 03. Final Production/
    """
    project_root = Path(project_root).resolve()

    # Mandatory Local Directory Paths
    preprod_dir = project_root / "01. Preproduction"
    media_dir = project_root / "02. Media Generation"
    audio_dir = media_dir / "audio"
    keyframes_dir = media_dir / "keyframes"
    combined_dir = media_dir / "combined"
    final_dir = project_root / "03. Final Production"

    # Create local directories
    all_dirs = [project_root, preprod_dir, media_dir, audio_dir, keyframes_dir, combined_dir, final_dir]
    for d in all_dirs:
        d.mkdir(parents=True, exist_ok=True)
        keep_file = d / ".keep"
        if not keep_file.exists() and d != project_root:
            keep_file.touch()

    print(f"✅ Local Scaffolding complete at:\n📁 {project_root}")
    print("   ├── 📁 01. Preproduction/")
    print("   ├── 📁 02. Media Generation/")
    print("   │   ├── 📁 audio/")
    print("   │   ├── 📁 keyframes/")
    print("   │   └── 📁 combined/")
    print("   └── 📁 03. Final Production/")

    # Sync Hierarchy to Google Drive if ID provided
    if gdrive_folder_id:
        print(f"\n🚀 Syncing directory scaffold to Google Drive (ID: {gdrive_folder_id})...")
        sub_list = [
            ("01. Preproduction", preprod_dir),
            ("02. Media Generation/audio", audio_dir),
            ("02. Media Generation/keyframes", keyframes_dir),
            ("02. Media Generation/combined", combined_dir),
            ("03. Final Production", final_dir)
        ]
        for sub_name, local_sub in sub_list:
            cmd = [
                "rclone", "sync",
                str(local_sub),
                f"{rclone_remote},root_folder_id={gdrive_folder_id}:{sub_name}",
                "--transfers=4"
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                print(f"   ✅ GDrive scaffold verified: {sub_name}")
            except subprocess.CalledProcessError as e:
                print(f"   ⚠️ Warning syncing {sub_name} to GDrive: {e.stderr.decode().strip()}")

    return {
        "root": project_root,
        "preproduction": preprod_dir,
        "audio": audio_dir,
        "keyframes": keyframes_dir,
        "combined": combined_dir,
        "final_production": final_dir
    }
