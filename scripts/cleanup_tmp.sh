#!/usr/bin/env bash
# cleanup_tmp.sh - daily /tmp media cleanup
set -euo pipefail

LOG_DIR="$HOME/.openclaw/workspace/memory/ops"
LOG_FILE="$LOG_DIR/tmp-cleanup.log"
mkdir -p "$LOG_DIR"

{
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting /tmp cleanup"

  # Delete old media files older than 6 hours
  find /tmp -maxdepth 1 -type f \
    \( -name '*.m4a' -o -name '*.wav' -o -name '*.webm' -o -name '*.mp4' -o -name '*.temp.*' \) \
    -mmin +360 -delete || true

  # Delete old pipeline/audio temp dirs older than 6 hours
  find /tmp -maxdepth 1 -type d \
    \( -name 'yt-pipeline-*' -o -name 'yt-*' -o -name 'audio_chunks' \) \
    -mmin +360 -exec rm -rf {} + 2>/dev/null || true

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Done"
} >> "$LOG_FILE" 2>&1
