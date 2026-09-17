# E2E Test Infra: HistorySnooze Pipeline Upgrade

## Test Philosophy
- Opaque-box, requirement-driven. Derives from ORIGINAL_REQUEST.md and NotebookLM SSOT.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Workload Testing.
- Non-destructive execution: Lightweight mocks and dry-run syntax verification for video/audio pipelines.

## Feature Inventory
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|--------|:------:|:------:|:------:|:------:|
| 1 | Master Reference Kit Generation | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | Prompt Engine Reference Tagging | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 3 | GFlow Media Tile Automation | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 4 | High-Density Beat Configuration | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 5 | Paragraph-Level Story Segmentation | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 6 | Render Pipeline Beat Alignment | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 7 | "Dim the Lights" Cue Anchoring | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 8 | Cosine Dynamic Lighting Ramp | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 9 | Ambient Stardust Sleep Overlay | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 10 | Render Stream-Copy Concatenation | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 11 | NotebookLM SSOT Synchronization | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 12 | Clean Slate Asset Purge | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| 13 | Matsuo Bashō Prompt Set & Generation | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| 14 | Google Sheets Pipeline Update | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test Runner: `pytest` and `npm run test` / `npx tsc --noEmit`
- Test Suites:
  - `tests/test_visual_consistency.py`: Prompt tagging syntax, anchor kit registry validation, tag stripping and parser regex.
  - `tests/test_beat_scaling.py`: 150–160 beat count verification, 10 beats/part distribution, paragraph alignment word count.
  - `tests/test_lighting_transition.py`: Audio cue parsing, Part 01 Beat 1 duration anchoring, FFmpeg filter graph syntax, luminance monotonicity.
  - `tests/test_notebooklm_sync.py`: NotebookLM note content verification (R1, R2, R3 documented).
  - `tests/test_gflow_automation.ts` or Node test: GFlow schema, `referenceIngredient` presence and CLI parameter extraction.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Matsuo Bashō 150-Beat Generation Pipeline Run | F1, F2, F3, F4, F5, F13 | High |
| 2 | Part 01 Audio Cue to Render Beat Transition Integration | F6, F7, F8, F9, F10 | High |
| 3 | Clean Slate Reset & Drive Synchronization Workflow | F1, F11, F12, F14 | Medium |
| 4 | Gatekeeper Audits GK1–GK7 on 150-Beat Artifacts | F4, F5, F6, F13 | High |

## Coverage Thresholds
- Tier 1: ≥5 per feature (Total ≥70 tests)
- Tier 2: ≥5 per feature boundary/edge cases (Total ≥70 tests)
- Tier 3: Pairwise coverage across feature interactions (Total ≥14 tests)
- Tier 4: ≥4 realistic application scenarios
