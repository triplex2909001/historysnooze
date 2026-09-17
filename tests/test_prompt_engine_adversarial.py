"""
Adversarial Stress Test Suite for HistorySnooze Prompt Engine (prompt_engine.py).
Target: hsnooze.scripting/prompt_engine.py & 00.codebases/prompt_engine.py
Agent: challenger_m1_1 (Empirical Challenger)

Challenge Dimensions:
1. Malformed bracket tags:
   - Nested brackets ([[TAG: x]], [[CHARACTER: basho]], [CHARACTER: [basho]])
   - Missing colons ([CHARACTER basho], [CHARACTER], [])
   - Invalid & plural tag types ([UNKNOWN: x], [CHARACTERS: x], [:x], [123: x])
   - Unicode & special characters in tag values ([CHARACTER: 松尾芭蕉], [CHARACTER: bashō], emojis, shell injections)
   - Empty tags ([], [:], [   ], [CHARACTER:], [CHARACTER:   ])
   - Inverted and unmatched bracket boundaries (][, ] [, stray brackets)
2. Character limits and boundary conditions around 1500 characters:
   - Exact boundaries at 1499, 1500, 1501 characters
   - Beat prefix exclusion (beat_Pxx_Bxx.jpg: excluded from length count)
   - Beat prefix without extension (beat_Pxx_Bxx: counts toward length)
   - Custom max_length boundaries
3. Injection of forbidden words inside scene descriptions or tags:
   - Direct injection of forbidden terms (photorealistic, 3d render, cgi, cyberpunk, modern, anime, .gif)
   - Case-insensitive evasion attempts (PhotoRealistic, 3D RENDER, .GIF)
   - Injection inside reference tags ([CHARACTER: modern], [SETTING: cgi])
   - Word boundary nuances & evasion variants (3d-render, octane-render, postmodern)
   - Non-interference with locked SIGNATURE_FRAME_TAIL (border, frame, margins)
4. Tag extraction and stripping with weird spacing and linebreaks:
   - Whitespace collapsing, tabs, leading/trailing whitespace
   - Strict newline rejection (\\n, \\r, \\r\\n)
   - Discrepancy detection: space before colon ([CHARACTER : basho])
   - Sanitization in build_consistent_prompt
5. Codebase mirror parity & symbol verification
"""

import os
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


def _make_valid_prompt(scene_desc: str = "A peaceful Zen garden with mossy stones") -> str:
    """Helper to generate a structurally valid base prompt."""
    return build_consistent_prompt(scene_desc, "matsuo_basho")


class TestMalformedBracketTagsAdversarial(unittest.TestCase):
    """Adversarial stress-testing of bracket syntax, nesting, tag types, and characters."""

    def test_nested_brackets_double_outer(self):
        prompt = "[[TAG: x]] " + _make_valid_prompt()
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(
            any("unknown reference tag type" in i.lower() for i in res["issues"]),
            f"Expected unknown tag error, got: {res['issues']}",
        )

    def test_nested_brackets_valid_inner_name(self):
        prompt = "[[CHARACTER: basho]] " + _make_valid_prompt()
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(
            any("unknown reference tag type" in i.lower() for i in res["issues"]),
            f"Expected unknown tag error, got: {res['issues']}",
        )

    def test_nested_brackets_inside_value(self):
        prompt = "[CHARACTER: [basho]] " + _make_valid_prompt()
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(
            any("invalid characters" in i.lower() or "missing colon" in i.lower() for i in res["issues"]),
            f"Expected invalid chars or bracket error, got: {res['issues']}",
        )

    def test_nested_tags_interleaved(self):
        prompt = "[CHARACTER: basho [SETTING: edo]] " + _make_valid_prompt()
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(
            any("invalid characters" in i.lower() for i in res["issues"]),
            f"Expected invalid character error for interleaved brackets, got: {res['issues']}",
        )

    def test_missing_colons_various(self):
        cases = [
            "[CHARACTER basho]",
            "[CHARACTER]",
            "[]",
            "[   ]",
            "[SETTING edo_hermitage]",
            "[PROP staff]",
        ]
        for tag in cases:
            prompt = f"{tag} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Failed to reject missing colon tag: {tag}")
            self.assertTrue(
                any("missing colon separator" in i.lower() for i in res["issues"]),
                f"Expected missing colon issue for {tag}, got: {res['issues']}",
            )

    def test_invalid_tag_types(self):
        invalid_types = [
            "[UNKNOWN: basho]",
            "[VEHICLE: boat]",
            "[FOO: bar]",
            "[:basho]",
            "[123: basho]",
            "[@CHARACTER: basho]",
        ]
        for tag in invalid_types:
            prompt = f"{tag} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Failed to reject invalid tag type: {tag}")
            self.assertTrue(
                any("unknown reference tag type" in i.lower() for i in res["issues"]),
                f"Expected unknown tag type issue for {tag}, got: {res['issues']}",
            )

    def test_plural_tag_types_rejected_by_validator(self):
        # Even if consumer GFlow cli.ts supports plural tags, prompt_engine validate_prompt
        # strictly enforces the singular canonical names
        plurals = [
            "[CHARACTERS: basho]",
            "[SETTINGS: edo_hermitage]",
            "[PROPS: inkstone]",
            "[INGREDIENTS: tea_leaves]",
        ]
        for tag in plurals:
            prompt = f"{tag} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Plural tag should be rejected by prompt_engine: {tag}")
            self.assertTrue(
                any("unknown reference tag type" in i.lower() for i in res["issues"]),
                f"Expected unknown tag type for {tag}, got: {res['issues']}",
            )

    def test_unicode_and_non_ascii_characters_in_tag_values(self):
        unicode_tags = [
            "[CHARACTER: 松尾芭蕉]",        # Kanji
            "[CHARACTER: bashō]",           # Non-ASCII latin with macron
            "[CHARACTER: basho 🏯]",        # Emoji
            "[SETTING: 江戸_hermitage]",     # Mixed Kanji and ASCII
            "[PROP: staff_★]",             # Special Unicode symbol
        ]
        for tag in unicode_tags:
            prompt = f"{tag} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Unicode in tag identifier should be rejected: {tag}")
            self.assertTrue(
                any("invalid characters" in i.lower() for i in res["issues"]),
                f"Expected invalid characters error for {tag}, got: {res['issues']}",
            )

    def test_injection_and_forbidden_characters_in_tag_values(self):
        dangerous_tags = [
            "[CHARACTER: basho;rm -rf /]",
            "[CHARACTER: <script>alert(1)</script>]",
            "[CHARACTER: basho&sora]",
            "[CHARACTER: basho|cat]",
            "[CHARACTER: basho$HOME]",
            "[CHARACTER: basho`id`]",
            "[CHARACTER: basho*]",
            "[CHARACTER: basho?]",
        ]
        for tag in dangerous_tags:
            prompt = f"{tag} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Dangerous characters in tag should be rejected: {tag}")
            self.assertTrue(
                any("invalid characters" in i.lower() for i in res["issues"]),
                f"Expected invalid characters error for {tag}, got: {res['issues']}",
            )

    def test_empty_tags_and_identifiers(self):
        empty_cases = [
            ("[]", "missing colon separator"),
            ("[:]", "empty identifier"),
            ("[CHARACTER:]", "empty identifier"),
            ("[CHARACTER:   ]", "empty identifier"),
            ("[:   ]", "empty identifier"),
        ]
        for tag, expected_err in empty_cases:
            prompt = f"{tag} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Empty tag should be rejected: {tag}")
            self.assertTrue(
                any(expected_err in i.lower() for i in res["issues"]),
                f"Expected '{expected_err}' for {tag}, got: {res['issues']}",
            )

    def test_unbalanced_brackets_cases(self):
        cases = [
            "[CHARACTER: basho",
            "CHARACTER: basho]",
            "[CHARACTER: basho]]",
            "[[CHARACTER: basho]",
            "[CHARACTER: basho] [SETTING: edo",
            "CHARACTER: basho] [SETTING: edo]",
        ]
        for tag in cases:
            prompt = f"{tag} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Unbalanced bracket should be rejected: {tag}")
            self.assertTrue(
                any("unbalanced square brackets" in i.lower() for i in res["issues"]),
                f"Expected unbalanced bracket issue for {tag}, got: {res['issues']}",
            )

    def test_inverted_brackets_structural_limitation(self):
        """
        Adversarial Observation:
        When close and open brackets appear inverted (e.g. '][' or '] [') with equal counts,
        prompt.count('[') != prompt.count(']') evaluates to False (counts are equal).
        Because bracket_blocks = re.findall(r'\\[([^\\]]*)\\]', prompt) only matches
        valid '[' followed by ']', isolated inverted brackets without enclosed content
        produce no bracket_blocks and thus bypass both the count check and the block validator.
        """
        prompt = "][ " + _make_valid_prompt()
        res = validate_prompt(prompt)
        # Empirically documents that simple bracket counter does not detect inverted bracket order
        # when total '[' equals ']' count.
        self.assertEqual(prompt.count("["), prompt.count("]"))
        # Document current behavior: is_valid is True because count matches and re.findall finds no blocks
        self.assertTrue(res["is_valid"])


class TestCharacterLimitsAndBoundaryConditions(unittest.TestCase):
    """Adversarial testing of the 1500-character ceiling and boundary conditions."""

    def setUp(self):
        self.base_prompt = _make_valid_prompt("Tranquil morning mist over the cedar trees")
        self.prefix = "beat_P01_B01.jpg: "

    def test_exact_1499_characters_passes(self):
        needed = 1499 - len(self.base_prompt)
        prompt = self.base_prompt + ", " + "x" * (needed - 2)
        self.assertEqual(len(prompt), 1499)
        res = validate_prompt(prompt)
        self.assertTrue(res["is_valid"], f"1499 chars failed: {res['issues']}")
        self.assertEqual(res["length"], 1499)

    def test_exact_1500_characters_passes(self):
        needed = 1500 - len(self.base_prompt)
        prompt = self.base_prompt + ", " + "x" * (needed - 2)
        self.assertEqual(len(prompt), 1500)
        res = validate_prompt(prompt)
        self.assertTrue(res["is_valid"], f"1500 chars failed: {res['issues']}")
        self.assertEqual(res["length"], 1500)

    def test_exact_1501_characters_fails(self):
        needed = 1501 - len(self.base_prompt)
        prompt = self.base_prompt + ", " + "x" * (needed - 2)
        self.assertEqual(len(prompt), 1501)
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["length"], 1501)
        self.assertTrue(
            any("exceeds maximum character length of 1500 (1501 characters)" in i for i in res["issues"]),
            f"Expected 1501 overflow error, got: {res['issues']}",
        )

    def test_beat_prefix_excluded_1500_chars_passes(self):
        body = self.base_prompt + ", " + "x" * (1500 - len(self.base_prompt) - 2)
        full_line = self.prefix + body
        self.assertEqual(len(body), 1500)
        self.assertEqual(len(full_line), 1500 + len(self.prefix))
        res = validate_prompt(full_line)
        self.assertTrue(res["is_valid"], f"Prefix excluded 1500 chars failed: {res['issues']}")
        self.assertEqual(res["length"], 1500)

    def test_beat_prefix_excluded_1501_chars_fails(self):
        body = self.base_prompt + ", " + "x" * (1501 - len(self.base_prompt) - 2)
        full_line = self.prefix + body
        self.assertEqual(len(body), 1501)
        self.assertEqual(len(full_line), 1501 + len(self.prefix))
        res = validate_prompt(full_line)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["length"], 1501)
        self.assertTrue(any("exceeds maximum character length of 1500" in i for i in res["issues"]))

    def test_beat_prefix_format_variations(self):
        # Valid prefixes with various part/beat combinations
        prefixes = [
            "beat_P01_B01.jpg: ",
            "beat_P15_B10.jpg: ",
            "beat_P05_B07.jpg: ",
            "beat_P1_B1.jpg: ",
        ]
        body = self.base_prompt + ", " + "x" * (1500 - len(self.base_prompt) - 2)
        for pfx in prefixes:
            line = pfx + body
            res = validate_prompt(line)
            self.assertTrue(res["is_valid"], f"Valid prefix {pfx} failed: {res['issues']}")
            self.assertEqual(res["length"], 1500)

    def test_beat_prefix_without_extension_counts_in_length(self):
        """
        Adversarial Observation:
        Prefix regex is r'^beat_P\\d+_B\\d+\\.jpg:\\s*'.
        If a line uses 'beat_P01_B01: ' without '.jpg', the prefix is NOT stripped,
        and its characters count against the 1500-character ceiling.
        """
        bare_pfx = "beat_P01_B01: "
        body = self.base_prompt + ", " + "x" * (1495 - len(self.base_prompt) - 2)
        # body is 1495 chars, with bare_pfx (14 chars) total line is 1509 chars
        line = bare_pfx + body
        self.assertEqual(len(line), 1509)
        res = validate_prompt(line)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["length"], 1509)
        self.assertTrue(any("exceeds maximum character length" in i for i in res["issues"]))

    def test_custom_max_length_parameter(self):
        body = _make_valid_prompt()
        res_default = validate_prompt(body, max_length=1500)
        self.assertTrue(res_default["is_valid"])

        res_strict = validate_prompt(body, max_length=len(body) - 5)
        self.assertFalse(res_strict["is_valid"])
        self.assertTrue(any("exceeds maximum character length" in i for i in res_strict["issues"]))

    def test_empty_prompt_fails_phrase_checks(self):
        res = validate_prompt("")
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("full-bleed" in i for i in res["issues"]))
        self.assertTrue(any("illuminated manuscript" in i for i in res["issues"]))


class TestForbiddenWordsInjection(unittest.TestCase):
    """Adversarial stress-testing of forbidden words, evasion techniques, and tag injection."""

    def test_all_standard_forbidden_terms_rejected(self):
        banned = [
            "photorealistic",
            "3d render",
            "cgi",
            "octane render",
            "cyberpunk",
            "modern",
            "anime",
            "parchment edge",
        ]
        for term in banned:
            prompt = _make_valid_prompt(f"A serene scene with {term} visual effects")
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Failed to reject forbidden term: {term}")
            self.assertTrue(
                any(term in i.lower() for i in res["issues"]),
                f"Expected '{term}' in issues, got: {res['issues']}",
            )

    def test_forbidden_terms_case_insensitivity(self):
        cased = [
            ("PhotoRealistic", "photorealistic"),
            ("3D RENDER", "3d render"),
            ("Cgi", "cgi"),
            ("OCTANE RENDER", "octane render"),
            ("CyberPunk", "cyberpunk"),
            ("MoDeRn", "modern"),
            ("ANIME", "anime"),
            ("Parchment Edge", "parchment edge"),
        ]
        for phrase, canonical in cased:
            prompt = _make_valid_prompt(f"A serene scene with {phrase} elements")
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Failed to reject mixed-case term: {phrase}")
            self.assertTrue(
                any(canonical in i.lower() for i in res["issues"]),
                f"Expected '{canonical}' in issues for '{phrase}', got: {res['issues']}",
            )

    def test_forbidden_terms_injected_inside_tags(self):
        # A tag identifier containing a standalone forbidden term like 'modern' or 'cgi'
        cases = [
            ("[CHARACTER: modern]", "modern"),
            ("[SETTING: cgi]", "cgi"),
            ("[PROP: cyberpunk]", "cyberpunk"),
            ("[INGREDIENT: anime]", "anime"),
        ]
        for tag, term in cases:
            prompt = f"{tag} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Tag containing forbidden term should fail: {tag}")
            self.assertTrue(
                any(term in i.lower() for i in res["issues"]),
                f"Expected '{term}' issue for tag {tag}, got: {res['issues']}",
            )

    def test_word_boundary_avoids_false_positives(self):
        # Legitimate words containing substrings of forbidden terms should pass
        # e.g., 'postmodern' shouldn't trigger 'modern', 'animation' shouldn't trigger 'anime'
        legit_cases = [
            "postmodern architecture analysis",
            "handcrafted animation drawing",
            "cginformation archives",
        ]
        for desc in legit_cases:
            prompt = _make_valid_prompt(desc)
            res = validate_prompt(prompt)
            self.assertTrue(res["is_valid"], f"False positive triggered on '{desc}': {res['issues']}")

    def test_forbidden_terms_hyphenated_evasion_discovery(self):
        """
        Adversarial Observation:
        The regex uses rf"\\b{re.escape(term)}\\b" for term in FORBIDDEN_TERMS.
        For multi-word terms like '3d render' and 'octane render', replacing the space
        with a hyphen ('3d-render', 'octane-render') or underscore ('3d_render')
        evades the literal space check in the term string.
        """
        evasions = [
            "3d-render",
            "3d_render",
            "octane-render",
        ]
        for evasion in evasions:
            prompt = _make_valid_prompt(f"A tranquil scene rendered with {evasion} technology")
            res = validate_prompt(prompt)
            # Empirically documents that hyphenated/underscored multi-word terms bypass the exact-string list
            self.assertTrue(
                res["is_valid"],
                f"Expected '{evasion}' to bypass exact-space word boundary regex (documented evasion)",
            )

    def test_signature_frame_tail_not_flagged(self):
        # SIGNATURE_FRAME_TAIL contains 'margins', 'parchment border', 'decorative frame', 'page border'
        # validate_prompt explicitly excludes 'border', 'frame', 'margin' from the forbidden check
        prompt = _make_valid_prompt("Matsuo Basho on the trail")
        self.assertIn("zero margins", prompt)
        self.assertIn("no parchment border", prompt)
        self.assertIn("no decorative frame", prompt)
        self.assertIn("no page border", prompt)
        res = validate_prompt(prompt)
        self.assertTrue(res["is_valid"], f"SIGNATURE_FRAME_TAIL falsely triggered issues: {res['issues']}")

    def test_gif_format_rejection(self):
        gif_cases = [
            "image.gif",
            "output.GIF",
            "animation.gifv",
            "reference.gif: prompt text",
        ]
        for case in gif_cases:
            prompt = f"{case} {_make_valid_prompt()}"
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Failed to reject .gif case: {case}")
            self.assertTrue(
                any(".gif" in i.lower() for i in res["issues"]),
                f"Expected .gif error for {case}, got: {res['issues']}",
            )

    def test_mandatory_phrases_enforcement(self):
        # Missing 'full-bleed edge-to-edge painting'
        p1 = "A tranquil scene, seventeenth-century Edo-period Japan, late-15th-century illuminated manuscript"
        res1 = validate_prompt(p1)
        self.assertFalse(res1["is_valid"])
        self.assertTrue(any("full-bleed" in i for i in res1["issues"]))

        # Missing 'illuminated manuscript'
        p2 = "A tranquil scene, seventeenth-century Edo-period Japan, full-bleed edge-to-edge painting extending to 16:9 canvas"
        res2 = validate_prompt(p2)
        self.assertFalse(res2["is_valid"])
        self.assertTrue(any("illuminated manuscript" in i for i in res2["issues"]))


class TestTagExtractionAndStrippingSpacingAndLinebreaks(unittest.TestCase):
    """Adversarial testing of whitespace, linebreaks, extraction, and stripping behavior."""

    def test_canonical_extraction_and_stripping(self):
        prompt = (
            "[CHARACTER: ref_character_basho] [SETTING: edo_hermitage] "
            "[PROP: inkstone_brush] [INGREDIENT: tea_bowl] "
            "Matsuo Basho sipping fresh tea at his rustic Fukagawa hermitage desk."
        )
        tags = extract_prompt_tags(prompt)
        self.assertEqual(tags["CHARACTER"], ["ref_character_basho"])
        self.assertEqual(tags["SETTING"], ["edo_hermitage"])
        self.assertEqual(tags["PROP"], ["inkstone_brush"])
        self.assertEqual(tags["INGREDIENT"], ["tea_bowl"])

        stripped = strip_prompt_tags(prompt)
        self.assertEqual(
            stripped,
            "Matsuo Basho sipping fresh tea at his rustic Fukagawa hermitage desk.",
        )

    def test_multiple_tags_of_same_type_extracted(self):
        prompt = (
            "[CHARACTER: basho] [CHARACTER: sora] [PROP: inkstone] [PROP: staff] "
            "Walking along the mountainous trail."
        )
        tags = extract_prompt_tags(prompt)
        self.assertEqual(tags["CHARACTER"], ["basho", "sora"])
        self.assertEqual(tags["PROP"], ["inkstone", "staff"])
        self.assertEqual(tags["SETTING"], [])
        self.assertEqual(tags["INGREDIENT"], [])

        stripped = strip_prompt_tags(prompt)
        self.assertEqual(stripped, "Walking along the mountainous trail.")

    def test_whitespace_collapsing_in_stripping(self):
        prompt = "   [CHARACTER: basho]    [SETTING: hermitage]      Basho writing.   "
        stripped = strip_prompt_tags(prompt)
        self.assertEqual(stripped, "Basho writing.")

    def test_stripping_with_no_tags_leaves_text_intact(self):
        text = "A simple scene description without any bracket tags."
        self.assertEqual(strip_prompt_tags(text), text)

    def test_stripping_embedded_tags_in_sentence(self):
        prompt = "Before [CHARACTER: basho] middle [SETTING: hermitage] after."
        stripped = strip_prompt_tags(prompt)
        self.assertEqual(stripped, "Before middle after.")

    def test_newlines_strictly_rejected_by_validator(self):
        newline_variants = [
            _make_valid_prompt() + "\n",
            _make_valid_prompt() + "\r",
            _make_valid_prompt() + "\r\n",
            "Line 1\n" + _make_valid_prompt(),
            "[CHARACTER:\nbasho] " + _make_valid_prompt(),
            "[CHARACTER: basho]\r\n" + _make_valid_prompt(),
        ]
        for prompt in newline_variants:
            res = validate_prompt(prompt)
            self.assertFalse(res["is_valid"], f"Failed to reject newline in prompt: {repr(prompt[:30])}")
            self.assertTrue(
                any("newline" in i.lower() for i in res["issues"]),
                f"Expected newline issue for {repr(prompt[:30])}, got: {res['issues']}",
            )

    def test_build_consistent_prompt_sanitizes_newlines(self):
        # build_consistent_prompt should collapse newlines in scene description into single spaces
        multiline_desc = "A peaceful hermitage.\nQuiet tatami mats.\rEvening lantern glow."
        prompt = build_consistent_prompt(multiline_desc, "matsuo_basho")
        self.assertNotIn("\n", prompt)
        self.assertNotIn("\r", prompt)
        res = validate_prompt(prompt)
        self.assertTrue(res["is_valid"], f"Sanitized prompt failed validation: {res['issues']}")

    def test_whitespace_tolerance_after_colon_in_extraction(self):
        prompt = "[CHARACTER:    basho   ] [SETTING:\tedo_hermitage\t] Scene text."
        tags = extract_prompt_tags(prompt)
        self.assertEqual(tags["CHARACTER"], ["basho"])
        self.assertEqual(tags["SETTING"], ["edo_hermitage"])
        stripped = strip_prompt_tags(prompt)
        self.assertEqual(stripped, "Scene text.")

    def test_space_before_colon_discrepancy(self):
        """
        Adversarial Observation:
        In validate_prompt:
          bracket_blocks = re.findall(r'\\[([^\\]]*)\\]', prompt)
          tag_type, tag_val = block.split(':', 1)
          tag_type_clean = tag_type.strip().upper()
        Because tag_type is stripped before checking valid_types, '[CHARACTER : basho]'
        is judged VALID by validate_prompt.
        HOWEVER:
          TAG_REGEX = r'\\[(CHARACTER|SETTING|PROP|INGREDIENT):\\s*([^\\]]+)\\]'
        TAG_REGEX requires ':' immediately after the tag type without preceding spaces.
        Consequently, extract_prompt_tags fails to extract '[CHARACTER : basho]',
        and strip_prompt_tags fails to strip it!
        """
        prompt = "[CHARACTER : basho] " + _make_valid_prompt()

        # 1. validate_prompt accepts it
        val_res = validate_prompt(prompt)
        self.assertTrue(val_res["is_valid"])

        # 2. extract_prompt_tags FAILS to extract the tag
        extracted = extract_prompt_tags(prompt)
        self.assertEqual(extracted["CHARACTER"], [])

        # 3. strip_prompt_tags FAILS to strip the tag
        stripped = strip_prompt_tags(prompt)
        self.assertIn("[CHARACTER : basho]", stripped)

    def test_spaces_inside_tag_identifier_rejected_by_validator(self):
        prompt = "[CHARACTER: ref character basho] " + _make_valid_prompt()
        res = validate_prompt(prompt)
        self.assertFalse(res["is_valid"])
        self.assertTrue(
            any("invalid characters" in i.lower() for i in res["issues"]),
            f"Expected invalid characters error for spaces inside tag value, got: {res['issues']}",
        )


class TestDualMirrorByteParityAndExports(unittest.TestCase):
    """Verify byte-for-byte parity and identical symbol exports between mirrors."""

    def test_prompt_engine_mirrors_byte_parity(self):
        p1 = REPO_ROOT / "hsnooze.scripting" / "prompt_engine.py"
        p2 = REPO_ROOT / "00.codebases" / "prompt_engine.py"
        self.assertTrue(p1.exists(), f"{p1} missing")
        self.assertTrue(p2.exists(), f"{p2} missing")
        content1 = p1.read_bytes()
        content2 = p2.read_bytes()
        self.assertEqual(
            content1,
            content2,
            "hsnooze.scripting/prompt_engine.py and 00.codebases/prompt_engine.py have diverged!",
        )

    def test_required_symbols_exported(self):
        import prompt_engine

        required = [
            "MASTER_REFERENCE_ANCHORS",
            "CULTURAL_ANCHORS",
            "SIGNATURE_FRAME_TAIL",
            "FORBIDDEN_TERMS",
            "VALID_TAG_TYPES",
            "TAG_REGEX",
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
        for sym in required:
            self.assertTrue(hasattr(prompt_engine, sym), f"Missing symbol {sym} in prompt_engine")


if __name__ == "__main__":
    unittest.main()
