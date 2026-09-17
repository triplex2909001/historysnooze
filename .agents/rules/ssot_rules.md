# SSOT & VISUAL PROMPT ENGINE MANDATORY RULES

Mọi thao tác liên quan đến tạo kịch bản, sinh prompt hình ảnh, xử lý voiceover và render video phải tuân thủ tuyệt đối:

1. **Image Prompts**:
   - Tham chiếu: `Documents/Structure/04_VISUAL_PROMPT_ENGINE.md`
   - Cấu trúc: 3-Tier (Narrative Scene + Period Anchor + Style Framing Tail)
   - Cấm: Midjourney tags (`--v 6.0`, `--ar 16:9`), cấm từ cấm (`photorealistic`, `3d render`, `cgi`, `border`, `frame`, `.gif`).
   - Số lượng: Đúng 150 beats (10 beats/part x 15 parts).
2. **Voiceover**:
   - Duy nhất: `k2-fsa/OmniVoice` Milo (`1VC_eN0rnm9l2d4ilogn9B2GqWzzaV4fS`).
   - Cấm: `edge_tts`, `pyttsx3`, `espeak`.
3. **Script**:
   - 15 parts, 10 paragraphs/part, ~15,500 - 17,000 từ.
