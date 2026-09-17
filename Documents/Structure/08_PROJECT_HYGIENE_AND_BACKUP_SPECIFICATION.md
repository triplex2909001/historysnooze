# 💾 FILE 8: TIÊU CHUẨN VỆ SINH MÃ NGUỒN, QUẢN TRỊ RÁC & CƠ CHẾ SAO LƯU GDRIVE ĐỘC LẬP TỪNG DỰ ÁN (08_PROJECT_HYGIENE_AND_BACKUP_SPECIFICATION.md)

> **Phiên bản:** 1.0 (Master Project Hygiene & Automated Backup Specification)
> **Áp dụng cho:** Toàn bộ các Dự án, Pipelines, Webhooks, Workflows và Trợ lý AI trên hệ thống (`vpsg16gb`, `HaRiDisk`, `Workspace`, `Telegram_Command_Center`, `NWL`).
> **Nguyên tắc bất biến (Iron Rule):** **MỖI DỰ ÁN BẮT BUỘC PHẢI SỞ HỮU DUY NHẤT 01 THƯ MỤC GOOGLE DRIVE BACKUP RIÊNG BIỆT** • Auto-Snapshot ≤ 7 ngày • Zero-Garbage • Rule ≤ 150 dòng/script backup.

---

## 📑 MỤC LỤC
1. [I. NGUYÊN TẮC BẮT BUỘC: 01 DỰ ÁN = 01 GDRIVE BACKUP FOLDER](#i-nguyên-tắc-bắt-buộc-01-dự-án--01-gdrive-backup-folder)
2. [II. CẤU TRÚC PHÂN CẤP THƯ MỤC BACKUP TRÊN GOOGLE DRIVE](#ii-cấu-trúc-phân-cấp-thư-mục-backup-trên-google-drive)
3. [III. MẪU SCRIPT TỰ ĐỘNG SAO LƯU CHUẨN (scripts/auto_backup.py ≤ 150 DÒNG)](#iii-mẫu-script-tự-động-sao-lưu-chuẩn-scriptsauto_backuppy--150-dòng)
4. [IV. QUY TRÌNH TÍCH HỢP NGAY KHI KHỞI TẠO BẤT KỲ DỰ ÁN MỚI NÀO](#iv-quy-trình-tích-hợp-ngay-khi-khởi-tạo-bất-kỳ-dự-án-mới-nào)
5. [V. BỘ TIÊU CHÍ KIỂM TOÁN VỆ SINH & SAO LƯU DÀNH CHO CỖ MÁY AUDIT](#v-bộ-tiêu-chí-kiểm-toán-vệ-sinh--sao-lưu-dành-cho-cỗ-máy-audit)
6. [VI. KỊCH BẢN LỆNH DỌN DẸP & SAO LƯU ĐỊNH KỲ (HYGIENE & BACKUP RUNBOOK)](#vi-kịch-bản-lệnh-dọn-dẹp--sao-lưu-định-kỳ-hygiene--backup-runbook)

---

## I. NGUYÊN TẮC BẮT BUỘC: 01 DỰ ÁN = 01 GDRIVE BACKUP FOLDER

Để chấm dứt vĩnh viễn tình trạng thất lạc dữ liệu, trôi dạt trạng thái (State Drift), mất database khi máy chủ gặp sự cố hoặc container bị hủy, hệ thống ban hành quy chế bất biến:

1. **Khóa cứng Định danh Thư mục Backup:**
   - Mỗi dự án khi sinh ra **BẮT BUỘC** phải được cấp phát 01 Thư mục Google Drive Backup chuyên dụng.
   - Thư mục này được định danh qua biến môi trường `GDRIVE_BACKUP_FOLDER_ID` hoặc khai báo trong file cấu hình `gdrive_folder_map.json` tại mục `"_backup_folder_id"`.
2. **Cấm dùng chung Thư mục Backup (Zero Cross-Backup):**
   - Tuyệt đối không sao lưu đè dữ liệu của Dự án A vào thư mục Backup của Dự án B.
   - Mỗi dự án chỉ đẩy dữ liệu vào đúng tài khoản Google Drive được gắn với Profile của dự án đó (ví dụ: `aleron.dt@gmail.com` cho NWL).
3. **Cơ chế Snapshot Tự Động:**
   - Mọi cơ sở dữ liệu SQLite (`pipeline.db`, `history.db`, state files) phải được đóng gói snapshot dạng nén `snapshot_YYYYMMDD_HHMMSS.db.gz` và tải lên Google Drive định kỳ tối thiểu 1 lần/tuần.

---

## II. CẤU TRÚC PHÂN CẤP THƯ MỤC BACKUP TRÊN GOOGLE DRIVE

Mỗi thư mục Backup của dự án trên Google Drive phải tuân thủ đúng cấu trúc 4 nhánh chuẩn sau:

```text
[Google Drive: TÊN_DỰ_ÁN_BACKUP_ROOT] (ID: GDRIVE_BACKUP_FOLDER_ID)
├── 01.Database_Snapshots/          # Chứa các bản sao lưu SQLite/State nén gzip (.db.gz)
│   ├── snapshot_20260820_000000.db.gz
│   └── snapshot_20260827_120000.db.gz
├── 02.Configs_And_Maps/             # Chứa bản sao các file JSON bản đồ, schema, routing
│   ├── gdrive_folder_map.json
│   └── pipeline_schema.json
├── 03.Templates_And_Assets/         # Chứa con dấu, chữ ký số, phôi hợp đồng, static files
│   ├── Signatures_Stamps/
│   └── Contract_Templates/
└── 04.Logs_Archive/                 # Chứa các file log cũ đã được nén xoay vòng (.log.gz)
    └── logs_2026_week_34.log.gz
```

---

## III. MẪU SCRIPT TỰ ĐỘNG SAO LƯU CHUẨN (`scripts/auto_backup.py` ≤ 150 DÒNG)

Mọi dự án phải tích hợp sẵn tệp script sao lưu tự động sau đây vào thư mục `scripts/auto_backup.py`:

```python
#!/usr/bin/env python3
"""
NWL & General Auto-Backup Engine (scripts/auto_backup.py)
Automates database snapshotting, gzip compression, and Google Drive upload.
Rule: File length <= 150 lines.
"""
import os
import sys
import gzip
import shutil
import json
from datetime import datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = Path(__file__).resolve().parent.parent
MAP_FILE = BASE_DIR / "gdrive_folder_map.json"

def resolve_token_path() -> Path:
    """Resolve token with multi-tier fallback."""
    if os.getenv("GDRIVE_TOKEN_PATH"):
        return Path(os.getenv("GDRIVE_TOKEN_PATH"))
    candidates = [
        Path.home() / ".cloud-profiles/nwl/gdrive/token.json",
        Path("/app/credentials/gdrive/token.json"),
        BASE_DIR / "credentials/gdrive/token.json"
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

def get_backup_folder_id(service) -> str:
    """Read backup folder id from map file or create dynamically."""
    if MAP_FILE.exists():
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "_backup_folder_id" in data:
                return data["_backup_folder_id"]
    # Fallback to env or create
    env_id = os.getenv("GDRIVE_BACKUP_FOLDER_ID")
    if env_id:
        return env_id
    # Create new backup root on Drive
    meta = {"name": f"00.BACKUP_{BASE_DIR.name.upper()}", "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=meta, fields="id").execute()
    return folder.get("id")

def upload_to_drive(service, file_path: Path, parent_id: str) -> str:
    """Uploads file to designated GDrive folder."""
    media = MediaFileUpload(str(file_path), mimetype="application/octet-stream", resumable=True)
    meta = {"name": file_path.name, "parents": [parent_id]}
    res = service.files().create(body=meta, media_body=media, fields="id").execute()
    return res.get("id")

def run_project_backup():
    """Executes database compression and full artifact snapshot."""
    token_path = resolve_token_path()
    if not token_path.exists():
        print(f"[-] GDrive token not found at {token_path}. Aborting backup.")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(token_path))
    service = build("drive", "v3", credentials=creds)
    backup_root_id = get_backup_folder_id(service)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Snapshot SQLite databases
    db_candidates = list(BASE_DIR.rglob("*.db")) + list(BASE_DIR.rglob("*.sqlite"))
    for db in db_candidates:
        if ".venv" in str(db) or "graft" in str(db):
            continue
        gz_name = f"snapshot_{db.stem}_{timestamp}.db.gz"
        gz_path = BASE_DIR / "artifacts" / gz_name
        gz_path.parent.mkdir(parents=True, exist_ok=True)
        with open(db, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        file_id = upload_to_drive(service, gz_path, backup_root_id)
        print(f"[✔] Database Snapshot uploaded: {gz_name} -> GDrive ID: {file_id}")
        gz_path.unlink(missing_ok=True)

    # 2. Sync JSON Maps & Configs
    if MAP_FILE.exists():
        map_id = upload_to_drive(service, MAP_FILE, backup_root_id)
        print(f"[✔] Config Map synced: {MAP_FILE.name} -> GDrive ID: {map_id}")

    print(f"\n🎉 Project Backup Completed Successfully at {datetime.now().isoformat()}!")

if __name__ == "__main__":
    run_project_backup()
```

---

## IV. QUY TRÌNH TÍCH HỢP NGAY KHI KHỞI TẠO BẤT KỲ DỰ ÁN MỚI NÀO

Bổ sung vào **Quy trình 6 Bước Khởi Tạo Dự Án** tại `00_TONG_QUAN.md (Phần VI)`:

* [ ] **Bước 2.1 (Cấp phát GDrive Backup):** Tạo thư mục `00.BACKUP_<TÊN_APP>` trên Google Drive của tài khoản chỉ định. Ghi `_backup_folder_id` vào `gdrive_folder_map.json`.
* [ ] **Bước 2.2 (Cài đặt Auto-Backup Script):** Sao chép mẫu `scripts/auto_backup.py` vào thư mục dự án và thiết lập quyền thực thi `chmod +x`.
* [ ] **Bước 2.3 (Thiết lập Lưới Vệ Sinh .gitignore):** Chặn đứng toàn bộ tệp tạm `.db.gz`, `.log.gz`, `temp/`, `.pytest_cache/`.

---

## V. BỘ TIÊU CHÍ KIỂM TOÁN VỆ SINH & SAO LƯU DÀNH CHO CỖ MÁY AUDIT

Khi cỗ máy kiểm toán (Auditing Machine / Fast Audit Playbook trong File 06) chạy kiểm tra định kỳ, nó sẽ **tự động kiểm tra 4 tiêu chí sau**:

| Mã Tiêu chí | Hạng mục kiểm tra | Tiêu chuẩn ĐẠT (PASS) ✅ | Vi phạm CẦN SỬA (FAIL) ❌ | Mức độ |
| :--- | :--- | :--- | :--- | :--- |
| **BKP-01** | **Khai báo GDrive Backup** | Có `_backup_folder_id` trong `gdrive_folder_map.json` hoặc biến môi trường `GDRIVE_BACKUP_FOLDER_ID` | Không có thư mục backup Drive riêng | 🚨 **CRITICAL** |
| **BKP-02** | **Script Sao lưu Sẵn sàng** | Tồn tại `scripts/auto_backup.py` (≤ 150 dòng) hoạt động không lỗi | Thiếu script sao lưu hoặc script > 150 dòng | ⚠️ **HIGH** |
| **BKP-03** | **Độ Tươi của Snapshot** | Có bản snapshot database tải lên Drive trong vòng ≤ 7 ngày qua | Quá 7 ngày chưa có snapshot mới | ⚠️ **HIGH** |
| **BKP-04** | **Vệ sinh Rác & Log** | Toàn bộ log ≤ 10MB, 0 file rác `__pycache__`, `00.INBOX` sạch 100% | File log > 10MB, còn rác trong `00.INBOX` | ⚠️ **MEDIUM** |

---

## VI. KỊCH BẢN LỆNH DỌN DẸP & SAO LƯU ĐỊNH KỲ (HYGIENE & BACKUP RUNBOOK)

Chạy kịch bản 3 bước này khi kiểm tra hoặc bảo dưỡng định kỳ:

```bash
# 1. Chạy Auto-Backup tức thì
python3 scripts/auto_backup.py

# 2. Dọn rác cache và thu hồi dung lượng cục bộ
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.tmp" -delete 2>/dev/null || true

# 3. Quét kiểm tra độ tươi của backup và rác log
ls -lh artifacts/ logs/ 2>/dev/null || true
```
