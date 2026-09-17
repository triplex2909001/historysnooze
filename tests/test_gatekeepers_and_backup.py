"""
Test Suite for 5 Gatekeepers & Auto-Backup Engine (Milestone 5).
Rule <= 150 lines strictly enforced.
"""
import gzip, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import auto_backup


class TestGatekeeperSpecifications(unittest.TestCase):
    """Verifies that GATEKEEPERS.md contains complete specs for GK0 through GK4."""

    def setUp(self):
        self.doc_path = REPO_ROOT / "GATEKEEPERS.md"
        self.assertTrue(self.doc_path.exists(), "GATEKEEPERS.md must exist at project root")
        self.content = self.doc_path.read_text(encoding="utf-8")

    def test_gk0_ingress_and_lease_lock_spec(self):
        for term in ["GK0", "Cloudflare KV", "10 min", "lease TTL", "rate limit", "anti-race", "quota"]:
            self.assertIn(term.lower(), self.content.lower(), f"GK0 missing spec term: {term}")

    def test_gk1_raw_input_and_clean_inbox_spec(self):
        for term in ["GK1", "15 parts", "150", "beats", "syntax", "RMS", "00.INBOX"]:
            self.assertIn(term.lower(), self.content.lower(), f"GK1 missing spec term: {term}")

    def test_gk2_processing_integrity_spec(self):
        for term in ["GK2", "audio chunk", "4K", "3840x2160", "color", "0.5s silence"]:
            self.assertIn(term.lower(), self.content.lower(), f"GK2 missing spec term: {term}")

    def test_gk3_master_qc_spec(self):
        for term in ["GK3", "Ken Burns", "4K 30fps", "dimming", "EBU R128", "-16 LUFS", "black frame", "1.0s", "2.0s"]:
            self.assertIn(term.lower(), self.content.lower(), f"GK3 missing spec term: {term}")

    def test_gk4_ledger_sync_and_alert_spec(self):
        for term in ["GK4", "atomic", "Central Ledger", "Google Sheets", "@youtube2drive_Bot", "8798886722", "dead-letter"]:
            self.assertIn(term.lower(), self.content.lower(), f"GK4 missing spec term: {term}")


class TestAutoBackupEngine(unittest.TestCase):
    """Tests auto_backup.py CLI, DB compression, zero-leak filtering, and folder resolution."""

    def test_cli_help_and_dry_run_flags(self):
        script = REPO_ROOT / "scripts" / "auto_backup.py"
        res_help = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
        self.assertEqual(res_help.returncode, 0)
        self.assertIn("auto_backup.py", res_help.stdout)

        res_dry = subprocess.run([sys.executable, str(script), "--dry-run"], capture_output=True, text=True)
        self.assertEqual(res_dry.returncode, 0)
        self.assertIn("Auto-Backup", res_dry.stdout)

    def test_database_compression_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db_file = tmp / "test_pipeline.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("CREATE TABLE tasks (id INT, status TEXT)")
            conn.execute("INSERT INTO tasks VALUES (1, 'DONE'), (2, 'PENDING')")
            conn.commit()
            conn.close()

            gz_out = auto_backup.compress_database(db_file, tmp / "artifacts", "20260915_120000")
            self.assertTrue(gz_out.exists())
            self.assertEqual(gz_out.name, "snapshot_test_pipeline_20260915_120000.db.gz")

            restored_db = tmp / "restored.db"
            with gzip.open(gz_out, "rb") as f_in, open(restored_db, "wb") as f_out:
                f_out.write(f_in.read())

            r_conn = sqlite3.connect(str(restored_db))
            rows = r_conn.execute("SELECT id, status FROM tasks ORDER BY id").fetchall()
            r_conn.close()
            self.assertEqual(rows, [(1, "DONE"), (2, "PENDING")])

    def test_zero_leak_filter_exclusions(self):
        leak_paths = [
            Path("/app/.secrets/token.json"), Path("/app/.env"), Path("/app/config/token.json"),
            Path("/app/credentials/passwords.txt"), Path("/app/__pycache__/module.cpython-312.pyc"),
            Path("/app/.pytest_cache/v/cache/nodeids"), Path("/app/credentials.json"),
            Path("/app/secret.sqlite"), Path("/app/client_secret.json"), Path("/app/api_key.sqlite"),
        ]
        for lp in leak_paths:
            self.assertTrue(auto_backup.is_secret_or_cache(lp), f"Must exclude secret/cache: {lp}")

        safe_paths = [
            Path("/app/history.db"), Path("/app/data.sqlite"),
            Path("/app/gdrive_folder_map.json"), Path("/app/pipeline_schema.json"),
        ]
        for sp in safe_paths:
            self.assertFalse(auto_backup.is_secret_or_cache(sp), f"Must include safe path: {sp}")

    def test_backup_folder_id_and_token_fallback(self):
        fid = auto_backup.get_backup_folder_id()
        self.assertTrue("00.BACKUP" in fid or "mock" in fid)
        self.assertEqual(auto_backup.execute_backup(dry_run=True), 0)

    def test_sqlite_wal_mode_backup_consistency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db_file = tmp / "wal_test.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("CREATE TABLE live_data (id INT, val TEXT)")
            conn.execute("INSERT INTO live_data VALUES (1, 'active_wal_frame')")
            conn.commit()
            gz_out = auto_backup.compress_database(db_file, tmp / "artifacts", "20260915_wal")
            conn.close()
            self.assertTrue(gz_out.exists())

            restored = tmp / "restored_wal.db"
            with gzip.open(gz_out, "rb") as f_in, open(restored, "wb") as f_out:
                f_out.write(f_in.read())
            r_conn = sqlite3.connect(str(restored))
            rows = r_conn.execute("SELECT id, val FROM live_data").fetchall()
            r_conn.close()
            self.assertEqual(rows, [(1, "active_wal_frame")])

    def test_invalid_token_graceful_fallback(self):
        script = REPO_ROOT / "scripts" / "auto_backup.py"
        res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Auto-Backup", res.stdout)
        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(auto_backup.execute_backup(), 0)


if __name__ == "__main__":
    unittest.main()
