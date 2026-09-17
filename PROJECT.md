# Project: HistorySnooze Documentary Pipeline Upgrade

## Architecture
HistorySnooze is an automated, long-form documentary production pipeline generating 90–120 minute ambient sleep documentaries. The system operates across four primary stages:
1. **Pre-production & Scripting (`hsnooze.scripting`)**: Topic ideation, 15-part script generation (~15,500–17,000 words), story segmentation, and visual prompt generation (`prompt_engine.py`, `online_script_producer.py`, `config.py`).
2. **Media Generation & Browser Automation (`hsnooze.gflow`)**: Standalone TypeScript/Playwright CLI automating Google Flow image generation, managing character consistency and reference media tiles (`src/cli.ts`, `src/flow/page.ts`, `src/jobs/schema.ts`).
3. **Voiceover Synthesis (`hsnooze.omni`)**: OmniVoice neural TTS voiceover generation producing 15 individual Part WAVs and stitched master voiceover with sentence-level timing manifests.
4. **Cinematic Video Rendering (`hsnooze.render`)**: 4K UHD 30fps Ken Burns ASMR video assembly with sub-pixel jitter-free zoompan, audio alignment, dynamic lighting transitions ("Dim the Lights"), ambient stardust particle overlay, and stream-copy master assembly (`kenburns_asmr.py`, `chunk_renderer.py`, `beat_aligner.py`, `master_assembler.py`).
5. **Single Source of Truth (`NotebookLM` & `Google Workspace`)**: NotebookLM RAG notebook `813e73eb-7327-4c9b-9651-fe416e6d180c`, Google Drive asset folders, and Google Sheets pipeline tracking (`1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Master Reference Kit Generation | Generate canonical reference sheets (`ref_character_*.jpg`, `ref_setting_*.jpg`, `ref_prop_*.jpg`) and deploy to Drive `02. Media Generation/references/` | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Prompt Engine Reference Tagging | Update `prompt_engine.py` to annotate prompts with `[CHARACTER]`, `[SETTING]`, `[PROP]`, and `[INGREDIENT]` tags and validate syntax | M1 | ORIGINAL_REQUEST §R1 |
| 3 | GFlow Media Tile Automation | Update `hsnooze.gflow/src/cli.ts` and `src/flow/page.ts` to parse tags and inject Character and Ingredient media tiles in Google Flow | M1 | ORIGINAL_REQUEST §R1 |
| 4 | High-Density Beat Configuration | Update `config.py` across packages to support 150–160 beats (~10 beats/part, 30–45s/beat) | M2 | ORIGINAL_REQUEST §R2 |
| 5 | Paragraph-Level Story Segmentation | Update `online_script_producer.py` and `prompt_engine.py` to generate granular visual descriptions aligned with narrative shifts | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Render Pipeline Beat Alignment | Update `beat_aligner.py` and `pipeline_orchestrator.py` Gatekeepers (GK3, GK6) to handle 150–160 beats | M2 | ORIGINAL_REQUEST §R2 |
| 7 | "Dim the Lights" Audio Cue Anchoring | Detect/anchor the "dim the lights" cue in Part 01 voiceover transcript to extract deterministic start/end timestamps | M3 | ORIGINAL_REQUEST §R3 |
| 8 | Cosine Dynamic Lighting Ramp | Implement smooth non-destructive brightness, gamma, and vignette dimming filter in `kenburns_asmr.py` for Part 01 Beat 1 | M3 | ORIGINAL_REQUEST §R3 |
| 9 | Ambient Stardust Sleep Overlay | Composite subtle drifting specks/stardust above Ken Burns motion using screen blending across all post-dimming beats | M3 | ORIGINAL_REQUEST §R3 |
| 10 | Render Pipeline Concatenation Integration | Update `chunk_renderer.py` and `master_assembler.py` to handle dynamic P01_B01 transition and stream-copy concatenate all beats | M3 | ORIGINAL_REQUEST §R3 |
| 11 | NotebookLM SSOT Synchronization | Sync Visual Consistency Architecture, 150-beat density, and Dim the Lights shader specs into notebook `813e73eb-7327-4c9b-9651-fe416e6d180c` | M4 | ORIGINAL_REQUEST §R4 |
| 12 | Clean Slate Asset Purge | Purge legacy 55 keyframes from local cache, VPS, and verify Google Drive folder `19krkuGIJ8l1eyASLIhKyi1oQS9f5cjmm` | M5 | ORIGINAL_REQUEST §R5 |
| 13 | Matsuo Bashō 150-Beat Regeneration | Generate 150–160 structured beats with Reference Anchor Kit tags in `combined_imageprompts.txt` and generate assets | M5 | ORIGINAL_REQUEST §R5 |
| 14 | Google Sheets Pipeline Update | Update Google Sheets dashboard (`1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo`) row 5 to reflect current pipeline status | M5 | ORIGINAL_REQUEST §R5 |
| 15 | E2E Acceptance Verification | Verify all acceptance criteria across Tiers 1–4 using automated test suites and gate audits | M6 | ORIGINAL_REQUEST Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Visual Consistency Architecture (Anchor Kit & GFlow) | Features 1, 2, 3: Reference sheets, prompt engine tagging, and GFlow media tile injection | none | DONE |
| M2 | High-Density Visual Beat Generation (150-160 Beats) | Features 4, 5, 6: Config scaling, paragraph segmentation, and beat alignment | M1 | DONE |
| M3 | "Dim the Lights" Cinematic Lighting Transition & Dark Sleep Overlay | Features 7, 8, 9, 10: Audio cue anchoring, cosine dimming curve, stardust overlay, and chunk renderer | M2 | PLANNED |
| M4 | NotebookLM SSOT Synchronization | Feature 11: Authoritative notes and sources in NotebookLM | M1, M2, M3 | PLANNED |
| M5 | Clean Slate Reset & Regeneration for Matsuo Bashō | Features 12, 13, 14: Cache/Drive purge, 150-beat prompt set generation, and Sheet update | M1, M2, M3, M4 | PLANNED |
| M6 | Acceptance Testing, Gatekeeper Audits & Delivery | Feature 15: Full E2E verification of acceptance criteria and deliverables | M1, M2, M3, M4, M5 | PLANNED |

## Interface Contracts
### `hsnooze.scripting/prompt_engine.py` ↔ `hsnooze.gflow`
- Format: `beat_P{part:02d}_B{beat:02d}.jpg: [CHARACTER: <name>] [SETTING: <setting_name>] [PROP: <prop_name>] [INGREDIENT: <ingredient_name>] <scene_description> <period_anchor> <style_fusion> <negative_constraints> <SIGNATURE_FRAME_TAIL>`
- Syntax:
  - Tags are optional per beat, enclosed in brackets.
  - `[CHARACTER: <id>]` maps to canonical character portrait reference (`ref_character_matsuo_basho`).
  - `[SETTING: <id>]` maps to canonical room/interior reference (`ref_setting_edo_hermitage`).
  - `[PROP: <id>]` maps to signature item reference (`ref_prop_bamboo_staff_hat`).
  - `[INGREDIENT: <id>]` generic reference tile.
  - Validation: Prompt must be a single line, <=1500 chars, no banned words (`photorealistic`, `3d render`).
- Consumer: `hsnooze.gflow/src/cli.ts` parses `[CHARACTER: (.*?)]` into `job.character: string[]` and `[(SETTING|PROP|INGREDIENT): (.*?)]` into `job.ingredients: string[]`, stripping bracketed tags from the text prompt submitted to Google Flow.

### `hsnooze.scripting/online_script_producer.py` ↔ `hsnooze.render/beat_aligner.py`
- Beat naming: `beat_P{part:02d}_B{beat:02d}.jpg`, 1-indexed.
- Beats per part: Exactly 10 beats per part for Parts 01–15 (total 150 beats) or Part 01 with 10 beats, P02-P14 with 10–11 beats, P15 with 10 beats (150–160 beats).
- Alignment Output (`beat_aligner.py`):
  ```python
  {
      "part_index": int,
      "total_duration": float,
      "num_beats": int,
      "beats": [
          {
              "beat_index": int,
              "image_path": str,
              "start_time": float,
              "end_time": float,
              "duration": float,
              "is_transition_beat": bool, # True ONLY for P01_B01
              "dim_start_sec": float,     # Cue start in P01
              "dim_end_sec": float,       # Cue end in P01
              "sleep_mode": bool          # True for P01_B02..B10 and P02..P15
          }
      ]
  }
  ```

### `hsnooze.render/kenburns_asmr.py` ↔ `hsnooze.render/chunk_renderer.py`
- Function Signature:
  ```python
  def render_kenburns_beat(
      image_path: str,
      duration: float,
      output_clip_path: str,
      zoom_in: bool = True,
      width: int = 3840,
      height: int = 2160,
      fps: int = 30,
      is_transition_beat: bool = False,
      dim_start_sec: float = 0.0,
      dim_end_sec: float = 0.0,
      sleep_mode: bool = False,
      overlay_asset_path: Optional[str] = None
  ) -> bool
  ```
- Video Encoding: 4K UHD H.264 YUV420p 30fps. All beat clips have identical stream properties so `chunk_renderer.py` concatenates them via `-c copy`.

## Code Layout
- `hsnooze.scripting/`:
  - `config.py`
  - `prompt_engine.py`
  - `online_script_producer.py`
- `hsnooze.gflow/`:
  - `src/cli.ts`
  - `src/flow/page.ts`
  - `src/flow/ui.ts`
  - `src/jobs/schema.ts`
- `hsnooze.render/`:
  - `config.py`
  - `kenburns_asmr.py`
  - `chunk_renderer.py`
  - `beat_aligner.py`
  - `master_assembler.py`
  - `pipeline_orchestrator.py`
  - `tests/test_render_pipeline.py`
- `00.codebases/`:
  - Mirrors of operational python scripts for Colab execution.
- `.agents/`:
  - Metadata, plans, progress, and gate status (NO source code or test binaries).
