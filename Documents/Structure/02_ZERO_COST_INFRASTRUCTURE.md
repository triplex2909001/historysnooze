# ☁️ FILE 2: HẠ TẦNG ĐIỆN TOÁN ĐÁM MÂY TỰ VẬN HÀNH 100% MIỄN PHÍ (02_ZERO_COST_INFRASTRUCTURE.md)

## I. BẢN ĐỒ HẠ TẦNG ZERO-COST (SYSTEM TOPOLOGY)

Triết lý cốt lõi của **Antigravity Framework** là giải phóng hoàn toàn nhà phát triển khỏi gánh nặng tài chính và công sức bảo trì hệ thống. Bằng cách loại bỏ hoàn toàn các VPS truyền thống và thay thế hệ thống CI/CD Jenkins cồng kềnh, chúng ta xây dựng một hệ thống phân tán toàn cầu hoàn toàn **Serverless & 100% Miễn Phí Trọn Đời (Zero-Cost Forever)** thông qua sự phối hợp nhịp nhàng của ba cực:

1. **Cloudflare Workers (Edge Gateway & AI Firewall):** Cổng đón tiếp siêu tốc (Zero cold-start) nằm tại Edge, chịu trách nhiệm nhận tín hiệu Webhook, chạy bộ lọc an ninh bằng AI để thanh lọc nội dung vi phạm, sau đó kích hoạt GitHub Actions chạy các tác vụ nặng.
2. **GitHub Actions Public Runner (Compute Engine):** Máy ảo Linux miễn phí hiệu năng cao (2 vCPU, 7GB RAM, 14GB SSD) chạy song song với cấu hình Ma trận cực đại (Matrix 15-18 jobs cùng lúc) để đảm bảo tốc độ render video và tổng hợp giọng nói nhanh nhất mà không tốn một xu.
3. **Google Workspace (Storage & State DB):** Sử dụng Google Sheets làm hệ cơ sở dữ liệu quản lý trạng thái động (Database) và Google Drive làm kho lưu trữ không giới hạn dung lượng để chứa hàng chục TB sản phẩm thô, phân đoạn và sản phẩm cuối.

---

## II. CLOUDFLARE WORKERS - CỔNG EDGE GATEWAY & BỘ LỌC AI FIREWALL

Cloudflare Workers đóng vai trò là "Cổng tiếp tân" trực tuyến hoạt động 24/7. Worker sẽ tiếp nhận các yêu cầu POST Webhook từ ứng dụng của bạn hoặc các nền tảng thứ ba, thực thi các kiểm tra bảo mật siêu nhẹ và kích hoạt hạ tầng điện toán nặng trên GitHub.

### 1. Cơ chế hoạt động của Edge AI Firewall
Trước khi kích hoạt máy ảo GitHub Actions chạy tốn tài nguyên, Cloudflare Worker sẽ gửi nội dung (prompt/text) sang mô hình AI bảo mật **Llama Guard 2** (`@cf/meta/llama-guard-2-8b`) chạy hoàn toàn miễn phí trên Cloudflare Workers AI. Nếu nội dung bị đánh giá là không an toàn (18+, bạo lực, rò rỉ thông tin nhạy cảm), hệ thống sẽ lập tức chặn đứng yêu cầu ngay tại Edge.

### 2. Code mẫu Cloudflare Worker gác cổng (`worker/cloudflare_router.js`)
```javascript
export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    try {
      const payload = await request.json();
      const textToValidate = payload.text || "";

      // 1. Chạy AI Firewall kiểm tra nội dung bẩn/nhạy cảm
      if (textToValidate) {
        const aiResponse = await env.AI.run("@cf/meta/llama-guard-2-8b", {
          text: textToValidate
        });

        if (aiResponse.unsafe) {
          return new Response(JSON.stringify({
            status: "BLOCKED",
            reason: "Nội dung không an toàn theo tiêu chuẩn Llama Guard 2."
          }), { status: 403, headers: { "Content-Type": "application/json" } });
        }
      }

      // 2. Kích hoạt GitHub Actions thông qua repository_dispatch
      const githubDispatchUrl = `https://api.github.com/repos/${env.GH_OWNER}/${env.GH_REPO}/dispatches`;

      const response = await fetch(githubDispatchUrl, {
        method: "POST",
        headers: {
          "Authorization": `token ${env.GH_PAT}`,
          "Accept": "application/vnd.github.v3+json",
          "User-Agent": "AntigravityEdgeGateway"
        },
        body: JSON.stringify({
          event_type: "start_heavy_task",
          client_payload: {
            task_id: payload.task_id || `task_${Date.now()}`,
            task_type: payload.task_type || "omnivoice",
            text: textToValidate
          }
        })
      });

      if (!response.ok) {
        throw new Error(`GitHub API Error: ${response.statusText}`);
      }

      return new Response(JSON.stringify({
        status: "SUCCESS",
        message: "Đã kích hoạt xử lý tác vụ nặng trên GitHub Actions."
      }), { status: 200 });

    } catch (error) {
      return new Response(JSON.stringify({ status: "ERROR", error: error.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }
  }
};
```

---

## III. GITHUB ACTIONS PUBLIC RUNNER - ĐỘNG CƠ ĐIỆN TOÁN ĐA TẦNG

GitHub Actions chính là "Xưởng gia công hạng nặng". Khi nhận được tín hiệu `repository_dispatch` gửi từ Cloudflare Workers, hệ thống máy ảo của GitHub sẽ được đánh thức để thực thi quy trình xử lý media đa tầng.

### 1. Ma trận song song cực đại (15–18 Parallel Jobs Matrix)
Để xử lý hàng trăm trang văn bản hoặc hàng nghìn khung hình video trong thời gian ngắn nhất, hệ thống chia nhỏ kịch bản đầu vào thành các mảnh siêu nhỏ (micro-chunks). Sau đó, sử dụng cấu hình **Matrix Strategy** của GitHub Actions để triệu hồi tối đa 15–18 máy ảo độc lập cùng xử lý song song. Việc này giúp giảm thời gian xử lý tổng thể từ vài tiếng xuống còn vài phút.

### 2. Cơ chế Weekly Cache Invalidation (Tự dọn rác Cache hàng tuần)
Khi chạy các mô hình AI như OmniVoice hay Whisper, máy ảo phải tải về các tệp Model Weights rất nặng. Để không mất thời gian tải lại mỗi khi chạy nhưng cũng không để rác cache cũ làm chậm hệ thống, Antigravity sử dụng cơ chế khóa cache theo tuần tự động làm mới: `week_num=$(date +'%Y-week-%V')`. Mỗi tuần một lần, cache cũ sẽ tự động bị hủy để nạp bản nâng cấp mới sạch sẽ.

### 3. File cấu hình Workflow đa tầng (`.github/workflows/multi_stage_pipeline.yml`)
```yaml
name: "Master Multi-Stage Parallel Pipeline"

on:
  workflow_dispatch:
    inputs:
      task_type:
        description: "Loại Engine"
        required: true
        default: "omnivoice"
      task_id:
        description: "Task ID"
        required: true
        default: "task_001"
  repository_dispatch:
    types: [start_heavy_task]

jobs:
  # BƯỚC 0: PHÂN TÍCH TẢI & CHIA PHÂN ĐOẠN (ORCHESTRATOR)
  orchestrator:
    name: "0. Phân tích Tải & Lập lịch"
    runs-on: ubuntu-latest
    outputs:
      task_id: ${{ steps.plan.outputs.task_id }}
      task_type: ${{ steps.plan.outputs.task_type }}
      chunk_matrix: ${{ steps.plan.outputs.chunk_matrix }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Lên kế hoạch và chia nhỏ chunk
        id: plan
        run: |
          pip install google-api-python-client google-auth requests
          python scripts/orchestrator_planner.py

  # BƯỚC L1: XỬ LÝ SONG SONG CỰC ĐẠI (BURST MATRIX)
  l1-micro-processing:
    name: "L1: Xử lý Chunk (Song song tối đa 18 instances)"
    needs: orchestrator
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      max-parallel: 18
      matrix:
        chunk: ${{ fromJson(needs.orchestrator.outputs.chunk_matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Thiết lập Bộ nhớ Cache cho Model Weights
        uses: actions/cache@v4
        with:
          path: ~/.cache/models
          key: ${{ runner.os }}-models-${{ secrets.CACHE_VERSION }}-${{ steps.get-week.outputs.week_num }}
      - name: Chạy L1 Engine Runner
        env:
          TASK_ID: ${{ needs.orchestrator.outputs.task_id }}
          TASK_TYPE: ${{ needs.orchestrator.outputs.task_type }}
          CHUNK_ID: ${{ matrix.chunk.id }}
          PAYLOAD: ${{ matrix.chunk.payload }}
          GDRIVE_SA_JSON: ${{ secrets.GDRIVE_SERVICE_ACCOUNT }}
        run: |
          pip install google-api-python-client google-auth requests sherpa-onnx faster-whisper
          python scripts/l1_engine_runner.py

  # BƯỚC L2: GỘP PHÂN ĐOẠN TẦNG TRUNG
  l2-mid-assembly:
    name: "L2: Gộp Đoạn văn (Silence 0.5s)"
    needs: [orchestrator, l1-micro-processing]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update && sudo apt-get install -y ffmpeg
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Chạy gộp L2
        env:
          TASK_ID: ${{ needs.orchestrator.outputs.task_id }}
          GDRIVE_SA_JSON: ${{ secrets.GDRIVE_SERVICE_ACCOUNT }}
        run: |
          pip install google-api-python-client google-auth requests
          python scripts/l2_mid_merge.py

  # BƯỚC L3: TỔNG HỢP MASTER & HOÀN TẤT PIPELINE
  l3-master-composite:
    name: "L3: Gộp Master (Silence 1.0s / 2.0s) & Báo cáo"
    needs: [orchestrator, l2-mid-assembly]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update && sudo apt-get install -y ffmpeg
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Chạy gộp Master & Upload Drive
        env:
          TASK_ID: ${{ needs.orchestrator.outputs.task_id }}
          GDRIVE_SA_JSON: ${{ secrets.GDRIVE_SERVICE_ACCOUNT }}
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        run: |
          pip install google-api-python-client google-auth requests
          python scripts/l3_master_merge.py
```

---

## IV. GOOGLE DRIVE API V3 THUẦN PYTHON - RESUMABLE CHUNKED UPLOAD

Thay vì sử dụng các công cụ đồng bộ bên thứ ba (như rclone) vốn dễ bị ngắt kết nối âm thầm khi tải lên các file video dung lượng lớn trên máy ảo GitHub Actions, Antigravity quy hoạch **sử dụng mã nguồn Python gọi trực tiếp thư viện Google Drive API v3 chính thống**.

### 1. Cơ chế Resumable Chunked Upload (Tải lên theo mảnh 5MB)
Toàn bộ các tệp tin thô, tệp phân đoạn và tệp Master cuối cùng đều được truyền tải qua cơ chế **Resumable Upload với kích thước phân đoạn cố định là 5MB/chunk**. Khi mạng gặp sự cố chập chờn, kết nối sẽ tự động thử lại (Retry) mà không phải tải lại tệp tin từ đầu.

### 2. Code cấu hình kết nối chuẩn (`scripts/gdrive_client.py`)
```python
import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

class GDriveManager:
    def __init__(self, sa_credentials_data=None):
        raw_data = sa_credentials_data or os.getenv("GDRIVE_SA_JSON")
        if not raw_data:
            raise ValueError("Thiếu cấu hình credentials GDRIVE_SA_JSON")

        creds_info = json.loads(raw_data)
        self.creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        self.service = build("drive", "v3", credentials=self.creds)

    def find_or_create_folder(self, folder_name: str, parent_id: str = None) -> str:
        """Tìm thư mục đã tồn tại, nếu chưa có thì tự động tạo mới."""
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = self.service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        if files:
            return files[0]["id"]

        # Nếu không tìm thấy, tạo mới
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            folder_metadata["parents"] = [parent_id]

        folder = self.service.files().create(body=folder_metadata, fields="id").execute()
        return folder.get("id")

    def upload_file_resumable(self, file_path: str, destination_folder_id: str) -> str:
        """Tải file lên với cơ chế Resumable Upload cắt lát 5MB chống đứt gãy kết nối."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        file_name = os.path.basename(file_path)
        file_metadata = {
            "name": file_name,
            "parents": [destination_folder_id]
        }

        # Thiết lập Chunk Size là 5MB (5 * 1024 * 1024 bytes)
        media = MediaFileUpload(
            file_path,
            resumable=True,
            chunksize=5 * 1024 * 1024
        )

        request = self.service.files().create(body=file_metadata, media_body=media, fields="id")
        response = None

        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[GDrive] Đang upload '{file_name}': {int(status.progress() * 100)}%...")

        print(f"[GDrive] Upload thành công! File ID: {response.get('id')}")
        return response.get("id")
```

---

## V. CƠ CHẾ CHỐNG TRÙNG LẶP & TỰ PHỤC HỒI (STATE RESUME CHECK)

Để tối ưu hóa thời gian chạy và tránh xử lý trùng lặp gây lãng phí tài nguyên, hệ thống áp dụng cơ chế **Resume Check** thông minh tại Tầng 0 (Orchestrator):

1. **Kiểm tra trạng thái:** Trước khi kích hoạt L1 Matrix cho một Chunk, script `orchestrator_planner.py` sẽ thực hiện quét nhanh danh sách tệp đang nằm trong thư mục tạm thời của Task trên Google Drive.
2. **Bỏ qua chunk cũ:** Nếu phát hiện tệp tin âm thanh hoặc hình ảnh của Chunk đó đã tồn tại trên Drive (ví dụ do một lượt chạy trước bị ngắt quãng giữa chừng do timeout mạng), hệ thống sẽ gán cờ bỏ qua và không kích hoạt Job Matrix cho Chunk đó nữa.
3. **Chỉ chạy tiếp:** Hệ thống chỉ gộp và xử lý tiếp các chunk còn thiếu, giúp tiết kiệm tối đa thời gian tính toán và hồi phục pipeline bị lỗi chỉ sau một nút bấm chạy lại.
