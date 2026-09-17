"""
HistorySnooze Script Producer - Network Clients (Google Sheets & Gemini)
Module: network_clients.py
Rule <= 150 lines compliant. Wrapped with universal @retry_network_op.
"""

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional

from retry_handler import retry_network_op

logger = logging.getLogger("hsnooze.script_producer.network")


@retry_network_op(max_retries=3, backoff_factor=2.0, exceptions=(Exception,))
def call_gemini_api(
    prompt: str,
    model: str = "gemini-1.5-pro",
    api_key: Optional[str] = None,
    timeout: float = 30.0,
) -> str:
    """Invokes Gemini REST API with automatic exponential retry."""
    key = (
        api_key
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )
    if not key:
        logger.info("No Gemini API key detected in environment; skipping network call.")
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
        candidates = result.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"]
        return ""


@retry_network_op(max_retries=3, backoff_factor=2.0, exceptions=(Exception,))
def fetch_pending_rows_from_sheets(
    spreadsheet_id: Optional[str] = None,
    worksheet_name: str = "Pipeline",
    credentials_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Scans Google Sheets for pending pipeline rows with automatic retry."""
    sheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEET_ID")
    cred_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not sheet_id or not cred_path or not os.path.exists(cred_path):
        logger.info("Google Sheets credentials/sheet_id not configured; returning empty list.")
        return []

    try:
        import gspread
        gc = gspread.service_account(filename=cred_path)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        return [r for r in records if str(r.get("Status", "")).strip().lower() == "pending"]
    except ImportError:
        logger.warning("gspread package not installed.")
        return []


@retry_network_op(max_retries=3, backoff_factor=2.0, exceptions=(Exception,))
def update_row_status_in_sheets(
    row_id: str,
    status: str = "Script",
    spreadsheet_id: Optional[str] = None,
    worksheet_name: str = "Pipeline",
    credentials_path: Optional[str] = None,
) -> bool:
    """Updates a pipeline row's status in Google Sheets with automatic retry."""
    sheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEET_ID")
    cred_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not sheet_id or not cred_path or not os.path.exists(cred_path):
        logger.info(f"Sheets credentials offline: simulated updating row {row_id} to status '{status}'.")
        return True

    try:
        import gspread
        gc = gspread.service_account(filename=cred_path)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(worksheet_name)
        cell = worksheet.find(row_id)
        if cell:
            status_col = 3
            worksheet.update_cell(cell.row, status_col, status)
            return True
        return False
    except ImportError:
        logger.warning("gspread package not installed.")
        return False


def generate_script_with_gemini(
    character_name: str, topic: str, api_key: Optional[str] = None
) -> str:
    """Generates 15-part voiceover script using Gemini network client."""
    prompt = (
        f"Generate a 15-part contemplative bedtime documentary script for {character_name} on topic: {topic}. "
        "Strictly 10 beats per part, formatted with '## Part XX: Title'."
    )
    return call_gemini_api(prompt, api_key=api_key)
