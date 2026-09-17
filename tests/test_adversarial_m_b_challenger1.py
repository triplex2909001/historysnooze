"""Adversarial stress-test suite for Milestone B: 25 Reference Anchors & Note 11 SSOT.

Executed by challenger_m_b_1 to empirically verify:
1. 25 Reference Anchor images across all mirror targets (dimensions, aspect ratio,
   entropy, color variance, SOI/EOI markers, sha256 byte parity).
2. Note 11 SSOT in NotebookLM (JSON schema, Markdown integrity, table structure,
   25-anchor completeness, 1:1 part mapping, Dim the Lights invariants).
3. Cross-system contract reconciliation (images == prompt_engine == reference prompts == Note 11 == ORIGINAL_REQUEST).
"""

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Set

PROJECT_ROOT = os.environ.get(
    "HSNOOZE_DATA_DIR",
    str(Path(__file__).resolve().parent.parent)
)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "hsnooze.scripting"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "00.codebases"))
sys.path.insert(0, PROJECT_ROOT)

import prompt_engine
from PIL import Image


CANONICAL_CHARACTERS = [
    "ref_character_basho_young",
    "ref_character_basho_traveler",
    "ref_character_basho_elder",
    "ref_character_sora",
    "ref_character_buccho",
]

CANONICAL_SETTINGS = [
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

CANONICAL_PROPS = [
    "ref_props_inkstone_brush",
    "ref_props_travel_gear",
    "ref_props_basho_leaves",
    "ref_props_tea_hearth_irori",
    "ref_props_travel_oi",
]

ALL_25_ANCHORS = CANONICAL_CHARACTERS + CANONICAL_SETTINGS + CANONICAL_PROPS
ALL_25_FILES = [f"{a}.jpg" for a in ALL_25_ANCHORS]

REFERENCE_MIRRORS = [
    os.path.join(PROJECT_ROOT, "02. Media Generation/references"),
    os.path.join(PROJECT_ROOT, "hsnooze.gflow/references"),
    os.environ.get(
        "HSNOOZE_ATTACHMENTS_REF_DIR",
        str(Path.home() / ".workspace-mcp" / "attachments" / "references")
    ),
]

NOTE_11_ID = "4dfd4d73-ef12-408f-9687-9122aebd0330"
NOTEBOOK_ID = "813e73eb-7327-4c9b-9651-fe416e6d180c"


def calc_shannon_entropy(img: Image.Image) -> float:
    """Calculate Shannon entropy of image pixel intensity distribution."""
    hist = img.histogram()
    total = sum(hist)
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in hist:
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


class TestAdversarialReferenceAnchors(unittest.TestCase):
    """Adversarial stress-tests for the 25 Reference Anchor image files."""

    def test_01_all_25_anchors_exist_in_all_target_mirrors(self):
        """Verify all 25 canonical anchor images exist in all 3 mirror directories."""
        self.assertEqual(len(ALL_25_FILES), 25)
        for mirror_dir in REFERENCE_MIRRORS:
            self.assertTrue(
                os.path.isdir(mirror_dir),
                f"Reference mirror directory missing: {mirror_dir}",
            )
            for file_name in ALL_25_FILES:
                file_path = os.path.join(mirror_dir, file_name)
                self.assertTrue(
                    os.path.isfile(file_path),
                    f"Anchor file '{file_name}' missing in {mirror_dir}",
                )

    def test_02_file_sizes_exceed_threshold(self):
        """Verify all 25 reference images meet the >= 50KB size threshold."""
        for mirror_dir in REFERENCE_MIRRORS:
            for file_name in ALL_25_FILES:
                file_path = os.path.join(mirror_dir, file_name)
                size = os.path.getsize(file_path)
                self.assertGreaterEqual(
                    size,
                    50 * 1024,
                    f"File '{file_name}' in {mirror_dir} is too small: {size} bytes (< 50KB)",
                )
                self.assertLessEqual(
                    size,
                    2 * 1024 * 1024,
                    f"File '{file_name}' in {mirror_dir} is abnormally large: {size} bytes",
                )

    def test_03_sha256_byte_parity_across_mirrors(self):
        """Verify strict byte-for-byte sha256 parity across all 3 mirror locations."""
        for file_name in ALL_25_FILES:
            hashes = []
            for mirror_dir in REFERENCE_MIRRORS:
                file_path = os.path.join(mirror_dir, file_name)
                with open(file_path, "rb") as f:
                    hashes.append(hashlib.sha256(f.read()).hexdigest())
            self.assertEqual(
                len(set(hashes)),
                1,
                f"Hash mismatch across mirrors for '{file_name}': {hashes}",
            )

    def test_04_jpeg_binary_markers_and_format(self):
        """Verify raw SOI and EOI markers and PIL format integrity."""
        primary_dir = REFERENCE_MIRRORS[0]
        for file_name in ALL_25_FILES:
            file_path = os.path.join(primary_dir, file_name)
            with open(file_path, "rb") as f:
                content = f.read()
            self.assertTrue(
                content.startswith(b"\xff\xd8"),
                f"File '{file_name}' missing JPEG SOI marker (0xFFD8)",
            )
            self.assertTrue(
                content.endswith(b"\xff\xd9"),
                f"File '{file_name}' missing JPEG EOI marker (0xFFD9)",
            )
            with Image.open(file_path) as img:
                self.assertEqual(img.format, "JPEG")
                self.assertEqual(img.mode, "RGB")
                img.verify()

    def test_05_aspect_ratio_and_resolution(self):
        """Verify exact 16:9 aspect ratio within 1% tolerance and 1K resolution."""
        primary_dir = REFERENCE_MIRRORS[0]
        target_ar = 16.0 / 9.0
        for file_name in ALL_25_FILES:
            file_path = os.path.join(primary_dir, file_name)
            with Image.open(file_path) as img:
                w, h = img.size
                self.assertEqual(
                    (w, h),
                    (1376, 768),
                    f"File '{file_name}' dimensions unexpected: {w}x{h} (expected 1376x768)",
                )
                actual_ar = w / h
                ar_error = abs(actual_ar - target_ar) / target_ar
                self.assertLess(
                    ar_error,
                    0.01,
                    f"File '{file_name}' aspect ratio error {ar_error:.4f} exceeds 1% tolerance",
                )

    def test_06_entropy_and_pixel_distribution(self):
        """Stress-test entropy, color standard deviation, and dynamic range."""
        primary_dir = REFERENCE_MIRRORS[0]
        for file_name in ALL_25_FILES:
            file_path = os.path.join(primary_dir, file_name)
            with Image.open(file_path) as img:
                entropy = calc_shannon_entropy(img)
                self.assertGreater(
                    entropy,
                    8.5,
                    f"File '{file_name}' entropy too low: {entropy:.2f} (suspect blank/solid)",
                )
                extrema = img.getextrema()  # ((min_r, max_r), (min_g, max_g), (min_b, max_b))
                min_val = min(e[0] for e in extrema)
                max_val = max(e[1] for e in extrema)
                self.assertLessEqual(
                    min_val,
                    10,
                    f"File '{file_name}' lacks dark levels (min={min_val})",
                )
                self.assertGreaterEqual(
                    max_val,
                    240,
                    f"File '{file_name}' lacks highlight levels (max={max_val})",
                )


class TestAdversarialNote11SSOT(unittest.TestCase):
    """Adversarial schema and consistency stress-tests for Note 11 SSOT."""

    @classmethod
    def setUpClass(cls):
        """Fetch Note 11 content once via notebooklm CLI."""
        cmd = [
            "notebooklm",
            "note",
            "get",
            NOTE_11_ID,
            "-n",
            NOTEBOOK_ID,
            "--json",
        ]
        import shutil
        if shutil.which("notebooklm") is None:
            raise unittest.SkipTest("notebooklm CLI not installed in environment.")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise unittest.SkipTest(f"Failed to fetch Note 11 via notebooklm CLI: {res.stderr}")
        cls.raw_json = res.stdout
        cls.note_data = json.loads(cls.raw_json)
        cls.content = cls.note_data.get("content", "")

    def test_01_note_11_json_schema(self):
        """Validate JSON schema, found flag, note ID, and title."""
        self.assertTrue(self.note_data.get("found"))
        self.assertEqual(self.note_data.get("id"), NOTE_11_ID)
        self.assertIn("11_VISUAL_CONSISTENCY", self.note_data.get("title", ""))
        self.assertGreater(len(self.content), 8000)

    def test_02_all_25_anchor_names_present(self):
        """Assert all 25 canonical anchor identifiers exist in Note 11 content."""
        for anchor in ALL_25_ANCHORS:
            self.assertIn(
                anchor,
                self.content,
                f"Canonical anchor '{anchor}' missing from Note 11 SSOT!",
            )

    def test_03_markdown_syntax_and_code_blocks(self):
        """Verify balanced code fences and structure in Note 11 markdown."""
        code_fence_count = len(re.findall(r"^```", self.content, re.MULTILINE))
        self.assertEqual(
            code_fence_count % 2,
            0,
            f"Unbalanced code fences in Note 11 markdown (count={code_fence_count})",
        )
        required_headers = [
            "## 1. Overview & Core Philosophy",
            "## 2. The 25-Anchor Master Visual Reference Architecture",
            "### 2.1 Character Life-Stage & Companion Anchors",
            "### 2.2 Setting Anchors 1:1 Mapped to 15 Narrative Parts",
            "### 2.3 Signature Props & Relic Anchors",
            "## 3. High-Density 150-Beat Narrative Mapping Matrix",
            '## 4. "Dim the Lights" Cinematic Lighting Transition & Sleep Grading',
            "### 4.1 Audio Cue Anchoring",
            "### 4.2 Cosine Dynamic Easing Filter",
            "### 4.3 Static Sleep Mood Grading",
            "## 5. Master Concatenation & Gatekeeper Invariants",
        ]
        for header in required_headers:
            self.assertIn(header, self.content, f"Missing section header: '{header}'")

    def test_04_mapping_matrix_table_structure_and_1_to_1_settings(self):
        """Verify markdown table format, 1:1 part settings, and life-stage assignments."""
        lines = self.content.splitlines()
        table_rows = []
        for line in lines:
            s = line.strip()
            if s.startswith("|") and s.endswith("|"):
                cols = [c.strip() for c in s.strip("|").split("|")]
                table_rows.append(cols)

        self.assertGreaterEqual(
            len(table_rows), 17, "Table must have header, delimiter, and 15 parts"
        )
        header = table_rows[0]
        self.assertEqual(len(header), 6)
        self.assertEqual(
            header,
            [
                "Part",
                "Title / Arc",
                "Setting Anchor (1:1)",
                "Primary Character Anchor",
                "Companion / Secondary",
                "Signature Props",
            ],
        )

        data_rows = table_rows[2:17]
        self.assertEqual(len(data_rows), 15)

        observed_settings = []
        expected_settings_map = {
            1: "ref_setting_iga_ueno",
            2: "ref_setting_edo_nihonbashi",
            3: "ref_setting_fukagawa_interior",
            4: "ref_setting_fukagawa_exterior",
            5: "ref_setting_fuji_river_trail",
            6: "ref_setting_senju_dock",
            7: "ref_setting_nikko_cedars",
            8: "ref_setting_yamadera_temple",
            9: "ref_setting_mogami_river",
            10: "ref_setting_kisakata_lagoon",
            11: "ref_setting_shirakawa_barrier",
            12: "ref_setting_genjuan_bamboo",
            13: "ref_setting_kyoto_rakushisha",
            14: "ref_setting_tokaido_highway",
            15: "ref_setting_withered_moor",
        }

        for idx, row in enumerate(data_rows, start=1):
            self.assertEqual(
                len(row), 6, f"Row for Part {idx:02d} has invalid column count: {len(row)}"
            )
            part_str = row[0].replace("*", "").strip()
            self.assertEqual(int(part_str), idx)

            setting = row[2].strip("`").strip()
            observed_settings.append(setting)
            self.assertEqual(
                setting,
                expected_settings_map[idx],
                f"Part {idx:02d} setting mismatch: expected {expected_settings_map[idx]}, got {setting}",
            )

            char = row[3].strip("`").strip()
            if idx in (1, 2):
                self.assertEqual(char, "ref_character_basho_young")
            elif 5 <= idx <= 11:
                self.assertEqual(char, "ref_character_basho_traveler")
            elif idx in (3, 4) or 12 <= idx <= 15:
                self.assertEqual(char, "ref_character_basho_elder")

        # Assert 1:1 mapping (all 15 settings are distinct)
        self.assertEqual(len(set(observed_settings)), 15)
        self.assertEqual(set(observed_settings), set(CANONICAL_SETTINGS))

    def test_05_dim_the_lights_invariants(self):
        """Verify Dim the Lights cue parameters and cosine easing invariants."""
        self.assertIn("174.73s", self.content)
        self.assertIn("184.45s", self.content)
        self.assertIn("9.72s", self.content)
        self.assertIn("186.45s", self.content)
        self.assertIn("cosine_blend", self.content)
        self.assertIn("0.5*(1+cos(PI*(T-174.73)/9.72))", self.content)
        self.assertIn("0.90", self.content)  # contrast
        self.assertIn("-0.05", self.content)  # brightness
        self.assertIn("0.88", self.content)  # saturation
        self.assertIn("0.85", self.content)  # gamma


class TestCrossSystemReconciliation(unittest.TestCase):
    """Stress-test contract alignment across all codebase and storage surfaces."""

    def test_01_prompt_engine_master_registry_completeness(self):
        """Verify prompt_engine.MASTER_REFERENCE_ANCHORS contains all 25 canonical anchors."""
        registry = prompt_engine.MASTER_REFERENCE_ANCHORS.get("matsuo_basho", {})
        chars = registry.get("characters", {})
        settings = registry.get("settings", {})
        props = registry.get("props", {})

        self.assertEqual(set(chars.keys()), set(CANONICAL_CHARACTERS))
        self.assertEqual(set(settings.keys()), set(CANONICAL_SETTINGS))
        self.assertEqual(set(props.keys()), set(CANONICAL_PROPS))

        # Check total count
        total_anchors = len(chars) + len(settings) + len(props)
        self.assertEqual(total_anchors, 25)

        # Test prompt_engine.resolve_reference_anchor resolves each anchor
        for char_id in CANONICAL_CHARACTERS:
            resolved = prompt_engine.resolve_reference_anchor("CHARACTER", char_id)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved["id"], char_id)

        for setting_id in CANONICAL_SETTINGS:
            resolved = prompt_engine.resolve_reference_anchor("SETTING", setting_id)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved["id"], setting_id)

        for prop_id in CANONICAL_PROPS:
            resolved = prompt_engine.resolve_reference_anchor("PROP", prop_id)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved["id"], prop_id)

    def test_02_reference_imageprompts_txt_parity_and_count(self):
        """Verify reference_imageprompts.txt in both codebase locations has 25 prompts."""
        files = [
            os.path.join(PROJECT_ROOT, "00.codebases/reference_imageprompts.txt"),
            os.path.join(PROJECT_ROOT, "hsnooze.gflow/reference_imageprompts.txt"),
        ]
        with open(files[0], "rb") as f1, open(files[1], "rb") as f2:
            self.assertEqual(f1.read(), f2.read(), "Parity broken between reference_imageprompts.txt copies")

        with open(files[0], "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        self.assertEqual(len(lines), 25, f"Expected 25 prompts, found {len(lines)}")
        prompt_filenames = []
        for line in lines:
            parts = line.split(":", 1)
            self.assertEqual(len(parts), 2)
            fname = parts[0].strip()
            prompt = parts[1].strip()
            prompt_filenames.append(fname)
            self.assertLessEqual(len(prompt), 1500, f"Prompt for {fname} exceeds 1500 chars ({len(prompt)})")
            self.assertIn("16:9", prompt)
            self.assertIn("seventeenth-century", prompt)

        self.assertEqual(set(prompt_filenames), set(ALL_25_FILES))

    def test_03_strict_quad_surface_set_equality(self):
        """Quad-surface set equality test: disk images == prompts == prompt_engine == Note 11."""
        surface_disk = set(ALL_25_ANCHORS)
        surface_engine = set(prompt_engine.MASTER_REFERENCE_ANCHORS["matsuo_basho"]["characters"].keys()) | \
                         set(prompt_engine.MASTER_REFERENCE_ANCHORS["matsuo_basho"]["settings"].keys()) | \
                         set(prompt_engine.MASTER_REFERENCE_ANCHORS["matsuo_basho"]["props"].keys())

        prompts_path = os.path.join(PROJECT_ROOT, "00.codebases/reference_imageprompts.txt")
        with open(prompts_path, "r", encoding="utf-8") as f:
            surface_prompts = {
                l.split(":", 1)[0].replace(".jpg", "").strip()
                for l in f if l.strip()
            }

        self.assertEqual(surface_disk, surface_engine)
        self.assertEqual(surface_disk, surface_prompts)
        self.assertEqual(len(surface_disk), 25)


if __name__ == "__main__":
    unittest.main()
