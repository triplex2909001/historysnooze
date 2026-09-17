"""Tests for DevContainer, Docker sandbox configuration, run.sh launcher, and monitor.py."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

class TestDevContainerAndDocker(unittest.TestCase):
    def test_devcontainer_json_specification(self):
        dc_path = REPO_ROOT / ".devcontainer" / "devcontainer.json"
        self.assertTrue(dc_path.exists(), "devcontainer.json missing")
        data = json.loads(dc_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("name"), "HistorySnooze DevContainer")
        self.assertEqual(data.get("remoteUser"), "vscode")
        self.assertEqual(data.get("service"), "sandbox")
        self.assertEqual(data.get("workspaceFolder"), "/workspace")
        self.assertEqual(data.get("dockerComposeFile"), ["../docker/docker-compose.yml"])
        self.assertIn("common-utils", str(data.get("features", {})))
        self.assertIn("python", str(data.get("features", {})))
        exts = data.get("customizations", {}).get("vscode", {}).get("extensions", [])
        self.assertTrue(any("python" in e for e in exts) and any("ruff" in e for e in exts))

    def test_docker_compose_and_dockerfile(self):
        compose_path = REPO_ROOT / "docker" / "docker-compose.yml"
        self.assertTrue(compose_path.exists(), "docker-compose.yml missing")
        data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        svc = data["services"]["sandbox"]
        self.assertEqual(svc.get("user"), "1000:1000")
        self.assertIn("no-new-privileges:true", svc.get("security_opt", []))
        self.assertIn("ALL", svc.get("cap_drop", []))
        self.assertTrue(any("size=64m" in t for t in svc.get("tmpfs", [])))
        self.assertTrue(any(":ro" in v and ".secrets" in v for v in svc.get("volumes", [])))
        df_content = (REPO_ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM python:3.11-slim", df_content)
        self.assertIn("USER vscode", df_content)

    def test_requirements_file(self):
        req_path = REPO_ROOT / "docker" / "requirements.txt"
        self.assertTrue(req_path.exists(), "docker/requirements.txt missing")
        content = req_path.read_text(encoding="utf-8")
        for pkg in ("rich", "pyyaml", "requests", "google-api-python-client", "pytest", "psutil"):
            self.assertIn(pkg, content)

    def test_run_script_launcher_and_security(self):
        run_sh = REPO_ROOT / "run.sh"
        self.assertTrue(run_sh.exists() and os.access(run_sh, os.X_OK), "run.sh missing or not executable")
        ret = subprocess.run(["bash", "-n", str(run_sh)], capture_output=True)
        self.assertEqual(ret.returncode, 0, f"run.sh syntax error: {ret.stderr.decode()}")
        content = run_sh.read_text(encoding="utf-8")
        for expected in ("--rm", "no-new-privileges:true", "--cap-drop ALL", "1000:1000", "size=64m"):
            self.assertIn(expected, content)
        help_res = subprocess.run([str(run_sh), "--help"], capture_output=True, text=True)
        self.assertEqual(help_res.returncode, 0)
        self.assertIn("HistorySnooze", help_res.stdout)

class TestMonitorTUI(unittest.TestCase):
    def test_monitor_module_and_dashboard_generation(self):
        sys.path.insert(0, str(REPO_ROOT))
        import monitor
        panel = monitor.generate_dashboard()
        self.assertIsNotNone(panel)
        ram = monitor.bench_ram()
        self.assertLessEqual(ram, 25.0, f"Monitor RAM {ram:.2f}MB exceeded 25MB threshold")

    def test_monitor_stages_and_quota_radar(self):
        sys.path.insert(0, str(REPO_ROOT))
        import monitor
        stage_names = [s[1] for s in monitor.STAGES]
        for expected in ("INGRESS (GK0)", "SCRIPTING (GK1)", "GENERATION (GK2)", "MASTER (GK3)", "LEDGER (GK4)"):
            self.assertTrue(any(expected in s for s in stage_names), f"Missing stage {expected}")
        res = subprocess.run([sys.executable, str(REPO_ROOT / "monitor.py"), "--once"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        for expected_service in ("Google Drive", "Gemini API", "@youtube2drive_Bot"):
            self.assertIn(expected_service, res.stdout)

    def test_monitor_db_fallback_and_history(self):
        sys.path.insert(0, str(REPO_ROOT))
        import monitor
        with tempfile.TemporaryDirectory() as tmp_dir:
            orig = os.environ.get("HSNOOZE_DATA_DIR")
            try:
                os.environ["HSNOOZE_DATA_DIR"] = tmp_dir
                self.assertEqual(monitor.get_history(), [])
                db_path = Path(tmp_dir) / "data" / "pipeline.db"
                db_path.parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(db_path) as conn:
                    conn.execute(
                        "CREATE TABLE run_history (id INTEGER PRIMARY KEY, timestamp TEXT, job_id TEXT, "
                        "step_current TEXT, status TEXT, duration REAL, detail TEXT)"
                    )
                    conn.execute("INSERT INTO run_history VALUES (1, '2026-09-15', 'job_1', 'GK0', 'SUCCESS', 1.2, 'ok')")
                rows = monitor.get_history()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0][1], "job_1")
            finally:
                if orig:
                    os.environ["HSNOOZE_DATA_DIR"] = orig
                else:
                    os.environ.pop("HSNOOZE_DATA_DIR", None)

    def test_monitor_cli_execution_flags(self):
        cmd = [sys.executable, str(REPO_ROOT / "monitor.py"), "--test-ram"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"monitor.py --test-ram failed: {res.stderr}")
        self.assertIn("Threshold <= 25.0 MB", res.stdout)
        cmd_once = [sys.executable, str(REPO_ROOT / "monitor.py"), "--once"]
        res_once = subprocess.run(cmd_once, capture_output=True, text=True)
        self.assertEqual(res_once.returncode, 0, f"monitor.py --once failed: {res_once.stderr}")
        self.assertIn("HISTORYSNOOZE MONITOR", res_once.stdout)

if __name__ == "__main__":
    unittest.main()
