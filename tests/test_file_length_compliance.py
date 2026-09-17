"""
HistorySnooze File Length & Modularity Compliance Test Suite (Milestone 6 / Milestone 3)
Authoritative Specifications:
- ORIGINAL_REQUEST.md: R3 (Tái Cấu Trúc Mã Nguồn Đơn Nhiệm Chuẩn Modularity - Rule <= 150 dòng/file)
- Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Section III: Tiêu chuẩn Modular & Chống Đứt Gãy: <= 150 dòng/file)
- Documents/Structure/03_SECURE_ISOLATION_VAULT.md (Section 5: Kiểm soát Context Rot: Chia nhỏ module < 150 dòng/file)
- Documents/Structure/08_PROJECT_HYGIENE_AND_BACKUP_SPECIFICATION.md (Section III & V: Script backup & operational scripts <= 150 dòng)
- PROJECT.md: Pillar 1 (Modularity & Single Responsibility), Features 11, 12, 13, 14, 20, 22

Testing Standards:
- Zero tautologies: Every assertion verifies explicit file length counts against the 150-line upper bound.
- Informative error reporting: When files exceed 150 lines, outputs exact paths, line counts, and excess line deltas.
- Boundary testing: Tests exact boundary conditions (150 lines compliant, 151 lines non-compliant).
"""

import os
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
    "venv",
    ".pytest_cache",
    ".agents",
    "node_modules",
    ".gflow",
    "graft",
    "02. Media Generation",
    "assets",
}

PRODUCTION_MODULE_DIRS = {
    "00.codebases",
    "hsnooze.render",
    "hsnooze.omni",
    "hsnooze.scripting",
    "scripts",
}

MAX_ALLOWED_LINES = 150


def count_file_lines(file_path: Path) -> int:
    """Counts the total physical lines in a file, handling UTF-8 decoding cleanly."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception as err:
        raise RuntimeError(f"Unable to read file '{file_path}': {err}")


def is_production_logic_file(file_path: Path, repo_root: Path) -> bool:
    """
    Determines if a Python file is an operational/production logic script.
    Excludes test files in tests/ and agent metadata.
    """
    try:
        rel = file_path.relative_to(repo_root)
    except ValueError:
        return False

    parts = rel.parts
    if not parts:
        return False

    # Exclude tests directory
    if "tests" in parts:
        return False

    # Check if in known production modules
    if any(m in parts for m in PRODUCTION_MODULE_DIRS):
        return True

    # Root-level production logic scripts (e.g. monitor.py, run.sh helpers)
    if len(parts) == 1 and file_path.suffix == ".py":
        return True

    return False


def scan_python_files(repo_root: Path, exclude_dirs: Optional[Set[str]] = None) -> List[Tuple[Path, int]]:
    """
    Scans repo_root for all Python files (excluding specified directories).
    Returns a list of (Path, line_count) tuples.
    """
    if exclude_dirs is None:
        exclude_dirs = EXCLUDED_DIRS

    results = []
    for root_dir, dirs, files in os.walk(repo_root, followlinks=False):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for fname in files:
            if fname.endswith(".py"):
                fpath = Path(root_dir) / fname
                line_count = count_file_lines(fpath)
                results.append((fpath, line_count))

    return results


def format_compliance_failure_message(
    violating_files: List[Tuple[Path, int]],
    total_scanned: int,
    max_lines: int,
    repo_root: Path
) -> str:
    """Formats a detailed, human-readable compliance failure diagnostic."""
    violating_files_sorted = sorted(violating_files, key=lambda x: x[1], reverse=True)
    header = (
        f"\n{'=' * 80}\n"
        f"🚨 FILE LENGTH COMPLIANCE VIOLATION (Rule <= {max_lines} lines/file)\n"
        f"Authoritative Requirement: R3 & Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md\n"
        f"Scanned {total_scanned} files. Found {len(violating_files)} file(s) exceeding {max_lines} lines:\n"
        f"{'-' * 80}\n"
        f"{'Lines':>7} | {'Excess':>7} | File Path\n"
        f"{'-' * 80}\n"
    )
    rows = []
    for fpath, lines in violating_files_sorted:
        try:
            rel = str(fpath.relative_to(repo_root))
        except ValueError:
            rel = str(fpath)
        excess = lines - max_lines
        rows.append(f"{lines:>7d} | {excess:>+7d} | {rel}")

    footer = (
        f"\n{'-' * 80}\n"
        f"REMEDIATION ACTION REQUIRED:\n"
        f"Decompose the above scripts into single-responsibility submodules strictly <= {max_lines} lines.\n"
        f"Operational refactoring targets are defined in PROJECT.md (Features 11, 12, 13, 14).\n"
        f"{'=' * 80}\n"
    )
    return header + "\n".join(rows) + footer


# ==============================================================================
# 1. Production Python Files Length Compliance Test Suite (Rule <= 150 Lines)
# ==============================================================================
class TestProductionFileLengthCompliance(unittest.TestCase):
    """
    Enforces that 100% of production/operational Python scripts strictly contain <= 150 lines.
    Covers: 00.codebases/, hsnooze.render/, hsnooze.omni/, hsnooze.scripting/, scripts/, and root scripts.
    """

    def test_production_python_files_strictly_contain_at_most_150_lines(self):
        """Scans all operational Python logic files and asserts line count <= 150."""
        all_py_files = scan_python_files(REPO_ROOT)
        production_files = [
            (fpath, lines) for fpath, lines in all_py_files
            if is_production_logic_file(fpath, REPO_ROOT)
        ]

        self.assertGreater(
            len(production_files), 0,
            f"No production Python files found in repository root: {REPO_ROOT}"
        )

        violating_files = [
            (fpath, lines) for fpath, lines in production_files
            if lines > MAX_ALLOWED_LINES
        ]

        if violating_files:
            fail_msg = format_compliance_failure_message(
                violating_files=violating_files,
                total_scanned=len(production_files),
                max_lines=MAX_ALLOWED_LINES,
                repo_root=REPO_ROOT
            )
            self.fail(fail_msg)

    def test_production_submodule_backup_scripts_compliance(self):
        """Specifically verifies that scripts/auto_backup.py (when present) satisfies <= 150 lines."""
        backup_script = REPO_ROOT / "scripts" / "auto_backup.py"
        if backup_script.exists():
            lines = count_file_lines(backup_script)
            self.assertLessEqual(
                lines, MAX_ALLOWED_LINES,
                f"scripts/auto_backup.py has {lines} lines, exceeding the {MAX_ALLOWED_LINES} line limit per File 08."
            )


# ==============================================================================
# 2. Repository-Wide Python Files Length Audit Test Suite
# ==============================================================================
class TestRepositoryWideFileLengthAudit(unittest.TestCase):
    """
    Performs full repository inventory audit across all Python files.
    Identifies total codebase line census and all files exceeding 150 lines.
    """

    def test_repository_python_file_inventory_and_line_census(self):
        """Audits all Python files in the repository and verifies scanner correctness."""
        all_py_files = scan_python_files(REPO_ROOT)
        self.assertGreaterEqual(
            len(all_py_files), 30,
            f"Expected at least 30 Python files in repository, found {len(all_py_files)}"
        )

        total_lines = sum(lines for _, lines in all_py_files)
        self.assertGreater(total_lines, 5000, f"Total codebase lines unexpectedly small: {total_lines}")

        compliant_files = [(f, l) for f, l in all_py_files if l <= MAX_ALLOWED_LINES]
        violating_files = [(f, l) for f, l in all_py_files if l > MAX_ALLOWED_LINES]

        compliance_pct = (len(compliant_files) / len(all_py_files)) * 100.0

        # Informative assertion: prints census summary
        print(
            f"\n[CENSUS] Total Python files: {len(all_py_files)} | "
            f"Compliant (<= 150): {len(compliant_files)} ({compliance_pct:.1f}%) | "
            f"Exceeding (> 150): {len(violating_files)} | "
            f"Total Lines: {total_lines:,}"
        )


# ==============================================================================
# 3. Compliance Scanner Unit & Boundary Verification Test Suite
# ==============================================================================
class TestFileLengthScannerUnitTests(unittest.TestCase):
    """Verifies that the line counting scanner logic correctly handles edge cases and boundary limits."""

    def test_scanner_boundary_exact_150_lines_is_compliant(self):
        """A file with exactly 150 lines must pass compliance check."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "exact_150.py"
            file_path.write_text("\n".join(f"# Line {i}" for i in range(1, 151)) + "\n", encoding="utf-8")
            count = count_file_lines(file_path)
            self.assertEqual(count, 150)
            self.assertLessEqual(count, MAX_ALLOWED_LINES)

    def test_scanner_boundary_151_lines_is_non_compliant(self):
        """A file with exactly 151 lines must fail compliance check (boundary violation)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "violating_151.py"
            file_path.write_text("\n".join(f"# Line {i}" for i in range(1, 152)) + "\n", encoding="utf-8")
            count = count_file_lines(file_path)
            self.assertEqual(count, 151)
            self.assertGreater(count, MAX_ALLOWED_LINES)

    def test_scanner_empty_file_zero_lines(self):
        """An empty file (0 lines) must pass compliance check."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "empty.py"
            file_path.write_text("", encoding="utf-8")
            count = count_file_lines(file_path)
            self.assertEqual(count, 0)
            self.assertLessEqual(count, MAX_ALLOWED_LINES)

    def test_scanner_directory_exclusion_filtering(self):
        """Scanner must exclude files inside .git, __pycache__, .venv, and .agents."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "clean.py").write_text("# clean\n", encoding="utf-8")
            (root / ".venv").mkdir()
            (root / ".venv" / "hidden.py").write_text("# venv\n", encoding="utf-8")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "cached.py").write_text("# pycache\n", encoding="utf-8")
            (root / ".agents").mkdir()
            (root / ".agents" / "agent.py").write_text("# agent\n", encoding="utf-8")

            scanned = scan_python_files(root, exclude_dirs={".venv", "__pycache__", ".agents"})
            scanned_names = [f.name for f, _ in scanned]
            self.assertIn("clean.py", scanned_names)
            self.assertNotIn("hidden.py", scanned_names)
            self.assertNotIn("cached.py", scanned_names)
            self.assertNotIn("agent.py", scanned_names)

    def test_is_production_logic_file_classification(self):
        """Verifies correct segregation between operational code and test code."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prod_file = root / "00.codebases" / "script.py"
            render_file = root / "hsnooze.render" / "renderer.py"
            test_file = root / "tests" / "test_module.py"

            self.assertTrue(is_production_logic_file(prod_file, root))
            self.assertTrue(is_production_logic_file(render_file, root))
            self.assertFalse(is_production_logic_file(test_file, root))


if __name__ == "__main__":
    unittest.main()
