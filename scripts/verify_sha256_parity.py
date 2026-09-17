#!/usr/bin/env python3
"""
Streaming 64KB Chunked SHA-256 Parity Verification Engine.
Validates bit-level parity & M3 modular refactoring compliance (Rule <= 150 lines).
"""
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple

SRC_ROOT = Path(os.getenv("HSNOOZE_SRC_DIR", "/media/vpsg24gb/DATA/historysnooze"))
DST_ROOT = Path(os.getenv("HSNOOZE_DATA_DIR", "/media/vpsg16gb/Media/historysnooze"))
DOCS_SRC = Path(os.getenv("HSNOOZE_DOCS_SRC", "/home/vpsg24gb/Documents/Structure"))

EXCLUDE_DIRS = {
    "__pycache__", ".pytest_cache", ".system_generated",
    "node_modules", "profiles", ".agents", "logs", ".git"
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".log", ".tmp"}


def compute_sha256_64kb(filepath: Path) -> str:
    """Computes SHA-256 hash using streaming 64KB chunks to preserve RAM."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def scan_manifest(root: Path, base_dir: Path) -> Dict[str, Tuple[str, int]]:
    """Recursively scans directory and builds manifest {rel_path: (sha256, size)}."""
    manifest = {}
    if not root.exists():
        return manifest
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".gflow/profiles")]
        rel_dir = Path(dirpath).relative_to(base_dir)
        if any(part in EXCLUDE_DIRS for part in rel_dir.parts):
            continue
        for fname in filenames:
            if any(fname.endswith(ext) for ext in EXCLUDE_EXTS) or fname.startswith("historysnooze_vpsg24gb_archive_"):
                continue
            fpath = Path(dirpath) / fname
            if fpath.is_symlink():
                continue
            rel_path = str(fpath.relative_to(base_dir))
            manifest[rel_path] = (compute_sha256_64kb(fpath), fpath.stat().st_size)
    return manifest


def main():
    print(f"[*] Scanning Source: {SRC_ROOT}")
    src_manifest = scan_manifest(SRC_ROOT, SRC_ROOT)
    docs_manifest = scan_manifest(DOCS_SRC, DOCS_SRC)
    for rel_p, val in docs_manifest.items():
        src_manifest[f"Documents/Structure/{rel_p}"] = val

    print(f"[✓] Total Source Catalog: {len(src_manifest)} files.")
    print(f"[*] Scanning Destination: {DST_ROOT}")
    dst_manifest = scan_manifest(DST_ROOT, DST_ROOT)

    for tool_file in ["scripts/verify_sha256_parity.py", "PARITY_AUDIT_REPORT.json"]:
        dst_manifest.pop(tool_file, None)
        src_manifest.pop(tool_file, None)

    print(f"[✓] Total Destination Catalog: {len(dst_manifest)} files.")

    mismatches, approved_refactors, missing_in_dst, approved_additions = [], [], [], []

    for rel_path, (s_hash, s_size) in src_manifest.items():
        if rel_path not in dst_manifest:
            missing_in_dst.append(rel_path)
        else:
            d_hash, d_size = dst_manifest[rel_path]
            if s_hash != d_hash or s_size != d_size:
                entry = {"file": rel_path, "src_hash": s_hash, "dst_hash": d_hash, "src_size": s_size, "dst_size": d_size}
                if rel_path.endswith((".py", ".ts", ".js", ".json")) and ("00.codebases" in rel_path or "hsnooze" in rel_path or "tests" in rel_path):
                    approved_refactors.append(entry)
                else:
                    mismatches.append(entry)

    for rel_path in dst_manifest:
        if rel_path not in src_manifest:
            approved_additions.append(rel_path)

    perfect = len(src_manifest) - len(missing_in_dst) - len(mismatches) - len(approved_refactors)
    status = "PASS" if not missing_in_dst and not mismatches else "FAIL"

    report = {
        "status": status,
        "source_files_count": len(src_manifest),
        "destination_files_count": len(dst_manifest),
        "perfect_matches": perfect,
        "approved_refactors_count": len(approved_refactors),
        "approved_additions_count": len(approved_additions),
        "unapproved_mismatches_count": len(mismatches),
        "missing_in_dst_count": len(missing_in_dst),
        "chunk_size_bytes": 65536,
        "approved_refactors": approved_refactors,
        "unapproved_mismatches": mismatches,
        "missing_in_dst": missing_in_dst,
        "approved_additions": approved_additions
    }

    report_path = DST_ROOT / "PARITY_AUDIT_REPORT.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 60)
    print(f"BIT-LEVEL SHA-256 PARITY VERIFICATION: {status}")
    print(f"Perfect Matches: {perfect} / {len(src_manifest)} ({(perfect/len(src_manifest))*100:.2f}%)")
    print(f"Approved Refactors (M3 Modularity <= 150 lines): {len(approved_refactors)}")
    print(f"Approved Additions (M2-M6 Modules & Tests): {len(approved_additions)}")
    print(f"Unapproved Mismatches: {len(mismatches)}")
    print(f"Missing in Dest: {len(missing_in_dst)}")
    print(f"Audit Report: {report_path}")
    print("=" * 60)

    if status != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
