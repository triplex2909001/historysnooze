# HISTORYSNOOZE PROJECT INSTRUCTIONS & IMMUTABLE USER RULES

## I. NGUYÊN TẮC BẮT BUỘC: SINGLE SOURCE OF TRUTH (RAG CỐ ĐỊNH)

Mọi hoạt động phân tích, tạo kịch bản, sinh prompt hình ảnh, xử lý voiceover, và render video BẮT BUỘC phải đọc và tuân thủ tuyệt đối các tài liệu SSOT tại thư mục `Documents/Structure/` (gốc từ NotebookLM `813e73eb-7327-4c9b-9651-fe416e6d180c`):

1. **Khởi tạo Thư mục Cố định (Scaffolding Ngay Từ Đầu)**:
   - Ngay khi duyệt IDEA (`Status = Pending` $\rightarrow$ `Script`), hệ thống BẮT BUỘC phải khởi tạo đủ **3 Thư Mục Cốt Lõi + 3 Subfolders** trên cả VPS và Google Drive thông qua [`00.codebases/project_scaffolder.py`](file:///media/vpsg16gb/Media/historysnooze/00.codebases/project_scaffolder.py):
     ```text
     📁 [Nhân Vật] - [Tiêu Đề YouTube]/
     ├── 📁 01. Preproduction/
     ├── 📁 02. Media Generation/
     │   ├── 📁 audio/
     │   ├── 📁 keyframes/
     │   └── 📁 combined/
     └── 📁 03. Final Production/
     ```
2. **Quy trình Tiền kỳ Nguyên tử (Atomic Pre-Production Bundle)**:
   - BẮT BUỘC sinh trọn gói cùng lúc **7 files cốt lõi** vào `01. Preproduction/` và mirror sang `02. Media Generation/combined/` thông qua [`00.codebases/preproduction_pipeline.py`](file:///media/vpsg16gb/Media/historysnooze/00.codebases/preproduction_pipeline.py):
     1. `Script - [Tên].docx`
     2. `Outline - [Tên].docx`
     3. `script_full.md`
     4. `outline.json`
     5. `metadata.json`
     6. `combined_voiceover.txt` (150 chunks)
     7. `combined_imageprompts.txt` (150 beats 3-Tier chuẩn `04_VISUAL_PROMPT_ENGINE.md`)
3. **Sinh Image Prompt**: BẮT BUỘC tuân thủ 100% tài liệu [`Documents/Structure/04_VISUAL_PROMPT_ENGINE.md`](file:///media/vpsg16gb/Media/historysnooze/Documents/Structure/04_VISUAL_PROMPT_ENGINE.md).
   - Đủ **150 beats** (10 beats/part).
   - Ghép qua công thức **3-Tier Visual Formula** (Scene Beat + Cultural/Period Anchor + Signature Frame Tail).
   - Tuyệt đối CẤM cú pháp Midjourney (`--ar 16:9`, `--v 6.0`, `--style raw`).
   - Tuyệt đối CẤM các từ khóa cấm: `photorealistic`, `3d render`, `cgi`, `octane render`, `border`, `frame`, `.gif`.
4. **Xử lý Voiceover**: BẮT BUỘC sử dụng 100% model **`k2-fsa/OmniVoice`** với Voice Milo reference ID `1VC_eN0rnm9l2d4ilogn9B2GqWzzaV4fS`. Tuyệt đối CẤM `edge_tts`, `pyttsx3`, `espeak`.
5. **Cấu trúc Kịch bản**: BẮT BUỘC tuân thủ [`Documents/Structure/00_TONG_QUAN.md`](file:///media/vpsg16gb/Media/historysnooze/Documents/Structure/00_TONG_QUAN.md) & [`Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md`](file:///media/vpsg16gb/Media/historysnooze/Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md).
6. **Kiểm tra Gatekeepers**: BẮT BUỘC chạy kiểm định GK1, GK2, GK3, GK4 theo [`GATEKEEPERS.md`](file:///media/vpsg16gb/Media/historysnooze/GATEKEEPERS.md) trước khi đồng bộ lên Google Drive.
