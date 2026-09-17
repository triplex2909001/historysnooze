# 04. VISUAL PROMPT ENGINE SPECIFICATION (SSOT)
**HistorySnooze Documentary Production Pipeline**
**Version:** 2.0.0 — Canonical Single Source of Truth (SSOT)

---

## 1. MỤC TIÊU & NGUYÊN TẮC CỐT LÕI (CORE PRINCIPLES)

1. **Chuẩn hóa 100% cho Google Flow (Imagen 3)**:
   - Tuyệt đối KHÔNG sử dụng cú pháp của Midjourney (`--ar 16:9`, `--style raw`, `--v 6.0`, `--s 250`, `--q 2`).
   - Tuyệt đối KHÔNG để lọt các tag ID thô (`[CHARACTER: ref_...]`, `[SETTING: ...]`, `[PROP: ...]`) vào chuỗi prompt gửi tới API Google Flow.
2. **Đồng nhất phong cách mỹ thuật (Art Style Consistency)**:
   - Toàn bộ hình ảnh trong video phải mang phong cách nghệ thuật lịch sử sang trọng, màu sắc trầm ấm, ánh sáng dịu mắt phù hợp video ru ngủ ASMR (Sleep Aid Documentary).
   - Không tạo ra ảnh 3D CGI giả tạo, không tạo tượng sáp đơ cứng (uncanny valley).
3. **Mật độ phân bổ 150 Beats (High-Density Keyframes)**:
   - Mỗi tập tài liệu 15 Part bắt buộc có đúng **150 visual beats** (10 beats/part).
   - Đặt tên file chuẩn hóa: `beat_P{part:02d}_B{beat:02d}.jpg` (từ `beat_P01_B01.jpg` đến `beat_P15_B10.jpg`).

---

## 2. BỘ 25 VISUAL ANCHORS (MASTER REFERENCE ANCHOR KIT)

Mỗi nhân vật lịch sử khi đưa vào sản xuất phải thiết lập tối thiểu 25 visual anchors:
1. **5 Character Life Stages / Portraits (`ref_character_*`)**:
   - Mô tả chi tiết: Tuổi tác, nét mặt, ánh mắt, kiểu tóc/râu, trang phục, chất liệu vải, biểu cảm đặc trưng qua từng thời kỳ (Tuổi trẻ, Trưởng thành, Đỉnh cao quyền lực, Tuổi già / Lưu đày).
2. **15 Setting Anchors (`ref_setting_*`)**:
   - 1:1 tương ứng với bối cảnh chính của 15 Parts.
   - Mô tả chi tiết: Kiến trúc thời đại (cột đá Cẩm thạch, mái ngói, gỗ tuyết tùng, tường thạch cao...), nguồn sáng (ánh nến, đuốc dầu, ánh trăng, hoàng hôn), góc máy.
3. **5 Signature Props (`ref_props_*`)**:
   - Đồ vật mang tính biểu tượng lịch sử (gươm báu, bút lông, nghiên mực, vương miện, văn kiện, cỗ xe...).

---

## 3. CÔNG THỨC PROMPT 3-TIER CHUẨN (3-TIER VISUAL PROMPT FORMULA)

Mỗi câu prompt bắt buộc phải được ghép tự động qua 3 tầng (Tier):

$$\text{Prompt} = \text{Tier 1 (Scene Beat)} + \text{Tier 2 (Cultural/Period Anchor)} + \text{Tier 3 (Signature Frame Tail)}$$

### Tầng 1: Narrative Scene Beat (Mô tả hành động/bối cảnh cụ thể)
- Trích xuất trực tiếp từ 10 đoạn văn của mỗi Part kịch bản.
- Tập trung vào nhân vật, hành động, ánh sáng cục bộ, cảm xúc.

### Tầng 2: Cultural & Period Anchor (Neo văn hóa & Kiến trúc chuẩn)
- Định hình thời kỳ lịch sử cụ thể (ví dụ: *seventeenth-century Edo-period Japan* / *first-century Imperial Rome* / *seventeenth-century Baroque France*).
- Mô tả chất liệu kiến trúc và trang phục chuẩn khảo cổ học.

### Tầng 3: Signature Frame & Master Style Tail (Định dạng & Phong cách mỹ thuật)
- **Chuẩn mỹ thuật (Master Style Tail)**:
  `late-15th-century illuminated manuscript style painting, tempera and shell-gold, flat perspective, fine brown-ink outlines, full-bleed edge-to-edge painting extending to all four edges of the 16:9 canvas, zero margins, no outer paper, no parchment border, no decorative frame, no page border, wide cinematic 16:9 composition, ultra-high-resolution (4K)`
- **Hoặc chuẩn Cinematic Film 35mm**:
  `cinematic historical film still, shot on 35mm anamorphic lens, Panavision cinematography, authentic period lighting, warm chiaroscuro candlelit shadows, subtle film grain, muted earthy color palette, wide 16:9 composition, full bleed edge-to-edge, no borders, 4K UHD`

---

## 4. BỘ LỌC TỪ CẤM (FORBIDDEN NEGATIVE CONSTRAINTS)

Bộ lọc `prompt_validator.py` và Gatekeeper GK3 sẽ tự động từ chối bất kỳ prompt nào chứa các từ sau:
- `photorealistic`
- `3d render`
- `cgi`
- `octane render`
- `cyberpunk`
- `modern`
- `anime`
- `border`
- `frame`
- `parchment edge`
- `margin`
- `.gif`

---

## 5. QUY CHUẨN FORMAT FILE PROMPT (`combined_imageprompts.txt`)

- Mỗi dòng prompt là **đơn dòng (Single Line)**, không được xuống dòng bên trong prompt.
- Các beat cách nhau bởi đúng **1 dòng trống (`\n\n`)**.
- Cú pháp mỗi dòng:
  `beat_P01_B01.jpg: [Mô tả chi tiết 3 tầng]`
- Độ dài tối đa mỗi prompt: $\le 1,500$ ký tự.
