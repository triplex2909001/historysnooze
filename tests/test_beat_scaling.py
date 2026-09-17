"""
Unit and Integration Test Suite for Milestone 2: High-Density Beat Scaling (150-160 Beats)
File: tests/test_beat_scaling.py
Target Milestone: Milestone 2 (High-Density Visual Beat Generation: 150-160 Beats)

Remediated Zero-Mock, Zero-Tautology Architecture:
1. Config Validation (EXPECTED_MIN_BEATS=150, EXPECTED_MAX_BEATS=160, TARGET_BEATS_PER_PART=10)
2. Three-way Mirror Parity (hsnooze.scripting, hsnooze.render, 00.codebases) for config, beat_aligner, and online_script_producer
3. Script Segmentation & Generation (StorySegmenter, MATSUO_BASHO_150_BEATS, export_script_and_prompts)
4. Beat Alignment Duration Validation (25.0s to 45.0s bounds on standard audio inputs)
5. Gatekeeper Audits (GK3 and GK6 genuine file-based audits passing on 150 beats, failing on legacy 45/55 beats & deficient parts)
6. Tag Presence & Validity (Milestone 1 reference anchors, canonical order, validate_prompt on canonical 150 beats)
"""

import importlib.util
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import os

# Setup repository root and import paths with environment-aware fixtures
HSNOOZE_DATA_DIR = os.environ.get("HSNOOZE_DATA_DIR")
if HSNOOZE_DATA_DIR and Path(HSNOOZE_DATA_DIR).exists():
    REPO_ROOT = Path(HSNOOZE_DATA_DIR)
elif (Path(__file__).resolve().parent.parent / "hsnooze.scripting").exists():
    REPO_ROOT = Path(__file__).resolve().parent.parent
else:
    REPO_ROOT = Path(__file__).resolve().parent.parent.parent


sys.path.insert(0, str(REPO_ROOT / "hsnooze.scripting"))
sys.path.insert(0, str(REPO_ROOT / "hsnooze.render"))

from beat_aligner import align_part_beats
import config
from online_script_producer import (
    StoryBeat,
    StorySegmenter,
    get_matsuo_basho_150_beats,
    MATSUO_BASHO_150_BEATS,
    export_script_and_prompts,
    PART_SETTINGS,
)
from pipeline_orchestrator import audit_gk3_prompts, audit_gk6_assets
from prompt_engine import (
    SIGNATURE_FRAME_TAIL,
    build_consistent_prompt,
    extract_prompt_tags,
    format_combined_prompts_file,
    resolve_reference_anchor,
    validate_prompt,
)


# ==============================================================================
# 1. Config Validation Test Suite
# ==============================================================================
class TestConfigBeatScaling(unittest.TestCase):
    """Tests for central configuration constants scaled for Milestone 2."""

    def test_config_expected_min_beats_equals_150(self):
        """EXPECTED_MIN_BEATS must be scaled from 45 to 150."""
        self.assertEqual(config.EXPECTED_MIN_BEATS, 150)

    def test_config_expected_max_beats_equals_160(self):
        """EXPECTED_MAX_BEATS must be scaled from 60 to 160."""
        self.assertEqual(config.EXPECTED_MAX_BEATS, 160)

    def test_config_target_beats_per_part_equals_10(self):
        """TARGET_BEATS_PER_PART must be defined and equal 10."""
        self.assertTrue(hasattr(config, "TARGET_BEATS_PER_PART"), "TARGET_BEATS_PER_PART missing from config")
        self.assertEqual(config.TARGET_BEATS_PER_PART, 10)

    def test_config_total_parts_equals_15(self):
        """TOTAL_PARTS must remain 15."""
        self.assertEqual(config.TOTAL_PARTS, 15)

    def test_config_beat_min_duration_sec(self):
        """BEAT_MIN_DURATION_SEC must be defined as 25.0."""
        self.assertTrue(hasattr(config, "BEAT_MIN_DURATION_SEC"), "BEAT_MIN_DURATION_SEC missing from config")
        self.assertEqual(config.BEAT_MIN_DURATION_SEC, 25.0)

    def test_config_beat_max_duration_sec(self):
        """BEAT_MAX_DURATION_SEC must be defined as 45.0."""
        self.assertTrue(hasattr(config, "BEAT_MAX_DURATION_SEC"), "BEAT_MAX_DURATION_SEC missing from config")
        self.assertEqual(config.BEAT_MAX_DURATION_SEC, 45.0)

    def test_config_math_consistency(self):
        """TOTAL_PARTS * TARGET_BEATS_PER_PART must equal EXPECTED_MIN_BEATS."""
        self.assertEqual(
            config.TOTAL_PARTS * config.TARGET_BEATS_PER_PART,
            config.EXPECTED_MIN_BEATS,
            "Mathematical inconsistency between TOTAL_PARTS, TARGET_BEATS_PER_PART, and EXPECTED_MIN_BEATS"
        )

    def test_config_status_flow_contains_image_stage(self):
        """STATUS_FLOW must contain Image stage."""
        self.assertIn("Image", config.STATUS_FLOW)


# ==============================================================================
# 2. Three-Way Config & Codebase Mirror Parity Test Suite
# ==============================================================================
class TestConfigMirrorParity(unittest.TestCase):
    """Tests byte-for-byte and attribute parity across all mirrors."""

    @classmethod
    def setUpClass(cls):
        cls.scripting_config = REPO_ROOT / "hsnooze.scripting" / "config.py"
        cls.render_config = REPO_ROOT / "hsnooze.render" / "config.py"
        cls.codebases_config = REPO_ROOT / "00.codebases" / "config.py"

        cls.render_aligner = REPO_ROOT / "hsnooze.render" / "beat_aligner.py"
        cls.codebases_aligner = REPO_ROOT / "00.codebases" / "beat_aligner.py"

        cls.scripting_producer = REPO_ROOT / "hsnooze.scripting" / "online_script_producer.py"
        cls.codebases_producer = REPO_ROOT / "00.codebases" / "online_script_producer.py"

    def test_all_three_config_files_exist(self):
        """All three config.py files must exist on disk."""
        self.assertTrue(self.scripting_config.exists(), "hsnooze.scripting/config.py missing")
        self.assertTrue(self.render_config.exists(), "hsnooze.render/config.py missing")
        self.assertTrue(self.codebases_config.exists(), "00.codebases/config.py missing")

    def test_byte_parity_scripting_vs_render_config(self):
        """hsnooze.scripting/config.py must match hsnooze.render/config.py byte-for-byte."""
        self.assertEqual(self.scripting_config.read_bytes(), self.render_config.read_bytes())

    def test_byte_parity_scripting_vs_codebases_config(self):
        """hsnooze.scripting/config.py must match 00.codebases/config.py byte-for-byte."""
        self.assertEqual(self.scripting_config.read_bytes(), self.codebases_config.read_bytes())

    def test_byte_parity_render_vs_codebases_beat_aligner(self):
        """hsnooze.render/beat_aligner.py must match 00.codebases/beat_aligner.py byte-for-byte."""
        self.assertEqual(self.render_aligner.read_bytes(), self.codebases_aligner.read_bytes())

    def test_byte_parity_scripting_vs_codebases_online_script_producer(self):
        """hsnooze.scripting/online_script_producer.py must match 00.codebases/online_script_producer.py byte-for-byte."""
        self.assertEqual(self.scripting_producer.read_bytes(), self.codebases_producer.read_bytes())

    def test_exported_symbols_parity_all_three(self):
        """All exported symbols and constants must match identically across all 3 modules."""
        def load_module(name: str, path: Path):
            spec = importlib.util.spec_from_file_location(name, str(path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        m_script = load_module("cfg_script", self.scripting_config)
        m_render = load_module("cfg_render", self.render_config)
        m_codebase = load_module("cfg_codebase", self.codebases_config)

        checked_attrs = [
            "TOTAL_PARTS",
            "EXPECTED_MIN_BEATS",
            "EXPECTED_MAX_BEATS",
            "TARGET_BEATS_PER_PART",
            "BEAT_MIN_DURATION_SEC",
            "BEAT_MAX_DURATION_SEC",
            "WIDTH",
            "HEIGHT",
            "FPS",
            "RESOLUTION",
            "ZOOM_START",
            "ZOOM_MAX",
            "STATUS_FLOW",
        ]
        for attr in checked_attrs:
            val_s = getattr(m_script, attr, None)
            val_r = getattr(m_render, attr, None)
            val_c = getattr(m_codebase, attr, None)
            self.assertIsNotNone(val_s, f"{attr} missing from hsnooze.scripting/config.py")
            self.assertEqual(val_s, val_r, f"{attr} differs between scripting ({val_s}) and render ({val_r})")
            self.assertEqual(val_s, val_c, f"{attr} differs between scripting ({val_s}) and codebases ({val_c})")


# ==============================================================================
# 3. Script Story Segmentation Test Suite (Zero-Mock, Real Producer & Beats)
# ==============================================================================
class TestScriptSegmentation(unittest.TestCase):
    """Tests for StorySegmenter, canonical MATSUO_BASHO_150_BEATS, and export_script_and_prompts."""

    def test_segment_part_text_preserves_exact_10_paragraphs(self):
        """StorySegmenter.segment_part_text returns 10 paragraphs unchanged when exactly 10 are provided."""
        paras_input = [f"Part paragraph {i} describing Basho journey." for i in range(1, 11)]
        raw_text = chr(10) + chr(10)
        raw_text = raw_text.join(paras_input)
        result = StorySegmenter.segment_part_text(1, raw_text)
        self.assertEqual(len(result), 10)
        self.assertEqual(result, paras_input)

    def test_segment_part_text_splits_few_paragraphs_at_sentences(self):
        """StorySegmenter.segment_part_text splits long multi-sentence paragraphs into exactly 10 segments."""
        long_paras = [
            "Basho set forth from Fukagawa hermitage at dawn. The morning mist clung gently to the Sumida river. Banana leaves rustled quietly in the early breeze.",
            "Along the trail to Ueno, traveler sandals kicked up light dust. Ancient cedar trees offered cool, deep shade. Pilgrims whispered verses in respectful reverence.",
            "Crossing mountain passes, the path narrowed past rocky waterfalls. Sweet cedar woodsmoke drifted from distant hamlets. The travelers paused to tighten their woven straw hats.",
            "Twilight settled over the tranquil valley. Paper lanterns flickered softly within roadside tea houses. Evening bells announced nightfall under starry skies."
        ]
        raw_text = chr(10) + chr(10)
        raw_text = raw_text.join(long_paras)
        result = StorySegmenter.segment_part_text(1, raw_text)
        self.assertEqual(len(result), 10)
        for seg in result:
            self.assertTrue(len(seg.strip()) > 0)

    def test_segment_part_text_merges_many_paragraphs_to_10(self):
        """StorySegmenter.segment_part_text merges adjacent short paragraphs until exactly 10 remain."""
        short_paras = [f"Brief note {i} on the trail through the mountain pass." for i in range(1, 15)]
        raw_text = chr(10) + chr(10)
        raw_text = raw_text.join(short_paras)
        result = StorySegmenter.segment_part_text(1, raw_text)
        self.assertEqual(len(result), 10)
        for seg in result:
            self.assertTrue(len(seg.strip()) > 0)

    def test_canonical_matsuo_basho_150_beats_structure(self):
        """MATSUO_BASHO_150_BEATS must contain exactly 150 StoryBeat objects (15 parts x 10 beats)."""
        beats = get_matsuo_basho_150_beats()
        self.assertEqual(len(beats), 150)
        self.assertEqual(len(MATSUO_BASHO_150_BEATS), 150)

        for p in range(1, 16):
            part_beats = [b for b in beats if b.part_index == p]
            self.assertEqual(len(part_beats), 10, f"Part {p} does not contain exactly 10 beats")
            for b_idx, b in enumerate(part_beats, start=1):
                self.assertIsInstance(b, StoryBeat)
                self.assertEqual(b.beat_index, b_idx)
                self.assertEqual(b.beat_id, f"beat_P{p:02d}_B{b_idx:02d}.jpg")
                self.assertTrue(len(b.title.strip()) > 0)
                self.assertGreaterEqual(len(b.scene_description.strip()), 20)
                self.assertTrue(len(b.narrative_text.strip()) > 0)

    def test_segment_script_into_150_beats_from_structured_script(self):
        """StorySegmenter.segment_script_into_150_beats successfully segments a full 15-part voiceover script."""
        parts_text = []
        sep = chr(10) + chr(10)
        for p in range(1, 16):
            p_body = sep.join([
                f"Introductory narrative for part {p}. Traveling along cedar trees. Streams murmur peacefully.",
                f"Midway through part {p}, contemplation deepens. Inkstone and brush rest on low wooden table.",
                f"Evening draws near in part {p}. Temple bells resonate across valleys. Stars shine brightly.",
                f"Final reflections for part {p}. Restful slumber envelops the quiet mountain inn."
            ])
            parts_text.append(f"## Part {p:02d}: Chapter {p}" + sep + p_body)

        full_script = sep.join(parts_text)
        beats = StorySegmenter.segment_script_into_150_beats(full_script, character_name="matsuo_basho")
        self.assertEqual(len(beats), 150)
        for p in range(1, 16):
            p_beats = [b for b in beats if b.part_index == p]
            self.assertEqual(len(p_beats), 10)

    def test_segment_script_into_150_beats_fallback_on_empty(self):
        """Empty script input falls back to the canonical 150 Matsuo Basho beats."""
        beats = StorySegmenter.segment_script_into_150_beats("", character_name="matsuo_basho")
        self.assertEqual(len(beats), 150)
        self.assertEqual(beats[0].beat_id, "beat_P01_B01.jpg")

    def test_export_script_and_prompts_writes_real_files(self):
        """export_script_and_prompts writes combined_imageprompts.txt and 15 part prompt files."""
        with tempfile.TemporaryDirectory() as td:
            res = export_script_and_prompts(MATSUO_BASHO_150_BEATS, td, character_name="matsuo_basho")
            self.assertIn("combined", res)
            self.assertIn("parts", res)
            self.assertTrue(Path(res["combined"]).exists())
            self.assertEqual(len(res["parts"]), 15)

            # Combined file has exactly 150 non-empty prompt lines
            with open(res["combined"], "r", encoding="utf-8") as f:
                comb_lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            self.assertEqual(len(comb_lines), 150)

            # Each part file has exactly 10 non-empty prompt lines
            for p in range(1, 16):
                p_path = Path(res["parts"][p])
                self.assertTrue(p_path.exists())
                with open(p_path, "r", encoding="utf-8") as f:
                    p_lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
                self.assertEqual(len(p_lines), 10, f"Part {p} prompt file has {len(p_lines)} lines, expected 10")


# ==============================================================================
# 4. Beat Alignment Duration Validation Test Suite
# ==============================================================================
class TestBeatAlignmentDurations(unittest.TestCase):
    """Tests for beat alignment timestamps and duration boundaries (25.0s to 45.0s)."""

    def setUp(self):
        self.beat_images = [f"/tmp/keyframes/beat_P02_B{i:02d}.jpg" for i in range(1, 11)]

    @patch("beat_aligner.get_audio_duration")
    def test_alignment_10_beats_standard_audio_duration_bounds(self, mock_get_duration):
        """Durations must fall strictly within [25.0s, 45.0s] for standard audio lengths (250s - 450s)."""
        test_durations = [250.0, 300.0, 360.0, 400.0, 450.0]
        for audio_dur in test_durations:
            mock_get_duration.return_value = audio_dur
            res = align_part_beats(part_index=2, audio_wav_path="/tmp/audio.wav", beat_images=self.beat_images)
            self.assertEqual(res["num_beats"], 10)
            for beat in res["beats"]:
                dur = beat["duration"]
                self.assertGreaterEqual(
                    dur, 25.0,
                    f"Beat {beat['beat_id']} duration ({dur:.2f}s) < 25.0s on audio length {audio_dur}s"
                )
                self.assertLessEqual(
                    dur, 45.0,
                    f"Beat {beat['beat_id']} duration ({dur:.2f}s) > 45.0s on audio length {audio_dur}s"
                )

    @patch("beat_aligner.get_audio_duration")
    def test_alignment_exact_lower_bound_25s(self, mock_get_duration):
        """Audio duration of 250.0s with 10 beats must yield exactly 25.0s per beat."""
        mock_get_duration.return_value = 250.0
        res = align_part_beats(part_index=2, audio_wav_path="/tmp/audio.wav", beat_images=self.beat_images)
        for beat in res["beats"]:
            self.assertEqual(beat["duration"], 25.0)

    @patch("beat_aligner.get_audio_duration")
    def test_alignment_exact_upper_bound_45s(self, mock_get_duration):
        """Audio duration of 450.0s with 10 beats must yield exactly 45.0s per beat."""
        mock_get_duration.return_value = 450.0
        res = align_part_beats(part_index=2, audio_wav_path="/tmp/audio.wav", beat_images=self.beat_images)
        for beat in res["beats"]:
            self.assertEqual(beat["duration"], 45.0)

    @patch("beat_aligner.get_audio_duration")
    def test_alignment_total_duration_conservation(self, mock_get_duration):
        """Sum of beat durations must exactly equal total audio duration (within 0.001s tolerance)."""
        mock_get_duration.return_value = 357.825
        res = align_part_beats(part_index=2, audio_wav_path="/tmp/audio.wav", beat_images=self.beat_images)
        sum_durs = sum(b["duration"] for b in res["beats"])
        self.assertAlmostEqual(sum_durs, 357.825, places=3)

    @patch("beat_aligner.get_audio_duration")
    def test_alignment_timeline_contiguity(self, mock_get_duration):
        """Beats must be strictly contiguous without gaps or overlaps."""
        total_audio = 360.0
        mock_get_duration.return_value = total_audio
        res = align_part_beats(part_index=2, audio_wav_path="/tmp/audio.wav", beat_images=self.beat_images)
        beats = res["beats"]
        self.assertEqual(beats[0]["start_time"], 0.0)
        for i in range(len(beats) - 1):
            self.assertEqual(
                beats[i]["end_time"],
                beats[i + 1]["start_time"],
                f"Gap or overlap between beat {i+1} and beat {i+2}"
            )
        self.assertEqual(beats[-1]["end_time"], total_audio)

    @patch("beat_aligner.get_audio_duration")
    def test_alignment_structure_and_keys(self, mock_get_duration):
        """Aligned beats must provide part_index, beat_index, beat_id, image_path, start_time, end_time, duration."""
        mock_get_duration.return_value = 360.0
        res = align_part_beats(part_index=2, audio_wav_path="/tmp/audio.wav", beat_images=self.beat_images)
        required_keys = ["part_index", "beat_index", "beat_id", "image_path", "start_time", "end_time", "duration"]
        for beat in res["beats"]:
            for k in required_keys:
                self.assertIn(k, beat)

    def test_alignment_empty_beats_raises_value_error(self):
        """align_part_beats must raise ValueError when 0 beat images are passed."""
        with patch("beat_aligner.get_audio_duration", return_value=360.0), self.assertRaises(ValueError):
            align_part_beats(part_index=1, audio_wav_path="/tmp/audio.wav", beat_images=[])


# ==============================================================================
# 5. Gatekeeper Audit Scaling Test Suite (GK3 & GK6 Zero-Mock / Zero-Tautology)
# ==============================================================================
class TestGatekeeperAuditScaling(unittest.TestCase):
    """Tests for Gatekeeper GK6 and GK3 audits passing on 150 beats and failing on legacy 45/55 beats."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.audio_dir = Path(self.test_dir) / "02. Media Generation" / "audio"
        self.keyframes_dir = Path(self.test_dir) / "02. Media Generation" / "keyframes"
        self.audio_dir.mkdir(parents=True)
        self.keyframes_dir.mkdir(parents=True)

        fake_riff = b"RIFF" + bytes(20000)
        # Create 15 standard WAV files
        for i in range(1, 16):
            (self.audio_dir / f"Part_{i:02d}.wav").write_bytes(fake_riff)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    # --------------------------------------------------------------------------
    # GK6 Asset Audits
    # --------------------------------------------------------------------------
    def test_gk6_audit_passes_on_150_keyframes(self):
        """GK6 audit must pass when exactly 150 keyframes exist (10 beats per part across 15 parts)."""
        fake_jpg = b"\xff\xd8\xff\xe0" + bytes(100)
        for p in range(1, 16):
            for b in range(1, 11):
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(fake_jpg)

        res = audit_gk6_assets(self.test_dir)
        self.assertTrue(res["passed_gk6"], f"GK6 failed on 150 keyframes: {res}")
        self.assertEqual(res["audio_count"], 15)
        self.assertEqual(res["image_count"], 150)

    def test_gk6_audit_fails_on_legacy_45_keyframes(self):
        """GK6 audit must fail when only 45 legacy keyframes exist."""
        fake_jpg = b"\xff\xd8\xff\xe0" + bytes(100)
        for p in range(1, 16):
            for b in range(1, 4):
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(fake_jpg)

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"], "GK6 unexpectedly passed on legacy 45 keyframes")
        self.assertEqual(res["image_count"], 45)

    def test_gk6_audit_fails_on_legacy_55_keyframes(self):
        """GK6 audit must fail when 55 keyframes exist (below 150 threshold)."""
        fake_jpg = b"\xff\xd8\xff\xe0" + bytes(100)
        count = 0
        for p in range(1, 16):
            for b in range(1, 11):
                if count >= 55:
                    break
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(fake_jpg)
                count += 1

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"], "GK6 unexpectedly passed on legacy 55 keyframes")
        self.assertEqual(res["image_count"], 55)

    def test_gk6_audit_fails_when_part_missing_beats(self):
        """GK6 audit must fail if total count is 149 (one beat missing)."""
        fake_jpg = b"\xff\xd8\xff\xe0" + bytes(100)
        for p in range(1, 16):
            beats_in_part = 9 if p == 15 else 10
            for b in range(1, beats_in_part + 1):
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(fake_jpg)

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"], "GK6 unexpectedly passed with 149 keyframes")
        self.assertEqual(res["image_count"], 149)

    def test_gk6_audit_fails_when_audio_file_missing(self):
        """GK6 audit must fail if 150 keyframes exist but only 14 audio parts exist."""
        (self.audio_dir / "Part_15.wav").unlink()
        fake_jpg = b"\xff\xd8\xff\xe0" + bytes(100)
        for p in range(1, 16):
            for b in range(1, 11):
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(fake_jpg)

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"], "GK6 unexpectedly passed with missing audio file")
        self.assertEqual(res["audio_count"], 14)

    def test_gk6_audit_fails_when_part_15_wav_missing_despite_15_total_wavs(self):
        """GK6 audit fails if Part_15.wav is missing even if 15 WAV files exist (e.g. Part_00.wav present)."""
        (self.audio_dir / "Part_15.wav").unlink()
        (self.audio_dir / "Part_00.wav").write_bytes(b"RIFF" + bytes(20000))
        fake_jpg = b"\xff\xd8\xff\xe0" + bytes(100)
        for p in range(1, 16):
            for b in range(1, 11):
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(fake_jpg)

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"], "GK6 unexpectedly passed when Part_15.wav was missing")
        self.assertEqual(res["audio_count"], 15)
        self.assertIn(15, res["missing_audio_parts"])
        self.assertTrue(any("Part_15.wav" in d for d in res["details"]))

    # --------------------------------------------------------------------------
    # GK3 Prompt Audits (Genuine Execution of audit_gk3_prompts)
    # --------------------------------------------------------------------------
    def test_gk3_audit_passes_on_150_valid_prompts(self):
        """GK3 prompt audit passes when 150 valid prompts (10 per part) exist in file."""
        prompts_file = Path(self.test_dir) / "combined_imageprompts.txt"
        lines = []
        for p in range(1, 16):
            for b in range(1, 11):
                bid = f"beat_P{p:02d}_B{b:02d}.jpg"
                ptext = build_consistent_prompt(
                    scene_description=f"Basho meditating along misty pine path in part {p} beat {b}",
                    character_name="matsuo_basho",
                    character_ref="ref_character_basho",
                    setting_ref="ref_setting_tohoku_trail"
                )
                lines.append(f"{bid}: {ptext}")
        sep = chr(10) + chr(10)
        prompts_file.write_text(sep.join(lines), encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir, str(prompts_file))
        self.assertTrue(res["passed_gk3"], f"GK3 audit failed unexpectedly: {res['details']}")
        self.assertEqual(res["total_count"], 150)
        self.assertEqual(len(res["deficient_parts"]), 0)
        for p in range(1, 16):
            self.assertEqual(res["part_counts"][p], 10)

    def test_gk3_audit_passes_on_repo_combined_imageprompts(self):
        """audit_gk3_prompts passes on real repository production combined_imageprompts.txt."""
        repo_prompts = REPO_ROOT / "00.codebases" / "combined_imageprompts.txt"
        if repo_prompts.exists():
            res = audit_gk3_prompts(str(REPO_ROOT), str(repo_prompts))
            self.assertTrue(res["passed_gk3"], f"Real combined_imageprompts failed GK3: {res['details']}")
            self.assertEqual(res["total_count"], 150)

    def test_gk3_audit_fails_on_legacy_45_prompts(self):
        """audit_gk3_prompts fails directly when audited file contains only 45 prompts."""
        p45_file = Path(self.test_dir) / "legacy_45_prompts.txt"
        lines = []
        for p in range(1, 16):
            for b in range(1, 4):
                lines.append(f"beat_P{p:02d}_B{b:02d}.jpg: Scene description for part {p} beat {b}")
        sep = chr(10) + chr(10)
        p45_file.write_text(sep.join(lines), encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir, str(p45_file))
        self.assertFalse(res["passed_gk3"], "audit_gk3_prompts unexpectedly passed on 45 prompts")
        self.assertEqual(res["total_count"], 45)
        self.assertEqual(len(res["deficient_parts"]), 15)
        self.assertTrue(any("outside required range" in d for d in res["details"]))

    def test_gk3_audit_fails_on_legacy_55_prompts(self):
        """audit_gk3_prompts fails directly when audited file contains only 55 prompts."""
        p55_file = Path(self.test_dir) / "legacy_55_prompts.txt"
        lines = []
        count = 0
        for p in range(1, 16):
            for b in range(1, 11):
                if count >= 55:
                    break
                lines.append(f"beat_P{p:02d}_B{b:02d}.jpg: Scene description for part {p} beat {b}")
                count += 1
        sep = chr(10) + chr(10)
        p55_file.write_text(sep.join(lines), encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir, str(p55_file))
        self.assertFalse(res["passed_gk3"], "audit_gk3_prompts unexpectedly passed on 55 prompts")
        self.assertEqual(res["total_count"], 55)
        self.assertTrue(len(res["deficient_parts"]) > 0)
        self.assertTrue(any("outside required range" in d for d in res["details"]))

    def test_gk3_audit_fails_on_deficient_parts(self):
        """audit_gk3_prompts fails when total is 150 but a part has < 10 beats (P01=9, P02=11)."""
        pdef_file = Path(self.test_dir) / "deficient_parts.txt"
        lines = []
        # Part 1: 9 beats
        for b in range(1, 10):
            lines.append(f"beat_P01_B{b:02d}.jpg: Scene P01 B{b}")
        # Part 2: 11 beats
        for b in range(1, 12):
            lines.append(f"beat_P02_B{b:02d}.jpg: Scene P02 B{b}")
        # Parts 3..15: 10 beats each
        for p in range(3, 16):
            for b in range(1, 11):
                lines.append(f"beat_P{p:02d}_B{b:02d}.jpg: Scene P{p:02d} B{b}")
        sep = chr(10) + chr(10)
        pdef_file.write_text(sep.join(lines), encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir, str(pdef_file))
        self.assertFalse(res["passed_gk3"], "audit_gk3_prompts unexpectedly passed on deficient part")
        self.assertEqual(res["total_count"], 150)
        self.assertEqual(res["deficient_parts"], [1])
        self.assertTrue(any("Part 01 has 9 prompts, expected at least 10" in d for d in res["details"]))

    def test_gk3_audit_fails_when_file_not_found(self):
        """audit_gk3_prompts fails gracefully when prompt file does not exist."""
        empty_dir = tempfile.mkdtemp()
        try:
            res = audit_gk3_prompts(empty_dir)
            self.assertFalse(res["passed_gk3"])
            self.assertEqual(res["total_count"], 0)
            self.assertTrue(any("not found" in d for d in res["details"]))
        finally:
            shutil.rmtree(empty_dir)

    def test_gk3_audit_fails_on_malformed_beat_lines(self):
        """audit_gk3_prompts fails when lines contain malformed beat syntax."""
        pmal_file = Path(self.test_dir) / "malformed_prompts.txt"
        lines = ["beat_invalid_format: Malformed beat line without part index"]
        for p in range(1, 16):
            for b in range(1, 11):
                if p == 1 and b == 1:
                    continue
                lines.append(f"beat_P{p:02d}_B{b:02d}.jpg: Valid scene")
        sep = chr(10) + chr(10)
        pmal_file.write_text(sep.join(lines), encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir, str(pmal_file))
        self.assertFalse(res["passed_gk3"])
        self.assertTrue(any("Malformed beat line format" in d for d in res["details"]))

    def test_gk3_audit_fails_on_syntax_errors(self):
        """GK3 prompt audit fails if any prompt contains malformed syntax or forbidden terms."""
        prompts_file = Path(self.test_dir) / "forbidden_terms_prompts.txt"
        lines = []
        for p in range(1, 16):
            for b in range(1, 11):
                bid = f"beat_P{p:02d}_B{b:02d}.jpg"
                ptext = build_consistent_prompt(
                    scene_description=f"Basho meditating along misty pine path in part {p} beat {b}",
                    character_name="matsuo_basho",
                    character_ref="ref_character_basho",
                    setting_ref="ref_setting_tohoku_trail"
                )
                if p == 1 and b == 1:
                    ptext += " photorealistic 3d render"
                lines.append(f"{bid}: {ptext}")
        sep = chr(10) + chr(10)
        prompts_file.write_text(sep.join(lines), encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir, str(prompts_file))
        self.assertFalse(res["passed_gk3"], "GK3 unexpectedly passed on prompt with forbidden terms")
        self.assertTrue(any("photorealistic" in d for d in res["details"]))
        self.assertTrue(any("3d render" in d for d in res["details"]))


# ==============================================================================
# 6. Tag Presence & Validity Test Suite (Canonical MATSUO_BASHO_150_BEATS)
# ==============================================================================
class TestTagPresenceAndValidity(unittest.TestCase):
    """Tests verifying 100% tag presence and validity against Milestone 1 registry on real canonical beats."""

    @classmethod
    def setUpClass(cls):
        """Load canonical 150 story beats from online_script_producer and generate real prompts."""
        cls.beats_data = get_matsuo_basho_150_beats()
        cls.prompts_dict = StorySegmenter.generate_part_prompts(cls.beats_data, character_name="matsuo_basho")
        cls.beats_150 = list(cls.prompts_dict.items())

    def test_all_150_beats_have_at_least_one_tag(self):
        """Every generated beat out of 150 must contain at least one bracketed reference tag."""
        self.assertEqual(len(self.beats_150), 150)
        for beat_id, prompt in self.beats_150:
            tags = extract_prompt_tags(prompt)
            total_tags = sum(len(v) for v in tags.values())
            self.assertGreater(total_tags, 0, f"Beat {beat_id} has 0 reference tags!")

    def test_all_tags_have_valid_type(self):
        """All tags must belong to VALID_TAG_TYPES (CHARACTER, SETTING, PROP, INGREDIENT)."""
        valid_types = {"CHARACTER", "SETTING", "PROP", "INGREDIENT"}
        for beat_id, prompt in self.beats_150:
            tags = extract_prompt_tags(prompt)
            for tag_type, vals in tags.items():
                if vals:
                    self.assertIn(tag_type, valid_types, f"Beat {beat_id} has invalid tag type: {tag_type}")

    def test_all_tags_resolve_in_m1_registry(self):
        """All extracted tags must resolve against MASTER_REFERENCE_ANCHORS for matsuo_basho."""
        for beat_id, prompt in self.beats_150:
            tags = extract_prompt_tags(prompt)
            for tag_type, vals in tags.items():
                for tag_val in vals:
                    anchor = resolve_reference_anchor(tag_type, tag_val, "matsuo_basho")
                    self.assertIsNotNone(anchor, f"Beat {beat_id} tag [{tag_type}: {tag_val}] unresolvable in M1 registry")
                    self.assertIn("id", anchor)
                    self.assertIn("file_name", anchor)
                    self.assertEqual(anchor["tag_type"], tag_type)

    def test_character_tags_resolve_to_canonical_characters(self):
        """CHARACTER tags must resolve to canonical character IDs."""
        canonical_chars = {
            "ref_character_basho_young",
            "ref_character_basho_traveler",
            "ref_character_basho_elder",
            "ref_character_sora",
            "ref_character_buccho",
        }
        for beat_id, prompt in self.beats_150:
            tags = extract_prompt_tags(prompt)
            for tag_val in tags.get("CHARACTER", []):
                anchor = resolve_reference_anchor("CHARACTER", tag_val, "matsuo_basho")
                self.assertIn(anchor["id"], canonical_chars)

    def test_setting_tags_resolve_to_canonical_settings(self):
        """SETTING tags must resolve to the 15 canonical part settings."""
        canonical_settings = set(PART_SETTINGS.values())
        for beat_id, prompt in self.beats_150:
            tags = extract_prompt_tags(prompt)
            for tag_val in tags.get("SETTING", []):
                anchor = resolve_reference_anchor("SETTING", tag_val, "matsuo_basho")
                self.assertIn(anchor["id"], canonical_settings)

    def test_prop_tags_resolve_to_canonical_props(self):
        """PROP tags must resolve to canonical prop IDs."""
        canonical_props = {
            "ref_props_inkstone_brush",
            "ref_props_travel_gear",
            "ref_props_basho_leaves",
            "ref_props_tea_hearth_irori",
            "ref_props_travel_oi",
        }
        for beat_id, prompt in self.beats_150:
            tags = extract_prompt_tags(prompt)
            for tag_val in tags.get("PROP", []):
                anchor = resolve_reference_anchor("PROP", tag_val, "matsuo_basho")
                self.assertIn(anchor["id"], canonical_props)

    def test_one_to_one_part_settings_mapping(self):
        """Every beat in Part p must reference the exact setting anchor for Part p."""
        for beat_id, prompt in self.beats_150:
            m = re.search(r"beat_P(\d+)_B(\d+)", beat_id)
            self.assertIsNotNone(m, f"Invalid beat ID format: {beat_id}")
            p_num = int(m.group(1))
            expected_setting = PART_SETTINGS[p_num]
            tags = extract_prompt_tags(prompt)
            setting_tags = tags.get("SETTING", [])
            self.assertEqual(len(setting_tags), 1, f"Beat {beat_id} expected 1 setting tag, got {setting_tags}")
            resolved = resolve_reference_anchor("SETTING", setting_tags[0], "matsuo_basho")
            self.assertEqual(resolved["id"], expected_setting, f"Beat {beat_id} setting {resolved['id']} != {expected_setting}")

    def test_character_life_stage_allocation(self):
        """Verifies character life-stage allocation across 150 beats: young (P01-02), traveler (P05-11 except P06_B04 sora), elder (P03-04, P12-15)."""
        for beat_id, prompt in self.beats_150:
            m = re.search(r"beat_P(\d+)_B(\d+)", beat_id)
            self.assertIsNotNone(m)
            p_num = int(m.group(1))
            b_num = int(m.group(2))
            tags = extract_prompt_tags(prompt)
            char_tags = tags.get("CHARACTER", [])
            self.assertEqual(len(char_tags), 1, f"Beat {beat_id} expected 1 character tag, got {char_tags}")
            resolved = resolve_reference_anchor("CHARACTER", char_tags[0], "matsuo_basho")
            if p_num == 6 and b_num == 4:
                expected_char = "ref_character_sora"
            elif p_num in (1, 2):
                expected_char = "ref_character_basho_young"
            elif 5 <= p_num <= 11:
                expected_char = "ref_character_basho_traveler"
            else:
                expected_char = "ref_character_basho_elder"
            self.assertEqual(resolved["id"], expected_char, f"Beat {beat_id} character {resolved['id']} != {expected_char}")

    def test_all_five_props_represented(self):
        """All 5 signature props must be contextually distributed across the 150 beats."""
        props_observed = set()
        for beat_id, prompt in self.beats_150:
            tags = extract_prompt_tags(prompt)
            for tag_val in tags.get("PROP", []):
                resolved = resolve_reference_anchor("PROP", tag_val, "matsuo_basho")
                props_observed.add(resolved["id"])
        self.assertEqual(props_observed, {
            "ref_props_inkstone_brush",
            "ref_props_travel_gear",
            "ref_props_basho_leaves",
            "ref_props_tea_hearth_irori",
            "ref_props_travel_oi",
        })

    def test_canonical_tag_ordering_in_all_prompts(self):
        """Tags within each prompt must follow canonical order: CHARACTER -> SETTING -> PROP -> INGREDIENT."""
        order_map = {"CHARACTER": 0, "SETTING": 1, "PROP": 2, "INGREDIENT": 3}
        tag_pattern = re.compile(r"\[(CHARACTER|SETTING|PROP|INGREDIENT):\s*([^\]]+)\]", re.IGNORECASE)
        for beat_id, prompt in self.beats_150:
            matches = [m.group(1).upper() for m in tag_pattern.finditer(prompt)]
            indices = [order_map[t] for t in matches]
            self.assertEqual(indices, sorted(indices), f"Beat {beat_id} tags not in canonical order: {matches}")

    def test_all_150_prompts_pass_validate_prompt(self):
        """Every generated prompt must pass validate_prompt with zero issues and length <= 1500 chars."""
        for beat_id, prompt in self.beats_150:
            full_line = f"{beat_id}: {prompt}"
            audit = validate_prompt(full_line)
            self.assertTrue(audit["is_valid"], f"Prompt {beat_id} failed validate_prompt: {audit['issues']}")
            self.assertEqual(audit["issues"], [])
            self.assertLessEqual(audit["length"], 1500, f"Prompt {beat_id} length ({audit['length']}) exceeds 1500 chars")
            self.assertTrue(prompt.endswith(SIGNATURE_FRAME_TAIL))


if __name__ == "__main__":
    unittest.main()
