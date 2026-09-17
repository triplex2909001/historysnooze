"""
Adversarial Stress Test Suite for HistorySnooze Beat Aligner (beat_aligner.py).
Target: hsnooze.render/beat_aligner.py & 00.codebases/beat_aligner.py
Agent: challenger_m2_1 (Empirical Challenger)

Coverage Dimensions:
1. Part 01 Beat 1 duration anchoring edge conditions:
   - p01_b01_duration > total_duration (raises ValueError)
   - p01_b01_duration == total_duration (raises ValueError)
   - dim_end_sec >= total_duration (raises ValueError)
   - Negative p01_b01_duration & negative dim_end_sec (graceful fallback)
   - Single beat anchoring behavior (num_beats == 1)
   - Anchoring ignored on parts other than Part 1 (P02-P15)
   - Anchoring close to total_duration (extreme remainder boundary)
   - Precedence of p01_b01_duration over dim_end_sec
2. Floating-point precision and duration conservation:
   - Sum of durations == total_duration within 1e-6 precision across irrational fractions (1/3, 1/7, 1/11, 1/13)
   - High-density beat counts (10, 100) floating-point accumulation drift check
   - Timeline contiguity (start_time of beat i+1 == end_time of beat i)
   - 500 pseudo-random float duration conservation stress test
3. Extreme durations:
   - total_duration = 0.0s (0 frame boundary)
   - total_duration = 36000.0s (10 hours sleep loop boundary)
   - Microsecond audio durations (0.001s, 0.01s)
4. Extreme beat counts:
   - 1 beat (P01 transition vs non-P01 sleep mode)
   - 2 beats (boundary split with/without anchoring)
   - 10 beats (canonical target count)
   - 100 beats (extreme density stress)
   - 0 beats (raises ValueError)
5. Schema adherence per PROJECT.md interface contracts:
   - Top-level dictionary schema
   - Beat-level dictionary schema (part_index, beat_index, beat_id, image_path, start_time, end_time, duration, is_transition_beat, dim_start_sec, dim_end_sec, sleep_mode)
   - is_transition_beat == True ONLY for P01_B01
   - sleep_mode == not is_transition_beat across all 15 parts
   - Dim timestamps populated only on P01_B01, 0.0 elsewhere
6. Warning generation and threshold boundary conditions:
   - In-bounds duration (25.0s to 45.0s) emits zero warnings
   - Exact boundaries at 25.0s and 45.0s emit zero warnings
   - Under lower bound (24.999s) emits warning
   - Over upper bound (45.001s) emits warning
   - Isolated warning on anchored Beat 1 out of bounds while others in bounds
   - Warning count and message format validation
7. Filesystem & Corner Cases:
   - Output to valid path with parent directories created
   - Bare filename output handling (os.makedirs("", exist_ok=True) defect detection)
   - Inverted dimming window (dim_start_sec > dim_end_sec)
8. Mirror parity:
   - hsnooze.render/beat_aligner.py vs 00.codebases/beat_aligner.py byte parity and execution parity
"""

import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hsnooze.render"))

from beat_aligner import align_part_beats
import config


# ==============================================================================
# 1. Part 01 Beat 1 Anchoring Adversarial Tests
# ==============================================================================
class TestPart01Beat1AnchoringAdversarial(unittest.TestCase):
    """Adversarial stress tests for Part 01 Beat 1 duration anchoring."""

    def setUp(self):
        self.images_10 = [f"/tmp/keyframes/beat_P01_B{i:02d}.jpg" for i in range(1, 11)]

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_p01_b01_duration_greater_than_total_raises_value_error(self, mock_dur):
        """p01_b01_duration > total_duration must raise ValueError."""
        mock_dur.return_value = 300.0
        with self.assertRaises(ValueError) as ctx:
            align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=350.0
            )
        self.assertIn("must be less than total duration", str(ctx.exception))

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_p01_b01_duration_equal_to_total_raises_value_error(self, mock_dur):
        """p01_b01_duration == total_duration must raise ValueError (leaving 0 for remaining beats)."""
        mock_dur.return_value = 300.0
        with self.assertRaises(ValueError) as ctx:
            align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=300.0
            )
        self.assertIn("must be less than total duration", str(ctx.exception))

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_dim_end_sec_greater_than_total_raises_value_error(self, mock_dur):
        """dim_end_sec > total_duration must raise ValueError when used as anchoring target."""
        mock_dur.return_value = 300.0
        with self.assertRaises(ValueError) as ctx:
            align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                dim_end_sec=320.0
            )
        self.assertIn("must be less than total duration", str(ctx.exception))

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_dim_end_sec_equal_to_total_raises_value_error(self, mock_dur):
        """dim_end_sec == total_duration must raise ValueError when used as anchoring target."""
        mock_dur.return_value = 300.0
        with self.assertRaises(ValueError) as ctx:
            align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                dim_end_sec=300.0
            )
        self.assertIn("must be less than total duration", str(ctx.exception))

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_negative_p01_b01_duration_falls_back_to_equal_split(self, mock_dur):
        """Negative p01_b01_duration is ignored and falls back gracefully to equal distribution."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=-15.0
            )
        # Should not anchor to negative number; each beat should be 35.0s
        for b in res["beats"]:
            self.assertEqual(b["duration"], 35.0)

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_zero_p01_b01_duration_falls_back_to_equal_split(self, mock_dur):
        """Zero p01_b01_duration is not treated as anchor and falls back to equal distribution."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=0.0
            )
        for b in res["beats"]:
            self.assertEqual(b["duration"], 35.0)

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_negative_dim_end_sec_falls_back_to_equal_split(self, mock_dur):
        """Negative dim_end_sec is ignored for anchoring and falls back to equal distribution."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                dim_end_sec=-20.0
            )
        for b in res["beats"]:
            self.assertEqual(b["duration"], 35.0)

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_ignored_on_parts_other_than_part_1(self, mock_dur):
        """p01_b01_duration and dim_end_sec must be ignored for anchoring when part_index != 1."""
        mock_dur.return_value = 350.0
        for p in range(2, 16):
            images = [f"/tmp/keyframes/beat_P{p:02d}_B{i:02d}.jpg" for i in range(1, 11)]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = align_part_beats(
                    part_index=p,
                    audio_wav_path="test.wav",
                    beat_images=images,
                    p01_b01_duration=60.0,
                    dim_end_sec=60.0
                )
            # Beat 1 should NOT be 60.0s, it should be 35.0s
            self.assertEqual(res["beats"][0]["duration"], 35.0)
            self.assertFalse(res["beats"][0]["is_transition_beat"])
            self.assertTrue(res["beats"][0]["sleep_mode"])

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_with_single_beat_ignores_anchor_and_takes_total(self, mock_dur):
        """When num_beats == 1, anchoring is bypassed and the single beat consumes total duration."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=["/tmp/img1.jpg"],
                p01_b01_duration=40.0
            )
        self.assertEqual(res["num_beats"], 1)
        self.assertEqual(res["beats"][0]["duration"], 350.0)

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_p01_b01_precedence_over_dim_end_sec(self, mock_dur):
        """p01_b01_duration takes explicit precedence over dim_end_sec when both provided."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=32.0,
                dim_end_sec=42.0
            )
        self.assertEqual(res["beats"][0]["duration"], 32.0)

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_dim_end_sec_used_when_p01_b01_duration_is_none(self, mock_dur):
        """dim_end_sec is used for anchoring when p01_b01_duration is None."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=None,
                dim_end_sec=28.5
            )
        self.assertEqual(res["beats"][0]["duration"], 28.5)

    @patch("beat_aligner.get_audio_duration")
    def test_anchoring_near_total_duration_conserves_total(self, mock_dur):
        """When p01_b01_duration is very close to total_duration, sum still equals total."""
        mock_dur.return_value = 300.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=299.9
            )
        sum_durs = sum(b["duration"] for b in res["beats"])
        self.assertAlmostEqual(sum_durs, 300.0, places=3)
        self.assertEqual(res["beats"][0]["duration"], 299.9)


# ==============================================================================
# 2. Floating-Point Precision & Conservation Tests
# ==============================================================================
class TestFloatingPointPrecisionAndConservation(unittest.TestCase):
    """Tests guaranteeing floating-point precision closure (sum of durations == total_duration to 1e-6)."""

    @patch("beat_aligner.get_audio_duration")
    def test_fractional_durations_conservation_various_beat_counts(self, mock_dur):
        """Conservation holds to 1e-6 precision across prime/fractional durations and beat counts."""
        test_durations = [
            100.0 / 3.0,     # 33.333333333333336
            357.825,         # exact 3-decimal milliseconds
            300.123456789,   # arbitrary 9-decimal precision
            411.7,           # 1-decimal float
            250.0001,        # 4-decimal
            360.333333,      # 6-decimal
            100.0 / 7.0,     # 14.285714285714286
            1000.0 / 11.0,   # 90.9090909090909
        ]
        beat_counts = [1, 2, 3, 7, 10, 11, 13, 20, 100]

        for dur in test_durations:
            mock_dur.return_value = dur
            for n_beats in beat_counts:
                images = [f"/tmp/img_{i:03d}.jpg" for i in range(n_beats)]
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)

                sum_dur = sum(b["duration"] for b in res["beats"])
                res_total = res["total_duration"]
                diff = abs(sum_dur - res_total)
                self.assertLess(
                    diff, 1e-6,
                    f"Conservation failed: td={dur}, beats={n_beats}, sum={sum_dur}, total={res_total}, diff={diff}"
                )

    @patch("beat_aligner.get_audio_duration")
    def test_timeline_contiguity_and_monotonicity(self, mock_dur):
        """Start and end times across all beats must be strictly monotonic and contiguous."""
        test_cases = [
            (357.825, 10),
            (300.333, 10),
            (250.0, 7),
            (400.123456, 15),
            (36000.0, 100),
        ]
        for total_dur, n_beats in test_cases:
            mock_dur.return_value = total_dur
            images = [f"/tmp/img_{i:03d}.jpg" for i in range(n_beats)]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)

            beats = res["beats"]
            self.assertEqual(beats[0]["start_time"], 0.0)
            for i in range(len(beats) - 1):
                curr_end = beats[i]["end_time"]
                next_start = beats[i + 1]["start_time"]
                self.assertAlmostEqual(
                    curr_end, next_start, places=3,
                    msg=f"Discontinuity between beat {i} and {i+1}: {curr_end} != {next_start}"
                )
                self.assertLessEqual(beats[i]["start_time"], beats[i]["end_time"])

            final_end = beats[-1]["end_time"]
            self.assertAlmostEqual(
                final_end, res["total_duration"], places=3,
                msg=f"Final beat end_time ({final_end}) != total_duration ({res['total_duration']})"
            )

    @patch("beat_aligner.get_audio_duration")
    def test_anchored_beat_conservation_various_ratios(self, mock_dur):
        """Anchored beats conserve total duration to 1e-6 precision across various ratios."""
        test_cases = [
            (350.0, 10, 30.0),
            (350.0, 10, 15.555),
            (357.825, 10, 44.444),
            (450.0, 10, 25.0),
            (300.0, 2, 100.0),
            (500.0, 100, 12.345),
        ]
        for total_dur, n_beats, b1_anchor in test_cases:
            mock_dur.return_value = total_dur
            images = [f"/tmp/img_{i:03d}.jpg" for i in range(n_beats)]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = align_part_beats(
                    part_index=1,
                    audio_wav_path="test.wav",
                    beat_images=images,
                    p01_b01_duration=b1_anchor
                )
            sum_dur = sum(b["duration"] for b in res["beats"])
            diff = abs(sum_dur - res["total_duration"])
            self.assertLess(
                diff, 1e-6,
                f"Anchored conservation failed: td={total_dur}, n={n_beats}, b1={b1_anchor}, diff={diff}"
            )

    @patch("beat_aligner.get_audio_duration")
    def test_stress_500_random_float_durations_conservation(self, mock_dur):
        """500 pseudo-random durations between 200.0 and 600.0 must all conserve duration to 1e-6."""
        rng = random.Random(42)
        for i in range(500):
            rand_dur = rng.uniform(200.0, 600.0)
            mock_dur.return_value = rand_dur
            images = [f"/tmp/img_{j:02d}.jpg" for j in range(10)]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)

            sum_dur = sum(b["duration"] for b in res["beats"])
            diff = abs(sum_dur - res["total_duration"])
            self.assertLess(diff, 1e-6, f"Iteration {i} failed: dur={rand_dur}, diff={diff}")


# ==============================================================================
# 3. Extreme Durations Tests
# ==============================================================================
class TestExtremeDurations(unittest.TestCase):
    """Stress tests on extreme duration values (0.0s, 36000.0s, micro-durations)."""

    @patch("beat_aligner.get_audio_duration")
    def test_extreme_zero_total_duration(self, mock_dur):
        """total_duration = 0.0s returns valid schema with 0.0 durations and emits warnings."""
        mock_dur.return_value = 0.0
        for n in [1, 2, 10]:
            images = [f"/tmp/img_{i}.jpg" for i in range(n)]
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)
                self.assertEqual(len(w), n, f"Expected {n} warnings for 0.0s total duration")
                self.assertEqual(res["total_duration"], 0.0)
                for b in res["beats"]:
                    self.assertEqual(b["duration"], 0.0)
                    self.assertEqual(b["start_time"], 0.0)
                    self.assertEqual(b["end_time"], 0.0)

    @patch("beat_aligner.get_audio_duration")
    def test_extreme_ten_hours_total_duration(self, mock_dur):
        """total_duration = 36000.0s (10 hours) calculates correctly, conserves duration, and warns."""
        mock_dur.return_value = 36000.0
        images = [f"/tmp/img_{i:02d}.jpg" for i in range(10)]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)
            self.assertEqual(len(w), 10)
            self.assertEqual(res["total_duration"], 36000.0)
            for b in res["beats"]:
                self.assertEqual(b["duration"], 3600.0)
            sum_dur = sum(b["duration"] for b in res["beats"])
            self.assertAlmostEqual(sum_dur, 36000.0, places=3)

    @patch("beat_aligner.get_audio_duration")
    def test_extreme_microsecond_duration(self, mock_dur):
        """total_duration = 0.001s (1ms) handles gracefully without floating point crashes."""
        mock_dur.return_value = 0.001
        images = [f"/tmp/img_{i}.jpg" for i in range(2)]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)
            self.assertEqual(len(w), 2)
            self.assertEqual(res["total_duration"], 0.001)
            sum_dur = sum(b["duration"] for b in res["beats"])
            self.assertAlmostEqual(sum_dur, 0.001, places=3)


# ==============================================================================
# 4. Extreme Beat Counts Tests
# ==============================================================================
class TestExtremeBeatCounts(unittest.TestCase):
    """Stress tests on beat counts: 0, 1, 2, 10, 100."""

    @patch("beat_aligner.get_audio_duration")
    def test_zero_beats_raises_value_error(self, mock_dur):
        """0 beat images must raise ValueError."""
        mock_dur.return_value = 350.0
        with self.assertRaises(ValueError) as ctx:
            align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=[])
        self.assertIn("No beat images provided", str(ctx.exception))

    @patch("beat_aligner.get_audio_duration")
    def test_one_beat_part_1(self, mock_dur):
        """1 beat in Part 1 is the transition beat and takes 100% duration."""
        mock_dur.return_value = 30.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=["img1.jpg"])
        self.assertEqual(res["num_beats"], 1)
        b = res["beats"][0]
        self.assertEqual(b["duration"], 30.0)
        self.assertTrue(b["is_transition_beat"])
        self.assertFalse(b["sleep_mode"])

    @patch("beat_aligner.get_audio_duration")
    def test_one_beat_part_2(self, mock_dur):
        """1 beat in Part 2 is in sleep mode and takes 100% duration."""
        mock_dur.return_value = 30.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(part_index=2, audio_wav_path="test.wav", beat_images=["img1.jpg"])
        self.assertEqual(res["num_beats"], 1)
        b = res["beats"][0]
        self.assertEqual(b["duration"], 30.0)
        self.assertFalse(b["is_transition_beat"])
        self.assertTrue(b["sleep_mode"])

    @patch("beat_aligner.get_audio_duration")
    def test_two_beats_part_1_unanchored(self, mock_dur):
        """2 beats unanchored in Part 1 splits duration 50/50."""
        mock_dur.return_value = 60.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=["a.jpg", "b.jpg"])
        self.assertEqual(res["num_beats"], 2)
        self.assertEqual(res["beats"][0]["duration"], 30.0)
        self.assertEqual(res["beats"][1]["duration"], 30.0)
        self.assertTrue(res["beats"][0]["is_transition_beat"])
        self.assertFalse(res["beats"][0]["sleep_mode"])
        self.assertFalse(res["beats"][1]["is_transition_beat"])
        self.assertTrue(res["beats"][1]["sleep_mode"])

    @patch("beat_aligner.get_audio_duration")
    def test_two_beats_part_1_anchored(self, mock_dur):
        """2 beats anchored in Part 1 sets B1 to anchor and B2 to remainder."""
        mock_dur.return_value = 60.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=["a.jpg", "b.jpg"],
                p01_b01_duration=25.0
            )
        self.assertEqual(res["beats"][0]["duration"], 25.0)
        self.assertEqual(res["beats"][1]["duration"], 35.0)

    @patch("beat_aligner.get_audio_duration")
    def test_one_hundred_beats_stress(self, mock_dur):
        """100 beats stress test: validates conservation and contiguity over 100 steps."""
        mock_dur.return_value = 3500.0
        images = [f"/tmp/img_{i:03d}.jpg" for i in range(100)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)
        self.assertEqual(res["num_beats"], 100)
        sum_dur = sum(b["duration"] for b in res["beats"])
        self.assertAlmostEqual(sum_dur, 3500.0, places=3)
        self.assertAlmostEqual(res["beats"][-1]["end_time"], 3500.0, places=3)


# ==============================================================================
# 5. Schema Adherence Tests
# ==============================================================================
class TestSchemaAdherence(unittest.TestCase):
    """Rigorous verification of schema conformance against PROJECT.md §Interface Contracts."""

    @patch("beat_aligner.get_audio_duration")
    def test_top_level_dictionary_schema(self, mock_dur):
        """Top-level dictionary must contain all required contract keys and valid types."""
        mock_dur.return_value = 350.0
        images = [f"/tmp/img_{i:02d}.jpg" for i in range(10)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)

        required_keys = {"part_index", "audio_path", "total_duration", "num_beats", "beats"}
        self.assertTrue(required_keys.issubset(res.keys()), f"Missing keys in top-level: {required_keys - set(res.keys())}")
        self.assertIsInstance(res["part_index"], int)
        self.assertIsInstance(res["audio_path"], str)
        self.assertIsInstance(res["total_duration"], float)
        self.assertIsInstance(res["num_beats"], int)
        self.assertIsInstance(res["beats"], list)

    @patch("beat_aligner.get_audio_duration")
    def test_beat_level_dictionary_schema(self, mock_dur):
        """Every beat dictionary must strictly contain all contract fields with appropriate types."""
        mock_dur.return_value = 350.0
        images = [f"/tmp/img_{i:02d}.jpg" for i in range(10)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=images)

        required_beat_keys = {
            "part_index", "beat_index", "beat_id", "image_path",
            "start_time", "end_time", "duration",
            "is_transition_beat", "dim_start_sec", "dim_end_sec", "sleep_mode"
        }
        for b in res["beats"]:
            self.assertTrue(required_beat_keys.issubset(b.keys()), f"Missing beat keys: {required_beat_keys - set(b.keys())}")
            self.assertIsInstance(b["part_index"], int)
            self.assertIsInstance(b["beat_index"], int)
            self.assertIsInstance(b["beat_id"], str)
            self.assertIsInstance(b["image_path"], str)
            self.assertIsInstance(b["start_time"], float)
            self.assertIsInstance(b["end_time"], float)
            self.assertIsInstance(b["duration"], float)
            self.assertIsInstance(b["is_transition_beat"], bool)
            self.assertIsInstance(b["dim_start_sec"], float)
            self.assertIsInstance(b["dim_end_sec"], float)
            self.assertIsInstance(b["sleep_mode"], bool)

    @patch("beat_aligner.get_audio_duration")
    def test_transition_and_sleep_mode_flags_across_all_15_parts(self, mock_dur):
        """is_transition_beat is True ONLY for P01_B01; sleep_mode is True everywhere else."""
        mock_dur.return_value = 350.0
        for p in range(1, 16):
            images = [f"/tmp/keyframes/beat_P{p:02d}_B{i:02d}.jpg" for i in range(1, 11)]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = align_part_beats(
                    part_index=p,
                    audio_wav_path="test.wav",
                    beat_images=images,
                    dim_start_sec=12.0,
                    dim_end_sec=25.0
                )
            for b in res["beats"]:
                idx = b["beat_index"]
                if p == 1 and idx == 1:
                    self.assertTrue(b["is_transition_beat"], "P01_B01 must have is_transition_beat = True")
                    self.assertFalse(b["sleep_mode"], "P01_B01 must have sleep_mode = False")
                    self.assertEqual(b["dim_start_sec"], 12.0)
                    self.assertEqual(b["dim_end_sec"], 25.0)
                else:
                    self.assertFalse(b["is_transition_beat"], f"P{p:02d}_B{idx:02d} must have is_transition_beat = False")
                    self.assertTrue(b["sleep_mode"], f"P{p:02d}_B{idx:02d} must have sleep_mode = True")
                    self.assertEqual(b["dim_start_sec"], 0.0)
                    self.assertEqual(b["dim_end_sec"], 0.0)


# ==============================================================================
# 6. Warning Generation Tests
# ==============================================================================
class TestWarningGeneration(unittest.TestCase):
    """Tests for warning emission when beat duration falls outside [25.0s, 45.0s]."""

    def setUp(self):
        self.images_10 = [f"/tmp/img_{i:02d}.jpg" for i in range(1, 11)]

    @patch("beat_aligner.get_audio_duration")
    def test_zero_warnings_nominal_range_35s(self, mock_dur):
        """Standard 35.0s beats generate zero warnings."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=self.images_10)
            self.assertEqual(len(w), 0)

    @patch("beat_aligner.get_audio_duration")
    def test_zero_warnings_exact_lower_bound_25s(self, mock_dur):
        """Beats exactly at 25.0s generate zero warnings."""
        mock_dur.return_value = 250.0
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=self.images_10)
            self.assertEqual(len(w), 0)

    @patch("beat_aligner.get_audio_duration")
    def test_zero_warnings_exact_upper_bound_45s(self, mock_dur):
        """Beats exactly at 45.0s generate zero warnings."""
        mock_dur.return_value = 450.0
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=self.images_10)
            self.assertEqual(len(w), 0)

    @patch("beat_aligner.get_audio_duration")
    def test_warning_below_lower_bound(self, mock_dur):
        """Beats at 24.99s generate UserWarning for each out-of-bound beat."""
        mock_dur.return_value = 249.9
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=self.images_10)
            self.assertGreater(len(w), 0)
            self.assertTrue(issubclass(w[0].category, UserWarning))
            self.assertIn("is outside target range [25.0s, 45.0s]", str(w[0].message))

    @patch("beat_aligner.get_audio_duration")
    def test_warning_above_upper_bound(self, mock_dur):
        """Beats at 45.01s generate UserWarning for each out-of-bound beat."""
        mock_dur.return_value = 450.1
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            align_part_beats(part_index=1, audio_wav_path="test.wav", beat_images=self.images_10)
            self.assertGreater(len(w), 0)
            self.assertTrue(issubclass(w[0].category, UserWarning))
            self.assertIn("is outside target range [25.0s, 45.0s]", str(w[0].message))

    @patch("beat_aligner.get_audio_duration")
    def test_isolated_warning_on_anchored_beat_1_below_bound(self, mock_dur):
        """When anchored B1 is 20.0s and beats 2..10 are ~36.6s, exactly 1 warning is generated."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=20.0
            )
            self.assertEqual(len(w), 1)
            self.assertIn("Beat P01_B01 duration 20.00s is outside target range", str(w[0].message))

    @patch("beat_aligner.get_audio_duration")
    def test_isolated_warning_on_anchored_beat_1_above_bound(self, mock_dur):
        """When anchored B1 is 50.0s and beats 2..10 are ~33.3s, exactly 1 warning is generated."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images_10,
                p01_b01_duration=50.0
            )
            self.assertEqual(len(w), 1)
            self.assertIn("Beat P01_B01 duration 50.00s is outside target range", str(w[0].message))


# ==============================================================================
# 7. Filesystem & Corner Cases Tests
# ==============================================================================
class TestFilesystemAndCornerCases(unittest.TestCase):
    """Corner cases covering JSON output paths, inverted dimming parameters, etc."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.images = [f"/tmp/img_{i}.jpg" for i in range(5)]

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("beat_aligner.get_audio_duration")
    def test_output_json_with_nested_subdirectory_writes_valid_json(self, mock_dur):
        """output_json_path with nested directory correctly creates parent folders and writes JSON."""
        mock_dur.return_value = 175.0
        out_path = Path(self.test_dir) / "sub1" / "sub2" / "beats.json"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images,
                output_json_path=str(out_path)
            )
        self.assertTrue(out_path.exists())
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["num_beats"], 5)
        self.assertEqual(loaded["total_duration"], 175.0)

    @patch("beat_aligner.get_audio_duration")
    def test_output_json_bare_filename_reveals_dirname_bug(self, mock_dur):
        """
        Documenting Bug: If output_json_path is a bare filename (e.g., 'beats.json'),
        os.path.dirname('beats.json') returns '', causing os.makedirs('', exist_ok=True)
        to raise FileNotFoundError: [Errno 2] No such file or directory: ''.
        """
        mock_dur.return_value = 175.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # We catch FileNotFoundError to document this edge case behavior
            try:
                align_part_beats(
                    part_index=1,
                    audio_wav_path="test.wav",
                    beat_images=self.images,
                    output_json_path="bare_filename_beats.json"
                )
                bare_succeeded = True
            except FileNotFoundError:
                bare_succeeded = False
            finally:
                if Path("bare_filename_beats.json").exists():
                    Path("bare_filename_beats.json").unlink()

            # The remediated implementation safely succeeds on bare filenames
            self.assertTrue(
                bare_succeeded,
                "Remediated beat_aligner.py line 154 safely handles bare filenames without FileNotFoundError"
            )

    @patch("beat_aligner.get_audio_duration")
    def test_inverted_dimming_window_handled(self, mock_dur):
        """dim_start_sec > dim_end_sec is stored verbatim without crashing."""
        mock_dur.return_value = 350.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = align_part_beats(
                part_index=1,
                audio_wav_path="test.wav",
                beat_images=self.images,
                dim_start_sec=40.0,
                dim_end_sec=20.0
            )
        # dim_end_sec (20.0) is used as anchor
        self.assertEqual(res["beats"][0]["duration"], 20.0)
        self.assertEqual(res["beats"][0]["dim_start_sec"], 40.0)
        self.assertEqual(res["beats"][0]["dim_end_sec"], 20.0)


# ==============================================================================
# 8. Mirror Parity Tests
# ==============================================================================
class TestMirrorParity(unittest.TestCase):
    """Verifies byte parity and runtime output parity between hsnooze.render and 00.codebases."""

    def test_byte_parity_render_vs_codebases(self):
        """hsnooze.render/beat_aligner.py must match 00.codebases/beat_aligner.py byte-for-byte."""
        render_file = REPO_ROOT / "hsnooze.render" / "beat_aligner.py"
        codebases_file = REPO_ROOT / "00.codebases" / "beat_aligner.py"
        self.assertTrue(render_file.exists())
        self.assertTrue(codebases_file.exists())
        self.assertEqual(
            render_file.read_text(encoding="utf-8"),
            codebases_file.read_text(encoding="utf-8"),
            "beat_aligner.py differs between hsnooze.render and 00.codebases!"
        )

    def test_execution_parity_both_modules(self):
        """Both modules executed on identical inputs produce identical dictionary outputs."""
        def load_mod(name, p):
            spec = importlib.util.spec_from_file_location(name, str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        m_render = load_mod("ba_render", REPO_ROOT / "hsnooze.render" / "beat_aligner.py")
        m_codebase = load_mod("ba_codebase", REPO_ROOT / "00.codebases" / "beat_aligner.py")

        images = [f"/tmp/img_{i:02d}.jpg" for i in range(10)]
        with patch.object(m_render, "get_audio_duration", return_value=357.825), \
             patch.object(m_codebase, "get_audio_duration", return_value=357.825):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res1 = m_render.align_part_beats(1, "test.wav", images, p01_b01_duration=32.5)
                res2 = m_codebase.align_part_beats(1, "test.wav", images, p01_b01_duration=32.5)
                self.assertEqual(res1, res2)


if __name__ == "__main__":
    unittest.main()
