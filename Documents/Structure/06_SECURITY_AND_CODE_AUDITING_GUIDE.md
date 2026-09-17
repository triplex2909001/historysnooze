# 🛡️ FILE 6: SỔ TAY KIỂM TOÁN BẢO MẬT & CHẤT LƯỢNG MÃ NGUỒN (06_SECURITY_AND_CODE_AUDITING_GUIDE.md)

> **Phiên bản:** 1.0 (Master Security & Code Audit Specification)
> **Áp dụng cho:** Toàn bộ hệ thống Dự án, Pipelines & Automation (`vpsg16gb`, `HaRiDisk`, `Workspace`, `Telegram_Command_Center`).
> **Mục đích sử dụng:** Sử dụng để tự động kiểm toán (Automated Auditing) sau mỗi lần build/refactor, hoặc kiểm tra định kỳ (Periodic Health Check) nhằm xác định mức độ an toàn credentials, tính bảo mật mã nguồn và sự tuân thủ kiến trúc chuẩn.
> **Nguyên tắc tối thượng:** Zero-Trust • Zero-Leak • Zero-Cross-Contamination • Single-Responsibility Submodules (≤ 150 dòng) • Zero-Idle Memory.

---

## 📑 MỤC LỤC
1. [I. TỔNG QUAN VỀ KHUNG KIỂM TOÁN (AUDIT FRAMEWORK)](#i-tổng-quan-về-khung-kiểm-toán-audit-framework)
2. [II. BỘ TIÊU CHÍ KIỂM TOÁN AN TOÀN CREDENTIALS & SECRETS (TRỤ CỘT BẢO MẬT)](#ii-bộ-tiêu-chí-kiểm-toán-an-toàn-credentials--secrets-trụ-cột-bảo-mật)
3. [III. BỘ TIÊU CHÍ KIỂM TOÁN KIẾN TRÚC & CHẤT LƯỢNG CODE (TRỤ CỘT CODEBASE)](#iii-bộ-tiêu-chí-kiểm-toán-kiến-trúc--chất-lượng-code-trụ-cột-codebase)
4. [IV. BẢNG TIÊU CHUẨN ĐÁNH GIÁ ĐẠT / KHÔNG ĐẠT (PASS/FAIL RUBRICS)](#iv-bảng-tiêu-chuẩn-đánh-giá-đạt--không-đạt-passfail-rubrics)
5. [V. KỊCH BẢN LỆNH KIỂM TOÁN TỰ ĐỘNG TỨC THÌ (FAST AUDIT PLAYBOOK)](#v-kịch-bản-lệnh-kiểm-toán-tự-động-tức-thì-fast-audit-playbook)
6. [VI. BIỂU MẪU XUẤT BÁO CÁO KIỂM TOÁN CHUẨN (AUDIT REPORT TEMPLATE)](#vi-biểu-mẫu-xuất-báo-cáo-kiểm-toán-chuẩn-audit-report-template)

---

## I. TỔNG QUAN VỀ KHUNG KIỂM TOÁN (AUDIT FRAMEWORK)

Khung kiểm toán được thiết kế thành **2 Trụ Cột Độc Lập** nhưng phối hợp chặt chẽ:

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 🛡️ TRỤ CỘT 1: KIỂM TOÁN BẢO MẬT, SECRETS & CÁCH LY MÔI TRƯỜNG              │
│    1. Zero Plaintext Secrets tại Workspace Root                            │
│    2. Khóa cứng phân định Bot Tokens (Cách ly NWL & Command Center)       │
│    3. Pre-Commit / Pre-Push Secret Scanning (Gitleaks, TruffleHog)         │
│    4. DevContainer Sandbox & Quyền Non-Root (UID 1000)                     │
│    5. Tuân thủ Hiến pháp AGENTS.md (Strict Email Draft, Clean 00.INBOX)    │
├────────────────────────────────────────────────────────────────────────────┤
│ 📐 TRỤ CỘT 2: KIỂM TOÁN KIẾN TRÚC MÃ NGUỒN & HIỆU NĂNG VẬN HÀNH            │
│    6. Định mức tệp tin ≤ 150 dòng (Chống Context Rot / AI Hallucination)   │
│    7. Tính toàn vẹn của 5 Chốt chặn Gatekeepers (GK0 – GK4)               │
│    8. Bộ kiểm thử tự động (Pytest Test Suite Coverage ≥ 95%)               │
│    9. Quản lý tài nguyên Zero-Idle Memory (On-demand Ephemeral Containers) │
│    10. Truy vấn ngữ cảnh AI Siêu tốc (Codebase Memory Graph < 1ms)         │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## II. BỘ TIÊU CHÍ KIỂM TOÁN AN TOÀN CREDENTIALS & SECRETS (TRỤ CỘT BẢO MẬT)

### 1. Tiêu chí 1: Zero Plaintext Secrets in Workspace Root (Tuyệt đối không lưu Secrets thô ở thư mục gốc)
* **Yêu cầu kiểm tra:** Thư mục làm việc / root của dự án tuyệt đối không được chứa bất kỳ tệp tin nhạy cảm ở dạng plaintext:
  * ❌ Cấm: `.agents_vault.json`, `user_oauth2.json`, `cookies.txt`, `client_secret.json`, `.env`, `service_account.json`.
  * ✅ Chuẩn: Toàn bộ thông tin đăng nhập phải được chuyển về lưu trữ an toàn tại `~/.cloud-profiles/<tên_ứng_dụng>/` với phân quyền `chmod 600 / 700`, hoặc đóng gói mã hóa AES-256 (`project_vault.enc`) và giải mã in-memory vào `/dev/shm/.vault`.
* **Quy tắc `.gitignore` bắt buộc:**
  ```gitignore
  # Secrets & Vaults
  *.env
  *.json
  !package.json
  !tsconfig.json
  !devcontainer.json
  *.enc
  *.pem
  *.key
  cookies.txt
  .agents_vault.json
  user_oauth2.json
  ```

### 2. Tiêu chí 2: Khóa Cứng Phân Định Telegram Bot Token (Hiến pháp AGENTS.md)
* **Yêu cầu kiểm tra:** Cấm tuyệt đối việc dùng chéo hoặc ghi đè Bot Token / Chat ID giữa các hệ thống:
  1. **Hệ thống Newway Logistics (NWL):**
     * **BẮT BUỘC VÀ DUY NHẤT:** `@newway_mcp_Bot` (Bot ID: `8944836049`, nạp từ `~/.cloud-profiles/nwl/telegram/bot_token.txt`).
     * Chỉ dùng cho nghiệp vụ logistics, hợp đồng, báo cáo NWL.
  2. **Hệ thống Telegram Command Center (Media & Cloud Runners):**
     * **BẮT BUỘC VÀ DUY NHẤT:** `@youtube2drive_Bot` (Bot ID: `8798886722`, nạp từ `~/.cloud-profiles/telegram_command_center/telegram/telegram_config.json`).
     * Dùng cho Command Center, GitHub Actions runner repo-01 $\rightarrow$ repo-09, Cloudflare Edge Relay.
  3. **Hệ thống HanaAssistant (Gia sư AI Bé Hana):**
     * **BẮT BUỘC VÀ DUY NHẤT:** `@hanalearningBot` (Bot ID: `8903373140`, nạp từ `~/.cloud-profiles/hana_assistant/telegram/bot_token.txt`).
     * **Nhóm đích duy nhất:** Nhóm `HaRiEdu` (`chat_id: -1003709159190`), Topic `Assistant Report` (`thread_id: 3`).
* **QUY TẮC BẮT BUỘC KHI THIẾU HOẶC LỖI CẤU HÌNH (PERMISSION PROTOCOL):**
  * Tuyệt đối cấm fallback sang bot token của container khác.
  * Nếu container chưa có bot token hoặc chat_id, AI Agent **BẮT BUỘC PHẢI HỎI TRỰC TIẾP USER ĐỂ XIN PHÉP VÀ XIN THÔNG TIN**.
* **Quy tắc quét trong mã nguồn & test:**
  * Không được hardcode chuỗi token thật trong các file `tests/`. Các test case giả lập buộc phải dùng token mock (ví dụ: `BOT_ID:MOCK_TOKEN_PLACEHOLDER`).

### 3. Tiêu chí 3: DevContainer Sandbox & Cô Lập Quyền Hạn
* **Yêu cầu kiểm tra:** Môi trường thực thi container / sandbox phải đảm bảo:
  * ✅ `remoteUser`: Phải là user không có quyền root (`vscode` hoặc `appuser` với UID/GID `1000:1000`). Cấm chạy bằng `root`.
  * ✅ `security_opt: ["no-new-privileges:true"]`.
  * ✅ `cap_drop: ["ALL"]` (Hủy bỏ mọi Linux capabilities nhạy cảm).
  * ✅ Mount `tmpfs: /dev/shm:size=64m` để chứa secrets tạm trong RAM.
  * ✅ Tham số `--rm` được cấu hình để tự động hủy container giải phóng tài nguyên.

### 4. Tiêu chí 4: Tuân Thủ Hiến Pháp Tương Tác Email & Google Drive
* **Email:** Đối với mọi tài khoản email, Agent **CHỈ ĐƯỢC TẠO THƯ NHÁP (`service.users().drafts().create()`)**, tuyệt đối không tự động gửi đi.
* **Google Drive `00.INBOX`:** Xóa sạch toàn bộ file trong `00.INBOX` (`1pSNyY3oSD1LNkkMt53iozEdqNd8xPvFn`) ngay sau khi hoàn tất trích xuất để tránh đọc trùng lặp.

---

## III. BỘ TIÊU CHÍ KIỂM TOÁN KIẾN TRÚC & CHẤT LƯỢNG CODE (TRỤ CỘT CODEBASE)

### 5. Tiêu chí 5: Quy Chuẩn Độ Dài Tệp Tin (File Length Constraint ≤ 150 Dòng)
* **Yêu cầu kiểm tra:** Tất cả các tệp mã nguồn Python/JavaScript/Shell phục vụ logic nghiệp vụ **phải có độ dài $\le 150$ dòng**.
* **Mục đích:** Đảm bảo mã nguồn đạt chuẩn Đơn nhiệm (Single Responsibility), hỗ trợ AI nạp 100% ngữ cảnh vào token window mà không bị cắt xén (Truncation) hoặc thoái hóa ngữ cảnh (Context Rot).
* **Quy tắc phân rã (Modularization):**
  * Tệp xử lý Stream/Media lớn $\rightarrow$ Tách thành: `scraper.py`, `downloader.py`, `splitter.py`, `publisher.py`, `qc_validator.py`.
  * Tệp điều phối Pipeline $\rightarrow$ Tách thành: `job_dispatcher.py`, `task_executor.py`, `ledger_sync.py`.

### 6. Tiêu chí 6: Tính Toàn Vẹn Của 5 Chốt Chặn Gatekeepers (GK0 – GK4)
* **Yêu cầu kiểm tra:** Dự án bắt buộc phải có tệp khai báo **`GATEKEEPERS.md`** tại thư mục gốc và mã nguồn phải triển khai đầy đủ 5 tầng kiểm soát theo đúng Domain của dự án:
  * **GK0 (Ingress & Distributed Lock):** Chống chạy trùng lặp giữa các máy chủ / runners, bảo vệ xác thực cổng vào.
  * **GK1 (Raw Input Validation & Clean Inbox):** Thẩm định tệp đầu vào, vệ sinh dữ liệu, xóa sạch `00.INBOX` sau khi trích xuất.
  * **GK2 (Processing Integrity & Modularity):** Kiểm tra tính toàn vẹn chuỗi logic/placeholder, đảm bảo file $\le 150$ dòng.
  * **GK3 (Output Compliance & Safety):** Tuân thủ chính sách cốt lõi của Domain (Email Drafts Only, EBU R128, JSON Schema).
  * **GK4 (Ledger Sync & Dead-Letter Alert):** Ghi nhận trạng thái hoàn tất vào Database / Google Drive và bắn cảnh báo sự cố về Telegram.

### 7. Tiêu chí 7: Tỷ Lệ Bao Phủ Của Bộ Kiểm Thử (Pytest Test Suite)
* **Yêu cầu kiểm tra:**
  * Số lượng test case phải bao phủ toàn bộ: Vault Config, Gatekeepers Integrity, Downloader & Splitter Logic, Adversarial Injection Resistance.
  * Tỷ lệ Passed: $\ge 95\%$.
  * **Zero Failure** đối với các test case liên quan đến rò rỉ bảo mật (Zero-Leak Tests).

### 8. Tiêu chí 8: Hiệu Năng Vận Hành & Tiết Kiệm Bộ Nhớ (Zero-Idle Memory)
* **Yêu cầu kiểm tra:**
  * Không duy trì các daemon nền nặng nề gây tốn RAM khi không có job (0 MB RAM / 0% CPU khi IDLE).
  * Bộ đệm tiếp nhận được ủy quyền cho **Cloudflare Worker + D1**.
  * Script TUI Visualizer (`monitor.py`) và SQLite `pipeline.db` thực thi nhanh, tiêu thụ $\le 25\text{MB}$ RAM và giải phóng tức thì.

---

## IV. BẢNG TIÊU CHUẨN ĐÁNH GIÁ ĐẠT / KHÔNG ĐẠT (PASS/FAIL RUBRICS)

| STT | Hạng mục kiểm toán | Tiêu chuẩn ĐẠT (PASS) ✅ | Vi phạm CẦN SỬA (FAIL) ❌ | Mức độ nghiêm trọng |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Plaintext Secrets tại Root** | Không có file credentials/vault thô ở root | Tồn tại `.agents_vault.json`, `cookies.txt`, `.env` | 🚨 **CRITICAL (Chặn Build)** |
| **2** | **Phân định Telegram Token** | Token NWL và Token Command Center biệt lập 100% | Dùng chung token hoặc lẫn lộn cấu hình | 🚨 **CRITICAL (Chặn Build)** |
| **3** | **Hardcoded Tokens trong Tests** | Sử dụng token mock dạng giả định | Chứa chuỗi token thật trong file test | 🚨 **CRITICAL (Chặn Push)** |
| **4** | **Quyền Hạn DevContainer** | `remoteUser: "vscode"` (UID 1000) | `remoteUser: "root"` | ⚠️ **HIGH** |
| **5** | **Độ dài tệp tin mã nguồn** | 100% tệp logic nghiệp vụ $\le 150$ dòng | Tồn tại file $> 150$ dòng (400 - 1100 dòng) | ⚠️ **MEDIUM** |
| **6** | **Chốt chặn Gatekeepers** | Đầy đủ 5 tầng GK0 $\rightarrow$ GK4 | Thiếu chốt chặn hoặc bỏ qua kiểm định | ⚠️ **HIGH** |
| **7** | **Kết quả Pytest Suite** | 100% Zero-Leak tests PASSED, tỷ lệ chung $\ge 95\%$ | Failed các test case bảo mật | 🚨 **CRITICAL** |
| **8** | **Nguyên tắc Email Drafts** | Chỉ gọi `drafts().create()` | Gọi `messages().send()` tự động | 🚨 **CRITICAL** |
| **9** | **Dọn dẹp `00.INBOX`** | Xóa sạch file sau khi xử lý xong | Để lại file rác gây đọc trùng | ⚠️ **MEDIUM** |
| **10** | **GDrive Backup & Snapshot** | Có thư mục Backup Drive riêng + snapshot $\le 7$ ngày ([File 08](file:///home/vpsg16gb/Documents/Structure/08_PROJECT_HYGIENE_AND_BACKUP_SPECIFICATION.md)) | Không có folder backup hoặc thiếu snapshot | 🚨 **CRITICAL** |

---

## V. KỊCH BẢN LỆNH KIỂM TOÁN TỰ ĐỘNG TỨC THÌ (FAST AUDIT PLAYBOOK)

Mỗi khi vừa build xong tính năng mới, hoặc định kỳ kiểm tra sức khỏe hệ thống, hãy thực hiện kịch bản 5 bước sau trong Terminal:

```bash
# ==============================================================================
# BƯỚC 1: QUÉT RÒ RỈ SECRETS & KHÓA BẢO MẬT (ZERO-LEAK SCAN)
# ==============================================================================
# 1.1. Quét tìm tệp secrets thô còn sót tại thư mục gốc
find . -maxdepth 1 -name "*.json" -not -name "package.json" -not -name "tsconfig.json"
find . -maxdepth 1 -name "*.env" -o -name "cookies.txt"

# 1.2. Quét tìm token thật bị hardcode trong mã nguồn
grep -rnE "[0-9]{9,11}:[A-Za-z0-9_-]{35}" . --exclude-dir={.git,.venv,__pycache__}

# ==============================================================================
# BƯỚC 2: KIỂM TOÁN ĐỘ DÀI TỆP TIN (FILE LENGTH COMPLIANCE <= 150 LINES)
# ==============================================================================
# Liệt kê tất cả các file Python vượt quá 150 dòng
find . -maxdepth 3 -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" -exec wc -l {} + | sort -rn | awk '$1 > 150 {print $0}'

# ==============================================================================
# BƯỚC 3: CHẠY TOÀN BỘ BỘ TEST SUITE KIỂM ĐỊNH (PYTEST ADVERSARIAL SUITE)
# ==============================================================================
pytest --tb=short

# ==============================================================================
# BƯỚC 4: KIỂM TRA PHÂN QUYỀN CONTAINER & DEVCONTAINER
# ==============================================================================
grep -rn '"remoteUser"' .devcontainer/devcontainer.json
grep -rn 'cap_drop' docker-compose.yml

# ==============================================================================
# BƯỚC 5: XÁC MINH BỘ NHỚ & TRẠNG THÁI HIỂN THỊ TUI (MONITOR)
# ==============================================================================
python3 monitor.py
```

---

## VI. BIỂU MẪU XUẤT BÁO CÁO KIỂM TOÁN CHUẨN (AUDIT REPORT TEMPLATE)

Khi hoàn tất kiểm toán, AI hoặc Kỹ sư kiểm định xuất báo cáo theo cấu trúc chuẩn sau:

```markdown
# 🏛️ BÁO CÁO KIỂM TOÁN DỰ ÁN: [TÊN DỰ ÁN]
> **Ngày kiểm toán:** [YYYY-MM-DD HH:MM]
> **Người / Agent thực hiện:** [Tên Agent / Antigravity]
> **Căn cứ đánh giá:** Bộ tiêu chuẩn [06_SECURITY_AND_CODE_AUDITING_GUIDE.md](file:///home/vpsg16gb/Documents/Structure/06_SECURITY_AND_CODE_AUDITING_GUIDE.md)

---

### 1. TỔNG KẾT KẾT QUẢ KIỂM TOÁN
* 🛡️ **Bảo mật & Secrets:** [✅ PASSED / ❌ FAILED] ([Số leaks] rò rỉ phát hiện)
* 🤖 **Khóa Cứng Bot Token:** [✅ CHUẨN ĐỊNH / ❌ VI PHẠM]
* 📐 **Độ Dài Tệp Tin (≤ 150 dòng):** [✅ 100% TUÂN THỦ / ⚠️ CÒN [N] FILES QUÁ DÒNG]
* 🧪 **Kiểm thử Tự động (Pytest):** [Số tests PASS]/[Tổng tests] ([Tỷ lệ]%)
* ⚡ **Mức Tiêu Thụ RAM:** [✅ ZERO-IDLE MEMORY / ⚠️ RUNNING DAEMON]

---

### 2. CHI TIẾT CÁC LỖ HỔNG & ĐIỂM VI PHẠM CẦN XỬ LÝ (NẾU CÓ)
1. **[Tên vi phạm 1]:** [Mô tả chi tiết và đường dẫn tệp `file.py:Lxx`]
   * *Biện pháp khắc phục:* [Giải pháp cụ thể]
2. **[Tên vi phạm 2]:** ...

---

### 3. HÀNH ĐỘNG KHẮC PHỤC NGAY LẬP TỨC (REMEDIATION PLAN)
- [ ] Hành động 1: ...
- [ ] Hành động 2: ...
```
