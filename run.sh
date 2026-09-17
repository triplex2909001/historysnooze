#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="/media/vpsg16gb/Media/historysnooze/.secrets"
IMAGE_NAME="historysnooze-sandbox"

show_help() {
    cat << 'EOF'
Usage: ./run.sh [OPTIONS] [COMMAND...]

HistorySnooze Fast Container Launcher (Zero-Idle Memory Sandbox)
Launches an ephemeral Docker container with strictly non-root UID 1000,
hardened Linux capabilities, read-only secrets mount, and auto-cleanup (--rm).

Options:
  -h, --help    Show this help message and exit
  --build       Force rebuild of the Docker sandbox image

Examples:
  ./run.sh                              # Interactive bash shell
  ./run.sh python monitor.py            # Run monitor dashboard
  ./run.sh pytest tests/                # Run test suite inside container
EOF
}

BUILD_IMAGE=false
CMD=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --build)
            BUILD_IMAGE=true
            shift
            ;;
        *)
            CMD+=("$1")
            shift
            ;;
    esac
done

if [ "$BUILD_IMAGE" = true ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "[*] Building container image: $IMAGE_NAME..."
    docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/docker/Dockerfile" "$SCRIPT_DIR"
fi

INTERACTIVE_FLAG="-it"
if [ ! -t 0 ]; then
    INTERACTIVE_FLAG="-i"
fi

if [ ${#CMD[@]} -eq 0 ]; then
    CMD=("bash")
fi

echo "[+] Launching HistorySnooze Sandbox (Zero-Idle Mode)..."
exec docker run $INTERACTIVE_FLAG --rm \
    --name "historysnooze-sandbox-$$-$RANDOM" \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    --tmpfs /dev/shm:rw,noexec,nosuid,size=64m \
    -v "/media/vpsg16gb/Media/historysnooze/.secrets:/workspace/.secrets:ro" \
    -v "$SCRIPT_DIR:/workspace" \
    -w /workspace \
    --user 1000:1000 \
    -e PYTHONUNBUFFERED=1 \
    -e HSNOOZE_DATA_DIR=/workspace \
    -e TELEGRAM_BOT_TOKEN_PATH=/workspace/.secrets/telegram/bot_token.txt \
    -e GDRIVE_TOKEN_PATH=/workspace/.secrets/gdrive/token.json \
    "$IMAGE_NAME" \
    "${CMD[@]}"
