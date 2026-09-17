"""
Adversarial and Stress Test Suite for Gatekeepers GK3/GK6 and StorySegmenter
File: tests/test_gatekeeper_and_segmenter_adversarial.py
Milestone: Milestone 2 Stress & Boundary Verification

Tests:
1. Gatekeeper GK3 Boundary Beat Counts (149, 150, 160, 161)
2. Gatekeeper GK6 Boundary Beat Counts & Pre-Assembly Verification
3. Deficient Part Audits (150 total beats, but Part 01 has 9 and Part 02 has 11)
4. Missing Audio WAV Files and Corrupted Keyframe Filenames/Extensions
5. CRLF Line Endings vs Unix LF in combined_imageprompts.txt and Scripts
6. StorySegmenter Pathological Narration Text (Empty string, no punctuation, single huge sentence, repetitive sentences)
7. Tag Injection, Character Limits (1500 chars), and validate_prompt Defense
"""

import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hsnooze.scripting"))
sys.path.insert(0, str(REPO_ROOT / "hsnooze.render"))

import config
from pipeline_orchestrator import audit_gk3_prompts, audit_gk6_assets
from online_script_producer import (
    StoryBeat,
    StorySegmenter,
    get_matsuo_basho_150_beats,
)
from prompt_engine import (
    build_consistent_prompt,
    validate_prompt,
    extract_prompt_tags,
    strip_prompt_tags,
    format_combined_prompts_file,
)


def _generate_valid_prompt_text(part: int, beat: int) -> str:
    return build_consistent_prompt(
        scene_description=f"Basho meditating quietly along the misty path in Part {part} Beat {beat}",
        character_name="matsuo_basho",
        character_ref="ref_character_basho",
        setting_ref="ref_setting_tohoku_trail",
        prop_ref="ref_props_travel_gear",
    )


# ==============================================================================
# 1. Gatekeeper GK3 Boundary Beat Counts (149, 150, 160, 161)
# ==============================================================================
class TestGK3BoundaryBeatCounts(unittest.TestCase):
    """Stress-tests GK3 prompt count boundaries: 149, 150, 160, 161 beats."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="hsnooze_gk3_boundary_")
        self.preprod_dir = Path(self.test_dir) / "01. Pre-Production"
        self.preprod_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_file = self.preprod_dir / "combined_imageprompts.txt"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _write_prompts(self, part_distribution: dict):
        """Helper to write combined_imageprompts.txt with a specific part distribution."""
        prompts = {}
        for p, count in part_distribution.items():
            for b in range(1, count + 1):
                bid = f"beat_P{p:02d}_B{b:02d}.jpg"
                prompts[bid] = _generate_valid_prompt_text(p, b)
        content = format_combined_prompts_file(prompts)
        self.prompts_file.write_text(content, encoding="utf-8")
        return len(prompts)

    def test_gk3_boundary_149_beats_must_fail(self):
        """Boundary test: exactly 149 beats (P01-P14 have 10, P15 has 9). Must fail GK3."""
        dist = {p: 10 for p in range(1, 15)}
        dist[15] = 9
        total = self._write_prompts(dist)
        self.assertEqual(total, 149)

        res = audit_gk3_prompts(self.test_dir)
        self.assertFalse(res["passed_gk3"], "GK3 should FAIL on 149 beats")
        self.assertEqual(res["total_count"], 149)
        self.assertIn(15, res["deficient_parts"])
        self.assertTrue(any("outside required range" in d for d in res["details"]))

    def test_gk3_boundary_150_beats_must_pass(self):
        """Boundary test: exactly 150 beats (10 beats per part for all 15 parts). Must pass GK3."""
        dist = {p: 10 for p in range(1, 16)}
        total = self._write_prompts(dist)
        self.assertEqual(total, 150)

        res = audit_gk3_prompts(self.test_dir)
        self.assertTrue(res["passed_gk3"], f"GK3 should PASS on 150 beats: {res['details']}")
        self.assertEqual(res["total_count"], 150)
        self.assertEqual(len(res["deficient_parts"]), 0)

    def test_gk3_boundary_160_beats_must_pass(self):
        """Boundary test: exactly 160 beats (P01-P10 have 11, P11-P15 have 10). Must pass GK3."""
        dist = {p: 11 if p <= 10 else 10 for p in range(1, 16)}
        total = self._write_prompts(dist)
        self.assertEqual(total, 160)

        res = audit_gk3_prompts(self.test_dir)
        self.assertTrue(res["passed_gk3"], f"GK3 should PASS on 160 beats: {res['details']}")
        self.assertEqual(res["total_count"], 160)
        self.assertEqual(len(res["deficient_parts"]), 0)

    def test_gk3_boundary_161_beats_must_fail(self):
        """Boundary test: exactly 161 beats (P01-P11 have 11, P12-P15 have 10). Must fail GK3."""
        dist = {p: 11 if p <= 11 else 10 for p in range(1, 16)}
        total = self._write_prompts(dist)
        self.assertEqual(total, 161)

        res = audit_gk3_prompts(self.test_dir)
        self.assertFalse(res["passed_gk3"], "GK3 should FAIL on 161 beats")
        self.assertEqual(res["total_count"], 161)
        self.assertTrue(any("outside required range" in d for d in res["details"]))


# ==============================================================================
# 2. Deficient Part Audits (150 total beats, but P01 has 9 and P02 has 11)
# ==============================================================================
class TestDeficientPartAudits(unittest.TestCase):
    """Stress-tests per-part minimum count of >=10 beats when total count is 150."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="hsnooze_deficient_part_")
        self.preprod_dir = Path(self.test_dir) / "01. Pre-Production"
        self.preprod_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_file = self.preprod_dir / "combined_imageprompts.txt"

        self.audio_dir = Path(self.test_dir) / "02. Media Generation" / "audio"
        self.keyframes_dir = Path(self.test_dir) / "02. Media Generation" / "keyframes"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.keyframes_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy 15 audio files
        for p in range(1, 16):
            (self.audio_dir / f"Part_{p:02d}.wav").write_bytes(b"RIFF\x24\x08\x00\x00WAVEfmt ")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gk3_fails_when_part_01_has_9_and_part_02_has_11_beats(self):
        """150 total prompts, but Part 01 has 9 and Part 02 has 11 beats. Must fail GK3."""
        dist = {p: 10 for p in range(1, 16)}
        dist[1] = 9
        dist[2] = 11

        prompts = {}
        for p, count in dist.items():
            for b in range(1, count + 1):
                bid = f"beat_P{p:02d}_B{b:02d}.jpg"
                prompts[bid] = _generate_valid_prompt_text(p, b)
        content = format_combined_prompts_file(prompts)
        self.prompts_file.write_text(content, encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir)
        self.assertEqual(res["total_count"], 150)
        self.assertFalse(res["passed_gk3"], "GK3 must fail if Part 01 has 9 beats")
        self.assertIn(1, res["deficient_parts"])
        self.assertNotIn(2, res["deficient_parts"])
        self.assertEqual(res["part_counts"][1], 9)
        self.assertEqual(res["part_counts"][2], 11)
        self.assertTrue(any("Part 01 has 9 prompts, expected at least 10" in d for d in res["details"]))

    def test_gk6_fails_when_part_01_has_9_and_part_02_has_11_keyframes(self):
        """150 total keyframes, but Part 01 has 9 and Part 02 has 11 keyframes. Must fail GK6."""
        dist = {p: 10 for p in range(1, 16)}
        dist[1] = 9
        dist[2] = 11

        count = 0
        for p, num_beats in dist.items():
            for b in range(1, num_beats + 1):
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
                count += 1
        self.assertEqual(count, 150)

        res = audit_gk6_assets(self.test_dir)
        self.assertEqual(res["image_count"], 150)
        self.assertEqual(res["audio_count"], 15)
        self.assertFalse(res["passed_gk6"], "GK6 must fail if Part 01 has 9 keyframes")
        self.assertIn(1, res["deficient_parts"])
        self.assertEqual(res["part_counts"][1], 9)
        self.assertEqual(res["part_counts"][2], 11)
        self.assertTrue(any("Part 01 has 9 keyframes, expected at least 10" in d for d in res["details"]))


# ==============================================================================
# 3. Missing Audio and Corrupted Keyframe Filenames
# ==============================================================================
class TestMissingAudioAndCorruptedKeyframes(unittest.TestCase):
    """Stress-tests GK6 and GK3 against missing audio WAVs and malformed keyframe filenames."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="hsnooze_corrupt_")
        self.audio_dir = Path(self.test_dir) / "02. Media Generation" / "audio"
        self.keyframes_dir = Path(self.test_dir) / "02. Media Generation" / "keyframes"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.keyframes_dir.mkdir(parents=True, exist_ok=True)

        for p in range(1, 16):
            (self.audio_dir / f"Part_{p:02d}.wav").write_bytes(b"RIFF\x24\x08\x00\x00WAVEfmt ")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_valid_150_keyframes(self):
        for p in range(1, 16):
            for b in range(1, 11):
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(b"\xff\xd8\xff\xe0")

    def test_gk6_fails_when_single_audio_wav_is_missing(self):
        """GK6 fails when 150 keyframes exist but Part_08.wav is missing (14 WAVs total)."""
        self._create_valid_150_keyframes()
        (self.audio_dir / "Part_08.wav").unlink()

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"])
        self.assertEqual(res["audio_count"], 14)
        self.assertTrue(any("Expected 15 WAV files, found 14" in d for d in res["details"]))

    def test_gk6_fails_when_all_audio_wavs_missing(self):
        """GK6 fails when audio directory is empty."""
        self._create_valid_150_keyframes()
        for f in self.audio_dir.glob("*.wav"):
            f.unlink()

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"])
        self.assertEqual(res["audio_count"], 0)

    def test_gk6_fails_when_audio_file_has_wrong_extension(self):
        """Part_01.mp3 instead of Part_01.wav -> only 14 WAV files found."""
        self._create_valid_150_keyframes()
        (self.audio_dir / "Part_01.wav").rename(self.audio_dir / "Part_01.mp3")

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"])
        self.assertEqual(res["audio_count"], 14)

    def test_gk6_fails_when_keyframe_filename_lacks_part_zero_padding(self):
        """Keyframe named beat_P1_B01.jpg (single digit part) instead of beat_P01_B01.jpg."""
        self._create_valid_150_keyframes()
        (self.keyframes_dir / "beat_P01_B01.jpg").rename(self.keyframes_dir / "beat_P1_B01.jpg")

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"])
        self.assertIn(1, res["deficient_parts"])
        self.assertEqual(res["part_counts"][1], 9)

    def test_gk6_fails_when_keyframe_has_forbidden_extension_gif(self):
        """Keyframe saved as .gif is not in jpg/jpeg/png glob, leaving part deficient."""
        self._create_valid_150_keyframes()
        (self.keyframes_dir / "beat_P01_B01.jpg").rename(self.keyframes_dir / "beat_P01_B01.gif")

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"])
        self.assertEqual(res["image_count"], 149)
        self.assertIn(1, res["deficient_parts"])

    def test_gk6_fails_when_keyframe_name_is_arbitrary_garbage(self):
        """Keyframe named beat_corrupted_artifact.jpg does not match beat_P01_, part is deficient."""
        self._create_valid_150_keyframes()
        (self.keyframes_dir / "beat_P01_B01.jpg").rename(self.keyframes_dir / "beat_corrupted_artifact.jpg")

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"])
        self.assertIn(1, res["deficient_parts"])

    def test_gk3_fails_on_malformed_beat_line_format(self):
        """GK3 flags malformed beat format like 'beat_01_01: prompt'."""
        preprod = Path(self.test_dir) / "01. Pre-Production"
        preprod.mkdir(parents=True, exist_ok=True)
        prompts_file = preprod / "combined_imageprompts.txt"

        lines = []
        for p in range(1, 16):
            for b in range(1, 11):
                if p == 1 and b == 1:
                    lines.append(f"beat_01_01: {_generate_valid_prompt_text(p, b)}")
                else:
                    lines.append(f"beat_P{p:02d}_B{b:02d}.jpg: {_generate_valid_prompt_text(p, b)}")
        prompts_file.write_text("\n\n".join(lines) + "\n", encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir)
        self.assertFalse(res["passed_gk3"])
        self.assertTrue(any("Malformed beat line format" in d for d in res["details"]))

    def test_gk3_fails_on_part_outside_1_to_15_range(self):
        """GK3 flags beat line with Part 16."""
        preprod = Path(self.test_dir) / "01. Pre-Production"
        preprod.mkdir(parents=True, exist_ok=True)
        prompts_file = preprod / "combined_imageprompts.txt"

        lines = []
        for p in range(1, 16):
            for b in range(1, 11):
                if p == 15 and b == 10:
                    lines.append(f"beat_P16_B01.jpg: {_generate_valid_prompt_text(16, 1)}")
                else:
                    lines.append(f"beat_P{p:02d}_B{b:02d}.jpg: {_generate_valid_prompt_text(p, b)}")
        prompts_file.write_text("\n\n".join(lines) + "\n", encoding="utf-8")

        res = audit_gk3_prompts(self.test_dir)
        self.assertFalse(res["passed_gk3"])
        self.assertTrue(any("outside expected range" in d for d in res["details"]))


# ==============================================================================
# 4. CRLF vs Unix LF Line Endings Handling
# ==============================================================================
class TestCRLFHandling(unittest.TestCase):
    """Stress-tests GK3 and validators on Windows CRLF (\\r\\n) vs Unix LF (\\n)."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="hsnooze_crlf_")
        self.preprod_dir = Path(self.test_dir) / "01. Pre-Production"
        self.preprod_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_file = self.preprod_dir / "combined_imageprompts.txt"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gk3_handles_pure_crlf_line_endings_in_combined_prompts(self):
        """combined_imageprompts.txt saved with pure Windows \\r\\n line endings passes GK3."""
        prompts = {}
        for p in range(1, 16):
            for b in range(1, 11):
                bid = f"beat_P{p:02d}_B{b:02d}.jpg"
                prompts[bid] = _generate_valid_prompt_text(p, b)

        # Construct file using explicit \r\n
        content_lf = format_combined_prompts_file(prompts)
        content_crlf = content_lf.replace("\n", "\r\n")
        self.prompts_file.write_bytes(content_crlf.encode("utf-8"))

        res = audit_gk3_prompts(self.test_dir)
        self.assertTrue(res["passed_gk3"], f"GK3 must pass on CRLF file: {res['details']}")
        self.assertEqual(res["total_count"], 150)
        self.assertEqual(len(res["deficient_parts"]), 0)

    def test_gk3_handles_mixed_lf_and_crlf_line_endings(self):
        """combined_imageprompts.txt with mixed \\r\\n and \\n line endings passes GK3."""
        prompts = {}
        for p in range(1, 16):
            for b in range(1, 11):
                bid = f"beat_P{p:02d}_B{b:02d}.jpg"
                prompts[bid] = _generate_valid_prompt_text(p, b)

        lines = []
        for i, (bid, text) in enumerate(prompts.items()):
            ending = "\r\n\r\n" if i % 2 == 0 else "\n\n"
            lines.append(f"{bid}: {text}{ending}")
        content_mixed = "".join(lines)
        self.prompts_file.write_bytes(content_mixed.encode("utf-8"))

        res = audit_gk3_prompts(self.test_dir)
        self.assertTrue(res["passed_gk3"], f"GK3 must pass on mixed LF/CRLF: {res['details']}")
        self.assertEqual(res["total_count"], 150)

    def test_validate_prompt_rejects_embedded_cr_and_crlf(self):
        """validate_prompt strictly rejects prompt strings containing \\r or \\r\\n."""
        valid = _generate_valid_prompt_text(1, 1)
        res_valid = validate_prompt(valid)
        self.assertTrue(res_valid["is_valid"])

        # Inject \r
        res_cr = validate_prompt(valid + "\r")
        self.assertFalse(res_cr["is_valid"])
        self.assertTrue(any("newline" in i.lower() for i in res_cr["issues"]))

        # Inject \r\n
        res_crlf = validate_prompt(valid + "\r\n")
        self.assertFalse(res_crlf["is_valid"])
        self.assertTrue(any("newline" in i.lower() for i in res_crlf["issues"]))

    def test_story_segmenter_crlf_script_limitation(self):
        """
        Adversarial test revealing StorySegmenter regex limitation with pure CRLF scripts.
        When a full 15-part script uses \\r\\n\\r\\n, re.findall with \\n\\n fails to match
        parts, silently falling back to canonical Basho beats.
        """
        parts_text = []
        for i in range(1, 16):
            parts_text.append(f"## Part {i:02d}: Custom Title\r\n\r\nParagraph 1.\r\n\r\nParagraph 2.")
        crlf_script = "\r\n\r\n".join(parts_text)

        matches = re.findall(r'## Part (\d+):[^\n]*\n\n(.*?)(?=\n## Part |\Z)', crlf_script, re.DOTALL)
        self.assertEqual(len(matches), 0, "Demonstrates re.findall with \\n\\n does not match \\r\\n\\r\\n")

        # Calling segment_script_into_150_beats returns fallback Basho beats rather than raising error
        beats = StorySegmenter.segment_script_into_150_beats(crlf_script)
        self.assertEqual(len(beats), 150)
        # Verify fallback occurred: titles are Basho canonical titles, not 'Custom Title'
        self.assertEqual(beats[0].title, "Ueno Mountain Trail at Twilight")


# ==============================================================================
# 5. StorySegmenter Pathological Narration Text Stress Testing
# ==============================================================================
class TestStorySegmenterPathologicalText(unittest.TestCase):
    """Stress-tests StorySegmenter against empty, unpunctuated, single-sentence, and repetitive inputs."""

    def test_segment_part_text_empty_string_crashes_with_value_error(self):
        """
        DEFENSIVE BEHAVIOR CHECK:
        StorySegmenter.segment_part_text(1, '') returns 10 fallback beats without crashing.
        """
        res = StorySegmenter.segment_part_text(1, "")
        self.assertEqual(len(res), 10)
        self.assertEqual(res[0], "Narrative beat 1")
        self.assertEqual(res[9], "Narrative beat 10")

    def test_segment_part_text_whitespace_only_crashes_with_value_error(self):
        """Whitespace-only input also returns 10 fallback beats without crashing."""
        res = StorySegmenter.segment_part_text(1, "   \n\n \t \n\n   ")
        self.assertEqual(len(res), 10)
        self.assertEqual(res[0], "Narrative beat 1")
        self.assertEqual(res[9], "Narrative beat 10")

    def test_segment_part_text_no_punctuation_returns_single_paragraph(self):
        """
        DEFENSIVE BEHAVIOR CHECK:
        When narrative text contains no punctuation (. ! ?), segment_part_text cannot
        split sentences and breaks early, returning 1 paragraph instead of 10.
        """
        no_punct_text = "This is a long continuous narration without any periods or question marks or exclamation marks running along the quiet ancient road"
        res = StorySegmenter.segment_part_text(1, no_punct_text)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], no_punct_text)

    def test_segment_part_text_single_huge_sentence_returns_single_paragraph(self):
        """A 1,000-word single sentence with a single terminal period cannot be split further."""
        huge_sentence = " ".join(["word"] * 1000) + "."
        res = StorySegmenter.segment_part_text(1, huge_sentence)
        self.assertEqual(len(res), 1)

    def test_segment_part_text_repetitive_few_sentences_returns_partial_count(self):
        """Text with only 3 sentences returns 3 paragraphs instead of 10."""
        text_3 = "The temple bell tolls. The cedar woodsmoke drifts. The evening river flows softly."
        res = StorySegmenter.segment_part_text(1, text_3)
        self.assertEqual(len(res), 3)

    def test_segment_part_text_sufficient_sentences_produces_exact_10_paragraphs(self):
        """Standard narration with 20+ sentences successfully produces exactly 10 paragraphs."""
        sentences = [f"Sentence number {i} describes the peaceful landscape." for i in range(1, 25)]
        normal_text = " ".join(sentences)
        res = StorySegmenter.segment_part_text(1, normal_text)
        self.assertEqual(len(res), 10)

    def test_segment_script_into_150_beats_handles_part_with_few_paragraphs(self):
        """
        segment_script_into_150_beats gracefully handles parts where segment_part_text
        returned fewer than 10 paragraphs by substituting 'Narrative beat {b_idx}'.
        """
        # Script where Part 01 has only 1 sentence
        parts_text = []
        for i in range(1, 16):
            if i == 1:
                parts_text.append(f"## Part {i:02d}: Title\n\nSingle unpunctuated sentence")
            else:
                sents = " ".join([f"Sentence {k} in part {i}." for k in range(1, 20)])
                parts_text.append(f"## Part {i:02d}: Title\n\n{sents}")
        script = "\n\n".join(parts_text)

        beats = StorySegmenter.segment_script_into_150_beats(script)
        self.assertEqual(len(beats), 150)
        # Part 1 Beat 1 gets the sentence
        self.assertEqual(beats[0].narrative_text, "Single unpunctuated sentence")
        # Part 1 Beat 2 gets fallback
        self.assertEqual(beats[1].narrative_text, "Narrative beat 2")


# ==============================================================================
# 6. Tag Injection, Character Limits (1500 chars), and validate_prompt Defense
# ==============================================================================
class TestTagInjectionAndPromptLimits(unittest.TestCase):
    """Stress-tests prompt length constraints, tag syntax, and injection defense."""

    def test_all_150_canonical_prompts_strictly_under_1500_chars(self):
        """Verify all 150 canonical Basho beats have lengths strictly <= 1500 chars."""
        beats = get_matsuo_basho_150_beats()
        self.assertEqual(len(beats), 150)
        prompts = StorySegmenter.generate_part_prompts(beats)
        self.assertEqual(len(prompts), 150)

        lengths = []
        for bid, p in prompts.items():
            res = validate_prompt(p)
            self.assertTrue(res["is_valid"], f"Canonical prompt {bid} failed validation: {res['issues']}")
            lengths.append(res["length"])
            self.assertLessEqual(res["length"], 1500, f"Prompt {bid} exceeds 1500 chars: {res['length']}")

        self.assertGreaterEqual(min(lengths), 1000)
        self.assertLessEqual(max(lengths), 1200)

    def test_oversized_scene_description_exceeding_1500_chars_is_flagged(self):
        """Prompt exceeding 1500 characters is rejected by validate_prompt."""
        oversized_desc = "A contemplative journey through the serene misty hills of seventeenth-century Japan. " * 20
        prompt = build_consistent_prompt(
            scene_description=oversized_desc,
            character_name="matsuo_basho",
            character_ref="ref_character_basho"
        )
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("exceeds maximum character length of 1500" in i for i in res["issues"]))

    def test_tag_injection_special_shell_and_sql_characters_rejected(self):
        """Tags with SQL/shell/XSS injection attempts are rejected by validate_prompt."""
        injections = [
            "basho; DROP TABLE users;--",
            "basho && rm -rf /",
            "basho | cat /etc/passwd",
            "<script>alert(1)</script>",
            "basho' OR '1'='1",
        ]
        for inj in injections:
            prompt = f"[CHARACTER: {inj}] " + _generate_valid_prompt_text(1, 1)
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Expected injection '{inj}' to be rejected")
            self.assertTrue(any("invalid characters" in i for i in res["issues"]))

    def test_tag_injection_unknown_type_rejected(self):
        """Unknown tag types (e.g. [ACTOR:], [CAMERA:], [LIGHT:]) are rejected."""
        unknown_tags = ["[ACTOR: basho]", "[CAMERA: wide_angle]", "[LIGHT: ambient_golden]"]
        for t in unknown_tags:
            prompt = f"{t} " + _generate_valid_prompt_text(1, 1)
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"])
            self.assertTrue(any("Unknown reference tag type" in i for i in res["issues"]))

    def test_tag_injection_empty_identifier_rejected(self):
        """Empty tag identifiers like [CHARACTER:] or [CHARACTER: ] are rejected."""
        empty_tags = ["[CHARACTER:]", "[CHARACTER: ]", "[SETTING:]", "[PROP: ]"]
        for t in empty_tags:
            prompt = f"{t} " + _generate_valid_prompt_text(1, 1)
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"])
            self.assertTrue(any("empty identifier" in i for i in res["issues"]))

    def test_tag_injection_missing_colon_rejected(self):
        """Tags missing colon separator like [CHARACTER basho] are rejected."""
        prompt = "[CHARACTER basho] " + _generate_valid_prompt_text(1, 1)
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("missing colon separator" in i for i in res["issues"]))

    def test_tag_injection_unbalanced_brackets_rejected(self):
        """Prompts with unbalanced brackets are rejected."""
        prompts = [
            "[CHARACTER: basho " + _generate_valid_prompt_text(1, 1),
            "CHARACTER: basho] " + _generate_valid_prompt_text(1, 1),
            "[[CHARACTER: basho]] " + _generate_valid_prompt_text(1, 1),
        ]
        for p in prompts:
            res = validate_prompt(p)
            self.assertFalse(res["is_valid"])

    def test_forbidden_words_in_tag_or_scene_rejected(self):
        """validate_prompt rejects forbidden terms in scene description or tags."""
        for term in ["photorealistic", "3d render", "cgi", "octane render", ".gif"]:
            prompt = build_consistent_prompt(
                scene_description=f"serene temple scene with {term} quality",
                character_name="matsuo_basho"
            )
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Forbidden term '{term}' was not caught!")


if __name__ == "__main__":
    unittest.main()
