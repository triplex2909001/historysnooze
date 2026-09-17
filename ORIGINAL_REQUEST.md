# Original User Request

## 2026-09-11T16:58:09Z

Upgrade the HistorySnooze documentary pipeline with a comprehensive Visual Consistency Architecture (characters, settings, props reference anchors), scale image generation from ~55 to 150–160 keyframes (~10 beats/part), implement the "Dim the Lights" dynamic lighting shader/vignette transition, document the architecture in NotebookLM notebook `813e73eb-7327-4c9b-9651-fe416e6d180c`, and regenerate Matsuo Bashō's media assets from scratch.

Working directory: `/Users/hanario/Documents/HistorySnooze`
Integrity mode: development

## Requirements

### R1. Visual Consistency Architecture (Anchor Kit & GFlow Integration)
Implement a 3-tier reference system for consistent character faces, costumes, hairstyles, recurring room interiors/furniture, and signature props:
- Generate pre-production Master Reference Sheets (`ref_character_*.jpg`, `ref_setting_*.jpg`, `ref_prop_*.jpg`).
- Update `prompt_engine.py` to annotate prompts with `[CHARACTER]`, `[SETTING]`, `[PROP]`, and `[INGREDIENT]` tags.
- Update `hsnooze.gflow` automation to automatically inject Character and Ingredient media tiles in Google Flow before generation.

### R2. High-Density Visual Beat Generation (150–160 Images)
Scale the visual beat density for 90–120 minute documentaries:
- Update `config.py` and story segmentation to generate ~10 beats per part (total 150–160 beats, ~30–45s per beat instead of 75–90s).
- Update `prompt_engine.py` and `online_script_producer.py` to produce granular visual descriptions aligned with paragraph-level narrative shifts.

### R3. "Dim the Lights" Cinematic Lighting Transition & Dark Sleep Overlay
Implement dynamic lighting and ambient particle/overlay in `kenburns_asmr.py` and `chunk_renderer.py`:
- Video begins with standard cover image/lighting from frame `00:00` up to the exact sentence before *"dim the lights"*.
- At the cue *"dim the lights"*, gradual lighting dim-down occurs across the remaining sentence/paragraph.
- From that point onward, the entire video maintains a deep, gentle darkened mood with subtle ambient drifting specks (particles/stardust) while keyframe Ken Burns motion continues beneath this soothing dark layer.

### R4. NotebookLM SSOT Synchronization
Update NotebookLM notebook (`813e73eb-7327-4c9b-9651-fe416e6d180c`):
- Document the new Visual Consistency Architecture, 150–160 beat generation density, and the "Dim the Lights" shader specifications as authoritative project notes and sources.

### R5. Clean Slate Reset & Regeneration for Matsuo Bashō
- Purge existing 55 keyframes from Google Drive (`19krkuGIJ8l1eyASLIhKyi1oQS9f5cjmm`) and local cache.
- Generate the new 150–160 image prompt set with Visual Reference Anchor Kit and regenerate all assets.

## Acceptance Criteria

### Visual Consistency & Reference System
- [ ] Master Reference Kit exists in Google Drive `02. Media Generation/references/` containing canonical character, setting, and prop images.
- [ ] Generated prompts in `combined_imageprompts.txt` include structured reference tags mapped to each beat.
- [ ] `hsnooze.gflow` successfully references character/ingredient tiles without manual intervention.

### Beat Density & Prompts
- [ ] Exact count of 150–160 structured beats across 15 parts (~10 beats per part).
- [ ] All beats adhere to Sleep Aid visual rules (no jarring lighting, no modern artifacts).

### Video Shading & Lighting Transitions
- [ ] FFmpeg filter accurately detects or anchors the "dim the lights" timestamp from audio transcript.
- [ ] Smooth brightness curve dims down to sleep ambient level without crushing color gradients.
- [ ] Ambient overlay / drifting specks rendered smoothly with Ken Burns motion beneath.

### NotebookLM & State Reset
- [ ] Notebook `813e73eb-7327-4c9b-9651-fe416e6d180c` contains updated notes reflecting the 150-beat consistency architecture.
- [ ] Google Drive `keyframes/` cleaned and populated with the new high-density, consistent keyframe set.
- [ ] Google Sheet status accurately reflects progress.

### R1.1. Standalone Pre-Production Anchor Prompt Generation (reference_imageprompts.txt)
- Create a dedicated generator in  to produce  PRIOR to .
- Contains targeted prompts for:
  1. : Protagonist canonical facial features, traveling attire, hair, footwear.
  2. : Key companion/disciple.
  3. : Establishing interior/exterior of primary home base / recurring rooms.
  4. : Primary landscape/journey environment.
  5. : Signature tools/objects (e.g. inkstone, brush, walking staff, hat).
- The pipeline runs  through Google Flow first, uploads the resulting images to Drive , and registers them into Google Flow as Characters & Ingredients before generating the 150–160 story beats ().

## 2026-09-11T23:58:49Z

Upgrade the HistorySnooze production pipeline with a comprehensive 25-Anchor Visual Reference Architecture (covering 5 Character life-stages, 15 individual Part settings 1:1, and 5 signature props), generate pre-production anchor assets, update 150-beat narrative prompt mapping in `combined_imageprompts.txt`, sync Single Source of Truth in NotebookLM `813e73eb-7327-4c9b-9651-fe416e6d180c`, and run full keyframe generation via `hsnooze.gflow` followed by Ken Burns & "Dim the Lights" sleep video rendering for Matsuo Bashō (`id_ea1551`).

Working directory: `/Users/hanario/Documents/HistorySnooze`
Integrity mode: development

## Requirements

### R1. 25-Anchor Master Visual Kit Specification & Codebase Update
Expand `MASTER_REFERENCE_ANCHORS` in `prompt_engine.py` to exactly 25 canonical anchors:
1. Characters (5): `ref_character_basho_young` (age 20 samurai), `ref_character_basho_traveler` (age 45–50 pilgrim), `ref_character_basho_elder` (age 51 master), `ref_character_sora` (disciple companion), `ref_character_buccho` (Zen master).
2. Settings 1:1 mapped to 15 Parts (15):
   - Part 01: `ref_setting_iga_ueno` (Ueno Castle & Iga mist)
   - Part 02: `ref_setting_edo_nihonbashi` (Nihonbashi Bridge & Kanda waterworks)
   - Part 03: `ref_setting_fukagawa_interior` (Fukagawa hut interior, tatami & desk)
   - Part 04: `ref_setting_fukagawa_exterior` (Sumida riverbank & banana tree in rain)
   - Part 05: `ref_setting_fuji_river_trail` (Fuji River trail & winter mist)
   - Part 06: `ref_setting_senju_dock` (Senju dock dawn departure)
   - Part 07: `ref_setting_nikko_cedars` (Nikkō Tōshōgū sacred giant cedars)
   - Part 08: `ref_setting_yamadera_temple` (Yamadera Ryūshakuji cliff temple)
   - Part 09: `ref_setting_mogami_river` (Mogami River summer rapids)
   - Part 10: `ref_setting_kisakata_lagoon` (Kisakata lagoon & weeping willows)
   - Part 11: `ref_setting_shirakawa_barrier` (Shirakawa Barrier ancient gate)
   - Part 12: `ref_setting_genjuan_bamboo` (Genjū-an bamboo hermitage Lake Biwa)
   - Part 13: `ref_setting_kyoto_rakushisha` (Rakushisha persimmon hut Kyoto)
   - Part 14: `ref_setting_tokaido_highway` (Tōkaidō post road in frost)
   - Part 15: `ref_setting_withered_moor` (Withered moor twilight dreamscape)
3. Props (5): `ref_props_inkstone_brush`, `ref_props_travel_gear`, `ref_props_basho_leaves`, `ref_props_tea_hearth_irori`, `ref_props_travel_oi`.
- Export standalone `reference_imageprompts.txt` (25 prompts) and upload to Google Drive `02. Media Generation/references/`.

### R2. High-Density 150-Beat Mapping (1:1 Anchor Injection)
- Update `online_script_producer.py` and `combined_imageprompts.txt` so every beat in each Part references its specific Part setting, the accurate life-stage character anchor, and relevant props:
  * Part 01 beats tagged with `[CHARACTER: ref_character_basho_young]` and `[SETTING: ref_setting_iga_ueno]`.
  * Part 07 beats tagged with `[CHARACTER: ref_character_basho_traveler]` and `[SETTING: ref_setting_nikko_cedars]`.
  * Part 13 beats tagged with `[CHARACTER: ref_character_basho_elder]` and `[SETTING: ref_setting_kyoto_rakushisha]`.
- Upload updated `combined_imageprompts.txt` to Google Drive `02. Media Generation/combined/`.

### R3. Reference Generation & GFlow Execution
- Generate and verify all 25 anchor images in Google Drive `02. Media Generation/references/`.
- Execute `hsnooze.gflow` automation to batch generate 150 keyframes into `02. Media Generation/keyframes/` using the 25 anchor tiles.

### R4. NotebookLM SSOT Synchronization
- Update Note 11 in notebook `813e73eb-7327-4c9b-9651-fe416e6d180c` with the 25-Anchor matrix and 1:1 Part mapping.

### R5. Render & Master Assembly Verification
- Render 15 video chunks with Ken Burns + "Dim the Lights" cosine transition (174.73s–184.45s) + static sleep grading + 4K ambient stardust overlay.
- Concatenate master documentary and update Google Sheet Row 5 Status to Done.
