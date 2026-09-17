"""
Adversarial Stress Test Suite for hsnooze.render.kenburns_asmr.
Empirically tests pathological timestamps, overlay fallback robustness,
zoompan expressions, non-standard dimensions, and colorspace conversions.
"""

import math
import os
import re
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

RENDER_DIR = os.path.join(PROJECT_ROOT, "hsnooze.render")
if RENDER_DIR not in sys.path:
    sys.path.insert(0, RENDER_DIR)

import kenburns_asmr
from kenburns_asmr import (
    build_zoompan_expr,
    build_filter_graph,
    build_render_command,
    render_kenburns_beat,
    DEFAULT_CONTRAST,
    DEFAULT_BRIGHTNESS,
    DEFAULT_GAMMA,
    DEFAULT_SATURATION,
    DEFAULT_VIGNETTE,
    DEFAULT_STARDUST_OPACITY,
)



class TestPathologicalTimestamps(unittest.TestCase):
    """Stress tests pathological timestamp inputs to build_filter_graph and build_render_command."""

    def test_dim_start_greater_than_dim_end_triggers_fallback(self):
        """When dim_start_sec > dim_end_sec, filter graph must fall back to safe defaults (38.0s, 45.0s)."""
        filt, out_label = build_filter_graph(
            is_transition_beat=True,
            dim_start_sec=50.0,
            dim_end_sec=30.0,
            has_overlay=False,
        )
        self.assertIn("lte(T,38.000)", filt)
        self.assertIn("gte(T,45.000)", filt)
        self.assertIn("/7.000", filt)
        self.assertEqual(out_label, "[out]")

    def test_dim_start_equals_dim_end_triggers_fallback(self):
        """When dim_start_sec == dim_end_sec, delta would be 0; must trigger fallback to 38.0s, 45.0s."""
        filt, out_label = build_filter_graph(
            is_transition_beat=True,
            dim_start_sec=42.0,
            dim_end_sec=42.0,
            has_overlay=False,
        )
        self.assertIn("lte(T,38.000)", filt)
        self.assertIn("gte(T,45.000)", filt)
        self.assertIn("/7.000", filt)
        self.assertNotIn("/0.000", filt)

    def test_dim_start_negative_clamped_to_zero(self):
        """Negative dim_start_sec must be clamped to 0.0 without crash or negative timestamps in expr."""
        filt, out_label = build_filter_graph(
            is_transition_beat=True,
            dim_start_sec=-12.5,
            dim_end_sec=10.0,
            has_overlay=False,
        )
        self.assertIn("lte(T,0.000)", filt)
        self.assertIn("gte(T,10.000)", filt)
        self.assertIn("/10.000", filt)
        self.assertNotIn("lte(T,-", filt)

    def test_both_dim_timestamps_negative_triggers_fallback(self):
        """When both timestamps are negative, clamped t0=0 >= t1, so fallback must trigger."""
        filt, out_label = build_filter_graph(
            is_transition_beat=True,
            dim_start_sec=-30.0,
            dim_end_sec=-5.0,
            has_overlay=False,
        )
        self.assertIn("lte(T,38.000)", filt)
        self.assertIn("gte(T,45.000)", filt)
        self.assertIn("/7.000", filt)

    def test_dim_end_greater_than_duration_command_structure(self):
        """When dim_end_sec > duration, filter graph and render command still build valid syntax."""
        duration = 20.0
        cmd = build_render_command(
            image_path="test.jpg",
            duration=duration,
            output_clip_path="out.mp4",
            is_transition_beat=True,
            dim_start_sec=25.0,
            dim_end_sec=35.0,
            overlay_asset_path=None,
        )
        self.assertIn("-t", cmd)
        idx = cmd.index("-t")
        self.assertEqual(cmd[idx + 1], "20.000")
        filter_idx = cmd.index("-filter_complex")
        filt = cmd[filter_idx + 1]
        self.assertIn("lte(T,25.000)", filt)
        self.assertIn("gte(T,35.000)", filt)

    def test_sub_millisecond_timestamp_delta_adversarial_check(self):
        """
        Adversarial edge case: if t1 > t0 but t1 - t0 < 0.0005s,
        round(t1 - t0, 3) rounds down to 0.000, which risks division by zero:
        PI*(T-t0)/0.000 in cosine easing expressions.
        Must fall back to safe defaults (38.0s, 45.0s, delta=7.0s).
        """
        t0 = 10.0
        t1 = 10.0004
        filt, out_label = build_filter_graph(
            is_transition_beat=True,
            dim_start_sec=t0,
            dim_end_sec=t1,
            has_overlay=False,
        )
        self.assertEqual(out_label, "[out]")
        self.assertIn("lte(T,38.000)", filt)
        self.assertIn("gte(T,45.000)", filt)
        self.assertIn("/7.000", filt)
        self.assertNotIn("/0.000", filt)

        # Verify all denominators in cosine expressions are strictly positive
        denominators = re.findall(r"PI\*\(T-[0-9\.]+\)/([0-9\.]+)", filt)
        self.assertTrue(len(denominators) >= 1)
        for d in denominators:
            val = float(d)
            self.assertGreater(
                val,
                0.0,
                f"Division by zero detected in filter graph: denominator is {d}!",
            )

    def test_sub_frame_duration_produces_total_frames_at_least_one(self):
        """When positive duration produces < 1 frame (e.g. 0.01s at 30fps), total_frames clamps to >= 1."""
        cmd = build_render_command(
            image_path="test.jpg",
            duration=0.01,
            output_clip_path="out.mp4",
            fps=30,
        )
        vf_idx = cmd.index("-vf")
        filt = cmd[vf_idx + 1]
        self.assertIn("d=1", filt)
        self.assertIn("fps=30", filt)


class TestOverlayAssetRobustness(unittest.TestCase):
    """Stress tests overlay asset edge cases: None, empty, missing, 0-byte, unreadable, directory."""

    def test_overlay_none_omits_input_and_stream_tag(self):
        """When overlay_asset_path is None, input 1 and [1:v] must be completely omitted."""
        cmd = build_render_command(
            image_path="test.jpg",
            duration=10.0,
            output_clip_path="out.mp4",
            sleep_mode=True,
            overlay_asset_path=None,
        )
        cmd_str = " ".join(cmd)
        self.assertNotIn("-stream_loop", cmd)
        self.assertNotIn("[1:v]", cmd_str)
        self.assertIn("-vf", cmd)

    def test_overlay_empty_string_omits_input_and_stream_tag(self):
        """When overlay_asset_path is empty string, falls back gracefully."""
        cmd = build_render_command(
            image_path="test.jpg",
            duration=10.0,
            output_clip_path="out.mp4",
            sleep_mode=True,
            overlay_asset_path="",
        )
        cmd_str = " ".join(cmd)
        self.assertNotIn("-stream_loop", cmd)
        self.assertNotIn("[1:v]", cmd_str)

    def test_overlay_nonexistent_file_omits_input_and_stream_tag(self):
        """When overlay_asset_path does not exist on disk, falls back gracefully."""
        cmd = build_render_command(
            image_path="test.jpg",
            duration=10.0,
            output_clip_path="out.mp4",
            sleep_mode=True,
            overlay_asset_path="/tmp/nonexistent_stardust_overlay_xyz_123.mp4",
        )
        cmd_str = " ".join(cmd)
        self.assertNotIn("-stream_loop", cmd)
        self.assertNotIn("[1:v]", cmd_str)
        self.assertIn("-vf", cmd)

    def test_overlay_zero_byte_file_omits_input_and_stream_tag(self):
        """When overlay_asset_path exists but is 0 bytes, falls back gracefully."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            empty_path = tmp.name
        try:
            self.assertEqual(os.path.getsize(empty_path), 0)
            cmd = build_render_command(
                image_path="test.jpg",
                duration=10.0,
                output_clip_path="out.mp4",
                sleep_mode=True,
                overlay_asset_path=empty_path,
            )
            cmd_str = " ".join(cmd)
            self.assertNotIn("-stream_loop", cmd)
            self.assertNotIn("[1:v]", cmd_str)
            self.assertIn("-vf", cmd)
        finally:
            if os.path.exists(empty_path):
                os.remove(empty_path)

    def test_overlay_unreadable_file_fallback(self):
        """
        Adversarial test: when overlay file exists and size > 0 but has chmod 000 (unreadable),
        it should ideally fall back rather than passing an unreadable file to ffmpeg.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"dummy overlay bytes")
            unreadable_path = tmp.name

        try:
            os.chmod(unreadable_path, 0o000)
            # Test whether build_render_command detects unreadable file
            is_readable = os.access(unreadable_path, os.R_OK)
            self.assertFalse(is_readable)

            cmd = build_render_command(
                image_path="test.jpg",
                duration=10.0,
                output_clip_path="out.mp4",
                sleep_mode=True,
                overlay_asset_path=unreadable_path,
            )
            # Check whether input 1 was omitted
            has_input_1 = any(unreadable_path in arg for arg in cmd)
            # Document finding: kenburns_asmr currently only checks exists and getsize > 0
            # If it fails to check os.access(R_OK), has_input_1 will be True.
            # We assert the safe behavior:
            self.assertFalse(
                has_input_1,
                "Unreadable file (chmod 000) was erroneously included as FFmpeg input 1!",
            )
        finally:
            os.chmod(unreadable_path, 0o644)
            if os.path.exists(unreadable_path):
                os.remove(unreadable_path)

    def test_overlay_directory_path_fallback(self):
        """
        Adversarial test: if a directory path is passed as overlay_asset_path,
        os.path.exists is True and getsize > 0 on POSIX.
        It should NOT be accepted as a valid overlay file.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            cmd = build_render_command(
                image_path="test.jpg",
                duration=10.0,
                output_clip_path="out.mp4",
                sleep_mode=True,
                overlay_asset_path=tmp_dir,
            )
            has_input_1 = any(tmp_dir in arg for arg in cmd)
            self.assertFalse(
                has_input_1,
                "Directory path was erroneously accepted as FFmpeg overlay input 1!",
            )

    def test_no_dangling_1v_stream_tags_in_transition_beat_fallback(self):
        """In transition beat without overlay, filter complex must use [0:v] only and never [1:v]."""
        filt, out_label = build_filter_graph(
            is_transition_beat=True,
            dim_start_sec=10.0,
            dim_end_sec=20.0,
            has_overlay=False,
        )
        self.assertIn("[0:v]", filt)
        self.assertNotIn("[1:v]", filt)
        self.assertEqual(out_label, "[out]")


class TestDimensionsAndZoompanExpressions(unittest.TestCase):
    """Tests non-standard dimensions, extreme durations, and zoompan boundary conditions."""

    def test_total_frames_one_zoom_in(self):
        """When total_frames=1, zoom_in expression must evaluate cleanly without ZeroDivisionError."""
        z_expr, x_expr, y_expr = build_zoompan_expr(zoom_in=True, total_frames=1)
        self.assertEqual(z_expr, "min(zoom+0.04000000,1.04)")
        self.assertEqual(x_expr, "iw/2-(iw/zoom/2)")
        self.assertEqual(y_expr, "ih/2-(ih/zoom/2)")

    def test_total_frames_one_zoom_out(self):
        """When total_frames=1, zoom_out expression evaluates cleanly."""
        z_expr, x_expr, y_expr = build_zoompan_expr(zoom_in=False, total_frames=1)
        self.assertEqual(z_expr, "if(eq(on,1),1.04,max(zoom-0.04000000,1.00))")
        self.assertEqual(x_expr, "iw/2-(iw/zoom/2)")
        self.assertEqual(y_expr, "ih/2-(ih/zoom/2)")

    def test_total_frames_zero_clamped_to_one(self):
        """total_frames=0 must clamp to 1 to prevent ZeroDivisionError."""
        z_expr, _, _ = build_zoompan_expr(zoom_in=True, total_frames=0)
        self.assertIn("0.04000000", z_expr)

    def test_total_frames_negative_clamped_to_one(self):
        """Negative total_frames must clamp to 1."""
        z_expr, _, _ = build_zoompan_expr(zoom_in=True, total_frames=-100)
        self.assertIn("0.04000000", z_expr)

    def test_extreme_duration_large_frame_count(self):
        """Extreme duration (100,000s = ~27.7h) must produce valid non-scientific notation."""
        z_expr, _, _ = build_zoompan_expr(zoom_in=True, total_frames=3000000)
        self.assertNotIn("e-", z_expr)
        self.assertIn("min(zoom+", z_expr)

    def test_non_standard_dimensions_in_filter(self):
        """Vertical (1080x1920) or ultrawide (2560x1080) dimensions must propagate to zoompan size."""
        for w, h in [(1080, 1920), (2560, 1080), (1280, 720), (1920, 1080)]:
            filt, _ = build_filter_graph(width=w, height=h, total_frames=300)
            self.assertIn(f"s={w}x{h}", filt)

    def test_zoompan_centering_geometry_invariants(self):
        """x and y pan expressions must maintain center alignment invariant: iw/2 - (iw/zoom/2)."""
        _, x_expr, y_expr = build_zoompan_expr(zoom_in=True, total_frames=900)
        self.assertEqual(x_expr, "iw/2-(iw/zoom/2)")
        self.assertEqual(y_expr, "ih/2-(ih/zoom/2)")


class TestColorspaceAndStreamIntegrity(unittest.TestCase):
    """Validates colorspace mappings and stream format transitions."""

    def test_rgba_conversion_before_screen_blend_transition_beat(self):
        """Transition beat with overlay must convert dimmed stream and overlay to RGBA before screen blend."""
        filt, out_label = build_filter_graph(
            is_transition_beat=True,
            dim_start_sec=10.0,
            dim_end_sec=20.0,
            has_overlay=True,
        )
        self.assertIn("format=rgba [kb_dimmed]", filt)
        self.assertIn("format=rgba,colorchannelmixer", filt)
        self.assertIn("[kb_dimmed][pts_alpha] blend=all_mode=screen", filt)
        self.assertEqual(out_label, "[out]")

    def test_rgba_conversion_before_screen_blend_sleep_mode(self):
        """Static sleep beat with overlay must convert base stream and overlay to RGBA before screen blend."""
        filt, out_label = build_filter_graph(
            sleep_mode=True,
            has_overlay=True,
        )
        self.assertIn("format=rgba [kb_dark]", filt)
        self.assertIn("format=rgba,colorchannelmixer", filt)
        self.assertIn("[kb_dark][pts_alpha] blend=all_mode=screen,format=rgba [out]", filt)
        self.assertEqual(out_label, "[out]")

    def test_output_always_has_pix_fmt_yuv420p(self):
        """Every operational mode must specify -pix_fmt yuv420p immediately before output path."""
        modes = [
            {"is_transition_beat": False, "sleep_mode": False, "has_overlay": False},
            {"is_transition_beat": True, "sleep_mode": False, "has_overlay": False},
            {"is_transition_beat": True, "sleep_mode": False, "has_overlay": True},
            {"is_transition_beat": False, "sleep_mode": True, "has_overlay": False},
            {"is_transition_beat": False, "sleep_mode": True, "has_overlay": True},
        ]

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"data")
            overlay_file = tmp.name

        try:
            for m in modes:
                ov = overlay_file if m["has_overlay"] else None
                cmd = build_render_command(
                    image_path="test.jpg",
                    duration=10.0,
                    output_clip_path="out.mp4",
                    is_transition_beat=m["is_transition_beat"],
                    dim_start_sec=2.0,
                    dim_end_sec=8.0,
                    sleep_mode=m["sleep_mode"],
                    overlay_asset_path=ov,
                )
                self.assertIn("-pix_fmt", cmd)
                pix_idx = cmd.index("-pix_fmt")
                self.assertEqual(cmd[pix_idx + 1], "yuv420p")
                self.assertEqual(cmd[pix_idx + 2], "out.mp4")
        finally:
            if os.path.exists(overlay_file):
                os.remove(overlay_file)


class TestRenderKenburnsBeatExecutionEdgeCases(unittest.TestCase):
    """Stress tests render_kenburns_beat filesystem and parameter boundaries."""

    def test_bare_filename_output_clip_path(self):
        """
        Adversarial test: when output_clip_path has no directory component (e.g., 'out.mp4'),
        os.path.dirname('out.mp4') returns ''. Calling os.makedirs('', exist_ok=True)
        crashes with FileNotFoundError: [Errno 2] No such file or directory: ''.
        """
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
            img_path = tmp_img.name

        try:
            # We mock subprocess.run so this test isolates the path handling logic
            with patch("subprocess.run") as mock_run:
                # Should handle bare filename without crashing in os.makedirs
                try:
                    render_kenburns_beat(
                        image_path=img_path,
                        duration=5.0,
                        output_clip_path="bare_clip_output.mp4",
                    )
                except FileNotFoundError as e:
                    if str(e) == "[Errno 2] No such file or directory: ''":
                        self.fail("render_kenburns_beat crashed on bare filename due to os.makedirs('')!")
                    raise
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    def test_nonexistent_input_image_raises_filenotfound(self):
        """render_kenburns_beat must raise FileNotFoundError for nonexistent input image."""
        with self.assertRaises(FileNotFoundError):
            render_kenburns_beat(
                image_path="/nonexistent/path/image_12345.jpg",
                duration=5.0,
                output_clip_path="/tmp/out.mp4",
            )

    def test_negative_or_zero_duration_handling(self):
        """
        Adversarial test: duration <= 0.0s is invalid for video rendering and must raise ValueError.
        """
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
            img_path = tmp_img.name

        try:
            for dur in [0.0, -1.0, -10.0]:
                with self.assertRaises(ValueError):
                    build_render_command(
                        image_path=img_path,
                        duration=dur,
                        output_clip_path="/tmp/out.mp4",
                    )
                with self.assertRaises(ValueError):
                    render_kenburns_beat(
                        image_path=img_path,
                        duration=dur,
                        output_clip_path="/tmp/out.mp4",
                    )
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)


if __name__ == "__main__":
    unittest.main()
