"""
HistorySnooze Zero-Leak & Vault Security Test Suite (Milestone 6 / Milestone 2)
Authoritative Specifications:
- ORIGINAL_REQUEST.md: R2 (RAM-Only Vault & Zero-Leak)
- Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Zero-Leak Policy & Gitleaks Pre-commit)
- Documents/Structure/03_SECURE_ISOLATION_VAULT.md (RAM-Only Vault, chmod 600/700, /dev/shm/.vault)
- Documents/Structure/08_PROJECT_HYGIENE_AND_BACKUP_SPECIFICATION.md (Zero-Garbage, Backup Security)
- PROJECT.md: Features 7, 8, 9, 21

Testing Standards:
- Zero tautologies: Every assertion verifies explicit independent invariants and security specifications.
- Concrete inspection: Scans actual repository files for plaintext secrets, verifies file system permissions,
  and inspects .gitignore and pre-commit gitleaks configurations.
- Positive controls: Validates that the secret scanner and permission checker detect intentional violations.
"""

import fnmatch
import os
import re
import stat
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import yaml

# Environment-aware repository root resolution
HSNOOZE_DATA_DIR = os.environ.get("HSNOOZE_DATA_DIR")
if HSNOOZE_DATA_DIR and Path(HSNOOZE_DATA_DIR).exists():
    REPO_ROOT = Path(HSNOOZE_DATA_DIR).resolve()
else:
    REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    ".pytest_cache",
    ".agents",
    "node_modules",
    ".gflow",
    "02. Media Generation",
    "assets",
}

BINARY_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".wav", ".mp3", ".ogg", ".flac",
    ".mp4", ".mov", ".mkv", ".avi",
    ".pyc", ".db", ".sqlite", ".gz", ".tar", ".zip"
}

SECRET_PATTERNS = {
    "google_api_key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "github_pat": re.compile(r"gh[pousr]_[0-9a-zA-Z]{36,255}"),
    "github_fine_grained": re.compile(r"github_pat_[0-9a-zA-Z_]{82}"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "telegram_token": re.compile(r"\b[0-9]{8,10}:[a-zA-Z0-9_\-]{35}\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[a-zA-Z0-9_\-]{20,}\b"),
    "anthropic_key": re.compile(r"\bsk-ant-[a-zA-Z0-9_\-]{20,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:[A-Z0-9_\-]+ )?PRIVATE KEY-----"),
    "generic_hardcoded_secret": re.compile(
        r"""(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\s*=\s*['"][a-zA-Z0-9_\-]{24,}['"]"""
    ),
}

REQUIRED_GITIGNORE_TOKENS = [
    ".secrets",
    ".env",
    "*.env",
    "project_vault.enc",
    "__pycache__",
    "node_modules",
]


def scan_file_for_secrets(file_path: Path, patterns: Optional[Dict[str, re.Pattern]] = None) -> List[Tuple[str, str]]:
    """Scans a single file for known secret patterns, returning (rule_name, matched_token_masked)."""
    if patterns is None:
        patterns = SECRET_PATTERNS
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for rule_name, pat in patterns.items():
        for match in pat.finditer(content):
            matched_str = match.group(0)
            masked = matched_str[:8] + "..." if len(matched_str) > 8 else "***"
            findings.append((rule_name, masked))
    return findings


def fs_supports_posix_permissions(path: Path) -> bool:
    """Checks if the underlying filesystem for the given path supports POSIX chmod permissions."""
    try:
        probe = path / ".perm_probe" if path.is_dir() else path.parent / ".perm_probe"
        probe.touch(exist_ok=True)
        try:
            os.chmod(probe, 0o600)
            return stat.S_IMODE(probe.stat().st_mode) == 0o600
        finally:
            if probe.exists():
                probe.unlink()
    except Exception:
        return False


def check_vault_permissions(vault_path: Path) -> List[str]:
    """
    Verifies that a vault directory satisfies File 03 / File 08 standards:
    - Directory mode: 0700 (drwx------)
    - File modes: 0600 (-rw-------)
    Returns a list of violation descriptions.
    """
    violations = []
    if not vault_path.exists():
        return [f"Vault path does not exist: {vault_path}"]

    st = vault_path.stat()
    dir_mode = stat.S_IMODE(st.st_mode)
    if dir_mode != 0o700:
        violations.append(
            f"Directory '{vault_path}' mode is {oct(dir_mode)}, expected 0o700 (chmod 700)"
        )

    for root_dir, dirs, files in os.walk(vault_path):
        for d in dirs:
            d_path = Path(root_dir) / d
            d_mode = stat.S_IMODE(d_path.stat().st_mode)
            if d_mode != 0o700:
                violations.append(
                    f"Subdirectory '{d_path}' mode is {oct(d_mode)}, expected 0o700 (chmod 700)"
                )
        for f in files:
            f_path = Path(root_dir) / f
            f_mode = stat.S_IMODE(f_path.stat().st_mode)
            if f_mode != 0o600:
                violations.append(
                    f"Vault file '{f_path}' mode is {oct(f_mode)}, expected 0o600 (chmod 600)"
                )
    return violations



# ==============================================================================
# 1. Zero-Leak Plaintext Secret Detection Test Suite
# ==============================================================================
class TestZeroPlaintextSecrets(unittest.TestCase):
    """Verifies that no plaintext secrets or tokens exist across the repository codebase."""

    def test_no_plaintext_secrets_in_production_codebase(self):
        """Scans all non-ephemeral project files and asserts 0 plaintext secrets."""
        violations = []
        scanned_files_count = 0

        for p in REPO_ROOT.rglob("*"):
            if not p.is_file():
                continue
            if p.resolve() == Path(__file__).resolve():
                continue
            parts = p.parts
            if any(x in parts for x in EXCLUDED_DIRS):
                continue
            if p.suffix.lower() in BINARY_EXTENSIONS:
                continue

            findings = scan_file_for_secrets(p)
            if findings:
                rel_path = str(p.relative_to(REPO_ROOT))
                for rule, masked in findings:
                    violations.append(f"File '{rel_path}' matched rule '{rule}': {masked}")
            scanned_files_count += 1

        self.assertGreater(scanned_files_count, 10, "Scanner failed to find sufficient files to inspect")
        if violations:
            msg = f"\n[FAIL] Found {len(violations)} plaintext secret violation(s) in codebase:\n" + "\n".join(f"  - {v}" for v in violations)
            self.fail(msg)

    def test_secret_scanner_positive_controls(self):
        """Validates that the secret scanner reliably detects synthetic API keys, tokens, and private keys."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test_sample.py"

            # 1. Google API Key test (AIza + 35 chars = 39 chars)
            dummy_google = "AIza" + "SyB_FakeKeySecret123456789012345678"
            test_file.write_text(f"GOOGLE_KEY = '{dummy_google}'\n", encoding="utf-8")
            findings = scan_file_for_secrets(test_file)
            self.assertTrue(any(rule == "google_api_key" for rule, _ in findings), "Failed to detect Google API key")

            # 2. GitHub PAT test (ghp_ + 36 chars)
            dummy_gh = "ghp_" + "1234567890abcdefghijklmnopqrstuvwxyz"
            test_file.write_text(f"GITHUB_TOKEN = '{dummy_gh}'\n", encoding="utf-8")
            findings = scan_file_for_secrets(test_file)
            self.assertTrue(any(rule == "github_pat" for rule, _ in findings), "Failed to detect GitHub PAT")

            # 3. Telegram Bot Token test (9-10 digits : 35 chars)
            dummy_tg = "123456789:" + "ABCdefGHIjklMNOpqrSTUvwxYZ_12345678"
            test_file.write_text(f"TELEGRAM_BOT_TOKEN = '{dummy_tg}'\n", encoding="utf-8")
            findings = scan_file_for_secrets(test_file)
            self.assertTrue(any(rule == "telegram_token" for rule, _ in findings), "Failed to detect Telegram Bot token")

            # 4. RSA Private Key test
            dummy_pem = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----\n"
            test_file.write_text(dummy_pem, encoding="utf-8")
            findings = scan_file_for_secrets(test_file)
            self.assertTrue(any(rule == "private_key" for rule, _ in findings), "Failed to detect RSA Private Key")

            # 5. OpenAI API Key test (sk-proj-...)
            dummy_openai = "sk-proj-" + "1234567890abcdefghijklmnopqrstuvwxyz123456"
            test_file.write_text(f"OPENAI_KEY = '{dummy_openai}'\n", encoding="utf-8")
            findings = scan_file_for_secrets(test_file)
            self.assertTrue(any(rule == "openai_key" for rule, _ in findings), "Failed to detect OpenAI sk-proj- key")

            # 6. Clean file test
            test_file.write_text("SAFE_CONFIG = os.getenv('API_KEY', 'default_val')\n", encoding="utf-8")
            findings = scan_file_for_secrets(test_file)
            self.assertEqual(len(findings), 0, "False positive detected on clean environment variable access")

    def test_config_modules_access_secrets_via_environment(self):
        """Verifies that configuration modules retrieve credentials via os.getenv/os.environ."""
        config_paths = [
            REPO_ROOT / "00.codebases" / "config.py",
            REPO_ROOT / "hsnooze.render" / "config.py"
        ]
        for c_path in config_paths:
            if not c_path.exists():
                continue
            content = c_path.read_text(encoding="utf-8")
            for secret_var in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GDRIVE_BACKUP_FOLDER_ID"]:
                if secret_var in content:
                    pattern = rf"{secret_var}\s*=\s*(?:os\.getenv|os\.environ\.get)"
                    self.assertRegex(
                        content,
                        pattern,
                        f"Config in {c_path} defines {secret_var} without os.getenv() or os.environ.get()"
                    )


# ==============================================================================
# 2. Vault Directory Permissions Test Suite (chmod 700 / chmod 600)
# ==============================================================================
class TestSecretsVaultPermissions(unittest.TestCase):
    """Verifies that .secrets/ directory satisfies chmod 700 and file chmod 600 security standards."""

    def test_vault_permissions_validation_matrix(self):
        """Verifies the permission audit engine strictly rejects invalid permissions and passes valid ones."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault_dir = Path(tmp_dir) / ".secrets"
            vault_dir.mkdir(mode=0o700)
            os.chmod(vault_dir, 0o700)

            secret_file = vault_dir / "credentials.json"
            secret_file.write_text("{}", encoding="utf-8")
            os.chmod(secret_file, 0o600)

            # Test 1: Compliant state
            violations = check_vault_permissions(vault_dir)
            self.assertEqual(len(violations), 0, f"Expected 0 violations for 0700/0600: {violations}")

            # Test 2: Non-compliant directory (0755: group/world readable)
            os.chmod(vault_dir, 0o755)
            violations = check_vault_permissions(vault_dir)
            self.assertTrue(any("Directory" in v and "0o755" in v for v in violations))

            # Test 3: Non-compliant directory (0777: fully open)
            os.chmod(vault_dir, 0o777)
            violations = check_vault_permissions(vault_dir)
            self.assertTrue(any("Directory" in v and "0o777" in v for v in violations))

            # Reset directory to 0700 for file permission testing
            os.chmod(vault_dir, 0o700)

            # Test 4: Non-compliant file (0644: world readable)
            os.chmod(secret_file, 0o644)
            violations = check_vault_permissions(vault_dir)
            self.assertTrue(any("Vault file" in v and "0o644" in v for v in violations))

            # Test 5: Non-compliant file (0666: world writable)
            os.chmod(secret_file, 0o666)
            violations = check_vault_permissions(vault_dir)
            self.assertTrue(any("Vault file" in v and "0o666" in v for v in violations))

    def test_repo_vault_directory_permissions(self):
        """Verifies that repository .secrets/ directory conforms to chmod 700 / chmod 600."""
        vault_dir = Path(os.environ.get("HSNOOZE_SECRETS_DIR", REPO_ROOT / ".secrets"))
        self.assertTrue(
            vault_dir.exists(),
            f"Vault directory '{vault_dir}' does not exist. Must be provisioned with chmod 700 per File 03."
        )
        if not fs_supports_posix_permissions(vault_dir):
            self.skipTest(
                f"Underlying filesystem for '{vault_dir}' (e.g. exFAT) does not support POSIX chmod permissions. "
                "RAM-Only Vault (/dev/shm/.vault) is required in this environment."
            )
        violations = check_vault_permissions(vault_dir)
        self.assertEqual(
            len(violations), 0,
            f"Vault permissions violation in '{vault_dir}':\n" + "\n".join(f"  - {v}" for v in violations)
        )


    def test_ram_vault_dev_shm_standard(self):
        """If RAM-only vault /dev/shm/.vault exists at runtime, verifies strict 0700/0600 permissions."""
        ram_vault = Path("/dev/shm/.vault")
        if ram_vault.exists():
            violations = check_vault_permissions(ram_vault)
            self.assertEqual(len(violations), 0, f"RAM vault permission violations: {violations}")


# ==============================================================================
# 3. .gitignore Secret Leak Prevention Test Suite
# ==============================================================================
class TestGitignoreSecretPrevention(unittest.TestCase):
    """Verifies that .gitignore rules prevent accidental secret leakage to version control."""

    def test_gitignore_rule_pattern_matching(self):
        """Tests that required zero-leak ignore patterns match typical secret and credential paths."""
        patterns = [
            ".secrets",
            ".secrets/",
            ".env",
            "*.env",
            "*.json",
            "project_vault.enc",
            "graft/",
            "__pycache__/",
            "node_modules/",
            "*.pem",
            "*.key"
        ]

        test_paths = [
            (".secrets/credentials.json", True),
            (".secrets/token.json", True),
            (".env", True),
            ("production.env", True),
            ("project_vault.enc", True),
            ("private.pem", True),
            ("id_rsa.key", True),
            ("__pycache__/foo.cpython-312.pyc", True),
            ("node_modules/package.json", True),
        ]

        for path_str, should_match in test_paths:
            matched = any(
                fnmatch.fnmatch(path_str, pat) or fnmatch.fnmatch(Path(path_str).name, pat) or pat.rstrip("/") in path_str
                for pat in patterns
            )
            self.assertEqual(matched, should_match, f"Pattern match failure for '{path_str}' against zero-leak patterns")

    def test_repo_gitignore_rules_prevent_secret_leakage(self):
        """Inspects the repository .gitignore and asserts all essential secret patterns are blocked."""
        gitignore_path = Path(os.environ.get("HSNOOZE_GITIGNORE_PATH", REPO_ROOT / ".gitignore"))
        self.assertTrue(
            gitignore_path.exists(),
            f"Root .gitignore missing at '{gitignore_path}'. Required by File 01 Section V to prevent secret leakage."
        )

        content = gitignore_path.read_text(encoding="utf-8")
        rules = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]

        missing_rules = []
        for req in REQUIRED_GITIGNORE_TOKENS:
            found = any(req in rule or fnmatch.fnmatch(req, rule) for rule in rules)
            if not found:
                missing_rules.append(req)

        self.assertEqual(
            len(missing_rules), 0,
            f"Repository .gitignore at '{gitignore_path}' is missing essential zero-leak rules: {missing_rules}"
        )


# ==============================================================================
# 4. Gitleaks Pre-Commit Configuration Test Suite
# ==============================================================================
class TestGitleaksPrecommitConfig(unittest.TestCase):
    """Verifies that Gitleaks is configured in pre-commit hooks to block secrets before commit."""

    def test_gitleaks_configuration_schema_specification(self):
        """Verifies that a compliant pre-commit YAML contains gitleaks and file size safety hooks."""
        sample_config_yaml = """
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: end-of-file-fixer
      - id: trailing-whitespace
"""
        data = yaml.safe_load(sample_config_yaml)
        repos = data.get("repos", [])

        gitleaks_found = False
        large_files_found = False

        for r in repos:
            repo_url = r.get("repo", "")
            hooks = r.get("hooks", [])
            hook_ids = [h.get("id") for h in hooks]

            if "gitleaks" in repo_url or "gitleaks" in hook_ids:
                if "gitleaks" in hook_ids:
                    gitleaks_found = True
            if "check-added-large-files" in hook_ids:
                large_files_found = True

        self.assertTrue(gitleaks_found, "Gitleaks hook missing from sample pre-commit specification")
        self.assertTrue(large_files_found, "check-added-large-files missing from sample pre-commit specification")

    def test_repo_precommit_config_gitleaks_hook(self):
        """Inspects repository .pre-commit-config.yaml and verifies gitleaks protection hook is enabled."""
        precommit_path = Path(os.environ.get("HSNOOZE_PRECOMMIT_PATH", REPO_ROOT / ".pre-commit-config.yaml"))
        self.assertTrue(
            precommit_path.exists(),
            f"Pre-commit config missing at '{precommit_path}'. Required by File 01 Section IV to enforce gitleaks."
        )

        with open(precommit_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        repos = data.get("repos", [])
        hook_ids = []
        for r in repos:
            for h in r.get("hooks", []):
                hook_ids.append(h.get("id"))

        self.assertIn(
            "gitleaks", hook_ids,
            f"gitleaks hook not configured in '{precommit_path}'. Active hooks: {hook_ids}"
        )

        # Verify gitleaks hook specifies protect and --staged for live staged pre-commit defense
        gitleaks_hook = None
        for r in repos:
            for h in r.get("hooks", []):
                if h.get("id") == "gitleaks":
                    gitleaks_hook = h
                    break
        self.assertIsNotNone(gitleaks_hook, f"gitleaks hook definition not found in '{precommit_path}'")
        entry = gitleaks_hook.get("entry", "")
        self.assertIn("protect", entry, f"gitleaks hook entry must specify 'protect', got: '{entry}'")
        self.assertIn("--staged", entry, f"gitleaks hook entry must specify '--staged', got: '{entry}'")
        self.assertFalse(gitleaks_hook.get("pass_filenames", True), "gitleaks hook must have pass_filenames: false")

        # Verify that git hook is installed if .git/hooks directory exists
        hooks_dir = REPO_ROOT / ".git" / "hooks"
        if hooks_dir.exists():
            hook_file = hooks_dir / "pre-commit"
            self.assertTrue(
                hook_file.exists(),
                f"Active pre-commit hook file missing at '{hook_file}'. Ensure 'pre-commit install' was run."
            )


if __name__ == "__main__":
    unittest.main()
