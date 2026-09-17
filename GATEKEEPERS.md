# 🛡️ Universal Polymorphic Gatekeepers Specification: HistorySnooze Pipeline
# File: GATEKEEPERS.md
# Standard: Documents/Structure/04_PIPELINE_GATEKEEPER_DASHBOARD.md & AGENTS.md Constitution

## I. Architectural Overview

The HistorySnooze production pipeline produces 90–120 minute ambient sleep documentaries. In accordance with the **Universal 5-Phase Lifecycle Pattern** (Documents/Structure/04_PIPELINE_GATEKEEPER_DASHBOARD.md), execution is governed by 5 Universal Polymorphic Gatekeepers (**GK0 through GK4**).

Every stage must strictly satisfy its designated gatekeeper criteria before advancing downstream. Any violation halts the pipeline, quarantines defective artifacts, logs diagnostics, and dispatches dead-letter alerts.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HISTORYSNOOZE 5-TIER GATEKEEPER TOPOLOGY                        │
├─────────────────┬──────────────────────────────────────────────────────────────────────┤
│ GK0: Ingress    │ Cloudflare KV Distributed Lease Lock (10 min TTL), Rate Limit, Quota │
│ GK1: Raw Input  │ 15 Parts, 150 Prompt Beats, Syntax QC, RMS Audio Check, Clean Inbox  │
│ GK2: Process    │ Audio Chunks Continuity, 4K Keyframes QC, 0.5s Inter-Chunk Silence   │
│ GK3: Master QC  │ Ken Burns 4K 30fps, Dynamic Dimming, EBU R128 -16 LUFS, Silence Gaps │
│ GK4: Ledger     │ Google Sheets Atomic Sync, Telegram Bot @youtube2drive_Bot ID 8798886722│
└─────────────────┴──────────────────────────────────────────────────────────────────────┘
```

---

## II. Detailed Gatekeeper Specifications

### Gatekeeper 0 (GK0): Ingress & Distributed Lease Lock

- **Purpose**: Controls pipeline entry, enforces distributed mutual exclusion, prevents race conditions, and validates upstream infrastructure quotas before committing compute resources.
- **Key Verification Checkpoints**:
  1. **Cloudflare KV Distributed Lease Lock**: Requests a distributed lease lock via Cloudflare KV worker using an atomic conditional write (`PUT /lease/:task_id?if_not_exists=true`).
  2. **10 Min Lease TTL**: Acquired lease is bounded by a strictly enforced 10 min lease TTL (Time-To-Live). The lock must be renewed with a heartbeat or it automatically expires, preventing orphaned locks if an instance crashes.
  3. **Anti-Race Ingress**: Idempotency check guarantees that duplicate webhook triggers or simultaneous matrix dispatches for the same story ID are rejected immediately (`HTTP 409 Conflict`).
  4. **Rate Limiting & Token Rotation**: Monitors API consumption against provider thresholds (Cloudflare Workers AI, Google Cloud, YouTube API). Automatically rotates authentication tokens when rate limits approach 80% saturation.
  5. **Quota Verification**: Inspects Google Drive destination quota (minimum 50 GB free storage required) and GitHub Actions workflow minutes before authorizing execution.
- **Pass/Fail Criteria**:
  - **PASS**: Distributed lock acquired, lease TTL = 10 min, quota verified, rate limit headroom > 20%.
  - **FAIL**: Lock held by active peer, insufficient quota, or rate limit exhausted. Halts immediately without side effects.

---

### Gatekeeper 1 (GK1): Raw Input QC & Clean Inbox

- **Purpose**: Validates raw narrative inputs, prompts, and initial voiceover generation at the boundary before initiating parallel processing.
- **Key Verification Checkpoints**:
  1. **Story Structure Specification**: Validates that narration contains exactly **15 parts** and an exact total of **150 prompt beats** (strictly 10 beats per part for consistent pacing).
  2. **Syntax Validation & Tag Integrity**: Enforces strict JSON Schema for story beats. Validates that all prompt tags (`[CHARACTER]`, `[SETTING]`, `[STYLE]`) conform to canonical references and prompt lengths remain within the 1500 character ceiling.
  3. **RMS Audio Check**: Scans each generated voiceover audio chunk:
     - File size must be $\ge 5\text{ KB}$.
     - RMS amplitude must not indicate dead silence ($< -50\text{ dBFS}$) or digital clipping ($\ge 0\text{ dBFS}$).
     - Audio duration must match text beat pacing thresholds (between 12.0s and 45.0s per beat).
  4. **Clean 00.INBOX Policy**: Raw input files staged in `00.INBOX` are validated, ingested, and automatically purged. Zero unverified or residual files may remain in `00.INBOX` upon GK1 completion.
- **Pass/Fail Criteria**:
  - **PASS**: 15 parts present, 150 beats validated, all audio chunks meet RMS standards, `00.INBOX` completely clean.
  - **FAIL**: Beat count mismatch, clipping/silent audio, schema error, or leftover files in `00.INBOX`. Triggers self-healing retry up to 3 times before raising a critical defect.

---

### Gatekeeper 2 (GK2): Processing Integrity

- **Purpose**: Audits mid-stage processing artifacts (voiceover chunks and visual keyframes) before final composite rendering.
- **Key Verification Checkpoints**:
  1. **Audio Chunks Continuity**: Audits the contiguous sequence of audio chunks from `chunk_001` through `chunk_150`. Detects any missing, truncated, or zero-byte chunks.
  2. **4K Keyframe Resolution & Color Validation**:
     - Image resolution must strictly measure **3840x2160** pixels (true 4K UHD 16:9).
     - Color space validation: 24-bit sRGB / Rec.709, valid color histogram (no solid black, blown-out white, or corrupted pixel blocks).
     - File format: Valid lossless PNG or high-quality JPEG without compression artifacts.
  3. **0.5s Silence Insertion Between Chunks**:
     - Pre-assembly enforces insertion of exactly **0.5s silence** between consecutive voiceover chunks using FFmpeg `apad` / `anullsrc` filters.
     - Guarantees natural, soothing breathing pauses between narrative beats for ASMR sleep induction.
- **Pass/Fail Criteria**:
  - **PASS**: 100% audio chunk sequence present (150/150), 100% keyframes verified at 3840x2160 with valid color gamut, 0.5s silence correctly inserted between chunks.
  - **FAIL**: Missing audio chunk index, non-4K resolution, corrupted image, or missing 0.5s chunk silence. Artifact quarantined.

---

### Gatekeeper 3 (GK3): Master QC

- **Purpose**: Comprehensive technical quality control of the final assembled master sleep documentary video and audio stream.
- **Key Verification Checkpoints**:
  1. **Ken Burns 4K 30fps Rendering**:
     - Video stream must render at true 3840x2160 resolution, 30.0 frames per second (fps), progressive scan.
     - Smooth pan-and-zoom motion vectors conforming to calm, hypnotic sleep pacing (maximum pan speed $\le 0.8\%$ per second, zoom factor between 1.00 and 1.15).
  2. **Dynamic Dimming Curve**:
     - Implements gradual, monotonic luminance attenuation over the video duration.
     - Scene brightness smoothly transitions from initial comfortable viewing levels (100%) down to ultra-low ambient lux levels (30–40% luminance) during the final 30 minutes, promoting uninterrupted sleep.
  3. **EBU R128 -16 LUFS Audio Normalization**:
     - Integrated Loudness target: strictly **-16.0 LUFS** (per EBU R128 broadcast standard).
     - Tolerance window: $\pm 2.0\text{ LUFS}$ (acceptable range between -18.0 LUFS and -14.0 LUFS).
     - Maximum True Peak: $\le -1.5\text{ dBTP}$ to avoid DAC inter-sample clipping on mobile and sleep headphones.
  4. **Black Frame Filtering**:
     - Scans entire video using FFmpeg `blackdetect=d=0.1:pix_th=0.10` to detect unintentional black frames, dropped frames, or rendering glitches. Zero unintended black gaps permitted.
  5. **Standardized Silence Gaps**:
     - Exactly **1.0s silence** between paragraphs.
     - Exactly **2.0s silence** between major story parts (Parts 1–15).
- **Pass/Fail Criteria**:
  - **PASS**: 4K 30fps Ken Burns confirmed, dynamic dimming curve verified, EBU R128 audio within -16.0 ± 2.0 LUFS, zero rogue black frames, silence gaps strictly 1.0s (paragraphs) and 2.0s (parts).
  - **FAIL**: Loudness drift > 2 LUFS, clipping, black frame detected, non-4K resolution, or silence gap anomaly. Master rejected; dead-letter alert dispatched.

---

### Gatekeeper 4 (GK4): Ledger Sync & Alert

- **Purpose**: Persists immutable state, logs production metrics to the Central Ledger, and notifies human operators and automated bots.
- **Key Verification Checkpoints**:
  1. **Atomic Row Sync to Google Sheets Central Ledger**:
     - Atomically writes final production record into the Single-Tab Master Dashboard (`Documents/Structure/04_PIPELINE_GATEKEEPER_DASHBOARD.md` Section VI).
     - Records: `Task ID`, `Engine`, `State` (`DONE`), `Done Chunks` (`150/150`), `Master File ID` (GDrive link), `EBU R128 Measured LUFS`, and `Execution Duration`.
  2. **Telegram Notification**:
     - Dispatches formatted success alert to Telegram Bot **`@youtube2drive_Bot`** (Bot/Chat ID: **`8798886722`**).
     - Message payload includes: Episode title, 15 parts / 150 beats summary, verified LUFS, SHA-256 fingerprint, and Google Drive master download link.
  3. **Dead-Letter Alerts on Failure**:
     - If ANY preceding gatekeeper (GK0–GK3) fails or encounters an unrecoverable exception, GK4 dispatches a high-priority dead-letter alert to Bot `@youtube2drive_Bot` ID `8798886722`.
     - Alert payload contains: Failed stage, error code, offending artifact path, stack trace snippet, and quarantine storage link.
  4. **Content Fingerprint & Idempotency Lock**:
     - Computes cryptographic SHA-256 hash:
       $$\text{Content Fingerprint} = \text{SHA-256}(\text{Master Media Bytes} + \text{Narration Text})$$
     - Persists fingerprint with status `PUBLISHED_IMMUTABLE` into Section IV of the Central Ledger to prevent accidental re-upload or duplicate publishing.
- **Pass/Fail Criteria**:
  - **PASS**: Ledger row updated atomically, Telegram message delivered to `@youtube2drive_Bot` ID `8798886722`, `PUBLISHED_IMMUTABLE` lock established.
  - **FAIL**: Network timeout after 3 retries, sheet update rejected, or notification delivery failure.

---

## III. Summary Matrix of Gatekeepers

| Gate | Phase Name | Primary Technology / Check | Strict Acceptance Threshold | Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **GK0** | Ingress & Lease Lock | Cloudflare KV Distributed Lock | 10 min lease TTL, rate limit OK, quota verified | Halt immediately (HTTP 409) |
| **GK1** | Raw Input QC & Clean Inbox | Schema Validator, RMS Audio Meter | 15 parts, 150 beats, RMS $\ge -50\text{ dBFS}$ & $< 0\text{ dBFS}$, clean `00.INBOX` | Retry $\le 3$ times, then alert |
| **GK2** | Processing Integrity | Chunk Sequence & Image Validator | 150/150 audio chunks, 4K (3840x2160) keyframes, 0.5s inter-chunk silence | Quarantine chunk & alert |
| **GK3** | Master QC | FFmpeg `ebur128`, `blackdetect`, Ken Burns | 4K 30fps, dynamic dimming, -16 LUFS (±2), gaps: 1.0s para / 2.0s parts | Reject master, Dead-Letter alert |
| **GK4** | Ledger Sync & Alert | Google Sheets API, Telegram Bot API | Atomic row sync, Bot `@youtube2drive_Bot` ID `8798886722`, `PUBLISHED_IMMUTABLE` | Retry backoff, Dead-Letter alert |

---

## IV. Fast Audit & Verification

To audit compliance of the HistorySnooze codebase against this specification:
1. Run gatekeeper test suite:
   ```bash
   pytest tests/test_gatekeepers_and_backup.py -v
   ```
2. Verify all 5 gatekeepers (GK0, GK1, GK2, GK3, GK4) pass static and dynamic assertions.
