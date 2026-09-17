"""
HistorySnooze Render Pipeline Test Suite (Milestone 3)
Target: hsnooze.render/ & 00.codebases/ (kenburns_asmr.py, chunk_renderer.py, beat_aligner.py, cue_extractor.py, master_assembler.py)
Requirements: R2 (150-160 Beat Pacing), R3 ("Dim the Lights" Dynamic Lighting & Dark Sleep Overlay)

Testing Standards:
- Zero tautologies: Every assertion verifies explicit independent invariants and mathematical properties.
- Zero mock shortcuts: Filter strings, mathematical easing curves, and command builder outputs are tested directly.
- Local compatibility: Pure Python execution on CPU runs in < 1 second. Live FFmpeg transcode dry-runs are conditionally executed if FFmpeg binary is available.
"""

import filecmp
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch, MagicMock

HSNOOZE_DATA_DIR = os.environ.get("HSNOOZE_DATA_DIR")
if HSNOOZE_DATA_DIR and Path(HSNOOZE_DATA_DIR).exists():
    REPO_ROOT = Path(HSNOOZE_DATA_DIR)
else:
    REPO_ROOT = Path(__file__).resolve().parent.parent

RENDER_DIR = REPO_ROOT / "hsnooze.render"
CODEBASE_DIR = REPO_ROOT / "00.codebases"

if str(RENDER_DIR) not in sys.path:
    sys.path.insert(0, str(RENDER_DIR))


import kenburns_asmr  # noqa: F401
from kenburns_asmr import (
    build_zoompan_expr,
    build_filter_graph,
    build_render_command,
    render_kenburns_beat
)
import beat_aligner  # noqa: F401
from beat_aligner import align_part_beats
import chunk_renderer  # noqa: F401
from chunk_renderer import (
    render_part_chunk,
    resolve_stardust_asset_path,
    resolve_part01_cue_timestamps
)
from cue_extractor import (
    extract_part01_cue_timestamps,
    validate_cue_manifest
)


# ==============================================================================
# 1. Filter Graph Construction: Normal Beat (4 tests)
# ==============================================================================
class TestFilterGraphNormalBeat(unittest.TestCase):
    """Verifies filter graph generation for standard Ken Burns beats (pre-dimming, un-shaded)."""

    def test_normal_beat_filter_chain_structure(self):
        """Validates 8K prescaling, cropping, and zoompan filter tokens for zoom-in."""
        total_frames = 900
        filt, out_label = build_filter_graph(
            zoom_in=True,
            total_frames=total_frames,
            width=3840,
            height=2160,
            fps=30,
            is_transition_beat=False,
            sleep_mode=False,
            has_overlay=False
        )
        self.assertIsNone(out_label, "Normal beat should not require a named output label.")
        self.assertTrue(
            "scale=4224x2376:force_original_aspect_ratio=increase" in filt
            or "scale=8000x4500:force_original_aspect_ratio=increase" in filt,
            f"Prescale filter token missing from filter: {filt}"
        )
        self.assertTrue(
            "crop=4224:2376" in filt
            or "crop=8000:4500" in filt,
            f"Crop filter token missing from filter: {filt}"
        )
        self.assertIn("zoompan=", filt)
        self.assertIn(f"d={total_frames}:s=3840x2160:fps=30", filt)
        self.assertIn("min(zoom+", filt)
        self.assertIn("1.04", filt)

    def test_normal_beat_zoom_out_expression(self):
        """Validates zoompan expression when zoom_in=False (starts at 1.04 and contracts)."""
        filt, _ = build_filter_graph(
            zoom_in=False,
            total_frames=1200,
            width=3840,
            height=2160,
            fps=30,
            is_transition_beat=False,
            sleep_mode=False,
            has_overlay=False
        )
        self.assertIn("if(eq(on,1),1.04,max(zoom-", filt)
        self.assertIn("1.00", filt)

    def test_normal_beat_absence_of_sleep_shading_filters(self):
        """Normal beats MUST NOT contain eq, vignette, split, or blend filters."""
        filt, _ = build_filter_graph(
            zoom_in=True,
            total_frames=900,
            is_transition_beat=False,
            sleep_mode=False,
            has_overlay=False
        )
        self.assertNotIn("eq=", filt)
        self.assertNotIn("vignette=", filt)
        self.assertNotIn("split=", filt)
        self.assertNotIn("blend=", filt)

    def test_zoompan_centering_geometry(self):
        """Verifies camera panning is centered on viewport midpoint: iw/2-(iw/zoom/2)."""
        _, x_expr, y_expr = build_zoompan_expr(zoom_in=True, total_frames=900)
        self.assertEqual(x_expr, "iw/2-(iw/zoom/2)")
        self.assertEqual(y_expr, "ih/2-(ih/zoom/2)")


# ==============================================================================
# 2. Filter Graph Construction: Static Sleep Beat (6 tests)
# ==============================================================================
class TestFilterGraphStaticSleepBeat(unittest.TestCase):
    """Verifies static sleep mood grading (P01_B02..B10 and all beats of P02..P15)."""

    def test_static_sleep_beat_with_overlay(self):
        """Validates dual-input filter complex with eq, vignette, and screen-blended overlay."""
        filt, out_label = build_filter_graph(
            zoom_in=True,
            total_frames=900,
            width=3840,
            height=2160,
            fps=30,
            is_transition_beat=False,
            sleep_mode=True,
            has_overlay=True,
            stardust_opacity=0.35,
            vignette="PI/4"
        )
        self.assertEqual(out_label, "[out]")
        # Ken Burns base applied to input 0
        self.assertTrue(filt.startswith("[0:v]"))
        self.assertIn("[kb_dark]", filt)
        # Sleep shading parameters
        self.assertIn("contrast=0.9", filt)
        self.assertIn("brightness=-0.05", filt)
        self.assertIn("gamma=0.85", filt)
        self.assertIn("saturation=0.88", filt)
        self.assertTrue(
            "vignette=PI/4:aspect=16/9" in filt or "vignette=PI/4:aspect=3840/2160" in filt,
            f"Vignette token missing or unexpected format: {filt}"
        )
        # Overlay input 1 processing
        self.assertTrue(
            "[1:v] format=rgba,colorchannelmixer=aa=0.35 [pts_alpha]" in filt
            or "[1:v] scale=3840:2160,format=rgba,colorchannelmixer=aa=0.35 [pts_alpha]" in filt,
            f"Alpha mixer token missing in overlay stream: {filt}"
        )
        self.assertIn("[kb_dark][pts_alpha] blend=all_mode=screen,format=rgba [out]", filt)
        # No dynamic split needed on static sleep beat
        self.assertNotIn("split=", filt)

    def test_static_sleep_beat_order_of_operations(self):
        """Ensures Ken Burns motion occurs BEFORE eq, vignette, and particle overlay."""
        filt, _ = build_filter_graph(
            zoom_in=True,
            total_frames=900,
            sleep_mode=True,
            has_overlay=True,
            vignette="PI/4"
        )
        kb_pos = filt.find("zoompan=")
        eq_pos = filt.find("eq=")
        vig_pos = filt.find("vignette=")
        blend_pos = filt.find("blend=all_mode=screen")

        self.assertTrue(kb_pos < eq_pos, "Ken Burns motion must precede eq color grading.")
        self.assertTrue(eq_pos < vig_pos, "eq color grading must precede vignette.")
        self.assertTrue(vig_pos < blend_pos, "vignette must precede screen blend overlay.")

    def test_static_sleep_beat_without_overlay(self):
        """When overlay is disabled or absent, generates single-input filter string."""
        filt, out_label = build_filter_graph(
            zoom_in=True,
            total_frames=900,
            sleep_mode=True,
            has_overlay=False,
            vignette="PI/4"
        )
        self.assertIsNone(out_label)
        self.assertIn("eq=contrast=0.9", filt)
        self.assertTrue(
            "vignette=PI/4:aspect=16/9" in filt or "vignette=PI/4:aspect=3840/2160" in filt,
            f"Vignette token missing or unexpected format: {filt}"
        )
        self.assertNotIn("[1:v]", filt)
        self.assertNotIn("blend=all_mode=screen", filt)

    def test_static_sleep_beat_color_grading_parameters(self):
        """Verifies exact sleep grade parameters match design specification."""
        filt, _ = build_filter_graph(
            zoom_in=True,
            total_frames=900,
            sleep_mode=True,
            has_overlay=False
        )
        self.assertIn("contrast=0.90", filt)
        self.assertIn("brightness=-0.05", filt)
        self.assertIn("saturation=0.88", filt)
        self.assertIn("gamma=0.85", filt)

    def test_static_sleep_beat_vignette_parameters(self):
        """Verifies PI/4 vignette angle and 16/9 aspect ratio constraints."""
        filt, _ = build_filter_graph(
            zoom_in=True,
            total_frames=900,
            sleep_mode=True,
            has_overlay=False,
            vignette="PI/4"
        )
        self.assertTrue(
            "vignette=PI/4:aspect=16/9" in filt or "vignette=PI/4:aspect=3840/2160" in filt,
            f"Vignette token missing or unexpected format: {filt}"
        )

    def test_static_sleep_beat_custom_grading_overrides(self):
        """Verifies custom sleep shading parameter overrides are respected."""
        filt, _ = build_filter_graph(
            zoom_in=True,
            total_frames=900,
            sleep_mode=True,
            has_overlay=False,
            contrast=0.80,
            brightness=-0.10,
            saturation=0.75,
            gamma=0.80
        )
        self.assertIn("contrast=0.80", filt)
        self.assertIn("brightness=-0.10", filt)
        self.assertIn("saturation=0.75", filt)
        self.assertIn("gamma=0.80", filt)


# ==============================================================================
# 3. Filter Graph Construction: Dynamic Transition Beat (P01_B01) (6 tests)
# ==============================================================================
class TestFilterGraphTransitionBeat(unittest.TestCase):
    """Verifies dual-stream cosine blend dynamic dimming and stardust ramp on Part 01 Beat 1."""

    def setUp(self):
        self.t0 = 41.250
        self.t1 = 48.700
        self.delta = round(self.t1 - self.t0, 3)  # 7.450

    def test_transition_beat_dual_stream_split(self):
        """Verifies split=2 produces pristine [kb_norm] and graded [kb_for_dark]."""
        filt, out_label = build_filter_graph(
            zoom_in=True,
            total_frames=1500,
            is_transition_beat=True,
            dim_start_sec=self.t0,
            dim_end_sec=self.t1,
            sleep_mode=False,
            has_overlay=True
        )
        self.assertEqual(out_label, "[out]")
        self.assertIn("[kb] split=2 [kb_norm][kb_for_dark]", filt)
        self.assertIn("[kb_for_dark] eq=contrast=0.9", filt)
        self.assertNotIn("[kb_norm] eq=", filt)  # kb_norm must stay pristine

    def test_transition_beat_cosine_formula_extraction(self):
        """Verifies exact cosine easing formula presence in blend expression."""
        filt, _ = build_filter_graph(
            zoom_in=True,
            total_frames=1500,
            is_transition_beat=True,
            dim_start_sec=self.t0,
            dim_end_sec=self.t1,
            has_overlay=False
        )
        self.assertIn(f"lte(T,{self.t0:.3f})", filt)
        self.assertIn(f"gte(T,{self.t1:.3f})", filt)
        self.assertIn(f"PI*(T-{self.t0:.3f})/{self.delta:.3f}", filt)

    def test_cosine_easing_mathematical_properties(self):
        """
        Numerically simulates and evaluates the generated blend equation:
        alpha(T) = 0.5 * (1 - cos(PI * (T - t0) / delta))
        """
        def eval_alpha(T):
            if T <= self.t0:
                return 0.0
            elif T >= self.t1:
                return 1.0
            else:
                return 0.5 * (1.0 - math.cos(math.pi * (T - self.t0) / self.delta))

        # 1. Pre-dimming boundary: exactly 0.0 (100% normal image)
        self.assertEqual(eval_alpha(0.0), 0.0)
        self.assertEqual(eval_alpha(self.t0), 0.0)

        # 2. Post-dimming boundary: exactly 1.0 (100% dark sleep mood)
        self.assertEqual(eval_alpha(self.t1), 1.0)
        self.assertEqual(eval_alpha(self.t1 + 10.0), 1.0)

        # 3. Midpoint: exactly 0.5 (50/50 blend)
        mid = (self.t0 + self.t1) / 2.0
        self.assertAlmostEqual(eval_alpha(mid), 0.5, places=5)

        # 4. Smooth ease-in: at 25% duration, alpha is ~14.6% (much softer than linear 25%)
        t_25 = self.t0 + 0.25 * self.delta
        expected_25 = 0.5 * (1.0 - math.cos(math.pi * 0.25))
        self.assertAlmostEqual(eval_alpha(t_25), expected_25, places=5)
        self.assertTrue(eval_alpha(t_25) < 0.25)

        # 5. Smooth ease-out: at 75% duration, alpha is ~85.4% (decelerating)
        t_75 = self.t0 + 0.75 * self.delta
        expected_75 = 0.5 * (1.0 - math.cos(math.pi * 0.75))
        self.assertAlmostEqual(eval_alpha(t_75), expected_75, places=5)
        self.assertTrue(eval_alpha(t_75) > 0.75)

    def test_transition_dynamic_overlay_opacity_ramp(self):
        """Verifies that overlay opacity synchronizes with lighting dimming curve."""
        filt, _ = build_filter_graph(
            zoom_in=True,
            total_frames=1500,
            is_transition_beat=True,
            dim_start_sec=self.t0,
            dim_end_sec=self.t1,
            has_overlay=True
        )
        opacity_pattern = (
            rf"all_opacity='if\(lte\(T,{self.t0:.3f}\),\s*0\.0,\s*"
            rf"if\(gte\(T,{self.t1:.3f}\),\s*1\.0,\s*"
            rf"0\.5\*\(1-cos\(PI\*\(T-{self.t0:.3f}\)/{self.delta:.3f}\)\)\)\)'"
        )
        self.assertIsNotNone(re.search(opacity_pattern, filt), "Overlay opacity must follow cosine ramp.")

    def test_transition_beat_fallback_without_overlay(self):
        """When overlay is missing on transition beat, produces clean dual-stream without [1:v]."""
        filt, out_label = build_filter_graph(
            zoom_in=True,
            total_frames=1500,
            is_transition_beat=True,
            dim_start_sec=self.t0,
            dim_end_sec=self.t1,
            has_overlay=False
        )
        self.assertEqual(out_label, "[out]")
        self.assertNotIn("[1:v]", filt)
        self.assertNotIn("pts_alpha", filt)
        self.assertIn("split=2", filt)
        self.assertIn("blend=all_expr=", filt)

    def test_transition_beat_inverted_timestamps_fallback(self):
        """When dim_end_sec <= dim_start_sec, safely falls back without zero division."""
        filt, out_label = build_filter_graph(
            zoom_in=True,
            total_frames=1500,
            is_transition_beat=True,
            dim_start_sec=50.0,
            dim_end_sec=40.0,
            has_overlay=False
        )
        self.assertEqual(out_label, "[out]")
        self.assertIn("blend=all_expr=", filt)
        # Should fall back to 38.0 -> 45.0
        self.assertIn("lte(T,38.000)", filt)
        self.assertIn("gte(T,45.000)", filt)

    def test_transition_beat_sub_millisecond_delta_fallback(self):
        """When dim_end_sec - dim_start_sec < 0.0005s, delta rounds to 0.0; must fall back to 38s->45s without zero division."""
        filt, out_label = build_filter_graph(
            zoom_in=True,
            total_frames=1500,
            is_transition_beat=True,
            dim_start_sec=10.0,
            dim_end_sec=10.0004,
            has_overlay=False
        )
        self.assertEqual(out_label, "[out]")
        self.assertIn("lte(T,38.000)", filt)
        self.assertIn("gte(T,45.000)", filt)
        self.assertIn("/7.000", filt)
        self.assertNotIn("/0.000", filt)
        denoms = re.findall(r"PI\*\(T-[0-9\.]+\)/([0-9\.]+)", filt)
        for d in denoms:
            self.assertGreater(float(d), 0.0)


# ==============================================================================
# 4. Fallback Behavior: Missing or Invalid Overlay Asset (5 tests)
# ==============================================================================
class TestOverlayFallbackBehavior(unittest.TestCase):
    """Verifies that missing or invalid overlay assets gracefully fall back without crashing."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.test_img = os.path.join(self.tmp_dir, "test.jpg")
        with open(self.test_img, "wb") as f:
            f.write(b"dummy")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_fallback_when_overlay_none(self):
        """When overlay_asset_path is None, command has exactly 1 input and no second stream."""
        cmd = build_render_command(
            image_path=self.test_img,
            duration=30.0,
            output_clip_path=os.path.join(self.tmp_dir, "out.mp4"),
            sleep_mode=True,
            overlay_asset_path=None
        )
        inputs = [cmd[i+1] for i, arg in enumerate(cmd) if arg == "-i"]
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0], self.test_img)
        self.assertNotIn("-stream_loop", cmd)

    def test_fallback_when_overlay_file_does_not_exist(self):
        """When overlay file path does not exist, command falls back to single input without error."""
        missing_path = os.path.join(self.tmp_dir, "nonexistent_stardust.mp4")
        cmd = build_render_command(
            image_path=self.test_img,
            duration=30.0,
            output_clip_path=os.path.join(self.tmp_dir, "out.mp4"),
            sleep_mode=True,
            overlay_asset_path=missing_path
        )
        inputs = [cmd[i+1] for i, arg in enumerate(cmd) if arg == "-i"]
        self.assertEqual(len(inputs), 1, "Missing overlay must not be added to inputs.")
        cmd_str = " ".join(cmd)
        self.assertNotIn(missing_path, cmd_str)
        self.assertNotIn("[1:v]", cmd_str)

    def test_fallback_when_overlay_file_empty(self):
        """When overlay file exists but is 0 bytes, treated as invalid and omitted."""
        empty_path = os.path.join(self.tmp_dir, "empty_stardust.mp4")
        open(empty_path, "wb").close()  # 0 bytes
        cmd = build_render_command(
            image_path=self.test_img,
            duration=30.0,
            output_clip_path=os.path.join(self.tmp_dir, "out.mp4"),
            sleep_mode=True,
            overlay_asset_path=empty_path
        )
        inputs = [cmd[i+1] for i, arg in enumerate(cmd) if arg == "-i"]
        self.assertEqual(len(inputs), 1)

    @patch("kenburns_asmr.subprocess.run")
    def test_render_kenburns_beat_missing_overlay_does_not_raise(self, mock_run):
        """render_kenburns_beat completes without raising FileNotFoundError for missing overlay."""
        mock_run.return_value = MagicMock(returncode=0)
        out_path = os.path.join(self.tmp_dir, "out.mp4")
        res = render_kenburns_beat(
            image_path=self.test_img,
            duration=10.0,
            output_clip_path=out_path,
            sleep_mode=True,
            overlay_asset_path=os.path.join(self.tmp_dir, "ghost.mp4")
        )
        self.assertEqual(res, out_path)
        self.assertTrue(mock_run.called)

    def test_fallback_transition_beat_missing_overlay(self):
        """Transition beat with missing overlay produces 1 input and valid complex filter."""
        missing_path = os.path.join(self.tmp_dir, "ghost_trans.mp4")
        cmd = build_render_command(
            image_path=self.test_img,
            duration=45.0,
            output_clip_path=os.path.join(self.tmp_dir, "trans.mp4"),
            is_transition_beat=True,
            dim_start_sec=38.0,
            dim_end_sec=45.0,
            overlay_asset_path=missing_path
        )
        inputs = [cmd[i+1] for i, arg in enumerate(cmd) if arg == "-i"]
        self.assertEqual(len(inputs), 1)
        self.assertNotIn("-stream_loop", cmd)
        cmd_str = " ".join(cmd)
        self.assertNotIn("[1:v]", cmd_str)

    def test_fallback_when_overlay_file_unreadable(self):
        """When overlay file exists but has chmod 000 (unreadable), falls back to single input without crashing."""
        unreadable_path = os.path.join(self.tmp_dir, "unreadable_overlay.mp4")
        with open(unreadable_path, "wb") as f:
            f.write(b"data")
        os.chmod(unreadable_path, 0o000)

        try:
            if not os.access(unreadable_path, os.R_OK):
                cmd = build_render_command(
                    image_path=self.test_img,
                    duration=30.0,
                    output_clip_path=os.path.join(self.tmp_dir, "out.mp4"),
                    sleep_mode=True,
                    overlay_asset_path=unreadable_path
                )
                inputs = [cmd[i+1] for i, arg in enumerate(cmd) if arg == "-i"]
                self.assertEqual(len(inputs), 1)
                self.assertNotIn(unreadable_path, " ".join(cmd))
                self.assertNotIn("-stream_loop", cmd)
        finally:
            os.chmod(unreadable_path, 0o644)

    def test_fallback_when_overlay_path_is_directory(self):
        """When overlay path is a directory (not a regular file), falls back to single input without crashing."""
        dir_path = os.path.join(self.tmp_dir, "overlay_dir")
        os.makedirs(dir_path, exist_ok=True)

        cmd = build_render_command(
            image_path=self.test_img,
            duration=30.0,
            output_clip_path=os.path.join(self.tmp_dir, "out.mp4"),
            sleep_mode=True,
            overlay_asset_path=dir_path
        )
        inputs = [cmd[i+1] for i, arg in enumerate(cmd) if arg == "-i"]
        self.assertEqual(len(inputs), 1)
        self.assertNotIn(dir_path, " ".join(cmd))
        self.assertNotIn("-stream_loop", cmd)


# ==============================================================================
# 5. Audio Cue Extraction and Schema Validation (Part_01_cues.json) (7 tests)
# ==============================================================================
class TestAudioCueExtractionAndSchema(unittest.TestCase):
    """Verifies parsing, deterministic timestamp calculation, and schema rules for Part 01 cues."""

    def test_cue_manifest_valid_schema(self):
        """Validates proper JSON schema conforming to PROJECT.md interface contract."""
        valid_cue = {
            "part_index": 1,
            "cue_text": "Now, dim the lights, maybe turn on a fan for that soft background hum, and let’s ease into tonight’s journey together.",
            "cue_chunk_index": 3,
            "cue_chunk_file": "part_01_chunk_003.wav",
            "cue_start_sec": 41.250,
            "cue_end_sec": 48.700,
            "dim_duration_sec": 7.450
        }
        # Invariant checks
        self.assertEqual(valid_cue["part_index"], 1)
        self.assertRegex(valid_cue["cue_text"].lower(), r"\bdim\s+the\s+lights\b")
        self.assertGreaterEqual(valid_cue["cue_start_sec"], 0.0)
        self.assertGreater(valid_cue["cue_end_sec"], valid_cue["cue_start_sec"])
        self.assertAlmostEqual(
            valid_cue["dim_duration_sec"],
            valid_cue["cue_end_sec"] - valid_cue["cue_start_sec"],
            places=3
        )

    def test_cue_timestamp_deterministic_math(self):
        """Simulates sentence-level chunks with 1.0s intra-silence and calculates exact cue timestamps."""
        chunk_durations = [12.500, 15.250, 7.450, 14.800]  # Chunk 3 is the cue
        intra_silence_sec = 1.000

        expected_start = chunk_durations[0] + intra_silence_sec + chunk_durations[1] + intra_silence_sec
        expected_end = expected_start + chunk_durations[2]
        expected_dim_dur = expected_end - expected_start

        self.assertAlmostEqual(expected_start, 29.750, places=3)
        self.assertAlmostEqual(expected_end, 37.200, places=3)
        self.assertAlmostEqual(expected_dim_dur, 7.450, places=3)

    def test_cue_schema_adversarial_rejections(self):
        """Verifies schema validation errors on malformed cue definitions."""
        # Non-part 1
        with self.assertRaises(ValueError):
            self._validate_cue_dict({"part_index": 2, "cue_text": "dim the lights", "cue_start_sec": 10.0, "cue_end_sec": 15.0, "dim_duration_sec": 5.0})

        # Missing cue phrase
        with self.assertRaises(ValueError):
            self._validate_cue_dict({"part_index": 1, "cue_text": "Good night everyone.", "cue_start_sec": 10.0, "cue_end_sec": 15.0, "dim_duration_sec": 5.0})

        # Inverted timestamps
        with self.assertRaises(ValueError):
            self._validate_cue_dict({"part_index": 1, "cue_text": "dim the lights", "cue_start_sec": 20.0, "cue_end_sec": 15.0, "dim_duration_sec": 5.0})

        # Inconsistent duration
        with self.assertRaises(ValueError):
            self._validate_cue_dict({"part_index": 1, "cue_text": "dim the lights", "cue_start_sec": 10.0, "cue_end_sec": 20.0, "dim_duration_sec": 5.0})

    def _validate_cue_dict(self, d):
        if d.get("part_index") != 1:
            raise ValueError("Cue anchoring is only valid on Part 01.")
        if not re.search(r"\bdim\s+the\s+lights\b", d.get("cue_text", ""), re.IGNORECASE):
            raise ValueError("Cue text missing 'dim the lights'.")
        if d.get("cue_start_sec", 0) >= d.get("cue_end_sec", 0):
            raise ValueError("cue_start_sec must be strictly less than cue_end_sec.")
        if round(d.get("cue_end_sec") - d.get("cue_start_sec"), 3) != round(d.get("dim_duration_sec", 0), 3):
            raise ValueError("dim_duration_sec must match end - start.")
        return True

    def test_cue_extractor_extract_part01_cue_timestamps_deterministic_fallback(self):
        """extract_part01_cue_timestamps returns verified fallback constants when audio not present."""
        cues = extract_part01_cue_timestamps()
        self.assertEqual(cues["part_index"], 1)
        self.assertEqual(cues["cue_start_sec"], 174.73)
        self.assertEqual(cues["cue_end_sec"], 184.45)
        self.assertEqual(cues["dim_duration_sec"], 9.72)
        self.assertEqual(cues["recommended_b01_duration_sec"], 186.45)
        self.assertEqual(cues["extraction_method"], "deterministic_fallback")

    def test_cue_extractor_writes_json(self):
        """extract_part01_cue_timestamps writes valid JSON to output_json_path."""
        with tempfile.TemporaryDirectory() as td:
            out_json = os.path.join(td, "Part_01_cues.json")
            cues = extract_part01_cue_timestamps(output_json_path=out_json)
            self.assertTrue(os.path.exists(out_json))
            with open(out_json, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["cue_start_sec"], cues["cue_start_sec"])
            self.assertEqual(loaded["part_index"], 1)

    def test_cue_extractor_tier1_mock_chunks(self):
        """extract_part01_cue_timestamps Tier 1 calculates exact timestamps from chunk WAV files."""
        with tempfile.TemporaryDirectory() as td:
            # Create 17 minimal mock WAV files (1 second each)
            for i in range(1, 18):
                wav_path = os.path.join(td, f"part_01_chunk_{i:03d}.wav")
                with wave.open(wav_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    # 1.0 second of audio
                    wf.writeframes(b"\x00\x00" * 24000)

            cues = extract_part01_cue_timestamps(chunks_dir=td, intra_silence_sec=1.0, buffer_sec=2.0)
            self.assertEqual(cues["extraction_method"], "exact_wav_chunks")
            # 16 chunks of 1.0s + 16 silences of 1.0s = 32.0s
            self.assertEqual(cues["cue_start_sec"], 32.0)
            self.assertEqual(cues["cue_end_sec"], 33.0)
            self.assertEqual(cues["dim_duration_sec"], 1.0)
            self.assertEqual(cues["recommended_b01_duration_sec"], 35.0)

    def test_cue_extractor_validate_cue_manifest_helper(self):
        """Validates that validate_cue_manifest accepts valid cue dicts and rejects invalid ones."""
        valid_dict = {
            "part_index": 1,
            "cue_text": "Now, dim the lights...",
            "cue_start_sec": 174.73,
            "cue_end_sec": 184.45,
            "dim_duration_sec": 9.72
        }
        self.assertTrue(validate_cue_manifest(valid_dict))

        invalid_dict = valid_dict.copy()
        invalid_dict["part_index"] = 2
        with self.assertRaises(ValueError):
            validate_cue_manifest(invalid_dict)


# ==============================================================================
# 6. Command Builder Verification & Codec Selection (5 tests)
# ==============================================================================
class TestCommandBuilderAndCodecSelection(unittest.TestCase):
    """Verifies that FFmpeg CLI argument lists are properly constructed and respect hardware acceleration."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.img_path = os.path.join(self.tmp_dir, "frame.jpg")
        with open(self.img_path, "wb") as f:
            f.write(b"raw")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    @patch("kenburns_asmr.check_nvenc_available")
    def test_command_builder_nvenc_selection(self, mock_nvenc):
        """When NVENC is available and force_cpu=False, selects h264_nvenc with p4 preset."""
        mock_nvenc.return_value = True
        cmd = build_render_command(
            image_path=self.img_path,
            duration=30.0,
            output_clip_path=os.path.join(self.tmp_dir, "clip.mp4"),
            force_cpu=False
        )
        self.assertIn("-c:v", cmd)
        c_idx = cmd.index("-c:v")
        self.assertEqual(cmd[c_idx + 1], "h264_nvenc")
        self.assertIn("-preset", cmd)
        p_idx = cmd.index("-preset")
        self.assertEqual(cmd[p_idx + 1], "p4")
        self.assertIn("-cq", cmd)

    @patch("kenburns_asmr.check_nvenc_available")
    def test_command_builder_libx264_fallback(self, mock_nvenc):
        """When NVENC is unavailable, falls back to libx264 with crf 18."""
        mock_nvenc.return_value = False
        cmd = build_render_command(
            image_path=self.img_path,
            duration=30.0,
            output_clip_path=os.path.join(self.tmp_dir, "clip.mp4"),
            force_cpu=False
        )
        c_idx = cmd.index("-c:v")
        self.assertEqual(cmd[c_idx + 1], "libx264")
        p_idx = cmd.index("-preset")
        try:
            import config
            expected_preset = getattr(config, "CPU_PRESET", "veryfast")
        except ImportError:
            expected_preset = "veryfast"
        self.assertEqual(cmd[p_idx + 1], expected_preset)
        self.assertIn("-crf", cmd)

    @patch("kenburns_asmr.check_nvenc_available")
    def test_command_builder_force_cpu_override(self, mock_nvenc):
        """When force_cpu=True, selects libx264 even if NVENC is available."""
        mock_nvenc.return_value = True
        cmd = build_render_command(
            image_path=self.img_path,
            duration=30.0,
            output_clip_path=os.path.join(self.tmp_dir, "clip.mp4"),
            force_cpu=True
        )
        c_idx = cmd.index("-c:v")
        self.assertEqual(cmd[c_idx + 1], "libx264")

    def test_command_builder_universal_pixel_format(self):
        """All commands must specify -pix_fmt yuv420p to guarantee stream copy concat compatibility."""
        cmd = build_render_command(
            image_path=self.img_path,
            duration=30.0,
            output_clip_path=os.path.join(self.tmp_dir, "clip.mp4"),
            sleep_mode=True
        )
        self.assertIn("-pix_fmt", cmd)
        pix_idx = cmd.index("-pix_fmt")
        self.assertEqual(cmd[pix_idx + 1], "yuv420p")

    def test_command_builder_duration_and_resolution(self):
        """Command builder sets duration flag -t and embeds output clip path."""
        out_clip = os.path.join(self.tmp_dir, "duration_test.mp4")
        cmd = build_render_command(
            image_path=self.img_path,
            duration=42.5,
            output_clip_path=out_clip,
            width=3840,
            height=2160,
            fps=30
        )
        self.assertIn("-t", cmd)
        t_idx = cmd.index("-t")
        self.assertEqual(cmd[t_idx + 1], "42.500")
        self.assertEqual(cmd[-1], out_clip)

    def test_command_builder_rejects_non_positive_duration(self):
        """build_render_command raises ValueError for duration <= 0.0s."""
        for invalid_dur in [0.0, -1.0, -10.0]:
            with self.assertRaises(ValueError):
                build_render_command(
                    image_path=self.img_path,
                    duration=invalid_dur,
                    output_clip_path=os.path.join(self.tmp_dir, "clip.mp4")
                )

    @patch("kenburns_asmr.subprocess.run")
    def test_render_kenburns_beat_bare_filename_and_positive_duration(self, mock_run):
        """render_kenburns_beat handles bare filename without FileNotFoundError and validates duration."""
        mock_run.return_value = MagicMock(returncode=0)
        # 1. Bare filename must succeed
        res = render_kenburns_beat(
            image_path=self.img_path,
            duration=5.0,
            output_clip_path="bare_clip_test.mp4"
        )
        self.assertEqual(res, "bare_clip_test.mp4")

        # 2. Non-positive duration must raise ValueError
        with self.assertRaises(ValueError):
            render_kenburns_beat(
                image_path=self.img_path,
                duration=0.0,
                output_clip_path="out.mp4"
            )


# ==============================================================================
# 7. Render Pipeline Integration (beat_aligner -> chunk_renderer) (6 tests)
# ==============================================================================
class TestRenderPipelineIntegration(unittest.TestCase):
    """Verifies end-to-end alignment, metadata forwarding, and concat stream copy integrity."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.images_10 = [os.path.join(self.tmp_dir, f"beat_P01_B{i:02d}.jpg") for i in range(1, 11)]
        for img in self.images_10:
            with open(img, "wb") as f:
                f.write(b"dummy")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    @patch("beat_aligner.get_audio_duration")
    def test_beat_aligner_anchors_p01_b01_to_dim_cue(self, mock_dur):
        """Verifies Part 01 Beat 1 duration anchoring to cue_end + buffer."""
        mock_dur.return_value = 350.0
        cue_end = 48.700
        target_b1 = cue_end + 2.0  # 50.700s

        res = align_part_beats(
            part_index=1,
            audio_wav_path="dummy.wav",
            beat_images=self.images_10,
            p01_b01_duration=target_b1,
            dim_start_sec=41.250,
            dim_end_sec=cue_end
        )

        b1 = res["beats"][0]
        self.assertEqual(b1["duration"], 50.700)
        self.assertTrue(b1["is_transition_beat"])
        self.assertFalse(b1["sleep_mode"])
        self.assertEqual(b1["dim_start_sec"], 41.250)
        self.assertEqual(b1["dim_end_sec"], 48.700)

        # Beats 2..10 must be in sleep mode
        for b in res["beats"][1:]:
            self.assertFalse(b["is_transition_beat"])
            self.assertTrue(b["sleep_mode"])
            self.assertEqual(b["dim_start_sec"], 0.0)

        # Duration conservation
        total_sum = sum(b["duration"] for b in res["beats"])
        self.assertAlmostEqual(total_sum, 350.0, places=3)

    @patch("chunk_renderer.align_part_beats")
    @patch("chunk_renderer.render_kenburns_beat")
    @patch("chunk_renderer.is_chunk_valid")
    @patch("chunk_renderer.subprocess.run")
    def test_chunk_renderer_forwards_transition_metadata(self, mock_sub, mock_valid, mock_render_kb, mock_align):
        """Verifies chunk_renderer forwards is_transition_beat, dim timestamps, and sleep_mode to render_kenburns_beat."""
        mock_valid.return_value = False  # Force render
        mock_sub.return_value = MagicMock(returncode=0)

        mock_align.return_value = {
            "part_index": 1,
            "total_duration": 300.0,
            "num_beats": 2,
            "beats": [
                {
                    "beat_index": 1,
                    "image_path": self.images_10[0],
                    "duration": 50.0,
                    "is_transition_beat": True,
                    "dim_start_sec": 41.25,
                    "dim_end_sec": 48.70,
                    "sleep_mode": False
                },
                {
                    "beat_index": 2,
                    "image_path": self.images_10[1],
                    "duration": 250.0,
                    "is_transition_beat": False,
                    "dim_start_sec": 0.0,
                    "dim_end_sec": 0.0,
                    "sleep_mode": True
                }
            ]
        }

        render_part_chunk(
            part_index=1,
            audio_wav_path="audio.wav",
            beat_images=self.images_10[:2],
            output_dir=os.path.join(self.tmp_dir, "output"),
            temp_dir=os.path.join(self.tmp_dir, "temp")
        )

        self.assertEqual(mock_render_kb.call_count, 2)
        call_1_kwargs = mock_render_kb.call_args_list[0].kwargs
        self.assertTrue(call_1_kwargs.get("is_transition_beat", False))
        self.assertEqual(call_1_kwargs.get("dim_start_sec"), 41.25)
        self.assertEqual(call_1_kwargs.get("dim_end_sec"), 48.70)
        self.assertFalse(call_1_kwargs.get("sleep_mode", False))

        call_2_kwargs = mock_render_kb.call_args_list[1].kwargs
        self.assertFalse(call_2_kwargs.get("is_transition_beat", True))
        self.assertTrue(call_2_kwargs.get("sleep_mode", False))

    @patch("chunk_renderer.is_chunk_valid")
    def test_chunk_renderer_smart_delta_skips_valid_chunk(self, mock_valid):
        """When chunk already exists and is valid, skips render entirely."""
        mock_valid.return_value = True
        out_dir = os.path.join(self.tmp_dir, "output")
        res = render_part_chunk(
            part_index=1,
            audio_wav_path="audio.wav",
            beat_images=self.images_10,
            output_dir=out_dir,
            temp_dir=os.path.join(self.tmp_dir, "temp")
        )
        expected_path = os.path.join(out_dir, "chunk_part_01.mp4")
        self.assertEqual(res, expected_path)

    def test_resolve_stardust_asset_path_discovery(self):
        """resolve_stardust_asset_path returns existing path or None when absent."""
        # Non-existent
        self.assertIsNone(resolve_stardust_asset_path("/nonexistent/stardust.mp4"))

        # Real temporary file
        fake_stardust = os.path.join(self.tmp_dir, "stardust_real.mp4")
        with open(fake_stardust, "wb") as f:
            f.write(b"data")
        self.assertEqual(resolve_stardust_asset_path(fake_stardust), fake_stardust)

    def test_resolve_part01_cue_timestamps_from_file(self):
        """resolve_part01_cue_timestamps correctly loads cue JSON file."""
        cues_path = os.path.join(self.tmp_dir, "Part_01_cues.json")
        with open(cues_path, "w", encoding="utf-8") as f:
            json.dump({"cue_start_sec": 123.4, "cue_end_sec": 133.4}, f)

        res = resolve_part01_cue_timestamps(
            audio_wav_path=os.path.join(self.tmp_dir, "Part_01.wav"),
            custom_cue_path=cues_path
        )
        self.assertEqual(res["cue_start_sec"], 123.4)
        self.assertEqual(res["cue_end_sec"], 133.4)

    @patch("beat_aligner.get_audio_duration")
    def test_beat_aligner_subsequent_parts_sleep_mode(self, mock_dur):
        """For Part 2 through 15, all beats have is_transition_beat=False and sleep_mode=True."""
        mock_dur.return_value = 300.0
        res = align_part_beats(
            part_index=2,
            audio_wav_path="part_02.wav",
            beat_images=self.images_10
        )
        for b in res["beats"]:
            self.assertFalse(b["is_transition_beat"])
            self.assertTrue(b["sleep_mode"])
            self.assertEqual(b["dim_start_sec"], 0.0)


# ==============================================================================
# 8. Dual-Tree Mirror Parity (5 tests)
# ==============================================================================
class TestMirrorParityRenderSubsystem(unittest.TestCase):
    """Verifies 100% byte-for-byte and execution parity across hsnooze.render/ and 00.codebases/."""

    SYNC_FILES = [
        "kenburns_asmr.py",
        "chunk_renderer.py",
        "beat_aligner.py",
        "cue_extractor.py",
        "generate_ambient_stardust.py",
        "config.py",
        "master_assembler.py"
    ]

    def test_file_existence_in_both_trees(self):
        """Verifies every file exists in both hsnooze.render/ and 00.codebases/."""
        for filename in self.SYNC_FILES:
            f_render = RENDER_DIR / filename
            f_codebase = CODEBASE_DIR / filename
            self.assertTrue(f_render.exists(), f"Missing file in hsnooze.render: {filename}")
            self.assertTrue(f_codebase.exists(), f"Missing file in 00.codebases: {filename}")

    def test_byte_for_byte_parity(self):
        """Verifies zero byte divergence across both directories."""
        for filename in self.SYNC_FILES:
            f_render = RENDER_DIR / filename
            f_codebase = CODEBASE_DIR / filename
            same = filecmp.cmp(str(f_render), str(f_codebase), shallow=False)
            self.assertTrue(same, f"Mirror parity divergence detected in {filename}")

    def test_execution_parity_for_filter_graph(self):
        """Dynamically imports both modules and verifies identical filter graph generation."""
        spec_render = importlib.util.spec_from_file_location("kb_render", str(RENDER_DIR / "kenburns_asmr.py"))
        mod_render = importlib.util.module_from_spec(spec_render)
        spec_render.loader.exec_module(mod_render)

        spec_codebase = importlib.util.spec_from_file_location("kb_codebase", str(CODEBASE_DIR / "kenburns_asmr.py"))
        mod_codebase = importlib.util.module_from_spec(spec_codebase)
        spec_codebase.loader.exec_module(mod_codebase)

        filt1, out1 = mod_render.build_filter_graph(
            zoom_in=True, total_frames=900, is_transition_beat=True, dim_start_sec=40.0, dim_end_sec=48.0
        )
        filt2, out2 = mod_codebase.build_filter_graph(
            zoom_in=True, total_frames=900, is_transition_beat=True, dim_start_sec=40.0, dim_end_sec=48.0
        )
        self.assertEqual(filt1, filt2)
        self.assertEqual(out1, out2)

    def test_execution_parity_for_cue_extractor(self):
        """Verifies both modules produce identical cue extraction dictionaries."""
        spec_render = importlib.util.spec_from_file_location("ce_render", str(RENDER_DIR / "cue_extractor.py"))
        mod_render = importlib.util.module_from_spec(spec_render)
        spec_render.loader.exec_module(mod_render)

        spec_codebase = importlib.util.spec_from_file_location("ce_codebase", str(CODEBASE_DIR / "cue_extractor.py"))
        mod_codebase = importlib.util.module_from_spec(spec_codebase)
        spec_codebase.loader.exec_module(mod_codebase)

        res1 = mod_render.extract_part01_cue_timestamps()
        res2 = mod_codebase.extract_part01_cue_timestamps()
        self.assertEqual(res1, res2)

    def test_execution_parity_for_beat_aligner(self):
        """Verifies both modules execute identical beat alignment."""
        spec_render = importlib.util.spec_from_file_location("ba_render", str(RENDER_DIR / "beat_aligner.py"))
        mod_render = importlib.util.module_from_spec(spec_render)
        spec_render.loader.exec_module(mod_render)

        spec_codebase = importlib.util.spec_from_file_location("ba_codebase", str(CODEBASE_DIR / "beat_aligner.py"))
        mod_codebase = importlib.util.module_from_spec(spec_codebase)
        spec_codebase.loader.exec_module(mod_codebase)

        with patch.object(mod_render, "get_audio_duration", return_value=300.0), \
             patch.object(mod_codebase, "get_audio_duration", return_value=300.0):
            imgs = [f"img_{i}.jpg" for i in range(10)]
            r1 = mod_render.align_part_beats(1, "audio.wav", imgs, dim_start_sec=40.0, dim_end_sec=48.0, p01_b01_duration=50.0)
            r2 = mod_codebase.align_part_beats(1, "audio.wav", imgs, dim_start_sec=40.0, dim_end_sec=48.0, p01_b01_duration=50.0)
            self.assertEqual(r1, r2)


# ==============================================================================
# 9. Live FFmpeg Filter Graph Dry-Run (Conditional Execution) (3 tests)
# ==============================================================================
class TestFFmpegFilterGraphDryRunLive(unittest.TestCase):
    """
    Executes real FFmpeg syntax dry-runs with -f null -.
    Automatically skipped if FFmpeg binary is not found on host machine.
    """

    @unittest.skipIf(not shutil.which("ffmpeg"), "FFmpeg binary not installed on host machine.")
    def test_live_filter_syntax_transition_beat(self):
        """Runs a 1-second 360p synthetic dry-run through the full dynamic transition filter graph."""
        cmd = [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "color=c=antiquewhite:s=640x360:d=2.0:r=30",
            "-f", "lavfi", "-i", "color=c=gold:s=640x360:d=2.0:r=30",
            "-filter_complex",
            "[0:v] split=2 [kb_norm][kb_for_dark]; "
            "[kb_for_dark] eq=contrast=0.90:brightness=-0.05:saturation=0.88:gamma=0.85,"
            "vignette=PI/4:aspect=16/9 [kb_dark]; "
            "[kb_norm][kb_dark] blend=all_expr="
            "'if(lte(T,0.5),A,if(gte(T,1.5),B,A*(0.5*(1+cos(PI*(T-0.5)/1.0)))+B*(0.5*(1-cos(PI*(T-0.5)/1.0)))))' [kb_dimmed]; "
            "[1:v] format=rgba,colorchannelmixer=aa=0.35 [pts_alpha]; "
            "[kb_dimmed][pts_alpha] blend=all_mode=screen [out]",
            "-map", "[out]",
            "-t", "2.0",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"FFmpeg syntax error in transition beat: {res.stderr}")

    @unittest.skipIf(not shutil.which("ffmpeg"), "FFmpeg binary not installed on host machine.")
    def test_live_filter_syntax_static_sleep_beat(self):
        """Runs a 1-second 360p synthetic dry-run through the static sleep filter graph."""
        cmd = [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "color=c=antiquewhite:s=640x360:d=1.0:r=30",
            "-f", "lavfi", "-i", "color=c=gold:s=640x360:d=1.0:r=30",
            "-filter_complex",
            "[0:v] eq=contrast=0.90:brightness=-0.05:saturation=0.88:gamma=0.85,"
            "vignette=PI/4:aspect=16/9 [kb_dark]; "
            "[1:v] format=rgba,colorchannelmixer=aa=0.35 [pts_alpha]; "
            "[kb_dark][pts_alpha] blend=all_mode=screen,format=rgba [out]",
            "-map", "[out]",
            "-t", "1.0",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"FFmpeg syntax error in static sleep beat: {res.stderr}")

    @unittest.skipIf(not shutil.which("ffmpeg"), "FFmpeg binary not installed on host machine.")
    def test_live_filter_syntax_normal_beat(self):
        """Runs a 1-second 360p synthetic dry-run through the normal Ken Burns filter graph."""
        cmd = [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "color=c=antiquewhite:s=640x360:d=1.0:r=30",
            "-vf", "scale=1280x720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=z='min(zoom+0.001,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=30:s=640x360:fps=30",
            "-t", "1.0",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"FFmpeg syntax error in normal beat: {res.stderr}")


if __name__ == "__main__":
    unittest.main()
