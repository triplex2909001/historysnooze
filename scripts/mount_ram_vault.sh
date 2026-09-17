#!/usr/bin/env bash
# ==============================================================================
# HistorySnooze RAM-Only Vault Manager
# Location: scripts/mount_ram_vault.sh
# Authority: Documents/Structure/03_SECURE_ISOLATION_VAULT.md (Section 2 & 3.3)
# ==============================================================================
set -euo pipefail

RAM_VAULT_DIR="/dev/shm/.vault"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SECRETS_DIR="${HSNOOZE_SECRETS_DIR:-${REPO_ROOT}/.secrets}"
ACTION="${1:-mount}"

case "${ACTION}" in
    mount|init)
        echo "[+] Provisioning RAM-Only Vault in tmpfs at ${RAM_VAULT_DIR}..."
        mkdir -p "${RAM_VAULT_DIR}"
        chmod 700 "${RAM_VAULT_DIR}"

        # 1. Decrypt project_vault.enc if present and MASTER_VAULT_PASS is set
        VAULT_ENC="${SECRETS_DIR}/project_vault.enc"
        if [[ -f "${VAULT_ENC}" ]]; then
            if [[ -n "${MASTER_VAULT_PASS:-}" ]]; then
                echo "[+] Decrypting encrypted vault to ${RAM_VAULT_DIR}/secrets.json..."
                openssl enc -aes-256-cbc -d -salt -pbkdf2 -in "${VAULT_ENC}" \
                    -out "${RAM_VAULT_DIR}/secrets.json" -pass env:MASTER_VAULT_PASS
                chmod 600 "${RAM_VAULT_DIR}/secrets.json"
                echo "[✔] AES-256 decrypted into RAM vault."
            else
                echo "[!] [WARN] Found ${VAULT_ENC} but MASTER_VAULT_PASS is unset. Skipping decryption." >&2
            fi
        fi

        # 2. Sync files from .secrets or cloud profile if present
        if [[ -d "${SECRETS_DIR}" ]]; then
            shopt -s dotglob nullglob
            for f in "${SECRETS_DIR}"/*; do
                if [[ -f "${f}" && "$(basename "${f}")" != "project_vault.enc" ]]; then
                    cp -p "${f}" "${RAM_VAULT_DIR}/"
                    chmod 600 "${RAM_VAULT_DIR}/$(basename "${f}")"
                fi
            done
            shopt -u dotglob nullglob
        fi

        # Enforce strict 0700/0600 permissions
        chmod 700 "${RAM_VAULT_DIR}"
        find "${RAM_VAULT_DIR}" -type f -exec chmod 600 {} + 2>/dev/null || true
        echo "[✔] RAM-Only Vault active at ${RAM_VAULT_DIR} with mode 0700/0600."
        ;;

    purge|unmount)
        echo "[+] Purging RAM-Only Vault from /dev/shm (Zero-Idle)..."
        if [[ -d "${RAM_VAULT_DIR}" ]]; then
            find "${RAM_VAULT_DIR}" -type f -exec shred -f -u -z {} + 2>/dev/null || rm -rf "${RAM_VAULT_DIR}"
            rm -rf "${RAM_VAULT_DIR}"
        fi
        echo "[✔] RAM-Only Vault completely erased from memory."
        ;;

    status|check)
        if [[ -d "${RAM_VAULT_DIR}" ]]; then
            echo "[✔] RAM Vault exists at ${RAM_VAULT_DIR}."
            ls -la "${RAM_VAULT_DIR}"
        else
            echo "[-] RAM Vault not initialized."
        fi
        ;;

    *)
        echo "Usage: $0 {mount|purge|status}"
        exit 1
        ;;
esac
