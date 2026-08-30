#!/usr/bin/env bash
# cleanup_tmp.sh — 每日清理 /tmp 影音暫存，防止 OOM
set -euo pipefail

LOG_DIR="$HOME/.openclaw/workspace/memory/ops"
LOG_FILE="$LOG_DIR/tmp-cleanup.log"
mkdir -p "$LOG_DIR"

{
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting /tmp cleanup"

  # 舊影音檔（超過 6 小時）
  find /tmp -type f \\( \
      -name "*.m4a" -o \
      -name "*.wav" -o \
      -name "*.webm" -o \
      -name "*.mp4" -o \
      -name "*.temp.*" -o \
      -name "*.temp*" \
    \) -mmin +360 -delete -print || true

  # 舊 yt-pipeline / yt-* / audio_chunks 目錄（超過 6 小時）
  find /tmp -mindepth 1 -maxdepth 1 -type d \\( \
      -name "yt-pipeline-*" -o \
      -name "yt-*" -o \
      -name "audio_chunks" \
    \) -mmin +360 -exec rm -rf {} + 2>/dev/null || true

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Done"
} >> "$LOG_FILE" 2>&1
