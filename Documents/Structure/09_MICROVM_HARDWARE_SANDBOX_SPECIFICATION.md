# 🛡️ ĐẶC TẢ KIẾN TRÚC CÔ LẬP PHẦN CỨNG MICROVM & ZERO-IDLE SANDBOX

> **Tài liệu:** `09_MICROVM_HARDWARE_SANDBOX_SPECIFICATION.md`
> **Bộ tài liệu:** Master System Architecture (`Documents/Structure`)
> **Mục tiêu:** Nâng cấp ranh giới bảo mật từ **Process-Level Container Sandbox** (trong `03_SECURE_ISOLATION_VAULT.md`) lên **Hardware-Assisted MicroVM Sandbox** (Firecracker / Kata Containers).
> **Nguyên tắc cốt lõi:** Cô lập phần cứng (Hardware VT-x/AMD-V) • Zero Cross-Contamination • Zero-Leak Memory Vault • Zero-Idle ($0/0 MB khi nghỉ).

---

## 📑 MỤC LỤC
1. [BỐI CẢNH & TẠI SAO PHẢI DÙNG MICROVM (WHY MICROVM?)](#1-bối-cảnh--tại-sao-phải-dùng-microvm-why-microvm)
2. [KIẾN TRÚC MICROVM ZERO-IDLE & COPY-ON-WRITE](#2-kiến-trúc-microvm-zero-idle--copy-on-write)
3. [CHIẾN LƯỢC BẢO MẬT HARDWARE-LEVEL RAM-ONLY VAULT](#3-chiến-lược-bảo-mật-hardware-level-ram-only-vault)
4. [MÔ HÌNH LAI (HYBRID DOCKER + MICROVM DEPLOYMENT)](#4-mô-hình-lai-hybrid-docker--microvm-deployment)
5. [BẢNG SO SÁNH HIỆU NĂNG & CHI PHÍ TÀI NGUYÊN](#5-bảng-so-sánh-hiệu-năng--chi-phí-tài-nguyên)
6. [BỘ KHUÔN MẪU CẤU HÌNH & SCRIPTS ĐIỀU PHỐI (IMPLEMENTATION TEMPLATES)](#6-bộ-khuôn-mẫu-cấu-hình--scripts-điều-phối-implementation-templates)
7. [QUY TRÌNH KIỂM SOÁT AN TOÀN & BẢO TRÌ (OPERATIONAL CHECKLIST)](#7-quy-trình-kiểm-soát-an-toàn--bảo-trì-operational-checklist)

---

## 1. BỐI CẢNH & TẠI SAO PHẢI DÙNG MICROVM (WHY MICROVM?)

Trong kỷ nguyên AI Agents tự động (Hermes, Antigravity, Auto-Runners), các agent liên tục nhận yêu cầu từ nhiều nguồn: tệp lạ từ `00.INBOX`, mã nguồn mở chưa kiểm duyệt trên GitHub, các lệnh tải media, và script do LLM tự sinh.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             RANH GIỚI BẢO MẬT                               │
│                                                                             │
│  [Docker Container Truyền Thống]          [MicroVM Sandbox - Firecracker]   │
│  ┌──────────────────────────────┐         ┌──────────────────────────────┐  │
│  │   App / Agent Process        │         │   App / Agent Process        │  │
│  ├──────────────────────────────┤         ├──────────────────────────────┤  │
│  │  Namespace / cgroups (Linux) │         │  Dedicated Guest Kernel      │  │
│  ├──────────────────────────────┤         ├──────────────────────────────┤  │
│  │  DÙNG CHUNG HOST KERNEL ⚠️   │         │  KVM Hypervisor (Hardware)   │  │
│  └──────────────────────────────┘         └──────────────────────────────┘  │
│        RỦI RO: Leak qua /proc,                   AN TOÀN TUYỆT ĐỐI:         │
│        /dev/shm, Kernel Exploits,                Cô lập bảng nhớ phần cứng, │
│        Lẫn lộn biến môi trường                   Tự hủy sạch khi tắt        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Hạn chế cốt tử của Docker Container truyền thống:
1. **Dùng chung Host Kernel:** Bất kỳ lỗ hổng Kernel Privilege Escalation hoặc cấu hình sai về Volume Mount / Host Network đều có thể dẫn đến việc Agent đọc chéo bộ nhớ của hệ thống khác.
2. **Nguy cơ Cross-Contamination Credentials:** Ba hệ thống độc lập trên hạ tầng (`NWL Logistics`, `Telegram Command Center`, `HanaAssistant`) có nguy cơ bị lộ hoặc dùng chéo Bot Token nếu cùng chia sẻ môi trường Process trên Host.
3. **Hiểm họa Prompt Injection & Supply Chain Attack:** Các thư viện bên thứ 3 hoặc file PDF độc hại từ bên ngoài có thể kích hoạt Remote Code Execution (RCE) trong container.

👉 **MicroVM là câu trả lời:** Cung cấp lớp cô lập phần cứng như một máy ảo độc lập hoàn chỉnh nhưng với chi phí tài nguyên và tốc độ tương đương Docker container.

---

## 2. KIẾN TRÚC MICROVM ZERO-IDLE & COPY-ON-WRITE

Để đảm bảo nguyên tắc **Zero-Idle Consumption (0 MB RAM / 0% CPU khi nghỉ)**, MicroVM được thiết kế theo cơ chế **Ephemeral On-Demand**.

```text
               ┌──────────────────────────────────────────────┐
               │              TRẠNG THÁI NGHỈ                 │
               │        (0 MB RAM / 0% CPU Footprint)         │
               └──────────────────────┬───────────────────────┘
                                      │ Yêu cầu Job mới
                                      ▼
               ┌──────────────────────────────────────────────┐
               │    KHỞI CHẠY TỨC THÌ (Boot: ~5ms - 20ms)     │
               │   • Load stripped kernel (vmlinux ~8MB)      │
               │   • Mount Base RootFS tĩnh (Read-Only)       │
               │   • Gắn RAM-Only Vault (/dev/shm)            │
               └──────────────────────┬───────────────────────┘
                                      │ Thực thi tác vụ
                                      ▼
               ┌──────────────────────────────────────────────┐
               │          THỰC THI TRONG CÔ LẬP               │
               │   • OverlayFS ghi nhận thay đổi tạm thời     │
               │   • Hardware VT-x chặn thoát sandbox         │
               └──────────────────────┬───────────────────────┘
                                      │ Hoàn tất Job / Lỗi
                                      ▼
               ┌──────────────────────────────────────────────┐
               │        TỰ HỦY SẠCH SẼ (--rm / Teardown)      │
               │   • Giải phóng 100% RAM ảo về Host           │
               │   • Xóa sạch delta layer OverlayFS           │
               │   • Trở về trạng thái Zero-Idle ($0)         │
               └──────────────────────────────────────────────┘
```

### Cơ chế Tối ưu Lưu trữ (Zero-Disk Bloat):
* **Single Base RootFS (Chỉ 1 bản duy nhất):** Base Image tối giản (Alpine / Debian stripped) chỉ nặng **~150MB – 300MB**, được lưu ở chế độ `Read-Only`.
* **Guest Kernel Tối Giản (`vmlinux`):** Kernel lược bỏ mọi driver không cần thiết, dung lượng chỉ **~5MB – 10MB**.
* **Copy-on-Write (OverlayFS Delta):** Khi hàng chục MicroVM khởi chạy cùng lúc, chúng đọc chung Base RootFS tĩnh. Mọi tệp tạm sinh ra trong quá trình chạy được lưu trên RAM hoặc file delta tạm và tự động biến mất khi VM tắt.

---

## 3. CHIẾN LƯỢC BẢO MẬT HARDWARE-LEVEL RAM-ONLY VAULT

Nguyên tắc **Zero-Leak** được nâng lên mức phần cứng:

### 1. Bảng Phân Trang Bộ Nhớ Riêng Biệt (EPT / NPT)
* MicroVM chạy trên không gian địa chỉ vật lý ảo được quản lý bởi phần cứng CPU (Extended Page Tables).
* Tiến trình trên Host OS (kể cả root) không thể dễ dàng dump vùng nhớ của Guest VM mà không can thiệp sâu vào KVM.

### 2. Tiêu Hủy Bí Mật Cấp Phát Vật Lý
* Toàn bộ Secrets (Google OAuth Tokens, Telegram Bot Tokens, Private Keys) được truyền vào MicroVM qua cơ chế **RAM-Only Vault** (`/dev/shm` bên trong Guest).
* Khi MicroVM hoàn thành công việc và tắt tiến trình KVM, toàn bộ vùng nhớ RAM được Hypervisor trả về cho Host Kernel và được kernel ghi đè/xóa sạch, triệt tiêu khả năng phục hồi dữ liệu từ RAM.

### 3. Phân Định Khóa Cứng 3 Hệ Thống Bằng Jailer
Mỗi hệ thống nghiệp vụ chạy trên một Profile MicroVM Jailer độc lập với chroot và cgroup riêng:
* **Jailer 1 (NWL Logistics):** Chỉ cấp phát quyền truy cập API Logistics và Token `newway_mcp_Bot` (`8944836049:...`).
* **Jailer 2 (Telegram Command Center):** Chỉ nạp Token `youtube2drive_Bot` (`8798886722:...`) và các workflow media.
* **Jailer 3 (Hana Assistant):** Chỉ nạp Token `hanalearningBot` (`8903373140:...`) và gắn đích gửi cố định nhóm HaRiEdu.

---

## 4. MÔ HÌNH LAI (HYBRID DOCKER + MICROVM DEPLOYMENT)

Hệ sinh thái trên `vpsg16gb` và `vpsg24gb` áp dụng mô hình phân tầng:

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                    TỔNG THỂ HỆ THỐNG MÁY CHỦ HYBRID                        │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 🔵 TẦNG 1: DỊCH VỤ DÀI HẠN (LONG-RUNNING DOCKER CONTAINERS)          │  │
│  │  • Nhiệm vụ: Duy trì Session, Webhook, API Gateway, Stdio MCP Bridge │  │
│  │  • Thành phần: Container gemininotebook, Tailscale SSH, Port Listeners│  │
│  │  • Đặc điểm: Nhẹ, duy trì trạng thái đăng nhập, RAM tĩnh thấp.       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼ Kích hoạt Job nhạy cảm                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 🔴 TẦNG 2: MÔI TRƯỜNG THỰC THI TỰ HỦY (EPHEMERAL MICROVM SANDBOX)    │  │
│  │  • Nhiệm vụ: Xử lý file 00.INBOX, tải media, chạy tool Agent tự do   │  │
│  │  • Thành phần: Firecracker MicroVM Sandboxes (Jailer)                │  │
│  │  • Đặc điểm: 0 MB khi nghỉ, khởi động trong 10ms, cách ly phần cứng. │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. BẢNG SO SÁNH HIỆU NĂNG & CHI PHÍ TÀI NGUYÊN

| Tiêu chí | Máy ảo truyền thống (KVM / VMware) | Docker Container thông thường | MicroVM Sandbox (Firecracker / Kata) |
| :--- | :--- | :--- | :--- |
| **RAM Overhead tĩnh** | 1GB – 4GB / VM | ~0 MB (Dùng chung Host Kernel) | **~5MB – 15MB / VM instance** |
| **Trạng thái khi nghỉ (Idle)** | Tiêu tốn RAM liên tục | 0 MB (khi dùng `--rm`) | **0 MB (tắt và hủy hoàn toàn)** |
| **Dung lượng đĩa cố định** | 20GB – 50GB / VM | 500MB – 2GB (Docker Images) | **~150MB – 300MB (1 Base duy nhất)** |
| **Tốc độ khởi động (Boot)** | 20s – 60s | 500ms – 1s | **5ms – 50ms (Thần tốc)** |
| **Ranh giới cô lập (Isolation)** | Phần cứng (Hardware VT-x) | Tiến trình (cgroups/namespaces) | **Phần cứng (Hardware VT-x / KVM)** |
| **Bảo vệ Secrets / Tokens** | Cô lập theo OS | Dễ bị lộ chéo qua Host/Env | **RAM-Only Vault cô lập phần cứng** |
| **Khả năng chạy hàng loạt** | Rất kém (Nặng máy) | Tốt | **Cực tốt (Hàng chục VM đồng thời)** |

---

## 6. BỘ KHUÔN MẪU CẤU HÌNH & SCRIPTS ĐIỀU PHỐI (IMPLEMENTATION TEMPLATES)

### 6.1. Cấu hình Firecracker MicroVM mẫu (`microvm_config.json`)
```json
{
  "boot-source": {
    "kernel_image_path": "/var/lib/firecracker/vmlinux-6.1.stripped",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off init=/init quiet"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "/var/lib/firecracker/rootfs_base.ext4",
      "is_root_device": true,
      "is_read_only": true
    }
  ],
  "machine-config": {
    "vcpu_count": 2,
    "mem_size_mib": 512,
    "smt": false
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "AA:FC:00:00:00:01",
      "host_dev_name": "tap_mv0"
    }
  ]
}
```

### 6.2. Script Điều Phối Khởi Chạy Tự Hủy (`run_ephemeral_sandbox.sh`)
```bash
#!/usr/bin/env bash
# ==============================================================================
# Script điều phối MicroVM Sandbox Ephemeral (Tự hủy sạch sẽ khi xong)
# ==============================================================================
set -euo pipefail

VM_ID="sandbox_$(date +%s%N | cut -b1-13)"
SOCKET_PATH="/tmp/firecracker_${VM_ID}.socket"
OVERLAY_DIR="/dev/shm/${VM_ID}_overlay"

mkdir -p "${OVERLAY_DIR}"
cleanup() {
    echo "🧹 [Cleanup] Đang tiêu hủy MicroVM: ${VM_ID}..."
    rm -f "${SOCKET_PATH}"
    rm -rf "${OVERLAY_DIR}"
    echo "✅ [Cleanup] Hoàn tất giải phóng 100% RAM và tài nguyên."
}
trap cleanup EXIT

# 1. Khởi chạy Firecracker daemon
firecracker --api-sock "${SOCKET_PATH}" &
FC_PID=$!

# 2. Đợi socket sẵn sàng
while [ ! -e "${SOCKET_PATH}" ]; do sleep 0.01; done

# 3. Cấu hình Kernel, Drives, Resources qua API Socket
curl -s --unix-socket "${SOCKET_PATH}" -X PUT 'http://localhost/boot-source' \
    -H 'Accept: application/json' -H 'Content-Type: application/json' \
    -d '{
        "kernel_image_path": "/var/lib/firecracker/vmlinux-6.1.stripped",
        "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
    }'

curl -s --unix-socket "${SOCKET_PATH}" -X PUT 'http://localhost/drives/rootfs' \
    -H 'Accept: application/json' -H 'Content-Type: application/json' \
    -d '{
        "drive_id": "rootfs",
        "path_on_host": "/var/lib/firecracker/rootfs_base.ext4",
        "is_root_device": true,
        "is_read_only": true
    }'

curl -s --unix-socket "${SOCKET_PATH}" -X PUT 'http://localhost/machine-config' \
    -H 'Accept: application/json' -H 'Content-Type: application/json' \
    -d '{
        "vcpu_count": 2,
        "mem_size_mib": 512
    }'

# 4. Kích hoạt Khởi động VM
curl -s --unix-socket "${SOCKET_PATH}" -X PUT 'http://localhost/actions' \
    -H 'Accept: application/json' -H 'Content-Type: application/json' \
    -d '{"action_type": "InstanceStart"}'

echo "🚀 [MicroVM] ${VM_ID} đã khởi động thành công trong Micro-sandbox."

# Chờ tiến trình VM hoàn thành tác vụ
wait ${FC_PID}
```

---

## 7. QUY TRÌNH KIỂM SOÁT AN TOÀN & BẢO TRÌ (OPERATIONAL CHECKLIST)

Khi đưa các tác vụ mới vào MicroVM Sandbox, quản trị viên và Agent phải tuân thủ:

1. **Kiểm tra KVM Hardware Acceleration:**
   Đảm bảo CPU hỗ trợ và KVM khả dụng: `ls -l /dev/kvm` (quyền truy cập cho nhóm `kvm`).
2. **Kiểm tra Base Image Hash (Integrity QC):**
   File `rootfs_base.ext4` phải được khóa SHA-256 để ngăn chặn chỉnh sửa trái phép.
3. **Quy tắc Xóa File `00.INBOX`:**
   Ngay sau khi MicroVM hoàn tất phân tích tệp từ `00.INBOX`, tệp gốc trên Google Drive phải bị xóa ngay lập tức theo đúng Quy tắc Clean Inbox.
4. **Quy tắc Kiểm soát Network Egress:**
   MicroVM chỉ được phép mở kết nối ra các domain nằm trong Whitelist (API Google, Cloudflare Relay, Telegram API), chặn toàn bộ các dải IP lạ để ngăn chặn rò rỉ dữ liệu qua kênh ngầm.
