"""
Unit Test Suite for Milestone 1 Visual Consistency Architecture:
- Reference Anchor Kit Registry (characters, settings, props, ingredients)
- Bracketed Reference Tag Construction, Canonical Ordering, Extraction, and Stripping
- Modernized validate_prompt Rules and Rich Metadata
- Dual-file Parity between hsnooze.scripting and 00.codebases
"""

import os
import sys
import unittest
from pathlib import Path

# Add hsnooze.scripting to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hsnooze.scripting"))

from prompt_engine import (
    MASTER_REFERENCE_ANCHORS,
    CULTURAL_ANCHORS,
    SIGNATURE_FRAME_TAIL,
    FORBIDDEN_TERMS,
    VALID_TAG_TYPES,
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


class TestReferenceAnchorKitRegistry(unittest.TestCase):
    """Tests for MASTER_REFERENCE_ANCHORS and anchor kit resolution."""

    def test_matsuo_basho_registry_structure(self):
        self.assertIn("matsuo_basho", MASTER_REFERENCE_ANCHORS)
        kit = MASTER_REFERENCE_ANCHORS["matsuo_basho"]
        for cat in ["characters", "settings", "props", "ingredients"]:
            self.assertIn(cat, kit)

    def test_matsuo_basho_characters(self):
        chars = MASTER_REFERENCE_ANCHORS["matsuo_basho"]["characters"]
        self.assertEqual(len(chars), 5)
        expected_chars = [
            "ref_character_basho_young",
            "ref_character_basho_traveler",
            "ref_character_basho_elder",
            "ref_character_sora",
            "ref_character_buccho",
        ]
        for c in expected_chars:
            self.assertIn(c, chars)
            data = chars[c]
            self.assertEqual(data["tag_type"], "CHARACTER")
            self.assertEqual(data["file_name"], f"{c}.jpg")
            self.assertTrue(len(data["description"]) > 50)

    def test_matsuo_basho_settings(self):
        settings = MASTER_REFERENCE_ANCHORS["matsuo_basho"]["settings"]
        self.assertEqual(len(settings), 15)
        expected_settings = [
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
        for s in expected_settings:
            self.assertIn(s, settings)
            data = settings[s]
            self.assertEqual(data["tag_type"], "SETTING")
            self.assertEqual(data["file_name"], f"{s}.jpg")

    def test_matsuo_basho_props(self):
        props = MASTER_REFERENCE_ANCHORS["matsuo_basho"]["props"]
        self.assertEqual(len(props), 5)
        expected_props = [
            "ref_props_inkstone_brush",
            "ref_props_travel_gear",
            "ref_props_basho_leaves",
            "ref_props_tea_hearth_irori",
            "ref_props_travel_oi",
        ]
        for p in expected_props:
            self.assertIn(p, props)
            data = props[p]
            self.assertEqual(data["tag_type"], "PROP")
            self.assertEqual(data["file_name"], f"{p}.jpg")

    def test_get_reference_anchor_kit_by_slug_variants(self):
        kit1 = get_reference_anchor_kit("matsuo_basho")
        kit2 = get_reference_anchor_kit("Matsuo Basho")
        kit3 = get_reference_anchor_kit("basho")
        self.assertIsNotNone(kit1)
        self.assertEqual(kit1, kit2)
        self.assertEqual(kit1, kit3)

    def test_get_reference_anchor_kit_unknown_returns_empty(self):
        kit = get_reference_anchor_kit("unknown_historical_figure_xyz")
        self.assertEqual(kit, {})

    def test_resolve_reference_anchor_exact_id(self):
        res_young = resolve_reference_anchor("CHARACTER", "ref_character_basho_young")
        self.assertIsNotNone(res_young)
        self.assertEqual(res_young["file_name"], "ref_character_basho_young.jpg")

        res_traveler = resolve_reference_anchor("CHARACTER", "ref_character_basho_traveler")
        self.assertIsNotNone(res_traveler)
        self.assertEqual(res_traveler["file_name"], "ref_character_basho_traveler.jpg")

        res_legacy = resolve_reference_anchor("CHARACTER", "ref_character_basho")
        self.assertIsNotNone(res_legacy)
        self.assertEqual(res_legacy["file_name"], "ref_character_basho_traveler.jpg")

        res_setting = resolve_reference_anchor("SETTING", "ref_setting_iga_ueno")
        self.assertIsNotNone(res_setting)
        self.assertEqual(res_setting["file_name"], "ref_setting_iga_ueno.jpg")

        res_prop = resolve_reference_anchor("PROP", "ref_props_travel_oi")
        self.assertIsNotNone(res_prop)
        self.assertEqual(res_prop["file_name"], "ref_props_travel_oi.jpg")

    def test_resolve_reference_anchor_aliases(self):
        # Basho aliases
        self.assertIsNotNone(resolve_reference_anchor("CHARACTER", "basho"))
        self.assertIsNotNone(resolve_reference_anchor("CHARACTER", "matsuo_basho"))
        self.assertIsNotNone(resolve_reference_anchor("CHARACTER", "ref_character_matsuo_basho"))
        self.assertIsNotNone(resolve_reference_anchor("CHARACTER", "protagonist"))

        # Sora aliases
        self.assertIsNotNone(resolve_reference_anchor("CHARACTER", "sora"))
        self.assertIsNotNone(resolve_reference_anchor("CHARACTER", "kawai_sora"))
        self.assertIsNotNone(resolve_reference_anchor("CHARACTER", "companion"))

        # Hermitage aliases
        self.assertIsNotNone(resolve_reference_anchor("SETTING", "fukagawa"))
        self.assertIsNotNone(resolve_reference_anchor("SETTING", "edo_hermitage"))
        self.assertIsNotNone(resolve_reference_anchor("SETTING", "basho_an"))

        # Trail aliases
        self.assertIsNotNone(resolve_reference_anchor("SETTING", "tohoku_trail"))
        self.assertIsNotNone(resolve_reference_anchor("SETTING", "mountain_pass"))
        self.assertIsNotNone(resolve_reference_anchor("SETTING", "oku_no_hosomichi"))

        # Prop aliases
        self.assertIsNotNone(resolve_reference_anchor("PROP", "inkstone_brush"))
        self.assertIsNotNone(resolve_reference_anchor("PROP", "bamboo_staff_inkstone"))
        self.assertIsNotNone(resolve_reference_anchor("PROP", "travel_gear"))

    def test_resolve_reference_anchor_cross_category_fallback(self):
        # Resolving via INGREDIENT should find setting or prop
        res = resolve_reference_anchor("INGREDIENT", "edo_hermitage")
        self.assertIsNotNone(res)
        self.assertEqual(res["file_name"], "ref_setting_fukagawa_interior.jpg")

        res_prop = resolve_reference_anchor("INGREDIENT", "bamboo_staff_inkstone")
        self.assertIsNotNone(res_prop)

    def test_resolve_reference_anchor_nonexistent(self):
        res = resolve_reference_anchor("CHARACTER", "non_existent_character")
        self.assertIsNone(res)

    def test_generate_reference_prompts_count_and_format(self):
        prompts = generate_reference_prompts("matsuo_basho")
        self.assertEqual(len(prompts), 25)
        expected_files = [
            # 5 Characters
            "ref_character_basho_young.jpg",
            "ref_character_basho_traveler.jpg",
            "ref_character_basho_elder.jpg",
            "ref_character_sora.jpg",
            "ref_character_buccho.jpg",
            # 15 Settings
            "ref_setting_iga_ueno.jpg",
            "ref_setting_edo_nihonbashi.jpg",
            "ref_setting_fukagawa_interior.jpg",
            "ref_setting_fukagawa_exterior.jpg",
            "ref_setting_fuji_river_trail.jpg",
            "ref_setting_senju_dock.jpg",
            "ref_setting_nikko_cedars.jpg",
            "ref_setting_yamadera_temple.jpg",
            "ref_setting_mogami_river.jpg",
            "ref_setting_kisakata_lagoon.jpg",
            "ref_setting_shirakawa_barrier.jpg",
            "ref_setting_genjuan_bamboo.jpg",
            "ref_setting_kyoto_rakushisha.jpg",
            "ref_setting_tokaido_highway.jpg",
            "ref_setting_withered_moor.jpg",
            # 5 Props
            "ref_props_inkstone_brush.jpg",
            "ref_props_travel_gear.jpg",
            "ref_props_basho_leaves.jpg",
            "ref_props_tea_hearth_irori.jpg",
            "ref_props_travel_oi.jpg",
        ]
        for fname in expected_files:
            self.assertIn(fname, prompts)
            prompt_str = prompts[fname]
            self.assertIn("full-bleed edge-to-edge painting", prompt_str)
            self.assertIn("illuminated manuscript", prompt_str)
            self.assertIn("seventeenth-century Edo-period Japan", prompt_str)

    def test_format_reference_prompts_file_structure(self):
        formatted = format_reference_prompts_file("matsuo_basho")
        lines = [line for line in formatted.split("\n") if line.strip()]
        self.assertEqual(len(lines), 25)
        for line in lines:
            self.assertTrue(line.startswith("ref_"))
            self.assertIn(".jpg: ", line)


class TestPromptTaggingAndConstruction(unittest.TestCase):
    """Tests for bracket tag formatting, header building, extraction, and stripping."""

    def test_format_bracket_tag(self):
        self.assertEqual(
            format_bracket_tag("CHARACTER", "ref_character_basho"),
            "[CHARACTER: ref_character_basho]",
        )
        self.assertEqual(
            format_bracket_tag("  setting  ", "  edo_hermitage  "),
            "[SETTING: edo_hermitage]",
        )
        self.assertEqual(
            format_bracket_tag("prop", "bamboo_staff"),
            "[PROP: bamboo_staff]",
        )
        self.assertEqual(
            format_bracket_tag("ingredient", "tea_bowl"),
            "[INGREDIENT: tea_bowl]",
        )

    def test_build_tag_header_single_tags(self):
        header = build_tag_header(character_ref="ref_character_basho")
        self.assertEqual(header, "[CHARACTER: ref_character_basho]")

        header_setting = build_tag_header(setting_ref="edo_hermitage")
        self.assertEqual(header_setting, "[SETTING: edo_hermitage]")

    def test_build_tag_header_canonical_ordering(self):
        # Must always be CHARACTER -> SETTING -> PROP -> INGREDIENT
        header = build_tag_header(
            ingredient_ref="tea_bowl",
            prop_ref="bamboo_staff",
            setting_ref="edo_hermitage",
            character_ref="ref_character_basho",
        )
        expected = (
            "[CHARACTER: ref_character_basho] [SETTING: edo_hermitage] "
            "[PROP: bamboo_staff] [INGREDIENT: tea_bowl]"
        )
        self.assertEqual(header, expected)

    def test_build_tag_header_multiple_per_type(self):
        header = build_tag_header(
            character_ref=["basho", "sora"],
            prop_ref=["inkstone", "staff"],
        )
        expected = "[CHARACTER: basho] [CHARACTER: sora] [PROP: inkstone] [PROP: staff]"
        self.assertEqual(header, expected)

    def test_build_tag_header_from_tags_dict(self):
        tags_dict = {
            "prop": "bamboo_staff",
            "character": "basho",
            "setting": "hermitage",
        }
        header = build_tag_header(tags=tags_dict)
        expected = "[CHARACTER: basho] [SETTING: hermitage] [PROP: bamboo_staff]"
        self.assertEqual(header, expected)

    def test_extract_prompt_tags(self):
        prompt = (
            "[CHARACTER: ref_character_basho] [SETTING: edo_hermitage] "
            "[PROP: inkstone] [INGREDIENT: tea_leaves] Basho sipping tea."
        )
        tags = extract_prompt_tags(prompt)
        self.assertEqual(tags["CHARACTER"], ["ref_character_basho"])
        self.assertEqual(tags["SETTING"], ["edo_hermitage"])
        self.assertEqual(tags["PROP"], ["inkstone"])
        self.assertEqual(tags["INGREDIENT"], ["tea_leaves"])

    def test_extract_prompt_tags_case_insensitive(self):
        prompt = "[character: basho] [setting: mountain_pass] Climbing the pass."
        tags = extract_prompt_tags(prompt)
        self.assertEqual(tags["CHARACTER"], ["basho"])
        self.assertEqual(tags["SETTING"], ["mountain_pass"])

    def test_strip_prompt_tags(self):
        prompt = (
            "[CHARACTER: ref_character_basho] [SETTING: edo_hermitage] "
            "Matsuo Basho contemplating at his writing desk."
        )
        stripped = strip_prompt_tags(prompt)
        self.assertEqual(stripped, "Matsuo Basho contemplating at his writing desk.")

    def test_strip_prompt_tags_no_tags_intact(self):
        prompt = "Matsuo Basho contemplating at his writing desk."
        stripped = strip_prompt_tags(prompt)
        self.assertEqual(stripped, prompt)

    def test_build_consistent_prompt_backward_compatible_no_tags(self):
        prompt = build_consistent_prompt("A peaceful Zen garden", "matsuo_basho")
        self.assertFalse(prompt.startswith("["))
        self.assertIn("A peaceful Zen garden", prompt)
        self.assertIn("seventeenth-century Edo-period Japan", prompt)
        self.assertIn(SIGNATURE_FRAME_TAIL, prompt)

    def test_build_consistent_prompt_with_tags_prepended(self):
        prompt = build_consistent_prompt(
            "Basho writing a verse by the hearth",
            "matsuo_basho",
            character_ref="ref_character_basho",
            setting_ref="ref_setting_fukagawa_interior",
            prop_ref="ref_props_inkstone_brush",
        )
        self.assertTrue(
            prompt.startswith(
                "[CHARACTER: ref_character_basho] "
                "[SETTING: ref_setting_fukagawa_interior] "
                "[PROP: ref_props_inkstone_brush]"
            )
        )
        self.assertIn("Basho writing a verse by the hearth", prompt)
        self.assertIn("illuminated manuscript", prompt)

    def test_format_combined_prompts_file(self):
        prompts = {
            "beat_P01_B01": "[CHARACTER: basho] Scene 1",
            "beat_P01_B02.jpg": "[SETTING: hermitage] Scene 2",
        }
        formatted = format_combined_prompts_file(prompts)
        self.assertIn("beat_P01_B01.jpg: [CHARACTER: basho] Scene 1", formatted)
        self.assertIn("beat_P01_B02.jpg: [SETTING: hermitage] Scene 2", formatted)
        self.assertIn("\n\n", formatted)


class TestValidatePrompt(unittest.TestCase):
    """Tests for validate_prompt rules, bracket validation, length enforcement, and metadata."""

    def test_valid_tagged_prompt(self):
        prompt = (
            "beat_P01_B01.jpg: [CHARACTER: ref_character_basho] [SETTING: edo_hermitage] "
            "A serene morning at the hermitage, seventeenth-century Edo-period Japan, "
            "authentic traditional Japanese timber architecture, late-15th-century illuminated manuscript "
            "style painting fused with Japanese Edo gold-leaf screen aesthetics, tempera and shell-gold accents, "
            "strictly authentic feudal Japanese architecture, no European castle battlements, "
            "full-bleed edge-to-edge painting extending to all four edges of the 16:9 canvas, "
            "zero margins, no outer paper, no parchment border, no decorative frame, no page border, "
            "wide cinematic 16:9 composition, ultra-high-resolution (4K)"
        )
        res = validate_prompt(prompt)
        self.assertTrue(res["is_valid"], f"Validation failed with issues: {res['issues']}")
        self.assertEqual(len(res["issues"]), 0)
        self.assertEqual(res["tags"]["CHARACTER"], ["ref_character_basho"])
        self.assertEqual(res["tags"]["SETTING"], ["edo_hermitage"])
        self.assertTrue(res["length"] <= 1500)

    def test_valid_untagged_prompt(self):
        prompt = build_consistent_prompt("A peaceful Zen garden with mossy stones", "matsuo_basho")
        res = validate_prompt(prompt)
        self.assertTrue(res["is_valid"], f"Validation failed with issues: {res['issues']}")

    def test_rejects_newlines(self):
        prompt = build_consistent_prompt("Line one", "matsuo_basho") + "\nLine two"
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("newline" in i.lower() for i in res["issues"]))

    def test_rejects_carriage_return(self):
        prompt = build_consistent_prompt("Line one", "matsuo_basho") + "\rLine two"
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("newline" in i.lower() for i in res["issues"]))

    def test_rejects_gif_format(self):
        prompt = build_consistent_prompt("Scene", "matsuo_basho") + " output.gif"
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any(".gif" in i for i in res["issues"]))

    def test_rejects_missing_full_bleed_phrase(self):
        prompt = "A serene painting, late-15th-century illuminated manuscript style, Edo Japan"
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("full-bleed" in i for i in res["issues"]))

    def test_rejects_missing_illuminated_manuscript_phrase(self):
        prompt = (
            "A serene painting in full-bleed edge-to-edge painting extending to all four edges of the 16:9 canvas"
        )
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("illuminated manuscript" in i for i in res["issues"]))

    def test_rejects_forbidden_terms(self):
        for term in ["photorealistic", "3d render", "cgi", "octane render", "cyberpunk"]:
            prompt = build_consistent_prompt(f"A {term} view of the river", "matsuo_basho")
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Failed to reject forbidden term: {term}")
            self.assertTrue(any(term in i for i in res["issues"]))

    def test_rejects_unbalanced_brackets(self):
        prompt = "[CHARACTER: basho A serene scene, " + build_consistent_prompt("scene", "matsuo_basho")
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("unbalanced" in i.lower() for i in res["issues"]))

    def test_rejects_missing_colon_in_bracket(self):
        prompt = "[CHARACTER basho] " + build_consistent_prompt("scene", "matsuo_basho")
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("colon" in i.lower() for i in res["issues"]))

    def test_rejects_unknown_tag_type(self):
        prompt = "[VEHICLE: boat] " + build_consistent_prompt("scene", "matsuo_basho")
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("unknown reference tag type" in i.lower() for i in res["issues"]))

    def test_rejects_empty_tag_identifier(self):
        prompt = "[CHARACTER: ] " + build_consistent_prompt("scene", "matsuo_basho")
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("empty identifier" in i.lower() for i in res["issues"]))

    def test_rejects_invalid_tag_characters(self):
        prompt = "[CHARACTER: basho@123!] " + build_consistent_prompt("scene", "matsuo_basho")
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("invalid characters" in i.lower() for i in res["issues"]))

    def test_accepts_valid_tag_characters_hyphen_underscore_dot(self):
        prompt = (
            "[CHARACTER: ref_character-basho.jpg] "
            + build_consistent_prompt("scene", "matsuo_basho")
        )
        res = validate_prompt(prompt)
        self.assertTrue(res["is_valid"], f"Valid tag chars failed: {res['issues']}")

    def test_length_limit_exceeded(self):
        long_desc = "Very long description " * 60
        prompt = build_consistent_prompt(long_desc, "matsuo_basho")
        res = validate_prompt(prompt, max_length=1200)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("exceeds maximum character length" in i for i in res["issues"]))

    def test_length_excludes_beat_prefix(self):
        base_prompt = build_consistent_prompt("A tranquil scene by the riverbank", "matsuo_basho")
        tagged_beat = f"beat_P01_B01.jpg: {base_prompt}"
        res = validate_prompt(tagged_beat)
        self.assertEqual(res["length"], len(base_prompt))


class TestCodebasesMirrorParity(unittest.TestCase):
    """Tests byte-for-byte parity and symbol exports between hsnooze.scripting and 00.codebases."""

    def test_source_files_byte_parity(self):
        scripting_path = REPO_ROOT / "hsnooze.scripting" / "prompt_engine.py"
        codebases_path = REPO_ROOT / "00.codebases" / "prompt_engine.py"
        self.assertTrue(scripting_path.exists(), "hsnooze.scripting/prompt_engine.py missing")
        self.assertTrue(codebases_path.exists(), "00.codebases/prompt_engine.py missing")

        scripting_content = scripting_path.read_text(encoding="utf-8")
        codebases_content = codebases_path.read_text(encoding="utf-8")
        self.assertEqual(
            scripting_content,
            codebases_content,
            "hsnooze.scripting and 00.codebases prompt_engine.py differ!",
        )

    def test_exported_symbols_match(self):
        import importlib.util

        spec_spe = importlib.util.spec_from_file_location(
            "spe_prompt_engine",
            str(REPO_ROOT / "hsnooze.scripting" / "prompt_engine.py"),
        )
        spe = importlib.util.module_from_spec(spec_spe)
        spec_spe.loader.exec_module(spe)

        spec_cb = importlib.util.spec_from_file_location(
            "cb_prompt_engine",
            str(REPO_ROOT / "00.codebases" / "prompt_engine.py"),
        )
        cb_module = importlib.util.module_from_spec(spec_cb)
        spec_cb.loader.exec_module(cb_module)

        expected_symbols = [
            "MASTER_REFERENCE_ANCHORS",
            "CULTURAL_ANCHORS",
            "SIGNATURE_FRAME_TAIL",
            "FORBIDDEN_TERMS",
            "VALID_TAG_TYPES",
            "resolve_character_anchor",
            "get_reference_anchor_kit",
            "resolve_reference_anchor",
            "format_bracket_tag",
            "build_tag_header",
            "extract_prompt_tags",
            "strip_prompt_tags",
            "build_consistent_prompt",
            "generate_reference_prompts",
            "format_reference_prompts_file",
            "validate_prompt",
            "format_combined_prompts_file",
        ]
        for sym in expected_symbols:
            self.assertTrue(hasattr(spe, sym), f"spe missing {sym}")
            self.assertTrue(hasattr(cb_module, sym), f"cb_module missing {sym}")


class TestPreproductionReferenceAssets(unittest.TestCase):
    """Tests that the canonical pre-production reference assets exist and adhere to standards."""

    CANONICAL_FILES = [
        "ref_character_matsuo_basho.jpg",
        "ref_character_sora.jpg",
        "ref_setting_edo_hermitage.jpg",
        "ref_setting_mountain_pass.jpg",
        "ref_prop_bamboo_staff_inkstone.jpg",
    ]

    LEGACY_FILES = [
        "ref_character_basho.jpg",
        "ref_setting_fukagawa_interior.jpg",
        "ref_setting_tohoku_trail.jpg",
        "ref_props_inkstone_brush.jpg",
    ]

    def test_local_attachments_cache_exists(self):
        default_ref = Path.home() / ".workspace-mcp" / "attachments" / "references"
        if not default_ref.exists():
            default_ref = REPO_ROOT / "02. Media Generation" / "references"
        cache_dir = Path(os.environ.get("HSNOOZE_ATTACHMENTS_REF_DIR", str(default_ref)))
        self.assertTrue(cache_dir.exists(), "attachments/references dir does not exist")
        for fname in self.CANONICAL_FILES:
            fpath = cache_dir / fname
            self.assertTrue(fpath.exists(), f"Missing canonical file: {fname}")
            size = fpath.stat().st_size
            self.assertGreaterEqual(size, 50000, f"File {fname} too small: {size} bytes")

        for fname in self.LEGACY_FILES:
            fpath = cache_dir / fname
            self.assertTrue(fpath.exists(), f"Missing legacy file: {fname}")

    def test_gflow_references_cache_exists(self):
        gflow_dir = REPO_ROOT / "hsnooze.gflow" / "references"
        self.assertTrue(gflow_dir.exists(), "hsnooze.gflow/references dir does not exist")
        for fname in self.CANONICAL_FILES:
            fpath = gflow_dir / fname
            self.assertTrue(fpath.exists(), f"Missing canonical gflow file: {fname}")
            size = fpath.stat().st_size
            self.assertGreaterEqual(size, 50000, f"File {fname} too small: {size} bytes")


if __name__ == "__main__":
    unittest.main()
