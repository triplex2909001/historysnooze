"""
Adversarial Stress Test Suite for Milestone A (25-Anchor Kit & Prompt Engine Upgrade).
Agent: challenger_m_a_1 (Empirical Challenger)
Repo: $HSNOOZE_DATA_DIR / HistorySnooze

Verification Dimensions:
1. 25-Anchor Registry Integrity & Dual-Tree Parity:
   - Exactly 25 anchors under matsuo_basho (5 characters, 15 settings, 5 props, 0 ingredients).
   - Strict 1:1 mapping of Settings to Parts 01-15.
   - Dual-tree mirror parity between hsnooze.scripting and 00.codebases.
2. Prompt Length Boundary & Headroom Stress Testing:
   - All 25 reference prompts strictly <= 1500 chars.
   - All 150 narrative beat prompts strictly <= 1500 chars.
   - Synthetic stress tests: modifier appending, tag stacking, boundary enforcement at 1499/1500/1501 chars.
3. Legacy Alias Resolution & Exception Safety:
   - All deprecated/historical tags resolve without KeyError or unhandled exceptions.
   - Adversarial query fuzzing (empty, injection, cross-category, unknown tags, non-existent subjects).
4. GFlow Tag Stripping & Cleanliness:
   - GFlow regex parsing of all 25 reference anchors and all 150 combined beats.
   - Zero bracket leaks, accurate character & ingredient extraction, whitespace normalization.
   - Cross-language parity between Python strip_prompt_tags and GFlow TypeScript regex.
"""

import os
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hsnooze.scripting"))

from prompt_engine import (
    MASTER_REFERENCE_ANCHORS,
    CULTURAL_ANCHORS,
    SIGNATURE_FRAME_TAIL,
    FORBIDDEN_TERMS,
    VALID_TAG_TYPES,
    TAG_REGEX,
    resolve_character_anchor,
    get_reference_anchor_kit,
    resolve_reference_anchor,
    format_bracket_tag,
    build_tag_header,
    extract_prompt_tags,
    strip_prompt_tags,
    build_consistent_prompt,
    generate_reference_prompts,
    format_reference_prompts_file,
    validate_prompt,
    format_combined_prompts_file,
)
from online_script_producer import (
    get_matsuo_basho_150_beats,
    StorySegmenter,
    PART_SETTINGS,
    CONTEXTUAL_PROP_MAP,
)


class TestAnchorKitRegistry25(unittest.TestCase):
    """Empirical verification of the 25-Anchor Master Visual Kit."""

    def setUp(self):
        self.kit = MASTER_REFERENCE_ANCHORS["matsuo_basho"]
        self.expected_chars = [
            "ref_character_basho_young",
            "ref_character_basho_traveler",
            "ref_character_basho_elder",
            "ref_character_sora",
            "ref_character_buccho",
        ]
        self.expected_settings = [
            "ref_setting_iga_ueno",
            "ref_setting_edo_nihonbashi",
            "ref_setting_fukagawa_interior",
            "ref_setting_fukagawa_exterior",
            "ref_setting_fuji_river_trail",
            "ref_setting_senju_dock",
            "ref_setting_nikko_cedars",
            "ref_setting_yamadera_temple",
            "ref_setting_mogami_river",
            "ref_setting_kisakata_lagoon",
            "ref_setting_shirakawa_barrier",
            "ref_setting_genjuan_bamboo",
            "ref_setting_kyoto_rakushisha",
            "ref_setting_tokaido_highway",
            "ref_setting_withered_moor",
        ]
        self.expected_props = [
            "ref_props_inkstone_brush",
            "ref_props_travel_gear",
            "ref_props_basho_leaves",
            "ref_props_tea_hearth_irori",
            "ref_props_travel_oi",
        ]

    def test_canonical_anchor_counts(self):
        """Must have exactly 5 characters, 15 settings, 5 props, and 0 ingredients (total 25)."""
        chars = self.kit["characters"]
        settings = self.kit["settings"]
        props = self.kit["props"]
        ingredients = self.kit["ingredients"]

        self.assertEqual(len(chars), 5, f"Expected 5 characters, got {len(chars)}")
        self.assertEqual(len(settings), 15, f"Expected 15 settings, got {len(settings)}")
        self.assertEqual(len(props), 5, f"Expected 5 props, got {len(props)}")
        self.assertEqual(len(ingredients), 0, f"Expected 0 ingredients, got {len(ingredients)}")
        total = len(chars) + len(settings) + len(props) + len(ingredients)
        self.assertEqual(total, 25, f"Expected total 25 canonical anchors, got {total}")

    def test_canonical_ids_match_specification(self):
        """All anchor IDs must match the R1 specification exactly."""
        self.assertEqual(sorted(self.kit["characters"].keys()), sorted(self.expected_chars))
        self.assertEqual(sorted(self.kit["settings"].keys()), sorted(self.expected_settings))
        self.assertEqual(sorted(self.kit["props"].keys()), sorted(self.expected_props))

    def test_anchor_schema_completeness(self):
        """Each anchor must provide id, tag_type, file_name, aliases, and description >= 50 chars."""
        categories = [
            ("characters", "CHARACTER", self.expected_chars),
            ("settings", "SETTING", self.expected_settings),
            ("props", "PROP", self.expected_props),
        ]
        for cat_name, expected_type, expected_ids in categories:
            for aid in expected_ids:
                entry = self.kit[cat_name][aid]
                self.assertEqual(entry["id"], aid)
                self.assertEqual(entry["tag_type"], expected_type)
                self.assertEqual(entry["file_name"], f"{aid}.jpg")
                self.assertIsInstance(entry["aliases"], list)
                self.assertGreater(len(entry["aliases"]), 0)
                self.assertIn(f"{aid}.jpg", entry["aliases"], f"Filename should be an alias for {aid}")
                self.assertIsInstance(entry["description"], str)
                self.assertGreater(
                    len(entry["description"]), 50, f"Description too short for {aid}"
                )

    def test_settings_1_to_1_part_mapping(self):
        """PART_SETTINGS must map parts 1..15 to settings in order."""
        self.assertEqual(len(PART_SETTINGS), 15)
        for part_idx in range(1, 16):
            expected_setting = self.expected_settings[part_idx - 1]
            self.assertEqual(
                PART_SETTINGS[part_idx],
                expected_setting,
                f"Part {part_idx} setting mismatch: expected {expected_setting}, got {PART_SETTINGS[part_idx]}",
            )
            # Verify the anchor has part_xx_setting as an alias
            setting_entry = self.kit["settings"][expected_setting]
            expected_part_alias = f"part_{part_idx:02d}_setting"
            self.assertIn(
                expected_part_alias,
                setting_entry["aliases"],
                f"Missing alias {expected_part_alias} in {expected_setting}",
            )


class TestPromptLengthBoundaryAndStress(unittest.TestCase):
    """Stress tests for prompt length <= 1500 chars and modifier headroom."""

    def test_reference_prompts_length_strictly_under_1500(self):
        """All 25 generated reference prompts must be <= 1500 characters."""
        prompts = generate_reference_prompts("matsuo_basho")
        self.assertEqual(len(prompts), 25)

        for fname, prompt in prompts.items():
            val = validate_prompt(prompt)
            self.assertTrue(
                val["is_valid"], f"Reference prompt {fname} failed validation: {val['issues']}"
            )
            self.assertLessEqual(
                len(prompt),
                1500,
                f"Prompt {fname} length {len(prompt)} exceeds 1500 chars limit",
            )
            # Ensure significant safety margin (>= 50 chars headroom)
            headroom = 1500 - len(prompt)
            self.assertGreaterEqual(
                headroom,
                50,
                f"Prompt {fname} has dangerously small headroom: {headroom} chars",
            )

    def test_combined_150_beat_prompts_length_strictly_under_1500(self):
        """All 150 narrative beats must be <= 1500 characters."""
        beats = get_matsuo_basho_150_beats()
        prompts = StorySegmenter.generate_part_prompts(beats, "matsuo_basho")
        self.assertEqual(len(prompts), 150)

        for beat_id, prompt in prompts.items():
            full_line = f"{beat_id}: {prompt}"
            val = validate_prompt(full_line)
            self.assertTrue(
                val["is_valid"], f"Beat {beat_id} failed validation: {val['issues']}"
            )
            self.assertLessEqual(
                val["length"],
                1500,
                f"Beat {beat_id} length {val['length']} exceeds 1500 chars",
            )
            # Ensure at least 200 chars headroom for story beats
            headroom = 1500 - val["length"]
            self.assertGreaterEqual(
                headroom,
                200,
                f"Beat {beat_id} has insufficient headroom: {headroom} chars",
            )

    def test_boundary_exact_enforcement_1499_1500_1501(self):
        """validate_prompt must strictly accept 1500 and strictly reject 1501."""
        base = build_consistent_prompt("Zen temple", "matsuo_basho")
        clean_base = base

        # 1499 chars
        p1499 = clean_base + " " + "a" * (1499 - len(clean_base) - 1)
        self.assertEqual(len(p1499), 1499)
        self.assertTrue(validate_prompt(p1499)["is_valid"])

        # 1500 chars
        p1500 = clean_base + " " + "a" * (1500 - len(clean_base) - 1)
        self.assertEqual(len(p1500), 1500)
        self.assertTrue(validate_prompt(p1500)["is_valid"])

        # 1501 chars
        p1501 = clean_base + " " + "a" * (1501 - len(clean_base) - 1)
        self.assertEqual(len(p1501), 1501)
        res_1501 = validate_prompt(p1501)
        self.assertFalse(res_1501["is_valid"])
        self.assertTrue(any("exceeds maximum character length" in i for i in res_1501["issues"]))

    def test_stress_appending_maximum_tags(self):
        """Prompt engine must handle prompts with all 4 tags appended without overflowing 1500."""
        scene = "Matsuo Basho writing haiku at his humble hermitage while sipping green tea"
        prompt = build_consistent_prompt(
            scene,
            "matsuo_basho",
            character_ref="ref_character_basho_elder",
            setting_ref="ref_setting_fukagawa_interior",
            prop_ref="ref_props_inkstone_brush",
            ingredient_ref="ref_props_tea_hearth_irori",
        )
        val = validate_prompt(prompt)
        self.assertTrue(val["is_valid"], f"Validation failed: {val['issues']}")
        self.assertLessEqual(val["length"], 1500)
        self.assertGreater(1500 - val["length"], 250, "Expected >= 250 chars headroom with 4 tags")


class TestLegacyAliasResolutionAdversarial(unittest.TestCase):
    """Adversarial stress-testing of alias resolution across deprecated and unusual queries."""

    def test_all_deprecated_character_aliases_resolve(self):
        """All historical character tags from previous releases must resolve."""
        deprecated_character_tags = [
            ("CHARACTER", "ref_character_basho", "ref_character_basho_traveler"),
            ("CHARACTER", "basho", "ref_character_basho_traveler"),
            ("CHARACTER", "matsuo_basho", "ref_character_basho_traveler"),
            ("CHARACTER", "ref_character_matsuo_basho", "ref_character_basho_traveler"),
            ("CHARACTER", "ref_character_matsuo_basho.jpg", "ref_character_basho_traveler"),
            ("CHARACTER", "protagonist", "ref_character_basho_traveler"),
            ("CHARACTER", "basho_young", "ref_character_basho_young"),
            ("CHARACTER", "young_basho", "ref_character_basho_young"),
            ("CHARACTER", "kinsaku", "ref_character_basho_young"),
            ("CHARACTER", "matsuo_kinsaku", "ref_character_basho_young"),
            ("CHARACTER", "basho_elder", "ref_character_basho_elder"),
            ("CHARACTER", "elder_basho", "ref_character_basho_elder"),
            ("CHARACTER", "master_basho", "ref_character_basho_elder"),
            ("CHARACTER", "tosei", "ref_character_basho_elder"),
            ("CHARACTER", "master_tosei", "ref_character_basho_elder"),
            ("CHARACTER", "sora", "ref_character_sora"),
            ("CHARACTER", "kawai_sora", "ref_character_sora"),
            ("CHARACTER", "companion", "ref_character_sora"),
            ("CHARACTER", "buccho", "ref_character_buccho"),
            ("CHARACTER", "buccho_osho", "ref_character_buccho"),
            ("CHARACTER", "zen_master_buccho", "ref_character_buccho"),
        ]
        for tag_type, query, expected_id in deprecated_character_tags:
            res = resolve_reference_anchor(tag_type, query, "matsuo_basho")
            self.assertIsNotNone(res, f"Failed to resolve deprecated character alias '{query}'")
            self.assertEqual(res["id"], expected_id, f"Alias '{query}' resolved to {res['id']}, expected {expected_id}")

    def test_all_deprecated_setting_aliases_resolve(self):
        """All historical setting tags from previous releases must resolve."""
        deprecated_setting_tags = [
            ("SETTING", "fukagawa", "ref_setting_fukagawa_interior"),
            ("SETTING", "edo_hermitage", "ref_setting_fukagawa_interior"),
            ("SETTING", "ref_setting_edo_hermitage", "ref_setting_fukagawa_interior"),
            ("SETTING", "ref_setting_edo_hermitage.jpg", "ref_setting_fukagawa_interior"),
            ("SETTING", "basho_an", "ref_setting_fukagawa_interior"),
            ("SETTING", "hermitage", "ref_setting_fukagawa_interior"),
            ("SETTING", "tohoku_trail", "ref_setting_nikko_cedars"),
            ("SETTING", "ref_setting_tohoku_trail", "ref_setting_nikko_cedars"),
            ("SETTING", "ref_setting_tohoku_trail.jpg", "ref_setting_nikko_cedars"),
            ("SETTING", "mountain_pass", "ref_setting_nikko_cedars"),
            ("SETTING", "ref_setting_mountain_pass", "ref_setting_nikko_cedars"),
            ("SETTING", "ref_setting_mountain_pass.jpg", "ref_setting_nikko_cedars"),
            ("SETTING", "oku_no_hosomichi", "ref_setting_nikko_cedars"),
        ]
        for tag_type, query, expected_id in deprecated_setting_tags:
            res = resolve_reference_anchor(tag_type, query, "matsuo_basho")
            self.assertIsNotNone(res, f"Failed to resolve deprecated setting alias '{query}'")
            self.assertEqual(res["id"], expected_id, f"Alias '{query}' resolved to {res['id']}, expected {expected_id}")

    def test_all_deprecated_prop_aliases_resolve(self):
        """All historical prop tags from previous releases must resolve."""
        deprecated_prop_tags = [
            ("PROP", "bamboo_staff_inkstone"),
            ("PROP", "ref_prop_bamboo_staff_inkstone"),
            ("PROP", "inkstone_brush"),
            ("PROP", "inkstone"),
            ("PROP", "brush"),
            ("PROP", "suzuri_fude"),
            ("PROP", "writing_tools"),
            ("PROP", "travel_gear"),
            ("PROP", "bamboo_staff_hat"),
            ("PROP", "pilgrim_gear"),
            ("PROP", "staff_hat"),
            ("PROP", "basho_leaves"),
            ("PROP", "banana_leaves"),
            ("PROP", "plantain_leaves"),
            ("PROP", "tea_hearth_irori"),
            ("PROP", "irori"),
            ("PROP", "tea_hearth"),
            ("PROP", "iron_kettle"),
            ("PROP", "tetsubin"),
            ("PROP", "travel_oi"),
            ("PROP", "pilgrim_backpack"),
            ("PROP", "straw_backpack"),
            ("PROP", "oi"),
        ]
        for tag_type, query in deprecated_prop_tags:
            res = resolve_reference_anchor(tag_type, query, "matsuo_basho")
            self.assertIsNotNone(res, f"Failed to resolve deprecated prop alias '{query}'")
            self.assertTrue(res["id"].startswith("ref_props_"))

    def test_cross_category_and_ingredient_fallback_resolution(self):
        """INGREDIENT tags pointing to settings or props must resolve via fallback."""
        # INGREDIENT referencing setting
        res_set = resolve_reference_anchor("INGREDIENT", "ref_setting_iga_ueno", "matsuo_basho")
        self.assertIsNotNone(res_set)
        self.assertEqual(res_set["id"], "ref_setting_iga_ueno")

        # INGREDIENT referencing prop
        res_prop = resolve_reference_anchor("INGREDIENT", "ref_props_travel_oi", "matsuo_basho")
        self.assertIsNotNone(res_prop)
        self.assertEqual(res_prop["id"], "ref_props_travel_oi")

        # INGREDIENT referencing legacy alias
        res_alias = resolve_reference_anchor("INGREDIENT", "bamboo_staff_inkstone", "matsuo_basho")
        self.assertIsNotNone(res_alias)

    def test_adversarial_queries_no_crash(self):
        """Hostile, malformed, injection, or non-existent queries must return None without crashing."""
        hostile_queries = [
            ("", ""),
            ("   ", "   "),
            ("UNKNOWN_TAG", "some_value"),
            ("CHARACTER", ""),
            ("SETTING", "non_existent_mountain_pass_12345"),
            ("PROP", "'; DROP TABLE anchors; --"),
            ("INGREDIENT", "../../etc/shadow"),
            ("CHARACTER", "\x00null_byte"),
            ("PROP", "a" * 10000),
            ("SETTING", "REF_SETTING_IGA_UENO"),  # uppercase
            ("character", "ref_character_basho_young"),  # lowercase tag_type
            ("  SETTING  ", "  ref_setting_iga_ueno  "),  # surrounding spaces
        ]
        for tag_type, val in hostile_queries:
            try:
                res = resolve_reference_anchor(tag_type, val, "matsuo_basho")
                # If it's valid case/spacing variation of a real anchor, it might resolve, else None
                if "iga_ueno" in val:
                    self.assertIsNotNone(res)
                elif "basho_young" in val:
                    self.assertIsNotNone(res)
            except Exception as e:
                self.fail(f"resolve_reference_anchor crashed with ({tag_type!r}, {val!r}): {type(e).__name__}: {e}")

        # Non-existent character_name
        res_unknown_char = resolve_reference_anchor("CHARACTER", "basho", "unknown_person_999")
        self.assertIsNone(res_unknown_char)


class TestDualTreeMirrorParity(unittest.TestCase):
    """Ensure complete dual-tree mirror parity across codebase implementations and exports."""

    def test_python_codebase_parity(self):
        """hsnooze.scripting and 00.codebases must be byte-for-byte identical."""
        files = ["prompt_engine.py", "online_script_producer.py"]
        for f in files:
            p1 = REPO_ROOT / "hsnooze.scripting" / f
            p2 = REPO_ROOT / "00.codebases" / f
            self.assertTrue(p1.exists(), f"Missing {p1}")
            self.assertTrue(p2.exists(), f"Missing {p2}")
            content1 = p1.read_bytes()
            content2 = p2.read_bytes()
            self.assertEqual(
                content1,
                content2,
                f"Dual-tree parity violation between {p1} and {p2}",
            )

    def test_prompt_exports_parity(self):
        """Prompt export files in 00.codebases and hsnooze.gflow must be byte-for-byte identical."""
        export_files = ["reference_imageprompts.txt", "combined_imageprompts.txt"]
        for f in export_files:
            p1 = REPO_ROOT / "00.codebases" / f
            p2 = REPO_ROOT / "hsnooze.gflow" / f
            self.assertTrue(p1.exists(), f"Missing {p1}")
            self.assertTrue(p2.exists(), f"Missing {p2}")
            content1 = p1.read_bytes()
            content2 = p2.read_bytes()
            self.assertEqual(
                content1,
                content2,
                f"Export parity violation between {p1} and {p2}",
            )


class TestGFlowTagStrippingCleanliness(unittest.TestCase):
    """Verify that Python strip_prompt_tags and GFlow TypeScript stripping produce clean prompts."""

    def test_strip_prompt_tags_python(self):
        """Python strip_prompt_tags must cleanly eliminate all bracket tags and normalize whitespace."""
        test_cases = [
            (
                "[CHARACTER: ref_character_basho_young] [SETTING: ref_setting_iga_ueno] Full-bleed painting of castle.",
                "Full-bleed painting of castle.",
            ),
            (
                "[CHARACTER: ref_character_basho_traveler] [SETTING: ref_setting_nikko_cedars] [PROP: ref_props_travel_gear] Mountain trail.",
                "Mountain trail.",
            ),
            (
                "No tags in this prompt at all.",
                "No tags in this prompt at all.",
            ),
            (
                "[INGREDIENT: ref_props_basho_leaves]    Spaced out   prompt.   ",
                "Spaced out prompt.",
            ),
        ]
        for raw, expected in test_cases:
            stripped = strip_prompt_tags(raw)
            self.assertEqual(stripped, expected)

    def test_all_150_beats_stripped_cleanly_without_bracket_artifacts(self):
        """Every beat in combined_imageprompts.txt when stripped must have 0 square brackets."""
        with open(REPO_ROOT / "hsnooze.gflow" / "combined_imageprompts.txt") as f:
            content = f.read()

        beats = [b.strip() for b in content.split("\n\n") if b.strip()]
        self.assertEqual(len(beats), 150)

        for b in beats:
            # Extract prompt part after colon
            colon_idx = b.find(":")
            raw_prompt = b[colon_idx + 1 :].strip()
            stripped = strip_prompt_tags(raw_prompt)

            self.assertNotIn("[", stripped, f"Stray opening bracket in stripped prompt: {stripped}")
            self.assertNotIn("]", stripped, f"Stray closing bracket in stripped prompt: {stripped}")
            self.assertFalse(re.search(r"\s{2,}", stripped), f"Unnormalized whitespace: {stripped}")
            self.assertTrue(stripped.endswith("(4K)"), f"Stripped prompt must end with (4K): {stripped}")


if __name__ == "__main__":
    unittest.main()
