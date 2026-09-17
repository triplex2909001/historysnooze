"""
HistorySnooze Milestone 3 Adversarial Challenge & Stress-Test Suite
Author / Runner: challenger_m3_2
Targets:
  - hsnooze.render/cue_extractor.py & 00.codebases/cue_extractor.py
  - hsnooze.render/beat_aligner.py & 00.codebases/beat_aligner.py

Objective Invariants Challenged:
1. cue_extractor.py:
   - Corrupted WAV headers, 0-byte WAV files, stereo PCM mismatch in extract_part01_cue_timestamps.
   - Empty chunks directory, missing chunk 17, missing directories.
   - Malformed JSON manifests in validate_cue_manifest (missing keys, non-numeric timestamps, negative duration, start >= end).
   - Graceful fallback tier activation (Tier 1 -> Tier 2 -> Tier 3).
2. beat_aligner.py:
   - Extreme audio durations (0.1s, 36000s).
   - Part 01 Beat 1 anchoring with missing vs present Part_01_cues.json.
   - Duration conservation: sum of beats == total duration within 1e-5s across all configurations.
   - Timestamp continuity: start_time[i] == end_time[i-1], end_time - start_time == duration.
   - Exact tagging: P01 Beat 1 (is_transition=True, sleep_mode=False), P01 Beats 2..N (is_transition=False, sleep_mode=True),
     P02..P15 all beats (is_transition=False, sleep_mode=True, dim cues == 0.0).
3. Dual-Tree Parity:
   - Identical execution across hsnooze.render/ and 00.codebases/.
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDER_DIR = REPO_ROOT / "hsnooze.render"
CODEBASE_DIR = REPO_ROOT / "00.codebases"

if str(RENDER_DIR) not in sys.path:
    sys.path.insert(0, str(RENDER_DIR))

import beat_aligner
import cue_extractor
from beat_aligner import align_part_beats, get_audio_duration
from cue_extractor import extract_part01_cue_timestamps, validate_cue_manifest


def make_test_wav(
    path: str,
    duration: float = 1.0,
    framerate: int = 44100,
    channels: int = 1,
    sampwidth: int = 2,
    silent: bool = True
) -> None:
    """Helper to generate a synthetically valid WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        n_frames = int(duration * framerate)
        raw = (b"\x00\x00" if silent else b"\x20\x00") * (n_frames * channels)
        wf.writeframes(raw)


def make_stitched_test_wav(
    path: str,
    n_chunks: int = 18,
    chunk_dur: float = 1.0,
    silence_dur: float = 1.0,
    framerate: int = 44100
) -> None:
    """Helper to generate a stitched WAV with alternating audio and silence gaps >= 0.8s."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        chunk_raw = b"\x20\x00" * int(chunk_dur * framerate)
        silence_raw = b"\x00\x00" * int(silence_dur * framerate)
        for _ in range(n_chunks):
            wf.writeframes(chunk_raw)
            wf.writeframes(silence_raw)


# ==============================================================================
# 1. Cue Extractor Adversarial Challenges (10 tests)
# ==============================================================================
class TestAdversarialCueExtractorCorruptionAndEdgeCases(unittest.TestCase):
    """Stress-tests cue_extractor against filesystem corruptions, 0-byte files, and missing data."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_empty_chunks_directory_activates_fallback(self):
        """Empty chunks directory must not crash and must activate fallback tier."""
        empty_dir = os.path.join(self.tmp_dir, "empty_chunks")
        os.makedirs(empty_dir, exist_ok=True)
        res = extract_part01_cue_timestamps(chunks_dir=empty_dir)
        self.assertEqual(res["extraction_method"], "deterministic_fallback")
        self.assertEqual(res["part_index"], 1)
        self.assertTrue(validate_cue_manifest(res))

    def test_missing_chunk_17_activates_fallback(self):
        """Directory with fewer than 17 chunks (e.g. 16) must activate fallback tier."""
        dir16 = os.path.join(self.tmp_dir, "chunks_16")
        os.makedirs(dir16, exist_ok=True)
        for i in range(1, 17):
            make_test_wav(os.path.join(dir16, f"part_01_chunk_{i:03d}.wav"), duration=1.0)
        res = extract_part01_cue_timestamps(chunks_dir=dir16)
        self.assertEqual(res["extraction_method"], "deterministic_fallback")
        self.assertTrue(validate_cue_manifest(res))

    def test_0byte_first_chunk_activates_fallback(self):
        """A 0-byte file at chunk 1 must be gracefully caught and trigger fallback tier."""
        dir_zero = os.path.join(self.tmp_dir, "chunks_zero1")
        os.makedirs(dir_zero, exist_ok=True)
        for i in range(1, 18):
            p = os.path.join(dir_zero, f"part_01_chunk_{i:03d}.wav")
            if i == 1:
                open(p, "wb").close()  # 0-byte file
            else:
                make_test_wav(p, duration=1.0)
        res = extract_part01_cue_timestamps(chunks_dir=dir_zero)
        self.assertEqual(res["extraction_method"], "deterministic_fallback")
        self.assertTrue(validate_cue_manifest(res))

    def test_0byte_target_chunk_17_activates_fallback(self):
        """A 0-byte file specifically at target chunk 17 must trigger fallback tier."""
        dir_zero17 = os.path.join(self.tmp_dir, "chunks_zero17")
        os.makedirs(dir_zero17, exist_ok=True)
        for i in range(1, 18):
            p = os.path.join(dir_zero17, f"part_01_chunk_{i:03d}.wav")
            if i == 17:
                open(p, "wb").close()
            else:
                make_test_wav(p, duration=1.0)
        res = extract_part01_cue_timestamps(chunks_dir=dir_zero17)
        self.assertEqual(res["extraction_method"], "deterministic_fallback")
        self.assertTrue(validate_cue_manifest(res))

    def test_corrupted_wav_header_in_chunk_activates_fallback(self):
        """Garbage data in chunk WAV header must not raise unhandled exception."""
        dir_corrupt = os.path.join(self.tmp_dir, "chunks_corrupt")
        os.makedirs(dir_corrupt, exist_ok=True)
        for i in range(1, 18):
            p = os.path.join(dir_corrupt, f"part_01_chunk_{i:03d}.wav")
            if i == 5:
                with open(p, "wb") as f:
                    f.write(b"NOT_A_VALID_RIFF_WAV_HEADER_DATA_00000000000")
            else:
                make_test_wav(p, duration=1.0)
        res = extract_part01_cue_timestamps(chunks_dir=dir_corrupt)
        self.assertEqual(res["extraction_method"], "deterministic_fallback")
        self.assertTrue(validate_cue_manifest(res))

    def test_0byte_stitched_wav_activates_fallback(self):
        """0-byte stitched Part_01.wav passed to Tier 2 must not crash and must activate Tier 3."""
        zero_wav = os.path.join(self.tmp_dir, "zero_part01.wav")
        open(zero_wav, "wb").close()
        res = extract_part01_cue_timestamps(part_01_wav_path=zero_wav)
        self.assertEqual(res["extraction_method"], "deterministic_fallback")
        self.assertTrue(validate_cue_manifest(res))

    def test_corrupted_stitched_wav_activates_fallback(self):
        """Corrupted stitched Part_01.wav passed to Tier 2 must activate Tier 3."""
        corrupt_wav = os.path.join(self.tmp_dir, "corrupt_part01.wav")
        with open(corrupt_wav, "wb") as f:
            f.write(b"GARBAGE_WAV_DATA_FOR_PART_01_TESTING_1234567890")
        res = extract_part01_cue_timestamps(part_01_wav_path=corrupt_wav)
        self.assertEqual(res["extraction_method"], "deterministic_fallback")
        self.assertTrue(validate_cue_manifest(res))

    def test_stereo_stitched_wav_activates_fallback(self):
        """Stereo WAV unpack mismatch in Tier 2 PCM scanner must gracefully activate Tier 3."""
        stereo_wav = os.path.join(self.tmp_dir, "stereo_part01.wav")
        make_test_wav(stereo_wav, duration=2.0, channels=2)
        res = extract_part01_cue_timestamps(part_01_wav_path=stereo_wav)
        self.assertEqual(res["extraction_method"], "deterministic_fallback")
        self.assertTrue(validate_cue_manifest(res))

    def test_tier1_failure_cascades_to_tier2_when_stitched_wav_valid(self):
        """When Tier 1 chunk directory is corrupted, Tier 2 zero-silence scanner must take over."""
        dir_corrupt = os.path.join(self.tmp_dir, "chunks_corrupt_cascade")
        os.makedirs(dir_corrupt, exist_ok=True)
        for i in range(1, 18):
            p = os.path.join(dir_corrupt, f"part_01_chunk_{i:03d}.wav")
            open(p, "wb").close()

        valid_stitched = os.path.join(self.tmp_dir, "valid_stitched.wav")
        make_stitched_test_wav(valid_stitched, n_chunks=18, chunk_dur=1.0, silence_dur=1.0)

        res = extract_part01_cue_timestamps(chunks_dir=dir_corrupt, part_01_wav_path=valid_stitched)
        self.assertEqual(res["extraction_method"], "zero_silence_scan")
        self.assertTrue(validate_cue_manifest(res))

    def test_output_json_path_written_on_fallback(self):
        """Fallback tier must properly write valid JSON when output_json_path is specified."""
        out_json = os.path.join(self.tmp_dir, "cues", "fallback_cues.json")
        extract_part01_cue_timestamps(output_json_path=out_json)
        self.assertTrue(os.path.exists(out_json))
        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["extraction_method"], "deterministic_fallback")
        self.assertEqual(data["part_index"], 1)
        self.assertEqual(data["cue_start_sec"], 174.73)
        self.assertTrue(validate_cue_manifest(data))


# ==============================================================================
# 2. Cue Manifest Validation Adversarial Challenges (11 tests)
# ==============================================================================
class TestAdversarialCueManifestValidation(unittest.TestCase):
    """Stress-tests validate_cue_manifest against malformed, missing, and invalid keys."""

    def test_empty_manifest_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            validate_cue_manifest({})

    def test_wrong_part_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_cue_manifest({
                "part_index": 2,
                "cue_text": "Now, dim the lights...",
                "cue_start_sec": 174.73,
                "cue_end_sec": 184.45,
                "dim_duration_sec": 9.72
            })

    def test_missing_cue_text_rejected(self):
        with self.assertRaises(ValueError):
            validate_cue_manifest({
                "part_index": 1,
                "cue_start_sec": 174.73,
                "cue_end_sec": 184.45,
                "dim_duration_sec": 9.72
            })

    def test_cue_text_missing_dim_the_lights_phrase_rejected(self):
        with self.assertRaises(ValueError):
            validate_cue_manifest({
                "part_index": 1,
                "cue_text": "Close your eyes and breathe deeply tonight.",
                "cue_start_sec": 174.73,
                "cue_end_sec": 184.45,
                "dim_duration_sec": 9.72
            })

    def test_non_numeric_cue_start_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            validate_cue_manifest({
                "part_index": 1,
                "cue_text": "Now, dim the lights...",
                "cue_start_sec": "not_a_number",
                "cue_end_sec": 184.45,
                "dim_duration_sec": 9.72
            })

    def test_non_numeric_cue_end_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            validate_cue_manifest({
                "part_index": 1,
                "cue_text": "Now, dim the lights...",
                "cue_start_sec": 174.73,
                "cue_end_sec": "invalid_end",
                "dim_duration_sec": 9.72
            })

    def test_none_timestamps_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            validate_cue_manifest({
                "part_index": 1,
                "cue_text": "Now, dim the lights...",
                "cue_start_sec": None,
                "cue_end_sec": 184.45,
                "dim_duration_sec": 9.72
            })

    def test_negative_cue_start_rejected(self):
        with self.assertRaises(ValueError):
            validate_cue_manifest({
                "part_index": 1,
                "cue_text": "Now, dim the lights...",
                "cue_start_sec": -10.0,
                "cue_end_sec": 184.45,
                "dim_duration_sec": 194.45
            })

    def test_start_greater_than_end_rejected(self):
        with self.assertRaises(ValueError):
            validate_cue_manifest({
                "part_index": 1,
                "cue_text": "Now, dim the lights...",
                "cue_start_sec": 200.0,
                "cue_end_sec": 100.0,
                "dim_duration_sec": -100.0
            })

    def test_start_equal_to_end_rejected(self):
        with self.assertRaises(ValueError):
            validate_cue_manifest({
                "part_index": 1,
                "cue_text": "Now, dim the lights...",
                "cue_start_sec": 150.0,
                "cue_end_sec": 150.0,
                "dim_duration_sec": 0.0
            })

    def test_duration_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            validate_cue_manifest({
                "part_index": 1,
                "cue_text": "Now, dim the lights...",
                "cue_start_sec": 100.0,
                "cue_end_sec": 110.0,
                "dim_duration_sec": 5.0  # Should be 10.0
            })


# ==============================================================================
# 3. Beat Aligner Adversarial Challenges: Extreme Durations & Anchoring (10 tests)
# ==============================================================================
class TestAdversarialBeatAlignerExtremeDurationsAndAnchoring(unittest.TestCase):
    """Stress-tests beat_aligner against extreme durations (0.1s, 36000s) and anchoring edge cases."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.imgs_10 = [f"beat_P01_B{i:02d}.jpg" for i in range(1, 11)]

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_extreme_small_duration_p01_anchored_raises_value_error(self):
        """0.1s total duration cannot host a 186.45s Beat 1 and must raise ValueError."""
        with patch("beat_aligner.get_audio_duration", return_value=0.1), self.assertRaises(ValueError):
            align_part_beats(
                part_index=1,
                audio_wav_path="dummy.wav",
                beat_images=self.imgs_10,
                p01_b01_duration=186.45
            )

    def test_extreme_small_duration_p01_unanchored_conserves_duration(self):
        """0.1s total duration unanchored must divide across beats and conserve duration within 1e-5s."""
        with patch("beat_aligner.get_audio_duration", return_value=0.1):
            res = align_part_beats(
                part_index=1,
                audio_wav_path="dummy.wav",
                beat_images=self.imgs_10
            )
            total = res["total_duration"]
            dur_sum = sum(b["duration"] for b in res["beats"])
            self.assertAlmostEqual(dur_sum, total, delta=1e-5)
            self.assertEqual(len(res["beats"]), 10)

    def test_extreme_small_duration_p02_conserves_duration(self):
        """0.1s total duration on Part 02 must conserve duration within 1e-5s."""
        with patch("beat_aligner.get_audio_duration", return_value=0.1):
            res = align_part_beats(
                part_index=2,
                audio_wav_path="dummy.wav",
                beat_images=self.imgs_10
            )
            dur_sum = sum(b["duration"] for b in res["beats"])
            self.assertAlmostEqual(dur_sum, res["total_duration"], delta=1e-5)

    def test_extreme_large_duration_p01_anchored_conserves_duration(self):
        """36000s (10 hours) on Part 01 anchored must conserve duration within 1e-5s."""
        with patch("beat_aligner.get_audio_duration", return_value=36000.0):
            res = align_part_beats(
                part_index=1,
                audio_wav_path="dummy.wav",
                beat_images=self.imgs_10,
                p01_b01_duration=186.45
            )
            beats = res["beats"]
            self.assertEqual(beats[0]["duration"], 186.45)
            dur_sum = sum(b["duration"] for b in beats)
            self.assertAlmostEqual(dur_sum, 36000.0, delta=1e-5)
            self.assertEqual(beats[-1]["end_time"], 36000.0)

    def test_extreme_large_duration_p15_conserves_duration(self):
        """36000s on Part 15 must conserve duration within 1e-5s with equal division."""
        with patch("beat_aligner.get_audio_duration", return_value=36000.0):
            res = align_part_beats(
                part_index=15,
                audio_wav_path="dummy.wav",
                beat_images=self.imgs_10
            )
            for b in res["beats"]:
                self.assertEqual(b["duration"], 3600.0)
            dur_sum = sum(b["duration"] for b in res["beats"])
            self.assertAlmostEqual(dur_sum, 36000.0, delta=1e-5)

    def test_cue_discovery_present_vs_absent(self):
        """Tests auto-discovery of Part_01_cues.json in audio directory."""
        audio_path = os.path.join(self.tmp_dir, "Part_01.wav")
        cues_path = os.path.join(self.tmp_dir, "Part_01_cues.json")

        # Absent scenario: unanchored equal division
        with patch("beat_aligner.get_audio_duration", return_value=350.0):
            res_absent = align_part_beats(part_index=1, audio_wav_path=audio_path, beat_images=self.imgs_10)
            b1_absent = res_absent["beats"][0]
            self.assertEqual(b1_absent["duration"], 35.0)
            self.assertEqual(b1_absent["dim_start_sec"], 0.0)
            self.assertEqual(b1_absent["dim_end_sec"], 0.0)

        # Present scenario: anchored to recommended_b01_duration_sec
        cue_data = {
            "part_index": 1,
            "cue_phrase": "dim the lights",
            "cue_start_sec": 174.73,
            "cue_end_sec": 184.45,
            "dim_duration_sec": 9.72,
            "recommended_b01_duration_sec": 186.45
        }
        with open(cues_path, "w", encoding="utf-8") as f:
            json.dump(cue_data, f)

        with patch("beat_aligner.get_audio_duration", return_value=350.0):
            res_present = align_part_beats(part_index=1, audio_wav_path=audio_path, beat_images=self.imgs_10)
            b1_present = res_present["beats"][0]
            self.assertEqual(b1_present["duration"], 186.45)
            self.assertEqual(b1_present["dim_start_sec"], 174.73)
            self.assertEqual(b1_present["dim_end_sec"], 184.45)

    def test_explicit_p01_b01_duration_overrides_cue_file(self):
        """Passing explicit p01_b01_duration overrides cue file recommended duration."""
        cues_path = os.path.join(self.tmp_dir, "Part_01_cues.json")
        cue_data = {
            "part_index": 1,
            "cue_phrase": "dim the lights",
            "cue_start_sec": 174.73,
            "cue_end_sec": 184.45,
            "recommended_b01_duration_sec": 186.45
        }
        with open(cues_path, "w", encoding="utf-8") as f:
            json.dump(cue_data, f)

        audio_path = os.path.join(self.tmp_dir, "Part_01.wav")
        with patch("beat_aligner.get_audio_duration", return_value=350.0):
            res = align_part_beats(
                part_index=1,
                audio_wav_path=audio_path,
                beat_images=self.imgs_10,
                p01_b01_duration=190.0
            )
            self.assertEqual(res["beats"][0]["duration"], 190.0)

    def test_zero_beat_images_raises_value_error(self):
        with patch("beat_aligner.get_audio_duration", return_value=300.0), self.assertRaises(ValueError):
            align_part_beats(part_index=1, audio_wav_path="dummy.wav", beat_images=[])

    def test_single_beat_image_conserves_duration(self):
        """Single beat image gets full total_duration."""
        with patch("beat_aligner.get_audio_duration", return_value=123.456):
            res = align_part_beats(
                part_index=1,
                audio_wav_path="dummy.wav",
                beat_images=["solo_beat.jpg"]
            )
            self.assertEqual(len(res["beats"]), 1)
            self.assertEqual(res["beats"][0]["duration"], 123.456)
            self.assertAlmostEqual(res["beats"][0]["duration"], res["total_duration"], delta=1e-5)

    def test_nonexistent_audio_file_raises_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            get_audio_duration("/nonexistent/path/to/missing_audio.wav")


# ==============================================================================
# 4. Beat Aligner Tagging, Continuity & Invariants (4 tests)
# ==============================================================================
class TestAdversarialBeatAlignerTaggingAndInvariants(unittest.TestCase):
    """Stress-tests transition tags, sleep mode tags, and timestamp continuity invariants."""

    def setUp(self):
        self.imgs_10 = [f"beat_B{i:02d}.jpg" for i in range(1, 11)]

    def test_part01_beat_tagging_invariants(self):
        """Part 01: Beat 1 is_transition=True & sleep_mode=False; Beats 2..10 is_transition=False & sleep_mode=True."""
        with patch("beat_aligner.get_audio_duration", return_value=350.0):
            res = align_part_beats(
                part_index=1,
                audio_wav_path="dummy.wav",
                beat_images=self.imgs_10,
                p01_b01_duration=186.45,
                dim_start_sec=174.73,
                dim_end_sec=184.45
            )
            for b in res["beats"]:
                idx = b["beat_index"]
                if idx == 1:
                    self.assertTrue(b["is_transition_beat"])
                    self.assertFalse(b["sleep_mode"])
                    self.assertEqual(b["dim_start_sec"], 174.73)
                    self.assertEqual(b["dim_end_sec"], 184.45)
                else:
                    self.assertFalse(b["is_transition_beat"])
                    self.assertTrue(b["sleep_mode"])
                    self.assertEqual(b["dim_start_sec"], 0.0)
                    self.assertEqual(b["dim_end_sec"], 0.0)

    def test_parts02_to_15_beat_tagging_invariants(self):
        """Parts 02..15: All beats have is_transition=False, sleep_mode=True, and dim cues == 0.0."""
        with patch("beat_aligner.get_audio_duration", return_value=350.0):
            for p in range(2, 16):
                res = align_part_beats(part_index=p, audio_wav_path="dummy.wav", beat_images=self.imgs_10)
                for b in res["beats"]:
                    idx = b["beat_index"]
                    self.assertFalse(b["is_transition_beat"], f"Part {p} Beat {idx} is_transition must be False")
                    self.assertTrue(b["sleep_mode"], f"Part {p} Beat {idx} sleep_mode must be True")
                    self.assertEqual(b["dim_start_sec"], 0.0)
                    self.assertEqual(b["dim_end_sec"], 0.0)

    def test_duration_conservation_and_continuity_matrix(self):
        """Tests duration conservation and timestamp continuity across wide parameter combinations."""
        durations = [0.5, 7.77, 42.123, 100.0, 350.0, 1234.567, 36000.0]
        beat_counts = [2, 5, 10, 11, 20]
        parts = [1, 2, 8, 15]

        for tot in durations:
            for count in beat_counts:
                imgs = [f"img_{i}.jpg" for i in range(1, count + 1)]
                for p in parts:
                    anchor = 186.45 if (p == 1 and tot > 200.0 and count > 1) else None
                    with patch("beat_aligner.get_audio_duration", return_value=tot):
                        res = align_part_beats(
                            part_index=p,
                            audio_wav_path="dummy.wav",
                            beat_images=imgs,
                            p01_b01_duration=anchor
                        )
                        beats = res["beats"]
                        total_out = res["total_duration"]

                        # Invariant 1: Sum of durations equals total duration within 1e-5s
                        dur_sum = sum(b["duration"] for b in beats)
                        self.assertAlmostEqual(
                            dur_sum, total_out, delta=1e-5,
                            msg=f"Failed conservation on P{p}, tot={tot}, beats={count}"
                        )

                        # Invariant 2: Start time of first beat is 0.0
                        self.assertEqual(beats[0]["start_time"], 0.0)

                        # Invariant 3: Continuity without gaps or overlaps
                        for i in range(len(beats)):
                            b = beats[i]
                            self.assertAlmostEqual(
                                b["end_time"] - b["start_time"], b["duration"], delta=1e-5
                            )
                            if i > 0:
                                self.assertEqual(beats[i]["start_time"], beats[i - 1]["end_time"])

                        # Invariant 4: End time of last beat equals total duration
                        self.assertAlmostEqual(beats[-1]["end_time"], total_out, delta=1e-5)

    def test_output_json_generation_and_roundtrip(self):
        """Verifies output JSON matches returned dictionary exactly."""
        with tempfile.TemporaryDirectory() as td:
            out_json = os.path.join(td, "nested", "beats_alignment.json")
            with patch("beat_aligner.get_audio_duration", return_value=300.0):
                res = align_part_beats(
                    part_index=1,
                    audio_wav_path="dummy.wav",
                    beat_images=self.imgs_10,
                    output_json_path=out_json
                )
                self.assertTrue(os.path.exists(out_json))
                with open(out_json, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.assertEqual(res, loaded)


# ==============================================================================
# 5. Dual-Tree Parity: hsnooze.render vs 00.codebases (2 tests)
# ==============================================================================
class TestAdversarialDualTreeParity(unittest.TestCase):
    """Verifies that hsnooze.render/ and 00.codebases/ yield identical outputs under adversarial stress."""

    def setUp(self):
        # Load 00.codebases modules dynamically
        spec_cue = importlib.util.spec_from_file_location(
            "codebase_cue_extractor", CODEBASE_DIR / "cue_extractor.py"
        )
        self.codebase_cue = importlib.util.module_from_spec(spec_cue)
        spec_cue.loader.exec_module(self.codebase_cue)

        spec_align = importlib.util.spec_from_file_location(
            "codebase_beat_aligner", CODEBASE_DIR / "beat_aligner.py"
        )
        self.codebase_align = importlib.util.module_from_spec(spec_align)
        spec_align.loader.exec_module(self.codebase_align)

    def test_dual_tree_cue_extractor_corruption_parity(self):
        """Both cue_extractor implementations must produce identical fallback outputs."""
        res_render = cue_extractor.extract_part01_cue_timestamps(chunks_dir="/nonexistent")
        res_codebase = self.codebase_cue.extract_part01_cue_timestamps(chunks_dir="/nonexistent")
        self.assertEqual(res_render, res_codebase)

    def test_dual_tree_beat_aligner_extreme_duration_parity(self):
        """Both beat_aligner implementations must produce identical outputs under extreme durations."""
        imgs = [f"beat_P01_B{i:02d}.jpg" for i in range(1, 11)]
        with patch.object(beat_aligner, "get_audio_duration", return_value=36000.0), \
             patch.object(self.codebase_align, "get_audio_duration", return_value=36000.0):
            res_render = beat_aligner.align_part_beats(
                part_index=1,
                audio_wav_path="dummy.wav",
                beat_images=imgs,
                p01_b01_duration=186.45
            )
            res_codebase = self.codebase_align.align_part_beats(
                part_index=1,
                audio_wav_path="dummy.wav",
                beat_images=imgs,
                p01_b01_duration=186.45
            )
            self.assertEqual(res_render, res_codebase)


if __name__ == "__main__":
    unittest.main()
