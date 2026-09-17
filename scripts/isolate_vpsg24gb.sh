#!/usr/bin/env bash
set -euo pipefail

# HistorySnooze vpsg24gb Safe Isolation & Decommissioning Script
# Enforces parity verification, garbage purge, archival, and read-only lockdown.

SRC_DIR="${HSNOOZE_SRC_DIR:-/media/vpsg24gb/DATA/historysnooze}"
DST_DIR="${HSNOOZE_DST_DIR:-/media/vpsg16gb/Media/historysnooze}"
ARCHIVE_DIR="${HSNOOZE_ARCHIVE_DIR:-}"
FORCE=0
DRY_RUN=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]
Options:
  --dry-run            Simulate isolation steps without making modifications
  --force              Bypass interactive confirmation prompt
  --src <dir>          Source directory (default: $SRC_DIR)
  --dest <dir>         Destination directory (default: $DST_DIR)
  --archive-dir <dir>  Archive destination directory (default: source dir)
  -h, --help           Show this help message
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    --src) SRC_DIR="$2"; shift 2 ;;
    --dest) DST_DIR="$2"; shift 2 ;;
    --archive-dir) ARCHIVE_DIR="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Error: Unknown argument '$1'" >&2; exit 1 ;;
  esac
done
ARCHIVE_DIR="${ARCHIVE_DIR:-$SRC_DIR}"

echo "=== HistorySnooze vpsg24gb Isolation Protocol ==="
echo "Source:      $SRC_DIR"
echo "Destination: $DST_DIR"

# Safeguard 1: Check destination exists, is populated, and contains core directories
if [[ ! -d "$DST_DIR" ]] || [[ -z "$(ls -A "$DST_DIR" 2>/dev/null)" ]]; then
  echo "Error: Destination '$DST_DIR' does not exist or is empty. Aborting." >&2
  exit 1
fi
if [[ ! -d "$DST_DIR/00.codebases" ]] && [[ ! -d "$DST_DIR/tests" ]]; then
  echo "Error: Destination '$DST_DIR' missing core directories (00.codebases or tests). Aborting." >&2
  exit 1
fi
echo "[OK] Safeguard 1: Destination directory exists and is populated."

# Safeguard 2: Verify Parity Audit Report exists and is PASS
PARITY_REPORT="$DST_DIR/PARITY_AUDIT_REPORT.json"
if [[ ! -f "$PARITY_REPORT" ]]; then
  echo "Error: Parity report missing at '$PARITY_REPORT'. Aborting." >&2
  exit 1
fi
if ! grep -q '"status"[[:space:]]*:[[:space:]]*"PASS"' "$PARITY_REPORT"; then
  echo "Error: Parity audit status is not PASS in '$PARITY_REPORT'. Aborting." >&2
  exit 1
fi
echo "[OK] Safeguard 2: Parity audit status verified as PASS."

# Safeguard 3: Force flag or interactive confirmation
if [[ "$FORCE" -ne 1 ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[DRY-RUN] Dry run mode enabled; skipping confirmation."
  elif [[ -t 0 ]]; then
    read -rp "Lock down and isolate '$SRC_DIR'? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[yY]$ ]]; then
      echo "Aborted by user." >&2
      exit 1
    fi
  else
    echo "Error: Non-interactive run requires --force flag. Aborting." >&2
    exit 1
  fi
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[DRY-RUN] Would purge cache files (__pycache__, .pytest_cache, logs, *.pyc)"
  echo "[DRY-RUN] Would package metadata into timestamped tarball"
  echo "[DRY-RUN] Would apply read-only protection (chmod -R a-w) to '$SRC_DIR'"
  echo "=== Isolation Dry-Run Complete (No Changes Made) ==="
  exit 0
fi

# Step 1: Purge cache and build artifacts
echo "[*] Purging cache artifacts from '$SRC_DIR'..."
find "$SRC_DIR" -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".vitest" \) -exec rm -rf {} + 2>/dev/null || true
find "$SRC_DIR" -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.log" -o -name "*.tmp" \) -delete 2>/dev/null || true
echo "[OK] Purged cache and temporary artifacts."

# Step 2: Package metadata into timestamped tarball
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE_NAME="historysnooze_vpsg24gb_archive_${TIMESTAMP}.tar.gz"
ARCHIVE_PATH="${ARCHIVE_DIR}/${ARCHIVE_NAME}"
echo "[*] Creating archive '$ARCHIVE_PATH'..."
mkdir -p "$ARCHIVE_DIR"
TMP_ARCHIVE="$(mktemp "${TMPDIR:-/tmp}/hsnooze_archive.XXXXXX.tar.gz")"
if [[ -d "$SRC_DIR/.agents" ]]; then
  tar -czf "$TMP_ARCHIVE" -C "$SRC_DIR" .agents
else
  tar -czf "$TMP_ARCHIVE" -C "$SRC_DIR" .
fi
mv "$TMP_ARCHIVE" "$ARCHIVE_PATH"
echo "[OK] Archive created successfully: $ARCHIVE_PATH"

# Step 3: Apply Read-Only protection
echo "[*] Setting read-only permissions on '$SRC_DIR'..."
chmod -R a-w "$SRC_DIR"
echo "[OK] Applied chmod -R a-w to '$SRC_DIR'."

echo "=================================================="
echo "Isolation status: SUCCESS"
echo "Source locked:    $SRC_DIR (READ-ONLY)"
echo "Archive:          $ARCHIVE_PATH"
echo "=================================================="
exit 0
