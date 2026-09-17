#!/usr/bin/env python3
"""HistorySnooze State Backup (Doc 08). Rule <= 150 lines. Zero-Leak protected."""
import argparse, gzip, json, os, shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
MAP_FILE = BASE_DIR / "gdrive_folder_map.json"
SKIP_KEYWORDS = ("secret", "credential", "client_secret", "token", "password", "key", ".env", "__pycache__", ".pytest_cache", ".git", ".venv", "node_modules")

for p in [BASE_DIR / "00.codebases", BASE_DIR / "hsnooze.render"]:
    if str(p) not in sys.path and p.exists():
        sys.path.insert(0, str(p))

try:
    from retry_handler import retry_network_op
except ImportError:
    try:
        from network_retry import retry_network_op
    except ImportError:
        retry_network_op = lambda func=None, **_kw: func if func else (lambda f: f)


def is_secret_or_cache(path: Path) -> bool:
    """Zero-leak filter: returns True if path contains sensitive secrets or caches."""
    return any(k in str(path).lower() for k in SKIP_KEYWORDS)


def compress_database(db_path: Path, output_dir: Path, timestamp: str) -> Path:
    """Compresses SQLite DB into gzip snapshot: snapshot_<name>_<timestamp>.db.gz."""
    output_dir.mkdir(parents=True, exist_ok=True)
    gz_path = output_dir / f"snapshot_{db_path.stem}_{timestamp}.db.gz"
    tmp_db = output_dir / f"_tmp_{db_path.stem}_{timestamp}.db"
    source = db_path
    try:
        src, dst = sqlite3.connect(str(db_path)), sqlite3.connect(str(tmp_db))
        try:
            src.backup(dst)
            source = tmp_db
        finally:
            dst.close()
            src.close()
    except Exception:
        tmp_db.unlink(missing_ok=True)
        source = db_path
    try:
        with open(source, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    finally:
        if source == tmp_db:
            tmp_db.unlink(missing_ok=True)
    return gz_path


def resolve_token_path() -> Optional[Path]:
    """Resolves GDrive token path with environment and profile fallbacks."""
    if os.getenv("GDRIVE_TOKEN_PATH") and Path(os.getenv("GDRIVE_TOKEN_PATH")).exists():
        return Path(os.getenv("GDRIVE_TOKEN_PATH"))
    cands = [Path.home() / ".cloud-profiles/media/gdrive/token.json", Path.home() / ".cloud-profiles/media/token.json", BASE_DIR / ".secrets/token.json"]
    return next((c for c in cands if c.exists()), None)


def get_backup_folder_id(service=None) -> str:
    """Retrieves backup folder ID from map file, env var, or creates folder."""
    if MAP_FILE.exists():
        try:
            with open(MAP_FILE, "r", encoding="utf-8") as f:
                bid = json.load(f).get("_backup_folder_id")
                if bid: return bid
        except Exception: pass
    if os.getenv("GDRIVE_BACKUP_FOLDER_ID"): return os.getenv("GDRIVE_BACKUP_FOLDER_ID")
    folder_name = f"00.BACKUP_{BASE_DIR.name.upper()}"
    if service is not None:
        meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
        return service.files().create(body=meta, fields="id").execute().get("id", "created_folder_id")
    return f"mock_or_pending_{folder_name}"


@retry_network_op(max_retries=3, backoff_factor=2.0)
def upload_to_drive(service, file_path: Path, parent_id: str) -> str:
    """Uploads file to designated GDrive backup folder with self-healing retries."""
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(file_path), mimetype="application/octet-stream", resumable=True)
    meta = {"name": file_path.name, "parents": [parent_id]}
    return service.files().create(body=meta, media_body=media, fields="id").execute().get("id", "")


def execute_backup(dry_run: bool = False, snapshot_only: bool = False) -> int:
    """Executes state snapshotting, compression, and optional Google Drive sync."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dbs = [p for p in sorted(list(BASE_DIR.rglob("*.db")) + list(BASE_DIR.rglob("*.sqlite"))) if not is_secret_or_cache(p)]
    configs = [p for p in [MAP_FILE, BASE_DIR / "pipeline_schema.json"] if p.exists() and not is_secret_or_cache(p)]
    token_path = resolve_token_path()

    print(f"[*] HistorySnooze Auto-Backup (timestamp: {timestamp})")
    print(f"[*] Discovered {len(dbs)} database(s), {len(configs)} config map(s).")
    for db in dbs:
        print(f"    - DB: {db.relative_to(BASE_DIR)}")

    service = None
    if not (dry_run or snapshot_only) and token_path:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            creds = Credentials.from_authorized_user_file(str(token_path))
            service = build("drive", "v3", credentials=creds)
        except Exception as e:
            print(f"[!] Warning: OAuth credential loading failed ({e}). Falling back to local snapshot.")

    artifacts_dir = BASE_DIR / "artifacts"
    if dry_run or snapshot_only or service is None:
        reason = "dry-run" if dry_run else ("snapshot-only" if snapshot_only else ("auth-fallback" if token_path else "token not found"))
        print(f"[i] Plan ({reason}): target folder={get_backup_folder_id()}. Creating local snapshots...")
        for db in dbs:
            gz = compress_database(db, artifacts_dir, timestamp)
            print(f"    [+] Created snapshot: {gz.name} ({gz.stat().st_size} bytes)")
        print(f"[✔] Auto-Backup plan executed without crashing ({reason}).")
        return 0

    folder_id = get_backup_folder_id(service)
    for db in dbs:
        gz_path = compress_database(db, artifacts_dir, timestamp)
        fid = upload_to_drive(service, gz_path, folder_id)
        print(f"[✔] Uploaded DB snapshot: {gz_path.name} -> Drive ID: {fid}")
        gz_path.unlink(missing_ok=True)
    for cfg in configs:
        fid = upload_to_drive(service, cfg, folder_id)
        print(f"[✔] Synced Config Map: {cfg.name} -> Drive ID: {fid}")
    print(f"[✔] HistorySnooze backup completed successfully to folder {folder_id}!")
    return 0


def main():
    parser = argparse.ArgumentParser(description="HistorySnooze Google Drive State Backup Engine")
    parser.add_argument("--dry-run", action="store_true", help="Simulate backup plan without network upload")
    parser.add_argument("--snapshot", action="store_true", help="Create local compressed DB snapshots only")
    args = parser.parse_args()
    sys.exit(execute_backup(dry_run=args.dry_run, snapshot_only=args.snapshot))


if __name__ == "__main__":
    main()
