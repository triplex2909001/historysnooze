"""
Empirical Stress-Testing and Challenge Harness for Milestone A:
150-Beat Narrative Mapping and Gatekeepers GK3/GK6.

File: tests/test_m_a_challenger2_harness.py
Author: challenger_m_a_2 (Critic & Specialist)
Mission:
  1. Validate exactly 150 beats across all 15 parts in combined_imageprompts.txt and get_matsuo_basho_150_beats().
  2. Verify every Part p (1..15) uses its exact designated setting from PART_SETTINGS[p] across all 10 beats of that part.
  3. Verify character life-stage transitions occur strictly at the defined boundaries:
     - P01-02: young (ref_character_basho_young)
     - P03-04: elder (ref_character_basho_elder)
     - P05-11: traveler (ref_character_basho_traveler, with ref_character_sora at P06_B04)
     - P12-15: elder (ref_character_basho_elder)
  4. Test pipeline_orchestrator.py audit functions (audit_gk3_prompts and audit_gk6_assets) against boundary conditions:
     - 149 beats (must fail)
     - 150 beats (must pass)
     - 151 beats (must pass if under 160)
     - 161 beats (must fail on GK3, document GK6 behavior)
  5. Test dual-tree parity across hsnooze.scripting, 00.codebases, and hsnooze.gflow.
"""

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
from online_script_producer import (
    StoryBeat,
    StorySegmenter,
    get_matsuo_basho_150_beats,
    PART_SETTINGS,
    CONTEXTUAL_PROP_MAP,
)
from pipeline_orchestrator import audit_gk3_prompts, audit_gk6_assets
from prompt_engine import (
    build_consistent_prompt,
    validate_prompt,
    extract_prompt_tags,
    resolve_reference_anchor,
    format_combined_prompts_file,
    SIGNATURE_FRAME_TAIL,
)


class Test150BeatNarrativeMappingStructure(unittest.TestCase):
    """Verifies that get_matsuo_basho_150_beats() satisfies the 150-beat high-density contract."""

    def setUp(self):
        self.beats = get_matsuo_basho_150_beats()

    def test_total_beat_count_is_exactly_150(self):
        """The canonical story generator must return exactly 150 StoryBeat objects."""
        self.assertEqual(len(self.beats), 150, f"Expected 150 beats, got {len(self.beats)}")

    def test_part_distribution_is_exactly_10_per_part(self):
        """Each of the 15 parts must contain exactly 10 beats numbered 1..10."""
        part_map = {}
        for b in self.beats:
            self.assertIsInstance(b, StoryBeat)
            part_map.setdefault(b.part_index, []).append(b)

        self.assertEqual(len(part_map), 15, f"Expected 15 parts, found {len(part_map)}")
        for p in range(1, 16):
            self.assertIn(p, part_map, f"Part {p} missing from story beats")
            p_beats = part_map[p]
            self.assertEqual(len(p_beats), 10, f"Part {p} has {len(p_beats)} beats, expected 10")
            for idx, b in enumerate(p_beats, start=1):
                self.assertEqual(b.beat_index, idx, f"Part {p} beat {idx} index mismatch: {b.beat_index}")
                expected_beat_id = f"beat_P{p:02d}_B{idx:02d}.jpg"
                self.assertEqual(b.beat_id, expected_beat_id, f"Part {p} beat {idx} ID mismatch: {b.beat_id}")
                self.assertTrue(len(b.title.strip()) > 0, f"Part {p} beat {idx} has empty title")
                self.assertTrue(len(b.scene_description.strip()) >= 20, f"Part {p} beat {idx} scene too short")
                self.assertTrue(len(b.narrative_text.strip()) > 0, f"Part {p} beat {idx} has empty narrative")

    def test_one_to_one_part_settings_in_code(self):
        """Every beat in Part p must match PART_SETTINGS[p] in get_matsuo_basho_150_beats()."""
        for b in self.beats:
            expected_setting = PART_SETTINGS[b.part_index]
            self.assertEqual(
                b.setting_ref,
                expected_setting,
                f"Beat {b.beat_id} in Part {b.part_index} has setting {b.setting_ref}, expected {expected_setting}"
            )

    def test_character_life_stage_boundaries_in_code(self):
        """
        Verify character life-stage assignments in get_matsuo_basho_150_beats():
        - Parts 01-02: ref_character_basho_young
        - Parts 03-04: ref_character_basho_elder
        - Parts 05-11: ref_character_basho_traveler (with ref_character_sora at P06_B04)
        - Parts 12-15: ref_character_basho_elder
        """
        for b in self.beats:
            p = b.part_index
            b_idx = b.beat_index
            char = b.character_ref
            if p in (1, 2):
                self.assertEqual(char, "ref_character_basho_young", f"{b.beat_id} expected young, got {char}")
            elif p in (3, 4):
                self.assertEqual(char, "ref_character_basho_elder", f"{b.beat_id} expected elder, got {char}")
            elif 5 <= p <= 11:
                if p == 6 and b_idx == 4:
                    self.assertEqual(char, "ref_character_sora", f"{b.beat_id} expected sora, got {char}")
                else:
                    self.assertEqual(char, "ref_character_basho_traveler", f"{b.beat_id} expected traveler, got {char}")
            elif 12 <= p <= 15:
                self.assertEqual(char, "ref_character_basho_elder", f"{b.beat_id} expected elder, got {char}")
            else:
                self.fail(f"Invalid part index {p}")


class TestCombinedImagePromptsFileValidation(unittest.TestCase):
    """Stress-tests the exported combined_imageprompts.txt in both 00.codebases and hsnooze.gflow."""

    @classmethod
    def setUpClass(cls):
        cls.codebase_prompts_path = REPO_ROOT / "00.codebases" / "combined_imageprompts.txt"
        cls.gflow_prompts_path = REPO_ROOT / "hsnooze.gflow" / "combined_imageprompts.txt"
        cls.beat_pattern = re.compile(r"^beat_P(\d{2})_B(\d{2})\.jpg\s*:\s*(.*)$")

    def test_prompt_files_exist_and_match_byte_for_byte(self):
        """00.codebases and hsnooze.gflow prompt files must exist and have 100% byte parity."""
        self.assertTrue(self.codebase_prompts_path.exists(), "00.codebases/combined_imageprompts.txt missing")
        self.assertTrue(self.gflow_prompts_path.exists(), "hsnooze.gflow/combined_imageprompts.txt missing")
        self.assertEqual(
            self.codebase_prompts_path.read_bytes(),
            self.gflow_prompts_path.read_bytes(),
            "00.codebases and hsnooze.gflow combined_imageprompts.txt differ!"
        )

    def test_combined_file_contains_exactly_150_prompts(self):
        """combined_imageprompts.txt must contain exactly 150 prompt lines."""
        content = self.codebase_prompts_path.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        self.assertEqual(len(lines), 150, f"Expected 150 prompt lines, got {len(lines)}")

    def test_1_to_1_part_settings_in_combined_prompts(self):
        """Every prompt line in Part p must reference PART_SETTINGS[p] via [SETTING: ...]."""
        content = self.codebase_prompts_path.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        for line in lines:
            m = self.beat_pattern.match(line)
            self.assertIsNotNone(m, f"Line does not match beat pattern: {line[:60]}")
            p = int(m.group(1))
            b = int(m.group(2))
            prompt_text = m.group(3)
            expected_setting = PART_SETTINGS[p]

            tags = extract_prompt_tags(prompt_text)
            self.assertIn("SETTING", tags, f"Part {p} Beat {b} missing SETTING tag")
            self.assertEqual(len(tags["SETTING"]), 1, f"Part {p} Beat {b} must have exactly 1 SETTING tag")
            setting_tag = tags["SETTING"][0]
            self.assertEqual(
                setting_tag,
                expected_setting,
                f"Part {p:02d} Beat {b:02d} setting {setting_tag} does not match 1:1 setting {expected_setting}"
            )

    def test_character_life_stage_boundaries_in_combined_prompts(self):
        """
        Verify strict character life-stage transitions in combined_imageprompts.txt:
        - P01-02 (20 beats): ref_character_basho_young
        - P03-04 (20 beats): ref_character_basho_elder
        - P05-11 (70 beats): ref_character_basho_traveler (P06_B04 has ref_character_sora)
        - P12-15 (40 beats): ref_character_basho_elder
        """
        content = self.codebase_prompts_path.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        for line in lines:
            m = self.beat_pattern.match(line)
            p = int(m.group(1))
            b = int(m.group(2))
            prompt_text = m.group(3)

            tags = extract_prompt_tags(prompt_text)
            self.assertIn("CHARACTER", tags, f"Part {p} Beat {b} missing CHARACTER tag")
            self.assertEqual(len(tags["CHARACTER"]), 1, f"Part {p} Beat {b} must have exactly 1 CHARACTER tag")
            char_tag = tags["CHARACTER"][0]

            if p in (1, 2):
                self.assertEqual(char_tag, "ref_character_basho_young", f"Part {p} Beat {b} expected young")
            elif p in (3, 4):
                self.assertEqual(char_tag, "ref_character_basho_elder", f"Part {p} Beat {b} expected elder")
            elif 5 <= p <= 11:
                if p == 6 and b == 4:
                    self.assertEqual(char_tag, "ref_character_sora", f"Part {p} Beat {b} expected sora")
                else:
                    self.assertEqual(char_tag, "ref_character_basho_traveler", f"Part {p} Beat {b} expected traveler")
            elif 12 <= p <= 15:
                self.assertEqual(char_tag, "ref_character_basho_elder", f"Part {p} Beat {b} expected elder")

    def test_all_150_prompts_pass_strict_validation(self):
        """Every single prompt in combined_imageprompts.txt passes validate_prompt with <=1500 chars."""
        content = self.codebase_prompts_path.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        max_len = 0
        longest_beat = ""
        for line in lines:
            m = self.beat_pattern.match(line)
            beat_id = f"beat_P{m.group(1)}_B{m.group(2)}.jpg"
            val = validate_prompt(line)
            self.assertTrue(val["is_valid"], f"Prompt {beat_id} invalid: {val.get('issues')}")
            self.assertEqual(val.get("issues"), [], f"Prompt {beat_id} has issues: {val.get('issues')}")
            self.assertLessEqual(val["length"], 1500, f"Prompt {beat_id} exceeds 1500 chars ({val['length']})")
            if val["length"] > max_len:
                max_len = val["length"]
                longest_beat = beat_id

        # Assert longest prompt is safely below 1500 chars
        self.assertLessEqual(max_len, 1500)
        self.assertGreater(max_len, 500)


class TestGatekeeperGK3BoundaryConditions(unittest.TestCase):
    """
    Stress-tests Gatekeeper GK3 (audit_gk3_prompts) against exact boundary conditions:
    - 149 beats (must fail)
    - 150 beats (must pass)
    - 151 beats (must pass)
    - 160 beats (must pass)
    - 161 beats (must fail)
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="challenger_gk3_")
        self.preprod = Path(self.test_dir) / "01. Pre-Production"
        self.preprod.mkdir(parents=True)
        self.prompts_path = self.preprod / "combined_imageprompts.txt"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_prompts_file(self, distribution: dict) -> int:
        prompts = {}
        for p, count in distribution.items():
            for b in range(1, count + 1):
                bid = f"beat_P{p:02d}_B{b:02d}.jpg"
                prompts[bid] = build_consistent_prompt(
                    scene_description=f"Basho meditating along quiet pine road Part {p} Beat {b}",
                    character_name="matsuo_basho",
                    character_ref="ref_character_basho_traveler",
                    setting_ref="ref_setting_nikko_cedars",
                    prop_ref="ref_props_travel_gear"
                )
        self.prompts_path.write_text(format_combined_prompts_file(prompts), encoding="utf-8")
        return len(prompts)

    def test_gk3_boundary_149_beats_must_fail(self):
        """149 beats: 14 parts have 10 beats, Part 15 has 9 beats. Must fail GK3."""
        dist = {p: 10 for p in range(1, 15)}
        dist[15] = 9
        total = self._create_prompts_file(dist)
        self.assertEqual(total, 149)

        res = audit_gk3_prompts(self.test_dir)
        self.assertFalse(res["passed_gk3"], "GK3 should fail on 149 beats")
        self.assertEqual(res["total_count"], 149)
        self.assertIn(15, res["deficient_parts"])
        self.assertTrue(any("outside required range" in d for d in res["details"]))

    def test_gk3_boundary_150_beats_must_pass(self):
        """150 beats: exactly 10 beats per part for 15 parts. Must pass GK3."""
        dist = {p: 10 for p in range(1, 16)}
        total = self._create_prompts_file(dist)
        self.assertEqual(total, 150)

        res = audit_gk3_prompts(self.test_dir)
        self.assertTrue(res["passed_gk3"], f"GK3 should pass on 150 beats: {res['details']}")
        self.assertEqual(res["total_count"], 150)
        self.assertEqual(len(res["deficient_parts"]), 0)
        self.assertEqual(len(res["details"]), 0)

    def test_gk3_boundary_151_beats_must_pass(self):
        """151 beats: Part 01 has 11 beats, Parts 02-15 have 10 beats (150 <= 151 <= 160). Must pass GK3."""
        dist = {p: 10 for p in range(1, 16)}
        dist[1] = 11
        total = self._create_prompts_file(dist)
        self.assertEqual(total, 151)

        res = audit_gk3_prompts(self.test_dir)
        self.assertTrue(res["passed_gk3"], f"GK3 should pass on 151 beats: {res['details']}")
        self.assertEqual(res["total_count"], 151)
        self.assertEqual(len(res["deficient_parts"]), 0)

    def test_gk3_boundary_160_beats_must_pass(self):
        """160 beats: Parts 01-10 have 11 beats, Parts 11-15 have 10 beats (upper limit 160). Must pass GK3."""
        dist = {p: 11 if p <= 10 else 10 for p in range(1, 16)}
        total = self._create_prompts_file(dist)
        self.assertEqual(total, 160)

        res = audit_gk3_prompts(self.test_dir)
        self.assertTrue(res["passed_gk3"], f"GK3 should pass on 160 beats: {res['details']}")
        self.assertEqual(res["total_count"], 160)
        self.assertEqual(len(res["deficient_parts"]), 0)

    def test_gk3_boundary_161_beats_must_fail(self):
        """161 beats: Parts 01-11 have 11 beats, Parts 12-15 have 10 beats (exceeds 160 max). Must fail GK3."""
        dist = {p: 11 if p <= 11 else 10 for p in range(1, 16)}
        total = self._create_prompts_file(dist)
        self.assertEqual(total, 161)

        res = audit_gk3_prompts(self.test_dir)
        self.assertFalse(res["passed_gk3"], "GK3 should fail on 161 beats")
        self.assertEqual(res["total_count"], 161)
        self.assertTrue(any("outside required range [150, 160]" in d for d in res["details"]))


class TestGatekeeperGK6BoundaryConditionsAndDivergence(unittest.TestCase):
    """
    Stress-tests Gatekeeper GK6 (audit_gk6_assets) against boundary conditions:
    - 149 keyframes (must fail)
    - 150 keyframes (must pass)
    - 151 keyframes (must pass)
    - 161 keyframes: Empirical finding on whether GK6 enforces upper bound.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="challenger_gk6_")
        self.audio_dir = Path(self.test_dir) / "02. Media Generation" / "audio"
        self.keyframes_dir = Path(self.test_dir) / "02. Media Generation" / "keyframes"
        self.audio_dir.mkdir(parents=True)
        self.keyframes_dir.mkdir(parents=True)

        for p in range(1, 16):
            (self.audio_dir / f"Part_{p:02d}.wav").write_bytes(b"RIFF" + bytes(1000))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_keyframes(self, distribution: dict) -> int:
        count = 0
        fake_jpg = b"\xff\xd8\xff\xe0" + bytes(50)
        for p, num in distribution.items():
            for b in range(1, num + 1):
                (self.keyframes_dir / f"beat_P{p:02d}_B{b:02d}.jpg").write_bytes(fake_jpg)
                count += 1
        return count

    def test_gk6_boundary_149_keyframes_must_fail(self):
        """149 keyframes: 14 parts have 10 keyframes, Part 15 has 9 keyframes. Must fail GK6."""
        dist = {p: 10 for p in range(1, 15)}
        dist[15] = 9
        total = self._create_keyframes(dist)
        self.assertEqual(total, 149)

        res = audit_gk6_assets(self.test_dir)
        self.assertFalse(res["passed_gk6"], "GK6 should fail on 149 keyframes")
        self.assertEqual(res["image_count"], 149)
        self.assertIn(15, res["deficient_parts"])
        self.assertTrue(any("Expected at least 150 images" in d for d in res["details"]))

    def test_gk6_boundary_150_keyframes_must_pass(self):
        """150 keyframes: exactly 10 keyframes per part for 15 parts. Must pass GK6."""
        dist = {p: 10 for p in range(1, 16)}
        total = self._create_keyframes(dist)
        self.assertEqual(total, 150)

        res = audit_gk6_assets(self.test_dir)
        self.assertTrue(res["passed_gk6"], f"GK6 should pass on 150 keyframes: {res['details']}")
        self.assertEqual(res["image_count"], 150)
        self.assertEqual(len(res["deficient_parts"]), 0)
        self.assertEqual(len(res["details"]), 0)

    def test_gk6_boundary_151_keyframes_must_pass(self):
        """151 keyframes: Part 01 has 11 keyframes, Parts 02-15 have 10 keyframes. Must pass GK6."""
        dist = {p: 10 for p in range(1, 16)}
        dist[1] = 11
        total = self._create_keyframes(dist)
        self.assertEqual(total, 151)

        res = audit_gk6_assets(self.test_dir)
        self.assertTrue(res["passed_gk6"], f"GK6 should pass on 151 keyframes: {res['details']}")
        self.assertEqual(res["image_count"], 151)
        self.assertEqual(len(res["deficient_parts"]), 0)

    def test_gk6_boundary_161_keyframes_behavior_analysis(self):
        """
        Adversarial evaluation: Does GK6 fail on 161 keyframes?
        Finding: In the current implementation of audit_gk6_assets(), GK6 only validates
        'has_min_images = (len(img_files) >= min_beats)'. It does NOT enforce EXPECTED_MAX_BEATS (160).
        Thus, GK6 passes on 161 keyframes while GK3 fails on 161 prompts.
        This test asserts the empirical reality of the codebase.
        """
        dist = {p: 11 if p <= 11 else 10 for p in range(1, 16)}
        total = self._create_keyframes(dist)
        self.assertEqual(total, 161)

        res = audit_gk6_assets(self.test_dir)
        # GK6 currently passes because line 221 only checks >= min_beats (150)
        self.assertTrue(res["passed_gk6"], "Empirical observation: GK6 has no upper bound check and passes >=150")
        self.assertEqual(res["image_count"], 161)


class TestDualTreeMirrorParity(unittest.TestCase):
    """Verifies dual-tree mirror parity across all relevant files."""

    def test_prompt_engine_parity(self):
        f1 = REPO_ROOT / "hsnooze.scripting" / "prompt_engine.py"
        f2 = REPO_ROOT / "00.codebases" / "prompt_engine.py"
        self.assertEqual(f1.read_bytes(), f2.read_bytes())

    def test_online_script_producer_parity(self):
        f1 = REPO_ROOT / "hsnooze.scripting" / "online_script_producer.py"
        f2 = REPO_ROOT / "00.codebases" / "online_script_producer.py"
        self.assertEqual(f1.read_bytes(), f2.read_bytes())

    def test_combined_imageprompts_parity(self):
        f1 = REPO_ROOT / "00.codebases" / "combined_imageprompts.txt"
        f2 = REPO_ROOT / "hsnooze.gflow" / "combined_imageprompts.txt"
        self.assertEqual(f1.read_bytes(), f2.read_bytes())

    def test_reference_imageprompts_parity(self):
        f1 = REPO_ROOT / "00.codebases" / "reference_imageprompts.txt"
        f2 = REPO_ROOT / "hsnooze.gflow" / "reference_imageprompts.txt"
        self.assertEqual(f1.read_bytes(), f2.read_bytes())


if __name__ == "__main__":
    unittest.main()
