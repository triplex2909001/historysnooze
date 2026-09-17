"""
HISTORYSNOOZE: DRIVE & SHEET SYNCHRONIZER
Module: drive_sync.py
SSOT-compliant with 06_PIPELINE_AUTOMATION_SPEC.md.
Rule <= 150 lines strictly enforced.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SERVICE_ACCOUNT_FILE = "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/marketingtools/service_account.json"
SPREADSHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
ROOT_FOLDER_ID = "179tF8VKOrd0mVdGUiFO4YOfpNMzj_C8k"
PREPROD_FOLDER_ID = "1q7gWW30eiMCqbUdc58K-fJBs-Rm0i96g"

# Explicit mapping of pre-created Drive files for in-place quota-free update
DRIVE_FILE_MAP = {
    "combined_imageprompts.txt": ["1VQA4lQbf1BiRolL_O_2-p3n5bzZlHAcf", "1c9PMk9sCB-hNGi-mT2YoytZhOBUbmw6j"],
    "script_full.md": ["1_Gxh2FJ-t2xgKX5G7z0PXY7u4PyVv3P6"],
    "metadata.json": ["1Qx77VT6RI9SjOfBRUDXVaCXGzw0zdg8W"],
    "outline.json": ["1PYaYAlK2oZvynW8uqqVUbgiXcFNL0AFl"],
    "Script - Julia Domna.docx": ["1YQL7fZXItOIbdyXSoPGzRnfmMH5h7G-g"],
    "Outline - Julia Domna.docx": ["1ng6w9I8q869c1HC8CV1N6L8LAQx-MXvk"]
}


def get_drive_and_sheets_services():
    """Create authenticated Google Drive and Google Sheets service clients."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
    )
    drive_service = build("drive", "v3", credentials=creds)
    sheets_service = build("sheets", "v4", credentials=creds)
    return drive_service, sheets_service


def sync_all_artifacts_to_drive(output_dir: Path) -> Dict[str, str]:
    """Upload all preproduction files in-place to Drive and update Google Sheets."""
    drive_service, sheets_service = get_drive_and_sheets_services()
    uploaded_links = {}

    mime_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json"
    }

    for fname, file_ids in DRIVE_FILE_MAP.items():
        fpath = output_dir / fname
        if not fpath.exists():
            print(f"Warning: Local file missing: {fname}")
            continue

        ext = fpath.suffix
        mtype = mime_types.get(ext, "application/octet-stream")
        media = MediaFileUpload(str(fpath), mimetype=mtype, resumable=True)

        for fid in file_ids:
            res = drive_service.files().update(
                fileId=fid,
                media_body=media,
                fields="id, name, webViewLink"
            ).execute()
            if fname not in uploaded_links:
                uploaded_links[fname] = res.get("webViewLink", "")
            print(f" [UPDATED IN DRIVE] {fname} (ID: {fid})")

    # Update Google Sheets Pipeline Row 10
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_range = "Pipeline!A10:O10"
    row_values = [
        "id_1f21ak",
        "Julia Domna",
        "Julia Domna: The Woman Who Ruled Rome from the Shadows - Her Secret Gripped an Empire",
        "JPEG",
        f"https://drive.google.com/drive/folders/{ROOT_FOLDER_ID}",
        "https://docs.google.com/document/d/1ng6w9I8q869c1HC8CV1N6L8LAQx-MXvk/edit?usp=drivesdk",
        "https://docs.google.com/document/d/1YQL7fZXItOIbdyXSoPGzRnfmMH5h7G-g/edit?usp=drivesdk",
        "GHA",
        "Done",
        "Automatic",
        "JPEG",
        "GHA",
        "",
        "",
        now_str
    ]

    sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=update_range,
        valueInputOption="USER_ENTERED",
        body={"values": [row_values]}
    ).execute()
    print(" [UPDATED GOOGLE SHEET] Tab 'Pipeline', Row 10 updated to 'Done'")

    return uploaded_links
