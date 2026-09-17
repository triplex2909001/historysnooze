# 📖 FILE 1: KIẾN TRÚC MÃ NGUỒN BỀN VỮNG & HIẾN PHÁP RÀNG BUỘC AI (01_ARCHITECTURE_CONSTRAINED_AI.md)

## I. TRIẾT LÝ CONSTRAINED AI ENGINEERING (KỸ NGHỆ AI CÓ KHUÔN KHỔ)
Sự tự do là kẻ thù của codebase lớn. Khi dự án mở rộng, việc cho phép AI "tự do Vibe Coding" sẽ dẫn đến **Context Rot (Thối rữa ngữ cảnh)** và **Technical Debt Sprawl**. Do giới hạn của context window, AI sẽ mất dần khả năng nắm bắt toàn cục, dẫn đến việc tự chế code mới, ghi đè logic cũ một cách chắp vá và gây xung đột.

Để chấm dứt tình trạng này, **Antigravity Framework** chuyển dịch hoàn toàn sang kiến trúc **Constrained AI Engineering (Kỹ nghệ AI có khuôn khổ)**: AI không được tự quyết định kiến trúc, mà chỉ là người thợ xây thực thi theo một "Hiến pháp" (Rulebooks) bất di bất dịch được định nghĩa sẵn.

---

## II. LƯỚI GÁC CỔNG & PHÂN BỔ NGỮ CẢNH CỤC BỘ (LOCAL DEV TOOLS)
Để AI đọc code thông minh hơn, code sạch hơn và tốn ít token hơn, hệ thống bắt buộc (MUST-HAVE) phải cài đặt 3 mảnh ghép điều phối cục bộ sau ngay trên máy Host trước khi viết code:

### 1. GRAFT - Bản Đồ Ngữ Cảnh Tĩnh (Chống Phình Context Window)
*   **Vai trò:** Thay vì nạp toàn bộ mã nguồn thô vào AI gây quá tải, Graft dùng Tree-sitter tạo ra một thư mục `graft/` chứa các tệp Markdown tóm tắt chức năng và liên kết (Graph) của mã nguồn. Nó giúp tiết kiệm 42% token và 46% lượt gọi tool, đồng thời từ chối nạp các file nhạy cảm.
*   **Cài đặt:** `npm install -g @nanonets/graft`.
*   **Kích hoạt trong dự án:** Chạy `graft init` tại thư mục gốc. Thư mục `graft/` được tạo ra đóng vai trò như một bộ nhớ cache cục bộ (tự động thêm vào `.gitignore`).

### 2. CODEBASE MEMORY MCP - Truy Vấn Đồ Thị Động
*   **Vai trò:** Bổ trợ cho Graft, đây là máy chủ MCP (Model Context Protocol) viết bằng pure C siêu nhẹ. Nó dựng một Đồ thị tri thức (Knowledge Graph) bằng SQLite trên máy local. Khi gstack hoặc Claude Code cần tìm hiểu "Hàm A được gọi ở đâu?", nó truy vấn qua MCP với độ trễ <1ms thay vì phải đọc lại toàn bộ text.

### 3. GSTACK - Biệt Đội Phát Triển Ảo (Virtual Dev Team)
*   **Vai trò:** Biến AI (Claude Code/Codex) thành một bộ máy chuyên nghiệp với 23 vai trò khác nhau (CEO, QA, Tech Lead, Release Manager). AI sẽ tự động đi review code (`/review`), mở trình duyệt thật chạy QA (`/qa`) dựa trên cấu hình chuẩn của Y Combinator.
*   **Cài đặt lên máy (Global):**
    ```bash
    git clone https://github.com/garrytan/gstack.git ~/.codex/skills/gstack
    cd ~/.codex/skills/gstack && ./setup --host codex
    ```

---

## III. TIÊU CHUẨN MÃ NGUỒN & QUY TRÌNH PHÁT TRIỂN

### 1. Quy trình TDD (Test-Driven Development) Ép Buộc AI
Mỗi khi yêu cầu AI thêm tính năng hoặc sửa bug, Agent bắt buộc tuân theo quy trình kiểm thử trước tiên nhằm chống phá vỡ kiến trúc cũ:
1.  **Viết Unit Test trước:** Định nghĩa rõ test case cho tính năng cần làm.
2.  **Chạy test & Code logic:** Bắt AI code cho đến khi tất cả các test case đều chuyển xanh (Pass). Nếu sửa tính năng mới mà làm gãy tính năng cũ, test suite sẽ báo đỏ để tự phục hồi.

### 2. Tiêu chuẩn Modular & Chống Đứt Gãy
*   **Giới hạn dòng code:** Mọi file mã nguồn bị ép giới hạn **không vượt quá 150 dòng** để giữ ngữ cảnh hẹp tối đa cho AI. Logic, API và cấu hình môi trường phải được tách biệt ở các thư mục riêng.
*   **Cơ chế tự phục hồi (Self-Healing):** Mọi tác vụ có kết nối mạng (I/O, gọi API, upload Google Drive) bắt buộc phải bọc trong khối `try-catch` an toàn và thiết lập cơ chế **Retry tối thiểu 3 lần** trước khi báo lỗi.

---

## IV. BẢO MẬT & KIỂM SOÁT TỰ ĐỘNG TRƯỚC KHI PUSH (PRE-COMMIT GATEKEEPERS)
Sử dụng các công cụ Terminal mã nguồn mở để chặn đứng 100% rủi ro bảo mật và kiểm tra chất lượng tự động trước khi code rời khỏi máy:

### 1. Công cụ trực quan (Terminal UI)
Cài đặt `lazygit` và `lazydocker` trên Linux để kiểm duyệt code thủ công. Dùng `lazygit` để xem Git diff và nhanh chóng revert (hủy bỏ) các đoạn code hỏng do AI viết ra mà không cần nhớ lệnh phức tạp.

### 2. Lưới chặn Rò rỉ Token (Zero-Leak)
Không bao giờ tin tưởng AI 100% về việc giữ bảo mật. Anh cần gài **Gitleaks** và **TruffleHog** vào file `.pre-commit-config.yaml` để đánh hơi Token/Credentials:
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
**Khởi tạo bằng lệnh:** `pip install pre-commit && pre-commit install`. Khi anh gõ `git commit`, hệ thống tự quét, nếu thấy API key hoặc file > 500KB, nó sẽ **chặn đứng commit lại ngay lập tức**.

---

## V. BỘ LUẬT TỐI CAO "HIẾN PHÁP" CHO AI AGENT
Trong mọi thư mục gốc của dự án, bắt buộc phải có các file thiết lập định hướng cố định, tạo thành "Single Source of Truth" (Nguồn chân lý duy nhất).

*Tạo file **`AGENTS.md`** (hoặc `.cursorrules`) tại thư mục gốc của dự án và ép AI luôn đọc file này trước tiên:*
```markdown
# AGENT OPERATIONAL DIRECTIVES

1. MÔI TRƯỜNG & KIẾN TRÚC:
- Mọi module không vượt quá 150 dòng/file.
- Tuyệt đối không tự ý xóa bỏ các hàm, logic hoặc comments cũ khi chưa được người dùng xác nhận.

2. BẢO MẬT (ZERO-LEAK POLICY):
- CẤM TUYỆT ĐỐI hardcode API Key, Token (Telegram, Google, Cloudflare) vào code.
- Mọi thông tin nhạy cảm bắt buộc phải gọi qua `os.getenv()` hoặc `process.env`.

3. HẠ TẦNG LƯU TRỮ:
- Không lưu trữ vĩnh viễn trên máy cục bộ hoặc Docker host. 100% tệp tin I/O phải giao tiếp qua Google Drive API v3 (Resumable Upload 5MB/chunk).
```

Cùng với file **`.gitignore`** bắt buộc chặn đứng mọi file biến môi trường và bộ đệm:
```text
.env
*.env
*.json
project_vault.enc
graft/
__pycache__/
node_modules/
```
