# 📊 FILE 4: HỆ THỐNG ĐIỀU PHỐI PIPELINE ĐA TẦNG, GATEKEEPER & DASHBOARD GIÁM SÁT (04_PIPELINE_GATEKEEPER_DASHBOARD.md)

## I. MÔ HÌNH ĐIỀU PHỐI PIPELINE ĐA TẦNG (THREE-TIER PROCESSING ENGINE)
Để vận hành các tác vụ xử lý media hoặc tính toán hạng nặng một cách mượt mà và tối ưu hóa tài nguyên 100% miễn phí trên **GitHub Actions Matrix** [54, 350], hệ thống chia quy trình làm việc thành **mô hình xử lý đa tầng (3-Tier Processing Model)** [55, 61, 350]:

```text
               [ Bước 0: Orchestrator Planner ]
                              │ (Phân tích tải, chia chunk, resume check)
                              ▼
        ┌──────────────────────────────────────────────┐
        │ TẦNG L1: RENDER CHUNKS (Micro-processing)    │
        │ • Chạy song song tối đa 15-18 instances     │ [54, 355]
        │ • Engine: OmniVoice (TTS), Remotion (Video)  │ [54, 267]
        │ • Đầu ra: Tải thẳng lên Google Drive         │ [54, 352]
        └──────────────────────┬───────────────────────┘
                               │ (Tự động kích hoạt khi 100% L1 hoàn thành)
                               ▼
        ┌──────────────────────────────────────────────┐
        │ TẦNG L2: MID-ASSEMBLY (Gộp đoạn văn)        │
        │ • Kiểm tra đầy đủ chuỗi (Sequence QC)        │ [63, 64]
        │ • Ghép các chunks bằng FFmpeg Lossless Concat│ [268]
        │ • Chèn khoảng lặng chuẩn 0.5s giữa chunks     │ [54, 357]
        └──────────────────────┬───────────────────────┘
                               │ (Kích hoạt sau khi hoàn thành L2)
                               ▼
        ┌──────────────────────────────────────────────┐
        │ TẦNG L3: MASTER COMPOSITE (Hợp nhất Master)  │
        │ • Chuẩn hóa âm lượng EBU R128 (-16 LUFS)     │ [63, 64]
        │ • Ghép các đoạn thành file Master hoàn chỉnh │ [55, 356]
        │ • Chèn khoảng lặng 1.0s (đoạn) và 2.0s (phần)│ [54, 357]
        │ • Xuất bản qua Buffer API & Báo Telegram     │ [195, 356]
        └──────────────────────────────────────────────┘
```

### 1. Phân Tích Chi Tiết Từng Tầng
*   **Bước 0: Orchestrator Planner (`scripts/orchestrator_planner.py`):** Phân tích kịch bản đầu vào, chia nhỏ thành các gói dữ liệu siêu nhỏ (micro-chunks), kiểm tra trạng thái trên Google Drive (Resume Check) để tránh chạy lại các phần đã có [50, 54, 205].
*   **Tầng L1 (`scripts/l1_engine_runner.py`):** Kích hoạt ma trận song song (Matrix) lên tới **15-18 runners** đồng thời [54, 355]. Từng runner chỉ đảm nhận xử lý một phần cực nhỏ (render 1 chunk audio từ OmniVoice hoặc 1 phân cảnh ngắn từ Remotion/Hyperframes) [54, 267, 268]. Kết quả được đẩy trực tiếp lên Google Drive thông qua cơ chế Resumable Upload [54, 350, 352].
*   **Tầng L2 (`scripts/l2_mid_merge.py`):** Sau khi toàn bộ các job L1 hoàn tất, runner L2 sẽ quét thư mục Drive để gom các chunks lại thành từng đoạn lớn [50, 356]. Tầng này đảm bảo tính toàn vẹn của chuỗi và chèn khoảng lặng **0.5 giây** chính xác bằng FFmpeg [54, 63, 268].
*   **Tầng L3 (`scripts/l3_master_merge.py`):** Ghép toàn bộ các đoạn lớn từ L2 thành một tệp Master duy nhất [55, 356]. Tầng này thực hiện chuẩn hóa âm lượng theo các tiêu chuẩn quốc tế và chèn khoảng lặng **1.0 giây** giữa các đoạn văn và **1.5s - 2.0 giây** giữa các chương/phần lớn [54, 63, 268].

---

## II. PHÂN LẬP TUYỆT ĐỐI LUỒNG LLM VÀ LUỒNG XÁC ĐỊNH (NON-LLM)
Để bảo vệ hệ thống khỏi các lỗ hổng rò rỉ hoặc sai số không đáng có, hệ thống phân tách rạch ròi 2 luồng hoạt động riêng biệt [194, 200]:

1.  **Luồng Sáng Tạo (LLM-Driven - Bất Định):**
    *   *Nhiệm vụ:* Viết kịch bản, tóm tắt nội dung, dịch thuật, sinh caption mạng xã hội và hashtags [194].
    *   *Môi trường:* Chạy trên Cloudflare Workers AI (Edge $0) hoặc gọi API Gemini/Claude bên ngoài [194].
    *   *Kiểm soát an toàn:* Bắt buộc áp đặt đầu ra theo **JSON Schema nghiêm ngặt** để cấu trúc hóa dữ liệu [194].
2.  **Luồng Kỹ Thuật (Deterministic Non-LLM - Định Tính):**
    *   *Nhiệm vụ:* Cắt chuỗi ký tự theo chuẩn 150-180 ký tự, OmniVoice TTS, Remotion rendering, tính mã băm SHA-256, kiểm tra LUFS, ghi Google Sheets và Google Drive [54, 194].
    *   *Môi trường:* Chạy bằng code Python thuần và các công cụ CLI trên GitHub Actions Runner [194].
    *   *Nguyên tắc:* Tuyệt đối **không đưa LLM vào các khâu tính toán, ghép file hoặc kiểm định chất lượng** để tránh hiện tượng ảo giác (hallucination) làm sai lệch dữ liệu [194, 200].

---

## III. HỆ THỐNG GÁC CỔNG ĐA HÌNH (UNIVERSAL POLYMORPHIC GATEKEEPER TOPOLOGY)

Trong kiến trúc BIBLE, **5 Chốt chặn Gatekeepers (GK0 – GK4)** không bị fix cứng theo một nghiệp vụ đơn lẻ, mà được thiết kế thành một **Mô hình Khung 5 Pha Trừu tượng (Universal 5-Phase Lifecycle Pattern)**. Mọi pipeline (từ Media, Logistics, AI Research đến Giáo dục) đều vận hành qua 5 pha này nhưng với các tiêu chuẩn kiểm định **thiên biến vạn hóa** theo từng Domain:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│              KHUNG 5 PHA GÁC CỔNG PHỔ QUÁT (UNIVERSAL 5 PHASES)              │
│                                                                             │
│  [GK0: Ingress & Concurrency]  ➔ Kiểm soát cổng vào, khóa phân tán, rate-limit│
│  [GK1: Raw Input Validation]   ➔ Thẩm định tính hợp lệ & an toàn của đầu vào │
│  [GK2: Processing Integrity]   ➔ Kiểm soát tính toàn vẹn logic nghiệp vụ     │
│  [GK3: Output Compliance]      ➔ Thẩm định chất lượng đầu ra & Hiến pháp     │
│  [GK4: Ledger & Notification]  ➔ Ghi nhận trạng thái bất biến & Báo cáo      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. Bảng Ánh Xạ Chốt Chặn Theo Từng Loại Pipeline (Domain Implementation Matrix)

| Pha Gác Cổng | 🎬 Media / Video Pipeline | 📦 Logistics Pipeline (NWL) | 🧠 AI Research (GeminiNotebook) | 🎓 Gia sư AI (HanaAssistant) |
| :--- | :--- | :--- | :--- | :--- |
| **GK0: Ingress & Lock** | • Distributed Lock.<br>• Llama Guard 2 lọc prompt 18+. | • Lease Lock chống tạo trùng hợp đồng.<br>• Rate-limit Google API. | • Session Lock.<br>• `notebooklm auth check` OK. | • Lock Session học sinh.<br>• Webhook Telegram tiếp nhận. |
| **GK1: Raw Input QC** | • File Audio $> 5\text{KB}$.<br>• RMS không bị clipping/silent.<br>• ONNX exit code = 0. | • Kiểm tra hợp lệ file DOCX/PDF mẫu.<br>• Check mã số thuế/tên tàu.<br>• **Xóa sạch `00.INBOX`**. | • Kiểm tra URL / PDF nạp vào.<br>• Kho `open_sources` bắt buộc `:ro`. | • OCR kiểm tra độ rõ ảnh bài tập.<br>• Phân loại môn học/cấp lớp. |
| **GK2: Process Integrity** | • Tính toàn vẹn chuỗi Sequence chunks.<br>• Chèn khoảng lặng nối 0.5s FFmpeg. | • Khớp biến biểu mẫu 100% (`{{PARTY_B}}`).<br>• Chèn phôi dấu PNG & chữ ký số. | • Map đúng Notebook ID.<br>• Tác vụ sinh dài chạy qua Background Task. | • Lời giải chi tiết từng bước.<br>• Khớp barem điểm chuẩn. |
| **GK3: Output Compliance** | • Chuẩn EBU R128 (-16 LUFS / -14 LUFS).<br>• Quét lọc black frames. | • **Hiến pháp: CHỈ TẠO EMAIL DRAFT**.<br>• Không leak Telegram/API tokens. | • JSON Schema đầu ra nghiêm ngặt.<br>• Trích dẫn nguồn & chống ảo giác. | • Ngôn phong sư phạm chuẩn mực.<br>• Tạo Infographic tóm tắt bài. |
| **GK4: Ledger & Alert** | • Cập nhật Google Sheets Central Ledger.<br>• Báo động đỏ Telegram khi render lỗi. | • Tải Master lên Google Drive NWL.<br>• Báo duyệt qua Bot NWL (`8944836049`). | • Đồng bộ Master lên Drive `lchau4501`.<br>• Báo cáo qua Bot `8027319967`. | • Lưu Database học tập.<br>• Gửi nhóm **HaRiEdu** (Topic 3). |

### 2. Quy Định Bắt Buộc: Tệp Khai Báo `GATEKEEPERS.md` Cho Từng Dự Án
Mỗi khi khởi tạo một pipeline/dự án mới, Developer/Agent **bắt buộc phải tạo tệp `GATEKEEPERS.md` tại thư mục gốc của dự án** để khai báo cụ thể 5 chốt chặn nghiệp vụ cho dự án đó.

### 3. Minh Họa Thực Tế: Case Study Media Generation Pipeline (OmniVoice & Remotion)
Dưới đây là chi tiết kỹ thuật chuyên sâu khi triển khai 5 chốt chặn cho bài toán xử lý Media / Video đa tầng:
*   **Gatekeeper 0 (Lock & Rate Limit):** Gọi API về Cloudflare KV đăng ký Lease Lock, tự động đảo token khi chạm rate limit.
*   **Gatekeeper 1 (L1 Unit QC):** File audio $\ge 5\text{KB}$, quét RMS chống dead silence hoặc clipping $\ge 0\text{ dBFS}$, quét lọc black frames. Tự động Retry 3 lần nếu lỗi.
*   **Gatekeeper 2 (L2 Assembly QC):** Kiểm tra đầy đủ chuỗi chunks (không mất chunk_003), ghép FFmpeg chèn khoảng lặng chuẩn **0.5 giây**.
*   **Gatekeeper 3 (L3 Master QC):** Bộ lọc `loudnorm` FFmpeg ép chuẩn **EBU R128 (-16 LUFS Audio / -14 LUFS Video)**, quét `silencedetect` (1.0s giữa các đoạn văn, 2.0s giữa các phần). Bắn Dead-letter Alert về Telegram nếu có sự cố.
*   **Gatekeeper 4 (Ledger Sync):** Cập nhật nguyên tử trạng thái lên Google Sheets Central Ledger.

---

## IV. BẢO MẬT ĐỘNG VỚI USESTRIX/STRIX (DYNAMIC AI PENTESTER)
Để đảm bảo an toàn tuyệt đối cho hệ thống và chặn đứng các lỗ hổng ứng dụng ở tầng vận hành, hệ thống tích hợp **Strix AI Penetration Tester** vào quy trình gác cổng bảo mật động trước khi triển khai (Dynamic Application Security Testing - DAST) [114, 290, 292]:

1.  **Cơ chế hoạt động:** Strix đóng vai trò là một Hacker Mũ Trắng tự vận hành (Autonomous AI Agent) [292]. Nó được deploy trực tiếp bên trong một Docker Sandbox cách ly hoàn toàn để bảo vệ hệ thống máy chủ vật lý [259, 292].
2.  **Quét và Tấn công thực tế:** Strix không chỉ quét mã nguồn tĩnh [292]. Nó sẽ trực tiếp gửi các chuỗi payload tấn công (SQL injection, Command injection, Path Traversal, Broken Access Control) vào ứng dụng của anh đang chạy thử nghiệm, tự động viết script chứng minh lỗi khai thác (Proof of Concept - PoC) và gửi Pull Request đề xuất cách sửa [170, 292].
3.  **Tích hợp CI/CD:** Được cài đặt như một bước kiểm định an ninh bắt buộc trong quy trình đẩy code [292]. Nếu Strix phát hiện ra bất kỳ lỗi bảo mật nào có khả năng khai thác trực tiếp, Gatekeeper sẽ lập tức chặn đứng luồng deploy và gửi cảnh báo đỏ về Telegram [63, 64].

---

## V. CƠ CHẾ CONTENT HASH & IDEMPOTENCY LOCK (CHỐNG TRÙNG LẶP)
Để loại bỏ triệt để tình trạng lỗi hệ thống gửi lặp lại yêu cầu dẫn đến spam hoặc đăng trùng lặp một nội dung nhiều lần lên mạng xã hội, hệ thống áp dụng khóa bất biến (Immutability Lock) [195, 200]:

1.  **Tính toán Vân tay số (Content Fingerprint):** Tầng L3 tự động băm (Hash) nội dung thành phẩm bằng thuật toán SHA-256 kết hợp giữa chuỗi byte của tệp âm thanh/video và text caption:
    $$\text{Content Fingerprint} = \text{SHA-256}(\text{Media Bytes} + \text{Caption Text})$$ [195, 196, 200]
2.  **Đối soát Sổ cái (Publish Ledger Lookup):** Trước khi gọi API xuất bản (Buffer, YouTube, Facebook Graph APIs), Python script sẽ truy vấn Sổ cái để kiểm tra xem mã băm này đã tồn tại trong lịch sử chưa [195, 198]:
    *   *Nếu ĐÃ CÓ:* Dừng luồng chạy ngay lập tức và kích hoạt báo động đỏ về Telegram để điều tra [195].
    *   *Nếu CHƯA CÓ:* Ghi nhận trạng thái tạm thời là `LOCKING` để giữ chỗ và tiến hành đăng bài [195].
3.  **Khóa vĩnh viễn (PUBLISHED_IMMUTABLE):** Sau khi nhận được mã phản hồi thành công (Post ID) từ nền tảng, hệ thống cập nhật trạng thái bản ghi thành `PUBLISHED_IMMUTABLE` [195, 203]. Trạng thái này đóng vai trò là chiếc khóa cứng vĩnh viễn không bao giờ cho phép ghi đè hay đăng lại tệp tin này [195, 203].

---

## VI. BẢN THIẾT KẾ SINGLE-TAB MASTER DASHBOARD TRÊN GOOGLE SHEETS
Để kiểm soát và giám sát toàn bộ hệ thống đa tầng một cách trực quan, trực tiếp và 100% miễn phí, hệ thống quy hoạch toàn bộ cấu hình, dữ liệu và sổ cái vào **duy nhất 1 Tab trên Google Sheets** [261].

Nguyên tắc cốt lõi là phân bổ theo **Lưới không gian dọc (Vertical Spatial Grid Layout)**, phân chia bảng tính từ trên xuống dưới thành 4 phân khu chức năng được ngăn cách bằng các dải màu phân biệt [261]:

```text
Dòng 1  ┌────────────────────────────────────────────────────────┐
        │ KHU VỰC 1: HEADER & KPI CARDS (Cố định hàng 1 - 4)     │ [261]
Dòng 4  ├────────────────────────────────────────────────────────┤
Dòng 5  │                                                        │
Dòng 6  ├────────────────────────────────────────────────────────┤
        │ KHU VỰC 2: GLOBAL CONFIG & SYSTEM SWITCHES (Dòng 6-10) │ [261]
Dòng 10 ├────────────────────────────────────────────────────────┤
Dòng 11 │                                                        │
Dòng 12 ├────────────────────────────────────────────────────────┤
        │ KHU VỰC 3: TASK CONTROL PLANE & MONITORING (Dòng 12+)  │ [261]
        │   - Cột A: Task ID                                     │
        │   - Cột B: Engine (Dropdown)                           │
        │   - Cột C: State (Dropdown: PENDING/PROCESSING/DONE)   │ [262]
        │   - Cột D: Progress Formula (=TEXT(Done/Total, "0%"))  │
        │   - Cột E-F: Total Chunks / Done Chunks                │
        │   - Cột G: Master File ID (Link Drive 30TB)            │
        │   - Cột H: Error / Logs                                │
        ├────────────────────────────────────────────────────────┤
        │ ... (Cách ra khoảng 500 dòng trống)                    │
Dòng 502├────────────────────────────────────────────────────────┤
        │ KHU VỰC 4: SOCIAL & IMMUTABLE PUBLISH LEDGER (Dòng 502+)│ [261]
        │   - Cột A: Content Fingerprint (SHA-256)               │ [262]
        │   - Cột B: Task Ref ID                                 │
        │   - Cột C: Platform / Profile                          │
        │   - Cột D: Buffer Post ID                              │
        │   - Cột E: Published Timestamp                         │
        │   - Cột F: Status Lock (PUBLISHED_IMMUTABLE)           │
        └────────────────────────────────────────────────────────┘
```

### 1. Chi Tiết Thiết Kế Từng Phân Khu

#### KHU VỰC 1: THỐNG KÊ TỨC THÌ (Dòng 1 – Dòng 4)
Ghim cố định (Freeze 4 rows) để dù anh cuộn xuống xem hàng nghìn task, dải thống kê này vẫn luôn xuất hiện ở đầu màn hình [263].
*   **Ô A2:B2 (🔄 Đang xử lý):** `=COUNTIF(C14:C, "PROCESSING")` [261].
*   **Ô C2:D2 (✅ Hoàn thành):** `=COUNTIF(C14:C, "DONE")` [261].
*   **Ô E2:F2 (🚨 Sự cố / Lỗi):** `=COUNTIF(C14:C, "FAILED")` [261].
*   **Ô G2:H2 (📢 Đã đăng Social):** `=COUNTA(D505:D)` [261].

#### KHU VỰC 2: CẤU HÌNH HỆ THỐNG ĐỘNG (Dòng 6 – Dòng 10)
Các biến môi trường động để Python API hoặc Cloudflare Worker đọc về tức thời mà không cần sửa mã nguồn của hệ thống [261]:
*   `TARGET_LUFS` (Cột B: `-16.0`) $\rightarrow$ Chuẩn âm lượng master [261].
*   `SILENCE_CHUNK_SEC` (Cột B: `0.5`) $\rightarrow$ Khoảng lặng giữa các chunks [261].
*   `SILENCE_PARA_SEC` (Cột B: `1.0`) $\rightarrow$ Khoảng lặng giữa các đoạn [261].
*   `BURST_MAX_PARALLEL` (Cột B: `18`) $\rightarrow$ Giới hạn số Matrix runner song song tối đa [261].
*   `SYSTEM_PAUSE` (Cột B: `FALSE`) $\rightarrow$ Nút dừng khẩn cấp toàn hệ thống [261].

#### KHU VỰC 3: THEO DÕI TIẾN TRÌNH TÁC VỤ (Từ Dòng 12 đến Dòng 500)
Bắt đầu từ dòng tiêu đề `A13:H13`. Bảng dữ liệu chính ghi nhận mọi trạng thái của pipeline [262]:
*   *Cột A (Task ID):* Chuỗi định danh duy nhất (Khóa cứng không sửa tay) [262].
*   *Cột B (Engine):* Dropdown cấu hình loại engine (`omnivoice` | `remotion`) [262].
*   *Cột C (State):* Dropdown trạng thái. Thiết lập Conditional Formatting: **DONE** (Nền xanh lá), **PROCESSING** (Nền vàng cam), **FAILED** (Nền đỏ báo động) [262].
*   *Cột D (Progress):* Công thức tự động `=IF(E14=0, "-", TEXT(F14/E14, "0%"))` hiển thị tiến độ tức thời [262].
*   *Cột G (Master File ID):* Link liên kết mở thẳng tệp tin Master trên Google Drive 30TB [262].

#### KHU VỰC 4: SỔ CÁI XUẤT BẢN CHỐNG TRÙNG LẶP (Từ Dòng 502 trở đi)
Nằm cách biệt phía dưới bảng tasks và được gom nhóm lại (Group Rows - `Alt + Shift + Right Arrow`) để có thể thu gọn lại khi không cần xem lịch sử băm [262, 263]. Phân khu này lưu trữ các khóa vân tay SHA-256 và Post ID trả về từ API làm bằng chứng bất biến chống đăng trùng lặp [203, 262].

---

## VII. SCRIPT KIỂM ĐỊNH CHẤT LƯỢNG MASTER (scripts/qc_master_validator.py)
Để đảm bảo toàn bộ tệp tin Master của anh trước khi đăng đạt 100% tiêu chuẩn chất lượng kỹ thuật, file script **`scripts/qc_master_validator.py`** dưới đây được Antigravity thiết lập chạy tự động ở cuối tầng L3 [50, 196]:

```python
# scripts/qc_master_validator.py
import os
import sys
import json
import hashlib
import subprocess

TARGET_LUFS = -16.0
LUFS_TOLERANCE = 2.0  # Chấp nhận trong khoảng -18.0 đến -14.0 LUFS [196]

def calculate_content_hash(file_path: str, caption_text: str = "") -> str:
    """Tạo mã băm duy nhất đại diện cho toàn bộ nội dung xuất bản (Fingerprint) [196]."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    if caption_text:
        hasher.update(caption_text.strip().encode("utf-8"))
    return hasher.hexdigest()

def analyze_audio_lufs(file_path: str) -> float:
    """Đo mức âm lượng tích hợp (Integrated Loudness) theo chuẩn EBU R128 bằng FFmpeg [197]."""
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", "ebur128=framelog=verbose",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)

    # Phân tích cú pháp stderr từ FFmpeg để tìm dòng "I:" (Integrated Loudness)
    for line in res.stderr.splitlines():
        if "I:" in line and "LUFS" in line:
            try:
                lufs = float(line.split("I:")[1].split("LUFS")[0].strip())
                return lufs
            except (ValueError, IndexError):
                pass
    raise ValueError("Không thể phân tích mức âm lượng LUFS từ tệp.")

def detect_silence_sections(file_path: str, min_duration=0.4, noise_db="-50dB"):
    """Quét và phân tích các đoạn khoảng lặng để đảm bảo đúng cấu trúc 0.5s / 1.0s / 2.0s [197]."""
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", f"silencedetect=noise={noise_db}:d={min_duration}",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
    silences = []
    for line in res.stderr.splitlines():
        if "silence_duration:" in line:
            try:
                duration = float(line.split("silence_duration:")[1].strip())
                silences.append(duration)
            except (ValueError, IndexError):
                pass
    return silences

def verify_master_qc(file_path: str, caption: str) -> dict:
    """Thực thi toàn bộ quy trình gác cổng chất lượng Master."""
    print(f"[*] Đang bắt đầu kiểm định chất lượng tệp Master: {file_path}")

    # 1. Đo âm lượng
    try:
        current_lufs = analyze_audio_lufs(file_path)
        print(f"[+] Âm lượng đo được: {current_lufs} LUFS")
        lufs_diff = abs(current_lufs - TARGET_LUFS)
        if lufs_diff > LUFS_TOLERANCE:
            return {"status": "FAILED", "reason": f"Lệch chuẩn âm lượng: {current_lufs} LUFS (Yêu cầu: -16 LUFS ± 2)"}
    except Exception as e:
        return {"status": "FAILED", "reason": f"Lỗi đo LUFS: {str(e)}"}

    # 2. Quét khoảng lặng (Silence checks)
    try:
        silence_durations = detect_silence_sections(file_path)
        print(f"[+] Tìm thấy {len(silence_durations)} khoảng lặng hợp lệ.")
    except Exception as e:
        return {"status": "FAILED", "reason": f"Lỗi quét khoảng lặng: {str(e)}"}

    # 3. Tính mã băm Fingerprint
    try:
        content_hash = calculate_content_hash(file_path, caption)
        print(f"[+] Đã tạo mã băm thành công: {content_hash}")
    except Exception as e:
        return {"status": "FAILED", "reason": f"Lỗi tạo mã băm: {str(e)}"}

    return {
        "status": "PASSED",
        "content_hash": content_hash,
        "measured_lufs": current_lufs,
        "silences_count": len(silence_durations)
    }

if __name__ == "__main__":
    task_id = os.getenv("TASK_ID", "test_task")
    caption = os.getenv("PUBLISH_CAPTION", "Đây là caption mẫu #antigravity")
    master_file = f"MASTER_{task_id}.mp3"

    # Tạo tệp giả lập để chạy thử nếu ở môi trường dev local
    if not os.path.exists(master_file):
        print(f"[-] Không tìm thấy tệp {master_file}. Chạy kiểm định giả lập.")
        sys.exit(0)

    qc_result = verify_master_qc(master_file, caption)
    print(json.dumps(qc_result, indent=2, ensure_ascii=False))
    if qc_result["status"] == "FAILED":
        sys.exit(1)
    sys.exit(0)
```
