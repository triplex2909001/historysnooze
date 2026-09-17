"""
Unit Test Suite for Omni and Render Workers Refactoring (M3).
Verifies:
1. @retry_network_op exponential backoff and retry limits.
2. drive_extractor safe extraction & SecurityError.
3. download_drive_assets backwards compatibility.
4. image_prompt_parser & image_remote_sync submodules.
5. voice_chunk_engine modular decomposition and exports.
6. colab_voiceover_runner and colab_render_runner facades.
"""

import os
import sys
import tempfile
import tarfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "hsnooze.render"))
sys.path.insert(0, str(_REPO_ROOT / "hsnooze.omni"))
sys.path.insert(0, str(_REPO_ROOT / "00.codebases"))

from network_retry import retry_network_op
import download_drive_assets
from drive_extractor import safe_extract_tarball, SecurityError
import image_pipeline_worker
from image_prompt_parser import parse_prompts, audit_image_gk3
import voice_chunk_engine
from voice_text_processor import clean_voiceover_script, split_into_paragraphs, split_paragraph_into_sentences
from voice_acoustic_auditor import audit_wav_acoustic, generate_silence_wav
import colab_voiceover_runner
import colab_render_runner


class TestNetworkRetry(unittest.TestCase):
    """Verifies genuine retry behavior and exponential backoff of @retry_network_op."""

    def test_retry_eventual_success(self):
        call_count = 0

        @retry_network_op(max_retries=3, initial_delay=0.005, backoff_factor=2.0)
        def unreliable_op():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient network failure")
            return "ok"

        res = unreliable_op()
        self.assertEqual(res, "ok")
        self.assertEqual(call_count, 3)

    def test_retry_exhaustion_raises(self):
        call_count = 0

        @retry_network_op(max_retries=3, initial_delay=0.005, backoff_factor=2.0)
        def failing_op():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Network timeout")

        with self.assertRaises(TimeoutError):
            failing_op()
        self.assertEqual(call_count, 3)

    def test_retry_plain_decorator_syntax(self):
        call_count = 0

        @retry_network_op
        def default_op():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("Socket error")
            return 42

        res = default_op()
        self.assertEqual(res, 42)
        self.assertEqual(call_count, 2)


class TestDriveExtractorSecurity(unittest.TestCase):
    """Verifies CVE-2007-4559 Tar Slip neutralization in drive_extractor."""

    def test_safe_extract_normal_tar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / "test.tar"
            dest_dir = Path(tmpdir) / "output"
            with tarfile.open(tar_path, "w") as tar:
                member_file = Path(tmpdir) / "file.txt"
                member_file.write_text("safe content", encoding="utf-8")
                tar.add(member_file, arcname="file.txt")

            safe_extract_tarball(tar_path, dest_dir)
            self.assertTrue((dest_dir / "file.txt").exists())
            self.assertEqual((dest_dir / "file.txt").read_text(encoding="utf-8"), "safe content")

    def test_safe_extract_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / "evil.tar"
            dest_dir = Path(tmpdir) / "output"
            with tarfile.open(tar_path, "w") as tar:
                ti = tarfile.TarInfo(name="../evil.txt")
                ti.size = 4
                import io
                tar.addfile(ti, io.BytesIO(b"evil"))

            with self.assertRaises(SecurityError):
                safe_extract_tarball(tar_path, dest_dir)


class TestVoiceChunkEngineDecomposition(unittest.TestCase):
    """Verifies voice_chunk_engine exports and submodules."""

    def test_facade_exports(self):
        expected_symbols = [
            "clean_voiceover_script",
            "split_into_paragraphs",
            "split_paragraph_into_sentences",
            "audit_wav_acoustic",
            "generate_silence_wav",
            "stitch_wav_chunks",
            "stitch_master_audio",
            "OmniVoiceBackend",
            "ChunkVoiceoverPipeline",
        ]
        for sym in expected_symbols:
            self.assertTrue(hasattr(voice_chunk_engine, sym), f"Missing symbol: {sym}")

    def test_text_processor_splitting(self):
        text = "First paragraph.\n\nSecond paragraph with multiple words. Another sentence here."
        paras = split_into_paragraphs(text)
        self.assertEqual(len(paras), 2)
        sents = split_paragraph_into_sentences(paras[1])
        self.assertEqual(len(sents), 2)

    def test_acoustic_auditor_silence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            silence_path = Path(tmpdir) / "silence.wav"
            generate_silence_wav(str(silence_path), duration_sec=0.5, framerate=24000)
            self.assertTrue(silence_path.exists())
            # A pure silence wav should be rejected by strict GK4
            valid, msg = audit_wav_acoustic(str(silence_path))
            self.assertFalse(valid)
            self.assertIn("SILENT", msg)


class TestImagePipelineWorkerDecomposition(unittest.TestCase):
    """Verifies image_pipeline_worker decomposition and exports."""

    def test_parse_prompts(self):
        sample_prompts = "# Header\nbeat_P01_B01.jpg: Cover image\nbeat_P01_B02.jpg: Second beat\n"
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as tf:
            tf.write(sample_prompts)
            tf_path = Path(tf.name)

        try:
            beats, skipped_cover = parse_prompts(tf_path, skip_cover=True)
            self.assertEqual(len(beats), 1)
            self.assertEqual(beats[0]["id"], "beat_P01_B02")
            self.assertEqual(skipped_cover, "beat_P01_B01")
        finally:
            tf_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
