# 🏛️ TỔNG QUAN KIẾN TRÚC HỆ THỐNG, QUẢN TRỊ PROFILE & BỘ CÔNG CỤ MUST-HAVE TOÀN CỤC

> **Phiên bản:** 1.0 (Master Architecture Guide)
> **Áp dụng cho:** Toàn bộ Apps, Pipelines, Workflows, Trợ lý AI và Dự án trên hệ sinh thái máy chủ (`vpsg16gb`, `vpsg24gb`, `HaRiDisk`).
> **Nguyên tắc cốt lõi:** 100% Containerized (DevContainer/Docker) • Zero-Leak (RAM-Only Vault) • Constrained AI Engineering.

---

## 📑 MỤC LỤC
1. [PHẦN I: BẢN ĐỒ KIỂM TOÁN PROFILE & CREDENTIALS TRÊN MÁY HỆ THỐNG](#phần-i-bản-đồ-kiểm-toán-profile--credentials-trên-máy-hệ-thống)
2. [PHẦN II: 5 TRỤ CỘT KIẾN TRÚC CHUẨN (DOCUMENTS/STRUCTURE)](#phần-ii-5-trụ-cột-kiến-trúc-chuẩn-documentsstructure)
3. [PHẦN III: BỘ CÔNG CỤ MUST-HAVE TOÀN CỤC (GLOBAL TOOLKIT)](#phần-iii-bộ-công-cụ-must-have-toàn-cục-global-toolkit)
4. [PHẦN IV: HƯỚNG DẪN CÀI ĐẶT & CẤU HÌNH CHI TIẾT TỪNG CÔNG CỤ](#phần-iv-hướng-dẫn-cài-đặt--cấu-hình-chi-tiết-từng-công-cụ)
5. [PHẦN V: CASE STUDY & BLUEPRINT MẪU: KIẾN TRÚC HOÀN CHỈNH DỰ ÁN NWL](#phần-v-case-study--blueprint-mẫu-kiến-trúc-hoàn-chỉnh-dự-án-newway-logistics-nwl)
6. [PHẦN VI: QUY TRÌNH 6 BƯỚC KHỞI TẠO BẤT KỲ DỰ ÁN MỚI NÀO (PROJECT CHECKLIST)](#phần-vi-quy-trình-6-bước-khởi-tạo-bất-kỳ-dự-án-mới-nào-project-checklist)
7. [PHẦN VII: MẪU LỆNH TEAMWORK PREVIEW DÀNH CHO DEVOPS & INFRA](#phần-vii-mẫu-lệnh-teamwork-preview-dành-cho-devops--infra)

---

## PHẦN I: BẢN ĐỒ KIỂM TOÁN PROFILE & CREDENTIALS TRÊN MÁY HỆ THỐNG

Hiện tượng chồng chéo và nhiễu loạn profile xuất phát từ việc cùng một tài khoản được đăng nhập ở nhiều thư mục cấu hình và tiến trình độc lập. Dưới đây là hiện trạng kiểm toán toàn bộ:

### 1. Bản Đồ Phân Bổ Tài Khoản (Email ➔ Thư mục lưu trữ)

| Tài khoản Email | Tên hiển thị | Vị trí lưu trữ Profile | Dung lượng | Ghi chú & Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **`aleron.dt@gmail.com`** | **Aleron DAU** | `~/.config/google-chrome/Default` | **2.8 GB** | **Profile GỐC (Root)**: Google Drive **30 TB** (Kho NWL, Legal, GCP, AI Studio). |
| **`lchau4501@gmail.com`** | **Tuấn Hoàng ĐẬU** | • `~/.config/google-chrome/Profile 4`<br>• `~/.chrome-colab-profile`<br>• `~/.chrome-temp-profile`<br>• `~/.config/google-chrome-colab-c`<br>• `~/.notebooklm/profiles/default` | 739 MB<br>323 MB<br>233 MB<br>144 MB<br>13 MB | Google Drive **5 TB**: Dùng cho GeminiNotebook Artifacts, AI Research, Edu. |
| **`analibrary2909@gmail.com`** | **ana library** | • `~/.config/google-chrome/Profile 3`<br>• `~/.chrome-gui-debug-profile`<br>• `~/.config/google-chrome-colab-b`<br>• `~/.config/google-chrome-debug` | 783 MB<br>87 MB<br>189 MB<br>290 MB | Google Drive **5 TB**: Dùng cho Media Library, Colab Runner & Debug GUI. |
| **`triplex2909.002@gmail.com`** | **Triple X 002** | • `~/.chrome-flow-profile`<br>• `~/.chrome-flow-profile-snooze`<br>• `~/.chrome-colab-profile-new` | **4.9 GB**<br>92 MB<br>91 MB | Google Drive **5 TB**: Đang chạy `.chrome-flow-profile` Remote Debugging Port `9222`. |
| **`comics2909.1@gmail.com`** | **Comic English 1** | • `~/.config/google-chrome/Profile 6`<br>• `~/.chrome-temp-profile-new` | 55 MB<br>150 MB | Dùng cho Cloudflare Workers & Chrome. |
| **`comics2909.2@gmail.com`** | **Comic English 2** | `~/.config/google-chrome/Profile 7` | 27 MB | Chrome Profile phụ. |
| **`hothihuong113@gmail.com`** | **hương hồ thị** | `~/.config/google-chrome/Profile 8` | 823 MB | Chrome Profile phụ (GCP Console, Labs). |
| **`nw.tuanhoang@gmail.com`** | **Hoàng ĐẬU Tuấn** | `~/.config/google-chrome/Profile 9` | 23 MB | Email công vụ phê duyệt cấp cao NWL. |

### 3. MA TRẬN ĐỊNH DANH TÀI KHOẢN ĐA DỊCH VỤ TOÀN CỤC (MASTER MULTI-ACCOUNT & CLOUD MATRIX)

Để ngăn chặn 100% tình trạng chồng chéo hoặc rò rỉ chéo dữ liệu giữa các dịch vụ đám mây, toàn bộ hệ thống áp dụng **Ma trận Khóa cứng Định danh (Strict Identity Binding Matrix)**:

| Dịch vụ Đám Mây | 📦 1. Newway Logistics (NWL) | 🧠 2. GeminiNotebook (AI Research) | 🎬 3. Media Runner (Command Center) | 🎓 4. Gia Sư AI (HanaAssistant) |
| :--- | :--- | :--- | :--- | :--- |
| **Thư mục Profile Vault** | `~/.cloud-profiles/nwl/` | `~/.cloud-profiles/gemininotebook/` | `~/.cloud-profiles/media/` | `~/.cloud-profiles/edu/` |
| **Google Drive** | `aleron.dt@gmail.com`<br>(Kho hợp đồng, con dấu, tài liệu) | `lchau4501@gmail.com`<br>(Kho Artifacts, Slide, Audio master) | `triplex2909.002@gmail.com` hoặc `analibrary2909@gmail.com` | `lchau4501@gmail.com`<br>(Kho bài giảng & tài liệu học tập) |
| **NotebookLM** | Profile: `nwl`<br>Account: `aleron.dt@gmail.com` | Profile: `default`<br>Account: `lchau4501@gmail.com` | Không sử dụng | Profile: `hana`<br>Account: `lchau4501@gmail.com` |
| **Gmail** | • Thường quy: `hcmbranch@newway-logistics.com`<br>• Quản trị: `nw.tuanhoang@gmail.com` | Không sử dụng | Không sử dụng | Không sử dụng |
| **Cloudflare D1 / Worker** | `pipeline-buffer-worker` (Edge Relay)<br>Secret: `CF_SECRET` | Không sử dụng | `pipeline-buffer-worker`<br>(D1: `pipeline_buffer`) | Webhook Endpoint riêng |
| **GitHub Actions** | Không sử dụng | Không sử dụng | Matrix Runners: `repo-01` $\rightarrow$ `repo-09`<br>(Encrypted Secrets via SealedBox) | Không sử dụng |
| **Telegram Bot** | `@newway_mcp_Bot`<br>(`8944836049:...`) | Bot Token Gemini:<br>(`8027319967:...`) | `@youtube2drive_Bot`<br>(`8798886722:...`) | `@hanalearningBot`<br>(`8903373140:...`)<br>Nhóm: `HaRiEdu` |

### 4. Quy Chuẩn Khai Báo Biến Môi Trường (Standardized ENV Variables)
Trong file `docker-compose.yml` hoặc `run.sh` của từng pipeline, các biến môi trường được chuẩn hóa theo quy ước:
```bash
# 1. Google Drive & NotebookLM
GDRIVE_ACCOUNT="aleron.dt@gmail.com"
GDRIVE_TOKEN_PATH="/workspace/.secrets/gdrive/token.json"
NOTEBOOKLM_ACCOUNT="aleron.dt@gmail.com"
NOTEBOOKLM_PROFILE="nwl"
NOTEBOOKLM_STORAGE_STATE="/workspace/.secrets/notebooklm/storage_state.json"

# 2. Gmail Multi-Account
GMAIL_COMPANY_ACCOUNT="hcmbranch@newway-logistics.com"
GMAIL_TOKEN_PATH="/workspace/.secrets/gmail/company/token.json"
GMAIL_EXECUTIVE_ACCOUNT="nw.tuanhoang@gmail.com"
GMAIL_EXECUTIVE_TOKEN_PATH="/workspace/.secrets/gmail/executive/token.json"

# 3. Cloudflare Buffer & Webhook
CF_WORKER_URL="https://pipeline-buffer-worker.hothihuong113.workers.dev"
CF_SECRET="antigravity_buffer_secret_token_2026"
PIPELINE_NAME="NWL-Invoicing"

# 4. Telegram Bot & Notification
TELEGRAM_BOT_TOKEN_PATH="/workspace/.secrets/telegram/bot_token.txt"
TELEGRAM_CHAT_ID="-1003709159190"
```

---

## PHẦN II: 5 TRỤ CỘT KIẾN TRÚC CHUẨN (DOCUMENTS/STRUCTURE)

### Trụ cột 1: Kỹ nghệ AI có khuôn khổ (Constrained AI Engineering)
* **Chống thoái hóa ngữ cảnh (Context Rot):** Không để AI tự do "vibe code". Mọi tác vụ phải tuân thủ nghiêm ngặt theo "Hiến pháp" `AGENTS.md` (hoặc `.cursorrules`).
* **Quy chuẩn kích thước tệp:** Mọi file mã nguồn **không được vượt quá 150 dòng**. Tách nhỏ thành các module chức năng độc lập.
* **Quy trình TDD bắt buộc:** Viết Unit Test trước $\rightarrow$ Chạy code $\rightarrow$ Tự phục hồi (Retry tối thiểu 3 lần).

### Trụ cột 2: Hạ tầng 100% Miễn Phí Trọn Đời (Zero-Cost Infrastructure)
* **Cloudflare Workers (Edge Gateway):** Chặn đứng prompt bẩn/18+ bằng **Llama Guard 2** (`@cf/meta/llama-guard-2-8b`) tại Edge ($0 cold-start), sau đó mới kích hoạt GitHub Actions.
* **GitHub Actions Runner (Compute Matrix):** Chạy ma trận song song cực đại **15–18 jobs** đồng thời để xử lý chunks siêu tốc, kèm cơ chế tự hủy cache hàng tuần (`week_num`).
* **Google Drive API v3 (Resumable Upload 5MB/chunk):** Không dùng tool sync bên thứ ba dễ đứt gãy; dùng code Python thuần gọi Google Drive API v3 cắt lát 5MB chống mất gói mạng.

### Trụ cột 3: DevContainer & RAM-Only Vault (Bảo mật Zero-Leak)
* **Không ghi secrets dạng Plaintext:** Tuyệt đối cấm lưu token, API keys trong source code hoặc commit vào Git.
* **Giải mã In-Memory vào RAM (`/dev/shm`):** Secrets lưu dưới dạng file mã hóa AES-256 (`project_vault.enc`), khi container khởi chạy `entrypoint.sh` sẽ giải mã thẳng vào RAM (`/dev/shm`) và tự biến mất khi tắt container (`--rm`).
* **Phân quyền Non-Root:** User trong container là `vscode` (UID 1000), khóa cứng `security_opt: [no-new-privileges:true]` và `cap_drop: [ALL]`.

### Trụ cột 4: Gatekeeper Đa Hình & Dashboard Giám Sát Quota
* **Khung 5 Pha Phổ Quát (Universal 5-Phase Pattern):**
  1. *GK0 (Ingress & Concurrency):* Khóa phân tán, rate-limit & **Pre-Flight Quota Check** (GDrive, GitHub, Cloudflare).
  2. *GK1 (Raw Input QC):* Thẩm định tệp đầu vào, vệ sinh dữ liệu, **xóa sạch 100% file trong `00.INBOX`**.
  3. *GK2 (Processing Integrity):* Đảm bảo tính toàn vẹn chuỗi/placeholder, tuân thủ module $\le 150$ dòng.
  4. *GK3 (Output Compliance & Safety):* Ép chuẩn đầu ra (**Email Drafts Only**, EBU R128, JSON Schema), zero-leak secrets.
  5. *GK4 (Ledger & Telemetry):* Cập nhật trạng thái bất biến lên Sổ cái và đồng bộ chỉ số Quota tiêu hao thực tế.
* **Tệp khai báo bắt buộc:** Mỗi dự án/pipeline bắt buộc có **`GATEKEEPERS.md`** tại thư mục gốc.
* **Chống đăng bài trùng lặp (Content Fingerprint):** Băm $\text{SHA-256}(\text{Media Bytes} + \text{Caption})$ và khóa bất biến `PUBLISHED_IMMUTABLE`.
* **Single-Tab Master Dashboard:** Quản lý toàn bộ hệ thống trên duy nhất 1 Tab Google Sheets chia theo 4 phân khu (Header KPI, Global Config, Task Control, Publish Ledger).

### Trụ cột 5: Điều Phối Pipeline In-View (D1 Buffer, On-Demand Engine & CLI `pipe`)
* **Cloudflare D1 Buffer 24/7 (Edge Hub):** Hộp thư tiếp nhận webhook miễn phí $0, không bao giờ rớt job kể cả khi máy local tắt.
* **Local Ephemeral Engine (`docker run --rm`):** Chỉ khởi động khi có việc, rút job về chạy tuần tự, tự hủy sau khi hoàn thành để giải phóng 100% RAM & Swap.
* **Dual-Mode Terminal UI (`rich`):** Xem sơ đồ Node và Quota Radar thời gian thực trực tiếp trên Host (0.02s) **mà không cần bật Docker Container**.
* **Bộ điều khiển toàn cầu `pipe`:** Công cụ CLI tại `~/.local/bin/pipe` cho phép kiểm tra quota, bật monitor, chạy on-demand và phục hồi job lỗi từ bất kỳ đâu.

### 🗺️ BẢN ĐỒ 11 TÀI LIỆU TIÊU CHUẨN KIẾN TRÚC TOÀN CỤC (MASTER SPECIFICATIONS MAP)

| Mã File | Tên Tài Liệu | Trọng Tâm Quy Chuẩn | Đối Tượng Áp Dụng |
| :--- | :--- | :--- | :--- |
| **`00_TONG_QUAN.md`** | Tổng Quan Kiến Trúc & Quản Trị Profile | Master Guide, Bộ công cụ Must-Have, Bản đồ Profile | Toàn hệ thống |
| **`01_ARCHITECTURE_CONSTRAINED_AI.md`** | Kiến Trúc Mã Nguồn Bền Vững & Hiến Pháp AI | Constrained AI, Quy chuẩn file $\le 150$ dòng, TDD, Graft | Toàn bộ Codebase |
| **`02_ZERO_COST_INFRASTRUCTURE.md`** | Hạ Tầng 100% Miễn Phí Trọn Đời | Cloudflare Workers AI, GitHub Actions Matrix 18 jobs, GDrive API | Tự động hóa & Cloud |
| **`03_SECURE_ISOLATION_VAULT.md`** | Chiến Lược Cô Lập & RAM-Only Vault | DevContainer, Decrypt in `/dev/shm`, Non-root UID 1000 | Container & Secrets |
| **`04_PIPELINE_GATEKEEPER_DASHBOARD.md`** | Pipeline Đa Tầng, Gatekeeper & Dashboard | 5 Gatekeepers (GK0–GK4), Quota Radar, Single-Tab Dashboard | Xử lý Media & Data |
| **`05_PIPELINES_IN_VIEW.md`** | Mô Hình Cloudflare D1 Buffer, Engine & CLI pipe | D1 Buffer 24/7, Ephemeral Engine, TUI Schema & pipe CLI | Webhook & Pipelines |
| **`06_SECURITY_AND_CODE_AUDITING_GUIDE.md`** | Sổ Tay Kiểm Toán Bảo Mật & Chất Lượng Mã Nguồn | 10 Tiêu chí Audit, Pass/Fail Rubrics, Fast Playbook | QA & Health Check |
| **`07_POST_AUDIT_TEAMWORK_REMEDIATION.md`** | Chiến Dịch Cải Tạo Codebase Đa Tác Tử (Teamwork) | 7 Chuyên gia AI phân rã code, Template Teamwork Preview | Refactor & Remediation |
| **`08_PROJECT_HYGIENE_AND_BACKUP_SPECIFICATION.md`** | Vệ Sinh Mã Nguồn & Sao Lưu GDrive Độc Lập | 1 Dự án = 1 GDrive Folder, `scripts/auto_backup.py` | Backup & Data Safety |
| **`09_MICROVM_HARDWARE_SANDBOX_SPECIFICATION.md`** | Đặc Tả Cô Lập Phần Cứng MicroVM & Zero-Idle | Firecracker / Kata Containers, Kernel riêng, Hardware VT-x | Sandbox Cấp Cao |
| **`10_AUTONOMOUS_ORCHESTRATION_HERMES_AGY_SPECIFICATION.md`** | Đặc Tả Tổng Quản Tự Hành Hermes & Antigravity Worker | Dual-Engine, SOP 5, Bridge hermes-agy, 7 Nguyên tắc Hiến pháp | Tự Động Hóa & Multi-Agent |

---

## PHẦN III: BỘ CÔNG CỤ MUST-HAVE TOÀN CỤC (GLOBAL TOOLKIT)

Bộ công cụ được chia làm 4 lớp bổ trợ hoàn hảo, **hoàn toàn KHÔNG xung đột với nhau**:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. GIAO DIỆN QUẢN TRỊ TRỰC QUAN & CLI CONTROLLERS (Chạy trên Termius)    │
│    • pipe: Bộ lệnh điều phối Pipeline toàn cầu (list, mon, quota, run)   │
│    • lazygit: Quản lý Git diff, xem nhánh, revert code lỗi do AI        │
│    • lazydocker: Quản lý Docker, stream logs trực tiếp, xem RAM/CPU     │
├─────────────────────────────────────────────────────────────────────────┤
│ 2. MÔI TRƯỜNG PHÁT TRIỂN CHUẨN HÓA BẤT BIẾN (DevContainer Sandbox)      │
│    • @devcontainers/cli: Build, run, exec container từ dòng lệnh       │
│    • .devcontainer.json: Khóa cứng môi trường non-root & toolchain      │
│    • tmpfs /dev/shm: Vùng nhớ RAM cô lập tuyệt đối cho Secrets          │
├─────────────────────────────────────────────────────────────────────────┤
│ 3. VŨ KHÍ NGỮ CẢNH AI (Local AI Dev Tools)                              │
│    • Graft: Bản đồ tĩnh Tree-sitter AST, tiết kiệm 42% tokens           │
│    • Codebase Memory MCP: Đồ thị quan hệ SQLite truy vấn hàm/class <1ms │
│    • Gstack: Biệt đội ảo 23 vai trò tự review & QA chuẩn Y Combinator   │
├─────────────────────────────────────────────────────────────────────────┤
│ 4. LƯỚI BẢO MẬT GÁC CỔNG TRƯỚC KHI COMMIT (Zero-Leak Gatekeepers)      │
│    • pre-commit: Khung kích hoạt hooks tự động khi gõ git commit        │
│    • Gitleaks: Đánh hơi và chặn đứng commit chứa API Key / Token (<0.1s)│
│    • TruffleHog: Quét entropy sâu và phát hiện rò rỉ khoá cấp cao       │
│    • .gitignore: Chặn đứng .env, credentials/, *.json, *.enc            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## PHẦN IV: HƯỚNG DẪN CÀI ĐẶT & CẤU HÌNH CHI TIẾT TỪNG CÔNG CỤ

### 1. Cài đặt DevContainer CLI (Global)
```bash
# Cài đặt qua NPM Global
npm install -g @devcontainers/cli

# Kiểm tra phiên bản
devcontainer --version
```

### 2. Cài đặt Bộ Đôi Terminal UI: `lazygit` & `lazydocker`
```bash
# Tạo thư mục bin cục bộ nếu chưa có
mkdir -p ~/.local/bin

# 1. Cài đặt lazygit
LAZYGIT_VERSION=$(curl -s "https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | grep -Po '"tag_name": "v\K[^"]*')
curl -Lo /tmp/lazygit.tar.gz "https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz"
tar -xf /tmp/lazygit.tar.gz -C /tmp
mv /tmp/lazygit ~/.local/bin/
rm /tmp/lazygit.tar.gz

# 2. Cài đặt lazydocker
curl https://raw.githubusercontent.com/jesseduffield/lazydocker/master/scripts/install_update_linux.sh | bash

# Cập nhật PATH và kiểm tra
export PATH="$HOME/.local/bin:$PATH"
lazygit --version
lazydocker --version
```
> **Mẹo sử dụng:**
> * Mở Termius hoặc Web SSH, gõ `lazygit` để xem Git diff và undo code. Bấm `q` để thoát.
> * Gõ `lazydocker` để xem danh sách container đang chạy và stream live logs. Bấm `q` để thoát.

### 3. Cài đặt Framework `pre-commit` (Global User)
```bash
# Cài đặt pre-commit cho Python user environment
pip install --user pre-commit

# Kiểm tra
pre-commit --version
```

### 4. Cấu hình Codebase Memory MCP Server
Binary `codebase-memory-mcp` (v0.8.1) đã có sẵn tại `~/.local/bin/codebase-memory-mcp`.
Để liên kết vào cấu hình MCP toàn cục hoặc từng dự án (trong file `mcp_config.json` hoặc `.claude.json`):
```json
{
  "mcpServers": {
    "codebase-memory": {
      "command": "/home/vpsg16gb/.local/bin/codebase-memory-mcp",
      "args": []
    }
  }
}
```

---

## PHẦN V: CASE STUDY & BLUEPRINT MẪU: KIẾN TRÚC HOÀN CHỈNH DỰ ÁN NEWWAY LOGISTICS (NWL)

Thư mục: `/media/vpsg16gb/HaRiDisk/LIBRARY/NWL`

Dự án **Newway Logistics (NWL)** là hình mẫu chuẩn mực (Golden Reference Blueprint) đã được chuẩn hóa và nghiệm thu 100% tuân thủ toàn bộ 5 Trụ Cột BIBLE:
* ✅ **100% Modularity:** Toàn bộ file mã nguồn (`src/server.py`, `src/services.py`, `src/tools_drive.py`, `src/tools_gmail.py`, `src/resilience.py`) đều $\le 150$ dòng.
* ✅ **Zero-Leak Credentials:** Thư mục `credentials/` được chuyển ra ngoài `~/.cloud-profiles/nwl/` và chỉ mount vào container dạng `:ro`.
* ✅ **Gatekeeper Đa Hình (`GATEKEEPERS.md`):** Đã thiết lập đầy đủ 5 pha chốt chặn nghiệp vụ Logistics và hợp đồng.
* ✅ **Cơ chế Sao lưu Tự Động:** Đã tích hợp `scripts/auto_backup.py` nén snapshot database lên Google Drive.
* ✅ **Pytest Suite Kháng Lỗi:** 33/33 test cases Passed (bao gồm AST Test chặn `messages().send()` và kiểm tra Zero-Leak).

### Các File Cấu Hình Chuẩn Mẫu Đã Triển Khai Trong NWL

#### A. File `.gitignore` (Bảo vệ tuyệt đối secrets)
```text
# Secrets & Credentials (Bảo mật tuyệt đối)
.env
*.env
credentials/
*.json
!agy_mcp_config.json
!gdrive_folder_map.json
!package.json
project_vault.enc

# Cache & Temp Files
__pycache__/
*.pyc
.pytest_cache/
graft/
node_modules/
artifacts/*.pdf
artifacts/*.docx
```

#### B. File `.devcontainer/devcontainer.json`
```json
{
  "name": "NWL - Logistics Automation DevContainer",
  "dockerComposeFile": ["../docker/docker-compose.yml"],
  "service": "sandbox",
  "workspaceFolder": "/workspace",
  "remoteUser": "vscode",
  "features": {
    "ghcr.io/devcontainers/features/common-utils:2": {
      "username": "vscode"
    },
    "ghcr.io/devcontainers/features/python:3": {
      "version": "3.11"
    }
  },
  "postCreateCommand": "pip install -r docker/requirements.txt pre-commit && pre-commit install",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff"
      ]
    }
  }
}
```

#### C. File `docker/docker-compose.yml` (Định danh Tài khoản Tách bạch 100%)
```yaml
version: '3.8'

services:
  sandbox:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: nwl-sandbox
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    volumes:
      - ..:/workspace:cached
      - ~/.cloud-profiles/nwl:/workspace/.secrets:ro
    tmpfs:
      - /dev/shm:rw,noexec,nosuid,size=64m
    working_dir: /workspace
    environment:
      - PYTHONUNBUFFERED=1
      # 1. GOOGLE DRIVE (Bắt buộc Aleron DAU)
      - GDRIVE_ACCOUNT=aleron.dt@gmail.com
      - GDRIVE_TOKEN_PATH=/workspace/.secrets/gdrive/token.json
      # 2. NOTEBOOKLM (Bắt buộc Aleron DAU - Profile nwl)
      - NOTEBOOKLM_ACCOUNT=aleron.dt@gmail.com
      - NOTEBOOKLM_STORAGE_PATH=/workspace/.secrets/notebooklm/storage_state.json
      # 3. GMAIL CÔNG TY (Nghiệp vụ thường quy)
      - GMAIL_COMPANY_ACCOUNT=hcmbranch@newway-logistics.com
      - GMAIL_COMPANY_TOKEN_PATH=/workspace/.secrets/gmail/company/token.json
      # 4. GMAIL QUẢN TRỊ CẤP CAO (Pháp lý & Chiến lược)
      - GMAIL_EXEC_ACCOUNT=nw.tuanhoang@gmail.com
      - GMAIL_EXEC_TOKEN_PATH=/workspace/.secrets/gmail/executive/token.json
      # 5. TELEGRAM BOT (Dành riêng cho Container NWL - Không dùng token ngoài)
      - TELEGRAM_BOT_TOKEN_PATH=/workspace/.secrets/telegram/bot_token.txt
```

#### QUY TẮC PHÂN PHỐI TÀI LIỆU & ARTIFACTS (STRICT DISPATCHING POLICY):
1. **Telegram Token Gắn Cố Định Theo Container & Cấm Dùng Token Chéo (Strict Telegram Isolation):**
   - Mỗi container chỉ sử dụng duy nhất Telegram Token và Chat ID được gắn cố định trong credentials của container đó (`~/.cloud-profiles/<tên_app>/telegram/bot_token.txt` hoặc `token.json`), **CẤM TUYỆT ĐỐI DÙNG TOKEN / CHAT ID NGOÀI CONTAINER**.
   - Các hệ thống hiện hữu:
     * **Container NWL:** `@newway_mcp_Bot` (Bot ID: `8944836049`, nạp từ `~/.cloud-profiles/nwl/telegram/bot_token.txt`).
     * **Container GeminiNotebook:** Bot Gemini (Bot ID: `8027319967`, nạp từ `~/.cloud-profiles/gemininotebook/telegram/bot_token.txt`).
     * **Container Command Center (Media Runner):** `@youtube2drive_Bot` (Bot ID: `8798886722`, nạp từ `~/.cloud-profiles/telegram_command_center/telegram/telegram_config.json`).
     * **Container HanaAssistant (Gia sư AI):** `@hanalearningBot` (Bot ID: `8903373140`, nạp từ `~/.cloud-profiles/hana_assistant/telegram/bot_token.txt`), nhóm đích duy nhất: `HaRiEdu` (`chat_id: -1003709159190`).
   - **QUY TẮC HỎI Ý KIẾN BẮT BUỘC (PERMISSION PROTOCOL):** Nếu một container chưa được cấu hình Telegram Token, hoặc token/chat_id bị lỗi kết nối, AI Agent **BẮT BUỘC PHẢI DỪNG LẠI VÀ HỎI TRỰC TIẾP USER ĐỂ XIN PHÉP / LẤY THÔNG TIN**, tuyệt đối **CẤM TỰ Ý LẤY TOKEN CỦA CONTAINER KHÁC LÀM DỰ PHÒNG**.
2. **Google Drive Mặc Định & Cơ chế Xác nhận (Confirmation Rule):**
   - Mặc định lưu/gửi vào đúng tài khoản Google Drive đã gắn của container đó (`aleron.dt@gmail.com` đối với NWL).
   - Trong trường hợp cấu hình có nhiều hơn 1 Google Drive, Agent **BẮT BUỘC PHẢI HỎI XÁC NHẬN (CONFIRM)** với User trước khi upload để chống phân mảnh dữ liệu.

#### D. File `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: end-of-file-fixer
      - id: trailing-whitespace
```

#### E. File `run.sh` (Kích hoạt nhanh Sandbox với cờ `--rm`)
```bash
#!/usr/bin/env bash
set -e

PROFILE="nwl"
PROFILE_PATH="$HOME/.cloud-profiles/$PROFILE"

if [ ! -d "$PROFILE_PATH" ]; then
    echo "[-] Thư mục profile $PROFILE_PATH không tồn tại!"
    exit 1
fi

echo "[+] Khởi chạy NWL Sandbox Container..."
docker run --rm -it \
    --name "nwl-sandbox-instance" \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    --tmpfs /dev/shm:rw,noexec,nosuid,size=64m \
    -v "$PROFILE_PATH":/workspace/.secrets:ro \
    -v "$(pwd)":/workspace \
    -e GDRIVE_TOKEN_PATH=/workspace/.secrets/gdrive/token.json \
    -e GMAIL_TOKEN_PATH=/workspace/.secrets/gmail/token.json \
    python:3.11-slim bash
```

---

## PHẦN VI: QUY TRÌNH 6 BƯỚC KHỞI TẠO BẤT KỲ DỰ ÁN MỚI NÀO (PROJECT CHECKLIST)

Mỗi khi tạo một App / Pipeline / Workflow mới, Agent và Lập trình viên bắt buộc tuân theo 6 bước sau:

* [ ] **Bước 1 (Hiến pháp):** Tạo `AGENTS.md` (hoặc `.cursorrules`) định nghĩa rõ giới hạn nghiệp vụ, email draft only, quy tắc dọn dẹp inbox.
* [ ] **Bước 2 (Chặn Secrets):** Tạo file `.gitignore` và `.pre-commit-config.yaml`, kích hoạt `pre-commit install`. Di chuyển credentials sang `~/.cloud-profiles/<tên_app>/`.
* [ ] **Bước 3 (Cấp phát GDrive Backup Riêng Biệt):** Bắt buộc cấp 01 Thư mục Google Drive Backup riêng (`_backup_folder_id` trong `gdrive_folder_map.json`) và tích hợp `scripts/auto_backup.py` ([File 08](file:///home/vpsg16gb/Documents/Structure/08_PROJECT_HYGIENE_AND_BACKUP_SPECIFICATION.md)).
* [ ] **Bước 4 (Container hóa & Khởi tạo Gatekeeper):** Khởi tạo thư mục `.devcontainer/devcontainer.json`, `docker/docker-compose.yml`, `docker/Dockerfile`, `run.sh` có cờ `--rm`, `cap_drop: [ALL]`, `tmpfs: /dev/shm`, và tạo bản thiết kế chốt chặn **`GATEKEEPERS.md`** cho dự án.
* [ ] **Bước 5 (Nạp Ngữ Cảnh AI):** Chạy lệnh `graft init` tại thư mục dự án và index vào `codebase-memory-mcp`.
* [ ] **Bước 6 (Tuân Thủ Modularity & TDD):** Kiểm tra toàn bộ mã nguồn viết ra đảm bảo $\le 150$ dòng/file, có Unit Test đi kèm và bọc `try-catch` retry 3 lần với I/O mạng.

---

## PHẦN VII: MẪU LỆNH TEAMWORK PREVIEW DÀNH CHO DEVOPS & INFRA

Khi cần phân công đội ngũ AI Subagents tự động hóa toàn bộ việc cài đặt hạ tầng và chuẩn hóa dự án, sử dụng mẫu lệnh `/teamwork-preview` sau:

```markdown
/teamwork-preview
Hãy đóng vai trò là một đội ngũ kỹ sư hạ tầng & DevOps tự động hóa, đọc kỹ tài liệu kiến trúc tại `/home/vpsg16gb/Documents/Structure/00_TONG_QUAN.md` và thực hiện đồng bộ 3 giai đoạn sau trên máy chủ `vpsg16gb`:

### GIAI ĐOẠN 1: CÀI ĐẶT & KIỂM TRA TOÀN BỘ CÔNG CỤ MUST-HAVE TRÊN MÁY HOST
1. Cài đặt DevContainer CLI: `npm install -g @devcontainers/cli`
2. Cài đặt pre-commit: `pip install --user pre-commit`
3. Cài đặt lazygit vào `~/.local/bin/` (tải release mới nhất từ GitHub)
4. Cài đặt lazydocker vào `~/.local/bin/` qua install script chính thức
5. Đảm bảo `~/.local/bin` đã được export vào `$PATH` trong `~/.bashrc`
6. Kiểm tra và xác nhận phiên bản hoạt động của toàn bộ 10 công cụ: `docker`, `docker compose`, `devcontainer`, `graft`, `codebase-memory-mcp`, `gstack`, `gitleaks`, `trufflehog`, `lazygit`, `lazydocker`.

### GIAI ĐOẠN 2: CẤU HÌNH LIÊN KẾT MCP TOÀN CỤC
1. Đăng ký máy chủ `codebase-memory-mcp` (`~/.local/bin/codebase-memory-mcp`) vào cấu hình MCP trong `~/.claude.json` và `agy_mcp_config.json`.
2. Kiểm tra khả năng khởi chạy stdio của Codebase Memory MCP.

### GIAI ĐOẠN 3: CHUẨN HÓA TOÀN DIỆN THƯ MỤC DỰ ÁN `/media/vpsg16gb/HaRiDisk/LIBRARY/NWL`
1. Bảo mật Credentials: Di chuyển an toàn toàn bộ token và client secrets từ `NWL/credentials/` sang thư mục bảo mật ngoài `~/.cloud-profiles/nwl/`.
2. Khởi tạo `.gitignore` tại gốc NWL để chặn đứng `.env`, `credentials/`, `*.json`, `*.enc`.
3. Tạo file `.pre-commit-config.yaml` và kích hoạt hook `pre-commit install`.
4. Thiết lập trọn bộ cấu hình DevContainer cho NWL:
   - Tạo `.devcontainer/devcontainer.json` (Non-root user `vscode`).
   - Tạo `docker/docker-compose.yml` (mount volume `:ro`, tmpfs `/dev/shm`, `security_opt`).
   - Tạo `docker/entrypoint.sh` và `run.sh` có cờ `--rm`.
5. Kích hoạt ngữ cảnh AI: Chạy lệnh `graft init` tại thư mục NWL.
6. Refactor mã nguồn: Rà soát các file vượt quá 150 dòng (`src/server.py`, `scripts/doc_signer.py`) và tách nhỏ thành các module chức năng $\le 150$ dòng.
7. Build thử nghiệm Docker container của NWL và xác nhận môi trường hoạt động hoàn hảo.
```
