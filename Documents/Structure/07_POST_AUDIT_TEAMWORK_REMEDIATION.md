# 🚀 FILE 7: HƯỚNG DẪN TÁC CHIẾN & MẪU LỆNH TEAMWORK PREVIEW CẢI TẠO DỰ ÁN HẬU KIỂM TOÁN (07_POST_AUDIT_TEAMWORK_REMEDIATION.md)

> **Phiên bản:** 1.0 (Master Post-Audit Teamwork Remediation Specification)
> **Áp dụng cho:** Toàn bộ hệ thống Dự án, Pipelines & Automation (`vpsg16gb`, `HaRiDisk`, `Workspace`, `Telegram_Command_Center`, `NWL`).
> **Mục đích sử dụng:** Đóng vai trò là cẩm nang hướng dẫn tác chiến và khung mẫu lệnh `/teamwork-preview` chuẩn hoá, được kích hoạt ngay sau khi có Báo cáo Kiểm toán theo [06_SECURITY_AND_CODE_AUDITING_GUIDE.md](file:///home/vpsg16gb/Documents/Structure/06_SECURITY_AND_CODE_AUDITING_GUIDE.md) nhằm tự động hoá 100% quá trình sửa lỗi, tái cấu trúc mã nguồn, cô lập bảo mật và đưa dự án về chuẩn kiến trúc Zero-VPS Solution.
> **Nguyên tắc cốt lõi:** Zero-Trust • Zero-Leak (RAM-Only Vault) • Rule ≤ 150 dòng/file • Zero-Idle Consumption (0 MB RAM khi nghỉ) • 5 Tầng Chốt chặn Gatekeepers.

---

## 📑 MỤC LỤC
1. [I. TỔNG QUAN VỀ CƠ CHẾ CHUYỂN GIAO HẬU KIỂM TOÁN (POST-AUDIT HANDOFF)](#i-tổng-quan-về-cơ-chế-chuyển-giao-hậu-kiểm-toán-post-audit-handoff)
2. [II. BIỆT ĐỘI 5 VAI TRÒ CHUYÊN VIÊN TRONG TEAMWORK PREVIEW (AGENT ROSTER)](#ii-biệt-đội-5-vai-trò-chuyên-viên-trong-teamwork-preview-agent-roster)
3. [III. KẾ HOẠCH TÁC CHIẾN CHI TIẾT 5 GIAI ĐOẠN (5-PHASE EXECUTION BLUEPRINT)](#iii-kế-hoạch-tác-chiến-chi-tiết-5-giai-đoạn-5-phase-execution-blueprint)
4. [IV. MẪU PROMPT /TEAMWORK-PREVIEW CHUẨN HOÁ PHỔ QUÁT (UNIVERSAL PROMPT TEMPLATE)](#iv-mẫu-prompt-teamwork-preview-chuẩn-hoá-phổ-quát-universal-prompt-template)
5. [V. QUY TRÌNH 3 BƯỚC KÍCH HOẠT & NGHIỆM THU TỰ ĐỘNG](#v-quy-trình-3-bước-kích-hoạt--nghiệm-thu-tự-động)
6. [VI. BẢNG MẪU TÙY BIẾN THEO ĐẶC THÙ TỪNG DỰ ÁN](#vi-bảng-mẫu-tùy-biến-theo-đặc-thù-từng-dự-án)

---

## I. TỔNG QUAN VỀ CƠ CHẾ CHUYỂN GIAO HẬU KIỂM TOÁN (POST-AUDIT HANDOFF)

Sau khi hoàn thành quy trình kiểm toán 5 bước (Fast Audit Playbook) theo [06_SECURITY_AND_CODE_AUDITING_GUIDE.md](file:///home/vpsg16gb/Documents/Structure/06_SECURITY_AND_CODE_AUDITING_GUIDE.md), kỹ sư kiểm định hoặc AI Auditor sẽ xuất ra một **Bản báo cáo kết quả kiểm toán (Audit Report)**.

Báo cáo này không chỉ dừng lại ở việc đánh giá Đạt/Không Đạt mà đóng vai trò là **Bản đặc tả lỗi đầu vào (Defect Specification & Input Prompt)** cho hệ thống Multi-Agent `/teamwork-preview` tiến hành phẫu thuật, cải tạo toàn diện dự án.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. FAST AUDIT PLAYBOOK (File 06)                                            │
│    • Quét rò rỉ Secrets & Plaintext Credentials ở Root                     │
│    • Đo lường danh sách file > 150 dòng                                     │
│    • Chạy Pytest Suite và phân tích nguyên nhân Fail                       │
│    • Kiểm tra phân quyền DevContainer non-root (UID 1000)                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Trích xuất Findings & Action Plan)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. ĐIỀN THÔNG TIN VÀO MẪU PROMPT /teamwork-preview (File 07)                │
│    • Thiết lập Working directory & Integrity mode                           │
│    • Ràng buộc 5 Requirements (R1 -> R5)                                   │
│    • Khóa cứng Acceptance Criteria khách quan                               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Kích hoạt lệnh /teamwork-preview)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. BIỆT ĐỘI MULTI-AGENT THỰC THI ĐỒNG BỘ (5 Giai đoạn)                      │
│    • Giai đoạn 1: Triệt tiêu Leaks & thiết lập RAM-Only Vault               │
│    • Giai đoạn 2: Phân rã mã nguồn đơn nhiệm (≤ 150 dòng/file)              │
│    • Giai đoạn 3: Đóng gói DevContainer On-demand & Zero-Idle               │
│    • Giai đoạn 4: Cài đặt 5 tầng chốt chặn Gatekeepers (GK0 - GK4)          │
│    • Giai đoạn 5: TDD Pytest Suite nghiệm thu (Pass ≥ 95%, Zero-Leak 100%)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## II. BIỆT ĐỘI 5 VAI TRÒ CHUYÊN VIÊN TRONG TEAMWORK PREVIEW (AGENT ROSTER)

Khi lệnh `/teamwork-preview` được kích hoạt, hệ thống sẽ phân công các vai trò chuyên biệt phối hợp cùng nhau:

| STT | Vai trò Agent | Trách nhiệm chính | Công cụ & Tài liệu tham chiếu |
| :--- | :--- | :--- | :--- |
| **1** | **Lead System Architect** | Điều phối toàn bộ kế hoạch, kiểm tra tính tương thích giữa các module và phê duyệt thay đổi cấu trúc thư mục. | `00_TONG_QUAN.md`, `01_ARCHITECTURE_CONSTRAINED_AI.md` |
| **2** | **Security & Vault Engineer** | Di dời credentials thô, mã hóa AES-256 PBKDF2 (`project_vault.enc`), cấu hình `.gitignore`, cài đặt `pre-commit` hooks (Gitleaks). | `03_SECURE_ISOLATION_VAULT.md`, `AGENTS.md` |
| **3** | **Codebase Refactoring Specialist** | Khởi tạo Graft AST, nạp Codebase Memory MCP, phân rã các file > 150 dòng thành các submodules đơn nhiệm, gài cơ chế Retry 3 lần. | `01_ARCHITECTURE_CONSTRAINED_AI.md`, `04_PIPELINE_GATEKEEPER_DASHBOARD.md` |
| **4** | **Serverless & DevOps Engineer** | Cấu hình Cloudflare D1 Buffer Worker, thiết lập `.devcontainer/devcontainer.json` non-root, cấu hình `docker-compose.yml`, dựng TUI `monitor.py`. | `02_ZERO_COST_INFRASTRUCTURE.md`, `05_PIPELINES_IN_VIEW.md` |
| **5** | **Adversarial QA & Gatekeeper Auditor** | Viết trọn bộ Pytest Suite (kiểm tra Zero-Leak, độ dài file, kháng lỗi mạng), kiểm định 5 tầng Gatekeeper (GK0 – GK4) và nghiệm thu dự án. | `04_PIPELINE_GATEKEEPER_DASHBOARD.md`, `06_SECURITY_AND_CODE_AUDITING_GUIDE.md` |

---

## III. KẾ HOẠCH TÁC CHIẾN CHI TIẾT 5 GIAI ĐOẠN (5-PHASE EXECUTION BLUEPRINT)

### 🛡️ Giai đoạn 1: Triệt Tiêu Rò Rỉ Bảo Mật & Đóng Gói RAM-Only Vault (Zero-Leak)
1. **Di dời Credentials thô:**
   - Quét toàn bộ thư mục gốc của dự án.
   - Di chuyển an toàn toàn bộ file `.env`, `cookies.txt`, `client_secret.json`, `token.json`, `service_account.json` sang `~/.cloud-profiles/<app_name>/` (phân quyền bảo mật `chmod 600 / 700`).
2. **Khởi tạo Lưới Gác Cổng (Pre-commit & Gitleaks):**
   - Tạo file `.gitignore` bất biến chặn:
     ```gitignore
     .env
     *.env
     *.json
     !package.json
     !tsconfig.json
     !devcontainer.json
     project_vault.enc
     graft/
     __pycache__/
     node_modules/
     ```
   - Tạo file `.pre-commit-config.yaml` tích hợp `gitleaks` và `check-added-large-files` (giới hạn $\le 500\text{KB}$).
   - Thực thi lệnh `pre-commit install` tại thư mục dự án.
3. **Mã hóa Vault In-Memory:**
   - Thiết lập script `docker/entrypoint.sh` giải mã file `project_vault.enc` trực tiếp vào vùng nhớ RAM `/dev/shm/.vault` khi container khởi động.

---

### 📐 Giai đoạn 2: Phân Rã Mã Nguồn Đơn Nhiệm Chuẩn Modularity (Rule ≤ 150 Dòng)
1. **Khởi tạo Ngữ cảnh AI Cục bộ:**
   - Chạy lệnh `graft init` tại thư mục dự án để tạo cây AST tĩnh.
   - Index dự án vào máy chủ [Codebase Memory MCP](file:///home/vpsg16gb/.local/bin/codebase-memory-mcp) để hỗ trợ truy vấn cấu trúc đồ thị hàm/class `<1ms`.
2. **Phân rã các file khổng lồ (> 150 dòng):**
   - **Tệp xử lý Stream/Media lớn:** Phân tách thành:
     * `scraper.py` (Lấy dữ liệu/metadata).
     * `downloader.py` (Tải media/tệp tin).
     * `splitter.py` (Cắt lát chunks $\le 45\text{MB}$ hoặc đoạn văn).
     * `publisher.py` (Xuất bản/upload).
     * `qc_validator.py` (Kiểm định kỹ thuật RMS, LUFS, Black frames).
   - **Tệp điều phối Pipeline:** Phân tách thành:
     * `job_dispatcher.py` (Kéo job và xử lý khóa phân tán).
     * `task_executor.py` (Chạy logic nghiệp vụ).
     * `ledger_sync.py` (Ghi sổ cái SQLite / Google Sheets).
3. **Cài đặt Cơ chế Tự phục hồi (Self-Healing):**
   - Bọc 100% các hàm gọi mạng I/O (Google Drive API, Telegram Bot API, HTTP requests) trong khối `try-except` với cơ chế **Retry tối thiểu 3 lần** kèm exponential backoff.

---

### ☁️ Giai đoạn 3: Chuyển Đổi Hạ Tầng Zero-VPS (Serverless & On-Demand Engine)
1. **Kết nối Cloudflare D1 Buffer 24/7 (Mô hình 1):**
   - Khai báo endpoint `/jobs/pull` và `/jobs/ack` của Cloudflare Worker trung tâm vào cấu hình pipeline.
   - Thiết lập cơ chế khóa tranh chấp Lease Lock 10 phút chống chạy trùng job giữa các instances.
2. **Đóng gói DevContainer Sandbox & Quyền Non-Root:**
   - Tạo file `.devcontainer/devcontainer.json` với `remoteUser: "vscode"` (UID 1000).
   - Tạo file `docker/docker-compose.yml` với các chốt an toàn:
     ```yaml
     security_opt:
       - no-new-privileges:true
     cap_drop:
       - ALL
     tmpfs:
       - /dev/shm:rw,noexec,nosuid,size=64m
     volumes:
       - ~/.cloud-profiles/<app_name>:/workspace/.secrets:ro
       - .:/workspace:cached
     ```
   - Tạo file `run.sh` kích hoạt với cờ `--rm` để container tự hủy sau khi xong việc, đạt **Zero-Idle Memory (0 MB RAM khi nghỉ)**.
3. **Tích hợp Terminal UI Visualizer (`monitor.py`):**
   - Dựng script `monitor.py` (thư viện `rich`) hiển thị sơ đồ đường đi động của các Node tiến trình và bảng log lịch sử từ SQLite `pipeline.db`.

---

### 🔒 Giai đoạn 4: Thiết Lập Bản Thiết Kế Gatekeeper Đa Hình (`GATEKEEPERS.md`) & 5 Tầng Chốt Chặn
1. **Khởi tạo `GATEKEEPERS.md`:** Tạo tệp khai báo 5 chốt chặn nghiệp vụ tại thư mục gốc của dự án theo đúng Domain (Logistics, Media, AI Research, Education).
2. **GK0 (Ingress & Distributed Lock):** Đảm bảo runner chỉ xử lý job khi lấy được khóa hợp lệ; tự động đảo token nếu dính Rate Limit.
3. **GK1 (Raw Input Validation & Clean Inbox):** Thẩm định tính toàn vẹn của tệp đầu vào, vệ sinh dữ liệu, **xóa sạch toàn bộ file trong `00.INBOX`** ngay sau khi trích xuất.
4. **GK2 (Processing Integrity & Modularity):** Kiểm tra tính đầy đủ của chuỗi xử lý/placeholder, đảm bảo 100% module $\le 150$ dòng.
5. **GK3 (Output Compliance & Safety):** Tuân thủ chính sách an toàn cốt lõi của Domain (**Email Drafts Only** đối với logistics/mail, EBU R128 đối với media, JSON Schema đối với AI), không rò rỉ secrets.
6. **GK4 (Ledger Sync & Dead-Letter Alert):** Ghi nhận trạng thái hoàn tất vào Database/Google Drive và gửi cảnh báo sự cố tức thì về Telegram Bot cố định của hệ thống.

---

### 🧪 Giai đoạn 5: Xây Dựng Bộ Kiểm Thử Tự Động & Nghiệm Thu (Pytest Adversarial Suite)
1. **Viết trọn bộ Pytest Suite:**
   - `test_vault_security.py`: Kiểm tra không có plaintext token nào tồn tại trong source code, env hay test files (Zero-Leak Test).
   - `test_file_length_compliance.py`: Quét tự động đảm bảo 100% file `.py` nghiệp vụ có độ dài $\le 150$ dòng.
   - `test_gatekeepers_integrity.py`: Kiểm thử logic 5 tầng GK0 $\rightarrow$ GK4.
   - `test_resilience_retry.py`: Giả lập lỗi timeout mạng và xác minh cơ chế Retry 3 lần hoạt động chính xác.
2. **Chạy nghiệm thu toàn diện:**
   - Thực thi `pytest --tb=short`.
   - Yêu cầu: Tỷ lệ Pass $\ge 95\%$ và **100% Zero-Leak Tests PASSED**.

---

## IV. MẪU PROMPT /TEAMWORK-PREVIEW CHUẨN HOÁ PHỔ QUÁT (UNIVERSAL PROMPT TEMPLATE)

> **Mẫu lệnh dưới đây được chuẩn hóa để copy-paste trực tiếp vào chat sau mỗi lần hoàn thành Báo cáo Kiểm toán:**

```markdown
/teamwork-preview
Hãy đóng vai trò là Biệt đội Kỹ sư Tự động hóa, An ninh & DevOps (Multi-Agent Engineering Team). Dựa trên kết quả Báo cáo Kiểm toán Bảo mật & Chất lượng mã nguồn vừa hoàn thành, hãy thực thi chiến dịch cải tạo toàn diện dự án theo đúng Tiêu chuẩn Kiến trúc [00_TONG_QUAN.md đến 09_MICROVM_HARDWARE_SANDBOX_SPECIFICATION.md] và Hiến pháp [AGENTS.md].

Working directory: [ĐIỀN ĐƯỜNG DẪN THỰC TẾ CỦA DỰ ÁN, VD: /media/vpsg16gb/HaRiDisk/LIBRARY/NWL]
Integrity mode: development

---

## 📌 BỐI CẢNH & HIỆN TRẠNG TỪ BÁO CÁO KIỂM TOÁN
- Dự án cần cải tạo: [ĐIỀN TÊN DỰ ÁN]
- Danh sách vi phạm Secrets/Credentials: [ĐIỀN CÁC FILE LỘ THIÊN HOẶC HARDCODED TOKENS PHÁT HIỆN ĐƯỢC]
- Danh sách file vượt quá 150 dòng cần tách: [ĐIỀN CÁC FILE > 150 DÒNG, VD: src/server.py (269 dòng), scripts/signer.py (364 dòng)]
- Trạng thái Container & Phân quyền: [CHƯA CÓ DEVCONTAINER / ĐANG CHẠY ROOT / THIẾU TMPFS /dev/shm]
- Trạng thái Test Suite: [FAILED N TESTS / THIẾU ZERO-LEAK TEST]

---

## 🎯 YÊU CẦU CẢI TẠO (REQUIREMENTS)

### R1. Triệt Tiêu Toàn Bộ Rò Rỉ Bảo Mật & Đóng Gói RAM-Only Vault (Zero-Leak)
- Di chuyển toàn bộ file token/secret thô sang thư mục bảo mật `~/.cloud-profiles/<tên_dự_án>/` với quyền `chmod 600`.
- Khởi tạo file `.gitignore` chuẩn chặn đứng mọi file `.env`, `*.json`, `*.enc`, `cookies.txt`, `graft/`, `__pycache__/`.
- Thiết lập `.pre-commit-config.yaml` tích hợp hook `gitleaks` và kích hoạt `pre-commit install`.
- Đảm bảo tính độc lập tuyệt đối của Telegram Bot Token theo Hiến pháp AGENTS.md (không dùng chung hoặc lẫn lộn token). Mọi file test phải sử dụng Token mock giả định.

### R2. Tái Cấu Trúc Mã Nguồn Đơn Nhiệm Chuẩn Modularity (Rule ≤ 150 dòng/file)
- Sử dụng Graft (`graft init`) và Codebase Memory MCP (`~/.local/bin/codebase-memory-mcp`) để lập bản đồ cấu trúc mã nguồn.
- Tiến hành phân rã 100% các file mã nguồn logic vượt quá 150 dòng thành các submodules nhỏ gọn, đơn nhiệm (Single Responsibility).
- Áp dụng cơ chế Tự phục hồi (Self-Healing): Bọc tất cả thao tác I/O mạng, Google Drive API, Telegram API trong khối `try-except` với Retry tối thiểu 3 lần kèm exponential backoff.

### R3. Thiết Lập Môi Trường Sandbox Non-Root & On-Demand Container (Zero-Idle Memory)
- Khởi tạo cấu hình `.devcontainer/devcontainer.json` khóa cứng user `remoteUser: "vscode"` (UID 1000), nghiêm cấm chạy bằng root.
- Cấu hình `docker/docker-compose.yml` với các chốt an toàn:
  * `security_opt: ["no-new-privileges:true"]`
  * `cap_drop: ["ALL"]`
  * `tmpfs: ["/dev/shm:rw,noexec,nosuid,size=64m"]`
  * Mount volumes credentials ở chế độ Read-Only (`:ro`).
- Tạo file script `run.sh` kích hoạt container với cờ `--rm` để tự hủy container giải phóng 100% RAM sau khi hoàn thành công việc.

### R4. Tích Hợp Mô Hình Serverless Cloudflare Buffer & Terminal UI Visualizer
- Tích hợp điều phối theo Mô hình 1 ([05_PIPELINES_IN_VIEW.md]): Rút jobs từ Cloudflare D1 Buffer (`/jobs/pull`) kèm khóa tranh chấp Lease Lock 10 phút.
- Xây dựng script TUI `monitor.py` (sử dụng thư viện `rich`) để hiển thị sơ đồ đường đi động của Pipeline và lưu trữ nhật ký thực thi vào SQLite nội bộ `pipeline.db`.

### R5. Xây Dựng 5 Tầng Gác Cổng (Gatekeepers) & Pytest Suite Kháng Lỗi Toàn Diện
- Đảm bảo luồng xử lý đi qua đủ 5 tầng Gatekeepers: GK0 (Distributed Lock) ➔ GK1 (Unit QC $\ge 5$KB) ➔ GK2 (Sequence QC & Silence 0.5s) ➔ GK3 (Master QC -16 LUFS & Dead-letter Telegram) ➔ GK4 (Central Ledger & Content Fingerprint).
- Tuân thủ nghiêm ngặt Hiến pháp AGENTS.md: Email CHỈ ĐƯỢC TẠO DRAFT (`drafts().create()`), thư mục Google Drive `00.INBOX` phải được XÓA SẠCH sau khi xử lý xong.
- Viết trọn bộ Pytest Suite bao phủ: Zero-Leak verification, Modular length verification ($\le 150$ lines), Gatekeepers integrity, Retry mechanisms. Đạt tỷ lệ Pass $\ge 95\%$.

---

## ✅ TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA)

### 1. Bảo Mật & Credentials (Zero-Leak)
- [ ] Không còn bất kỳ file `.env`, `.json` credentials nào nằm lộ thiên ở thư mục root dự án.
- [ ] Lệnh `grep -rnE "[0-9]{9,11}:[A-Za-z0-9_-]{35}" .` không tìm thấy token thật bị hardcode trong source code và file test.
- [ ] File `.gitignore` và `.pre-commit-config.yaml` đã được cài đặt và kích hoạt thành công.

### 2. Chuẩn Hóa Độ Dài Mã Nguồn (Rule ≤ 150 dòng)
- [ ] Lệnh `find . -maxdepth 3 -name "*.py" -exec wc -l {} + | awk '$1 > 150'` trả về 0 kết quả (100% file logic $\le 150$ dòng).
- [ ] Các module được phân rã rõ ràng theo đúng chức năng (Scraper, Downloader, Splitter, Publisher, QC Validator).

### 3. Môi Trường Sandbox & Zero-Idle
- [ ] `.devcontainer/devcontainer.json` chỉ định `remoteUser: "vscode"`.
- [ ] `docker-compose.yml` có đầy đủ `cap_drop: [ALL]`, `tmpfs: /dev/shm` và `security_opt`.
- [ ] Container tự hủy sau khi chạy xong (`--rm`), không để lại tiến trình chiếm dụng RAM khi nghỉ (Zero-Idle).

### 4. Vận Hành & Kiểm Thử (Pytest Suite)
- [ ] Chạy `pytest --tb=short` đạt tỷ lệ Pass $\ge 95\%$ và 100% Zero-Leak tests Passed.
- [ ] Script `python monitor.py` chạy độc lập, hiển thị sơ đồ trực quan TUI và tiêu thụ $\le 25\text{MB}$ RAM.
```

---

## V. QUY TRÌNH 3 BƯỚC KÍCH HOẠT & NGHIỆM THU TỰ ĐỘNG

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ BƯỚC 1: XUẤT BÁO CÁO KIỂM TOÁN (AUDIT REPORT)                               │
│ • Chạy Fast Audit Playbook (Mục V của File 06) để phát hiện các vi phạm.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ BƯỚC 2: COPY MẪU LỆNH & ĐIỀN THÔNG SỐ (FILL PROMPT TEMPLATE)                │
│ • Copy mẫu lệnh tại Mục IV của File 07 này.                                 │
│ • Điền tên dự án, đường dẫn root và danh sách vi phạm vào template.        │
├─────────────────────────────────────────────────────────────────────────────┤
│ BƯỚC 3: GỬI LỆNH /teamwork-preview & GIÁM SÁT NGHIỆM THU                    │
│ • Gửi prompt vào phiên chat.                                                │
│ • Biệt đội AI Teamwork tự động refactor, đóng gói và chạy nghiệm thu.       │
│ • Chạy lại Fast Audit để xác nhận 100% tiêu chí chuyển sang trạng thái PASS.│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## VI. BẢNG MẪU TÙY BIẾN THEO ĐẶC THÙ TỪNG DỰ ÁN

| Loại hình Dự án | Các Module Cần Phân Rã Đặc Thù | Quy Chuẩn Gatekeeper Trọng Tâm | Cấu hình Secrets Profile |
| :--- | :--- | :--- | :--- |
| **Dự án Nghiệp vụ Logistics (NWL)** | • `invoice_parser.py`<br>• `contract_signer.py`<br>• `gmail_draft_builder.py` | • **Bắt buộc:** Email Drafts Only (`drafts().create()`)<br>• **Bắt buộc:** Xóa sạch `00.INBOX` Google Drive | `~/.cloud-profiles/nwl/`<br>Token NWL: `8944836049:...` (`@newway_mcp_Bot`) |
| **Dự án Media / Content Generation** | • `script_splitter.py`<br>• `voice_synthesizer.py`<br>• `video_stitcher.py`<br>• `lufs_normalizer.py` | • **GK1:** File $\ge 5\text{KB}$, RMS check<br>• **GK2:** Silence gap 0.5s<br>• **GK3:** EBU R128 (-16 LUFS) | `~/.cloud-profiles/media/`<br>Token Command: `8798886722:...` (`@youtube2drive_Bot`) |
| **Dự án Webhook & Data Sync (Buffer)** | • `webhook_receiver.py`<br>• `lease_locker.py`<br>• `drive_chunk_uploader.py` | • **GK0:** Lease Lock 10 phút chống tranh chấp<br>• **GK4:** Băm SHA-256 & `PUBLISHED_IMMUTABLE` | `~/.cloud-profiles/sync/`<br>Cloudflare D1 Secret |
| **Dự án Trí Tuệ Nhân Tạo (Gemini/AI Research)** | • `research_collector.py`<br>• `notebook_prompter.py`<br>• `slide_generator.py` | • **Bắt buộc:** Schema JSON đầu ra nghiêm ngặt<br>• **Bắt buộc:** Tự hủy cache model hàng tuần | `~/.cloud-profiles/gemininotebook/`<br>Token Gemini: `8027319967:...` |
