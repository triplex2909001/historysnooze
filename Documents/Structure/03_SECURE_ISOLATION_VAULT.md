CHIẾN LƯỢC CÔ LẬP VÀ RAM-ONLY VAULT: 03_SECURE_ISOLATION_VAULT.MD

Trong kỷ nguyên Vibe Coding, việc cô lập môi trường thực thi không còn là một lựa chọn mà là lớp phòng thủ cuối cùng chống lại sự thoái hóa ngữ cảnh (Context Rot) và các cuộc tấn công Prompt Injection có chủ đích. Các nghiên cứu bảo mật (chiến dịch IDEsaster) xác nhận 100% các công cụ AI IDE hiện nay đều dễ tổn thương trước Prompt Injection, dẫn đến thực thi mã từ xa (RCE). Kiến trúc dưới đây được thiết kế theo tư duy Zero-Trust, triệt tiêu mọi khả năng rò rỉ secrets và ngăn chặn mã độc chuỗi cung ứng (ClawHavoc) ngay từ giai đoạn khởi tạo.

1. MÔ HÌNH CÔ LẬP 5 TẦNG (FIVE-LAYER ISOLATION TOPOLOGY)

Hệ thống bắt buộc phải vận hành qua 5 chốt chặn (Gatekeepers) để đảm bảo tính toàn vẹn của dữ liệu và ngăn chặn rò rỉ tài sản trí tuệ.

Tầng	Chức năng chính	Công nghệ sử dụng	Gatekeeper tương ứng
Tầng 0: Orchestrator	Điều phối, lọc nội dung nhạy cảm, quản lý Rate Limit.	Cloudflare Workers, Llama Guard 2	Gatekeeper 0: Distributed Lock & Account Dispatcher.
Tầng 1: L1 Matrix	Thực thi micro-chunks (TTS/STT) trong môi trường ephemeral.	Ephemeral Containers, OmniVoice, Whisper.	Gatekeeper 1: Unit QC (Size > 5KB, RMS, ONNX Exit Code).
Tầng 2: L2 Assembly	Hợp nhất phân đoạn, kiểm tra tính toàn vẹn chuỗi dữ liệu.	FFmpeg, Segment Logic.	Gatekeeper 2: Integrity QC (Sequence check, 0.5s silence).
Tầng 3: L3 Master	Kiểm định thượng tầng, chuẩn hóa Master và Compliance.	Google Drive API v3, EBU R128.	Gatekeeper 3: Compliance QC (-16 LUFS/Podcast, -14 LUFS/Video).
Tầng 4: Central Ledger	Ghi nhật ký trạng thái và báo cáo sự cố thời gian thực.	Google Sheets API, Telegram Bot API.	Gatekeeper 4: Atomic Update & Telegram Incident Report.

2. KIẾN TRÚC DEVCONTAINER RAM-ONLY VAULT

Nguyên lý "Zero-Leak" yêu cầu tuyệt đối không ghi secrets xuống đĩa ở trạng thái plaintext.

* Giải mã In-Memory: Secrets được lưu trữ dưới dạng file AES-256 (project_vault.enc). Khi khởi chạy, entrypoint giải mã trực tiếp vào /dev/shm (Shared Memory) - vùng bộ nhớ RAM tạm thời.
* Bảo vệ bằng --tmpfs: Thư mục secrets trong container phải được gắn (mount) bằng --tmpfs để đảm bảo dữ liệu chỉ tồn tại trong RAM và biến mất ngay khi container dừng.
* Cơ chế Tự hủy (Auto-destruct): Bắt buộc sử dụng tham số --rm để xóa sạch mọi dấu vết thực thi sau khi hoàn thành tác vụ.

3. BỘ KHUÔN MẪU CẤU TRÚC 4 FILE (CORE TEMPLATE SPECIFICATIONS)

3.1. devcontainer.json (Môi trường phát triển chuẩn)

Nghiêm cấm chạy container dưới quyền root.

* Features: Khóa cứng việc cài đặt gitleaks và trufflehog để quét secrets tự động.
* remoteUser: Phải thiết lập user không có quyền root (vscode hoặc node) để hạn chế blast radius nếu bị RCE qua Prompt Injection.

3.2. docker-compose.yml (Cấu hình tài nguyên cô lập)

Sử dụng image cố định phiên bản để tránh rủi ro chuỗi cung ứng.

services:
  sandbox:
    image: python:3.11-slim
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    volumes:
      - .:/workspace:cached
    tmpfs:
      - /dev/shm:rw,noexec,nosuid,size=64m
    working_dir: /workspace


3.3. entrypoint.sh (Cơ chế giải mã In-Memory)

Script này là chốt chặn cuối cùng kiểm soát việc giải mã secrets.

#!/bin/bash
set -e

# Kiểm tra biến môi trường bắt buộc
if [ -z "$MASTER_VAULT_PASS" ]; then
    echo "ERROR: MASTER_VAULT_PASS is not set. Aborting."
    exit 1
fi

VAULT_FILE="/workspace/.secrets/project_vault.enc"
RAM_ENV_DIR="/dev/shm/.vault"

if [ -f "$VAULT_FILE" ]; then
    mkdir -p "$RAM_ENV_DIR"
    chmod 700 "$RAM_ENV_DIR"
    # Giải mã AES-256 PBKDF2 trực tiếp vào RAM
    openssl enc -aes-256-cbc -d -salt -pbkdf2 -in "$VAULT_FILE" \
    -out "$RAM_ENV_DIR/secrets.json" -pass env:MASTER_VAULT_PASS
    echo "[+] Secrets decrypted to RAM-Only Vault (/dev/shm)."
fi

exec "$@"


3.4. run.sh (Script kích hoạt Sandbox)

Bắt buộc mount profile secrets dưới dạng ReadOnly (:ro).

#!/usr/bin/env bash
PROFILE=${1:-default}
PROFILE_PATH="$HOME/.cloud-profiles/$PROFILE"

if [ ! -d "$PROFILE_PATH" ]; then
    echo "[-] Profile $PROFILE does not exist!"
    exit 1
fi

docker run --rm -it \
    --name "vibe-sandbox-$PROFILE" \
    --env-file .env \
    --tmpfs /dev/shm:rw,noexec,nosuid,size=64m \
    -v "$PROFILE_PATH":/workspace/.secrets:ro \
    -v "$(pwd)":/workspace \
    sandbox-image bash


4. QUY TRÌNH GATEKEEPER & KIỂM ĐỊNH CHẤT LƯỢNG (QC)

* [ ] QC L1 (Unit): Kiểm tra dung lượng file (>5KB) và mức RMS âm thanh; ONNX exit code phải bằng 0.
* [ ] QC L2 (Assembly): Kiểm tra tính đầy đủ của chuỗi Sequence (không mất chunk); khoảng lặng Paragraph gộp chuẩn 0.5s.
* [ ] QC L3 (Master): Chuẩn hóa Loudness (EBU R128): -16 LUFS (Podcast) hoặc -14 LUFS (Video).
* [ ] QC L4 (Ledger): Cập nhật trạng thái Atomic lên Google Sheets và đẩy Incident Report qua Telegram nếu phát hiện lỗi.

5. CHỈ DẪN BẢO MẬT VÀ QUY TẮC CỐT LÕI

1. Tuyệt đối không Hardcode: Sử dụng os.getenv cho mọi API Key. Khóa cứng phiên bản thư viện: google-api-python-client==2.118.0, sherpa-onnx==1.10.20, faster-whisper==1.0.1.
2. Cảnh báo "Ảo giác Package" (Slopsquatting): Dogoo Software cảnh báo 20% package AI đề xuất là bịa đặt. Phải kiểm tra sự tồn tại của thư viện trên PyPI/NPM trước khi cài đặt.
3. Xác thực Row Level Security (RLS): Nghiêm cấm việc chỉ kiểm tra "đã đăng nhập". Phải kiểm tra "quyền sở hữu dữ liệu" (Ownership) để tránh rò rỉ chéo dữ liệu giữa các tài khoản.
4. Chống Shadow AI: Mọi Agent/Script triển khai mới phải được review bởi con người. Không deploy nhanh hơn khả năng kiểm soát của hệ thống bảo mật.
5. Cơ chế Resilience: Mọi tác vụ I/O bắt buộc có cơ chế Retry tối thiểu 3 lần.
6. Kiểm soát Context Rot: Chia nhỏ module (<150 dòng/file). Sử dụng AGENTS.md để áp đặt luật kiến trúc cố định cho LLM.
7. Cô Lập Telegram Bot & Cấm Cross-Container Fallback: Mỗi container chỉ được phép sử dụng DUY NHẤT Bot Token và Chat ID được cấp phát riêng trong vault của container đó. CẤM TUYỆT ĐỐI việc tự ý lấy Token/Chat ID của container khác làm dự phòng khi gặp lỗi. Nếu container chưa có cấu hình Telegram hoặc gặp lỗi gửi tin, AI Agent BẮT BUỘC PHẢI DỪNG LẠI VÀ HỎI USER để xin phép.

6. XỬ LÝ SỰ CỐ & PHỤC HỒI (TROUBLESHOOTING)

Sự cố: Chunk L1 bị lỗi hoặc timeout giữa chừng | Khắc phục: Kích hoạt lại orchestrator_planner.py để check file trên Drive và chỉ chạy tiếp các chunk thiếu.

Sự cố: Gatekeeper chặn do lỗi LUFS | Khắc phục: Chạy script FFmpeg với filter loudnorm theo đúng chuẩn (-16 LUFS Podcast / -14 LUFS Video).

Sự cố: Chặn đăng bài do trùng Content Hash | Khắc phục: Đây là cơ chế bảo mật. Không xóa bản ghi cũ trong Publish_Ledger trừ khi có thay đổi nội dung.

Sự cố: Lộ Secrets trong lịch sử Git | Khắc phục: Xóa commit là không đủ. Bắt buộc thu hồi (rotate) và thay đổi toàn bộ API Keys ngay lập tức.
