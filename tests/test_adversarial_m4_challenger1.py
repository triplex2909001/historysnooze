"""
Adversarial Stress Test Suite for Milestone 4 (monitor.py & Sandbox).
Author / Runner: challenger_m4_1 (Empirical Challenger)
Target: /media/vpsg16gb/Media/historysnooze/monitor.py
"""
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unittest
from pathlib import Path
from rich.errors import MarkupError

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import monitor


class TestMonitorMemoryStress(unittest.TestCase):
    """Stress tests verifying peak memory never exceeds 25.0 MB under any scenario."""

    def test_ram_empty_db_under_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HSNOOZE_DATA_DIR"] = tmp
            cmd = [sys.executable, str(REPO_ROOT / "monitor.py"), "--test-ram"]
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertIn("RAM Consumption:", res.stdout)
            time_cmd = ["/usr/bin/time", "-v", sys.executable, str(REPO_ROOT / "monitor.py"), "--test-ram"]
            t_res = subprocess.run(time_cmd, env=env, capture_output=True, text=True)
            rss = [l for l in t_res.stderr.splitlines() if "Maximum resident set size" in l]
            self.assertTrue(rss, "Could not measure RSS")
            rss_mb = int(rss[0].split()[-1]) / 1024.0
            self.assertLessEqual(rss_mb, 25.0, f"Peak RSS {rss_mb:.2f} MB exceeds 25.0 MB")

    def test_ram_large_db_1000_entries_under_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "pipeline.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE run_history (id INTEGER PRIMARY KEY, timestamp TEXT, job_id TEXT, "
                    "step_current TEXT, status TEXT, duration REAL, detail TEXT)"
                )
                entries = [
                    (i, "2026-09-15", f"job_{i}", "GK2", "SUCCESS", 1.5, f"Detail {i} padding " * 10)
                    for i in range(1, 1001)
                ]
                conn.executemany("INSERT INTO run_history VALUES (?,?,?,?,?,?,?)", entries)

            env = os.environ.copy()
            env["HSNOOZE_DATA_DIR"] = tmp
            time_cmd = ["/usr/bin/time", "-v", sys.executable, str(REPO_ROOT / "monitor.py"), "--test-ram"]
            t_res = subprocess.run(time_cmd, env=env, capture_output=True, text=True)
            self.assertEqual(t_res.returncode, 0)
            rss = [l for l in t_res.stderr.splitlines() if "Maximum resident set size" in l]
            rss_mb = int(rss[0].split()[-1]) / 1024.0
            self.assertLessEqual(rss_mb, 25.0, f"Peak RSS {rss_mb:.2f} MB exceeds 25.0 MB")

    def test_ram_heavy_db_10000_entries_under_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "pipeline.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE run_history (id INTEGER PRIMARY KEY, timestamp TEXT, job_id TEXT, "
                    "step_current TEXT, status TEXT, duration REAL, detail TEXT)"
                )
                entries = [
                    (i, "2026-09-15", f"job_{i}", "GK3", "SUCCESS", 2.0, "X" * 2000)
                    for i in range(1, 10001)
                ]
                conn.executemany("INSERT INTO run_history VALUES (?,?,?,?,?,?,?)", entries)

            env = os.environ.copy()
            env["HSNOOZE_DATA_DIR"] = tmp
            time_cmd = ["/usr/bin/time", "-v", sys.executable, str(REPO_ROOT / "monitor.py"), "--once"]
            t_res = subprocess.run(time_cmd, env=env, capture_output=True, text=True)
            self.assertEqual(t_res.returncode, 0)
            rss = [l for l in t_res.stderr.splitlines() if "Maximum resident set size" in l]
            rss_mb = int(rss[0].split()[-1]) / 1024.0
            self.assertLessEqual(rss_mb, 25.0, f"Peak RSS {rss_mb:.2f} MB exceeds 25.0 MB")

    def test_ram_invalid_args_under_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HSNOOZE_DATA_DIR"] = tmp
            time_cmd = ["/usr/bin/time", "-v", sys.executable, str(REPO_ROOT / "monitor.py"), "--invalid-flag-12345"]
            t_res = subprocess.run(time_cmd, env=env, capture_output=True, text=True)
            rss = [l for l in t_res.stderr.splitlines() if "Maximum resident set size" in l]
            rss_mb = int(rss[0].split()[-1]) / 1024.0
            self.assertLessEqual(rss_mb, 25.0, f"Peak RSS {rss_mb:.2f} MB exceeds 25.0 MB")

    def test_ram_multi_iteration_leak_check(self):
        tracemalloc.start()
        tracemalloc.reset_peak()
        for _ in range(100):
            _ = monitor.generate_dashboard()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / (1024 * 1024)
        self.assertLessEqual(peak_mb, 25.0, f"Tracemalloc peak {peak_mb:.2f} MB exceeds 25.0 MB")


class TestMonitorSQLiteRobustness(unittest.TestCase):
    """Stress tests verifying SQLite corruption, locking, empty states, and fallback."""

    def test_corrupt_database_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "pipeline.db")
            with open(db_path, "wb") as f:
                f.write(b"CORRUPTED_BINARY_DATA\x00\xff\xfe" * 100)
            orig = os.environ.get("HSNOOZE_DATA_DIR")
            os.environ["HSNOOZE_DATA_DIR"] = tmp
            try:
                rows = monitor.get_history()
                self.assertEqual(rows, [])
                panel = monitor.generate_dashboard()
                self.assertIsNotNone(panel)
            finally:
                if orig: os.environ["HSNOOZE_DATA_DIR"] = orig
                else: os.environ.pop("HSNOOZE_DATA_DIR", None)

    def test_locked_database_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "pipeline.db")
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE run_history (id INTEGER PRIMARY KEY, timestamp TEXT, job_id TEXT, "
                "step_current TEXT, status TEXT, duration REAL, detail TEXT)"
            )
            conn.execute("INSERT INTO run_history VALUES (1, '2026-09-15', 'job_1', 'GK0', 'SUCCESS', 1.0, 'ok')")
            conn.commit()
            conn.execute("BEGIN EXCLUSIVE")

            orig = os.environ.get("HSNOOZE_DATA_DIR")
            os.environ["HSNOOZE_DATA_DIR"] = tmp
            try:
                rows = monitor.get_history()
                self.assertEqual(rows, [])
                panel = monitor.generate_dashboard()
                self.assertIsNotNone(panel)
            finally:
                conn.rollback()
                conn.close()
                if orig: os.environ["HSNOOZE_DATA_DIR"] = orig
                else: os.environ.pop("HSNOOZE_DATA_DIR", None)

    def test_empty_table_displays_standby_and_idle(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "pipeline.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE run_history (id INTEGER PRIMARY KEY, timestamp TEXT, job_id TEXT, "
                    "step_current TEXT, status TEXT, duration REAL, detail TEXT)"
                )
            orig = os.environ.get("HSNOOZE_DATA_DIR")
            os.environ["HSNOOZE_DATA_DIR"] = tmp
            try:
                rows = monitor.get_history()
                self.assertEqual(rows, [])
                res = subprocess.run([sys.executable, str(REPO_ROOT / "monitor.py"), "--once"], env=dict(os.environ, HSNOOZE_DATA_DIR=tmp), capture_output=True, text=True)
                self.assertEqual(res.returncode, 0)
                self.assertIn("STANDBY", res.stdout)
                self.assertIn("IDLE", res.stdout)
            finally:
                if orig: os.environ["HSNOOZE_DATA_DIR"] = orig
                else: os.environ.pop("HSNOOZE_DATA_DIR", None)


class TestMonitorVulnerabilities(unittest.TestCase):
    """Adversarial reproduction tests for confirmed bugs in monitor.py."""

    def test_reproduce_markup_error_on_bracketed_file_paths(self):
        """Verifies that escaped bracketed error details do not crash monitor with MarkupError."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "pipeline.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE run_history (id INTEGER PRIMARY KEY, timestamp TEXT, job_id TEXT, "
                    "step_current TEXT, status TEXT, duration REAL, detail TEXT)"
                )
                conn.execute(
                    "INSERT INTO run_history VALUES (1, '2026-09-15', 'job_fail', 'GK2', 'FAILED', 1.0, "
                    "'Error: [/workspace/renderer.py] line 42 failed')"
                )
            orig = os.environ.get("HSNOOZE_DATA_DIR")
            os.environ["HSNOOZE_DATA_DIR"] = tmp
            try:
                panel = monitor.generate_dashboard()
                monitor.console.print(panel)
                self.assertIsNotNone(panel)
            finally:
                if orig: os.environ["HSNOOZE_DATA_DIR"] = orig
                else: os.environ.pop("HSNOOZE_DATA_DIR", None)

    def test_reproduce_attribute_error_on_integer_step(self):
        """Verifies that integer step_current is coerced safely and does not crash with AttributeError."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "pipeline.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE run_history (id INTEGER PRIMARY KEY, timestamp TEXT, job_id TEXT, "
                    "step_current, status TEXT, duration REAL, detail TEXT)"
                )
                conn.execute("INSERT INTO run_history VALUES (1, '2026-09-15', 'job_1', 1, 'SUCCESS', 1.0, 'ok')")
            orig = os.environ.get("HSNOOZE_DATA_DIR")
            os.environ["HSNOOZE_DATA_DIR"] = tmp
            try:
                panel = monitor.generate_dashboard()
                self.assertIsNotNone(panel)
            finally:
                if orig: os.environ["HSNOOZE_DATA_DIR"] = orig
                else: os.environ.pop("HSNOOZE_DATA_DIR", None)

    def test_reproduce_value_error_on_non_numeric_duration(self):
        """Verifies that non-numeric duration strings default safely to 0.0 and do not crash with ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "pipeline.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE run_history (id INTEGER PRIMARY KEY, timestamp TEXT, job_id TEXT, "
                    "step_current TEXT, status TEXT, duration, detail TEXT)"
                )
                conn.execute("INSERT INTO run_history VALUES (1, '2026-09-15', 'job_1', 'GK0', 'SUCCESS', 'invalid', 'ok')")
            orig = os.environ.get("HSNOOZE_DATA_DIR")
            os.environ["HSNOOZE_DATA_DIR"] = tmp
            try:
                panel = monitor.generate_dashboard()
                self.assertIsNotNone(panel)
            finally:
                if orig: os.environ["HSNOOZE_DATA_DIR"] = orig
                else: os.environ.pop("HSNOOZE_DATA_DIR", None)


class TestMonitorCLI(unittest.TestCase):
    """Stress tests for CLI invocation options."""

    def test_cli_once(self):
        res = subprocess.run([sys.executable, str(REPO_ROOT / "monitor.py"), "--once"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("HISTORYSNOOZE MONITOR", res.stdout)

    def test_cli_live_sigint_handling(self):
        proc = subprocess.Popen(
            [sys.executable, str(REPO_ROOT / "monitor.py"), "--live"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(1.0)
        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=3)
        self.assertEqual(proc.returncode, 0, f"Expected clean exit code 0 on SIGINT, got {proc.returncode}")

    def test_cli_help_behavior(self):
        """Verifies CLI behavior with --help."""
        res = subprocess.run([sys.executable, str(REPO_ROOT / "monitor.py"), "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Usage: python monitor.py", res.stdout)


if __name__ == "__main__":
    unittest.main()
