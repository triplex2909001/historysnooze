"""HistorySnooze vpsg24gb Isolation Script Test Suite (Milestone 6)."""

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "isolate_vpsg24gb.sh"


class TestIsolateVpsg24gb(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_isolate_")
        self.src_dir, self.dst_dir = Path(self.tmp_dir) / "src", Path(self.tmp_dir) / "dst"
        self.archive_dir = Path(self.tmp_dir) / "archive"
        for d in (self.src_dir, self.dst_dir, self.archive_dir, self.dst_dir / "00.codebases"):
            d.mkdir(parents=True, exist_ok=True)
        (self.dst_dir / "app.py").write_text("print('ready')")
        self._write_parity_report(status="PASS")

    def tearDown(self):
        subprocess.run(["chmod", "-R", "u+w", self.tmp_dir], check=False)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_parity_report(self, status="PASS"):
        report = {"status": status, "source_files_count": 10, "perfect_matches": 10}
        (self.dst_dir / "PARITY_AUDIT_REPORT.json").write_text(json.dumps(report))

    def _run_script(self, args, stdin=None):
        cmd = [str(SCRIPT_PATH)] + args
        return subprocess.run(cmd, input=stdin, text=True, capture_output=True)

    def test_cli_help_flag(self):
        """--help displays usage info and exits zero."""
        res = self._run_script(["--help"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Usage:", res.stdout)
        self.assertIn("--dry-run", res.stdout)
        self.assertIn("--force", res.stdout)

    def test_cli_dry_run_flag(self):
        """--dry-run simulates actions without purging or modifying permissions."""
        pycache = self.src_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.pyc").write_text("cached")
        res = self._run_script(["--dry-run", "--src", str(self.src_dir), "--dest", str(self.dst_dir)])
        self.assertEqual(res.returncode, 0)
        self.assertIn("[DRY-RUN]", res.stdout)
        self.assertTrue((pycache / "mod.pyc").exists())
        self.assertTrue(os.access(self.src_dir, os.W_OK))

    def test_safeguard_destination_missing_or_empty(self):
        """Script aborts if destination directory is missing, empty, or lacks core dirs."""
        non_existent = Path(self.tmp_dir) / "non_existent"
        res = self._run_script(["--force", "--src", str(self.src_dir), "--dest", str(non_existent)])
        self.assertNotEqual(res.returncode, 0)

        empty_dst = Path(self.tmp_dir) / "empty_dst"
        empty_dst.mkdir()
        res_empty = self._run_script(["--force", "--src", str(self.src_dir), "--dest", str(empty_dst)])
        self.assertNotEqual(res_empty.returncode, 0)

        no_core = Path(self.tmp_dir) / "no_core"
        no_core.mkdir()
        (no_core / "some_file.txt").write_text("hello")
        res_no_core = self._run_script(["--force", "--src", str(self.src_dir), "--dest", str(no_core)])
        self.assertNotEqual(res_no_core.returncode, 0)

    def test_safeguard_parity_report_missing_or_failed(self):
        """Script aborts if PARITY_AUDIT_REPORT.json is missing or not PASS."""
        report_file = self.dst_dir / "PARITY_AUDIT_REPORT.json"
        report_file.unlink()
        res_missing = self._run_script(["--force", "--src", str(self.src_dir), "--dest", str(self.dst_dir)])
        self.assertNotEqual(res_missing.returncode, 0)

        self._write_parity_report(status="FAIL")
        res_fail = self._run_script(["--force", "--src", str(self.src_dir), "--dest", str(self.dst_dir)])
        self.assertNotEqual(res_fail.returncode, 0)

    def test_safeguard_non_interactive_requires_force(self):
        """Script aborts when run without terminal input and without --force."""
        res = self._run_script(["--src", str(self.src_dir), "--dest", str(self.dst_dir)], stdin="")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("requires --force", res.stderr)

    def test_custom_src_default_archive_location(self):
        """Passing custom --src without --archive-dir saves archive inside src."""
        custom_src = Path(self.tmp_dir) / "custom_src"
        custom_src.mkdir()
        (custom_src / "data.txt").write_text("payload")
        res = self._run_script(["--force", "--src", str(custom_src), "--dest", str(self.dst_dir)])
        self.assertEqual(res.returncode, 0)
        archives = list(custom_src.glob("historysnooze_vpsg24gb_archive_*.tar.gz"))
        self.assertEqual(len(archives), 1)

    def test_full_isolation_workflow(self):
        """Executes purge, archive creation, and read-only lockdown."""
        agents_dir = self.src_dir / ".agents"
        agents_dir.mkdir()
        (agents_dir / "meta.json").write_text('{"run": 1}')
        (self.src_dir / "main.py").write_text("print('core')")
        (self.src_dir / "test.pyc").write_text("binary")
        pycache = self.src_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.pyc").write_text("cache")

        res = self._run_script([
            "--force", "--src", str(self.src_dir),
            "--dest", str(self.dst_dir), "--archive-dir", str(self.archive_dir),
        ])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Isolation status: SUCCESS", res.stdout)
        self.assertFalse((self.src_dir / "test.pyc").exists())
        self.assertFalse(pycache.exists())
        self.assertTrue((self.src_dir / "main.py").exists())

        archives = list(self.archive_dir.glob("historysnooze_vpsg24gb_archive_*.tar.gz"))
        self.assertEqual(len(archives), 1)
        with tarfile.open(archives[0], "r:gz") as tar:
            self.assertTrue(any("meta.json" in n for n in tar.getnames()))

        self.assertFalse(os.access(self.src_dir / "main.py", os.W_OK))
        self.assertFalse(os.access(self.src_dir, os.W_OK))


if __name__ == "__main__":
    unittest.main()
