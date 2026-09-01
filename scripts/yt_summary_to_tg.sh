#!/usr/bin/env bash
# yt_summary_to_tg.sh — YouTube link → 繁體中文摘要 PDF → Telegram (via tg-send-doc.sh)
# Usage: yt_summary_to_tg.sh <youtube_url_or_video_id> [chat_id] [model]

set -euo pipefail

# Load secrets from .env (chmod 600, not in git)
if [[ -f "/home/ubuntu/scripts/yt-pipeline/.env" ]]; then
    set -a
    source "/home/ubuntu/scripts/yt-pipeline/.env"
    set +a
fi

URL_OR_ID="${1:-}"
CHAT_ID="${2:-160408068}"
MODEL="${3:-tiny}"

if [[ -z "$URL_OR_ID" ]]; then
    echo "Usage: yt_summary_to_tg.sh <youtube_url_or_video_id> [chat_id] [model]" >&2
    exit 1
fi

VIDEO_ID=$(python3 -c "
import re, sys
s = sys.argv[1]
m = re.search(r'(?:v=|youtu\.be/|/embed/|/v/|/shorts/|watch\?v=|^)([a-zA-Z0-9_-]{11})', s)
print(m.group(1) if m else '')
" "$URL_OR_ID")

if [[ -z "$VIDEO_ID" ]]; then
    echo "❌ Cannot extract video ID from: $URL_OR_ID" >&2
    exit 1
fi

PIPELINE="/home/ubuntu/hermes-backup/yt-pipeline/yt_pipeline.sh"
DISTILL="/home/ubuntu/hermes-backup/yt-pipeline/distill_summary.sh"
RENDER="/home/ubuntu/scripts/render_summary_pdf.py"
SEND="/home/ubuntu/.openclaw/scripts/tg-send-doc.sh"
TOKEN_FILE="$HOME/.openclaw/credentials/telegram-know2learn-token.txt"

# Defaults (override via /home/ubuntu/scripts/yt-pipeline/.env)
DISTILL_API_BASE="${DISTILL_API_BASE:-https://api.deepseek.com/v1}"
DISTILL_MODEL="${DISTILL_MODEL:-deepseek-chat}"

for f in "$PIPELINE" "$DISTILL" "$RENDER" "$SEND" "$TOKEN_FILE"; do
    if [[ ! -f "$f" ]]; then
        echo "❌ Missing: $f" >&2
        exit 1
    fi
done

echo "📺 Processing $VIDEO_ID (model=$MODEL)..."

# Try subtitle path first; fallback to Whisper only if no transcript produced.
"$PIPELINE" --video-id "$VIDEO_ID" --model "$MODEL" --no-summary --quiet || true

OUTPUT_DIR="$HOME/.openclaw/workspace/ds-agent/memory/$(date +%Y-%m-%d)/yt-transcripts/$VIDEO_ID"
if [[ ! -d "$OUTPUT_DIR" ]] || [[ -z "$(find "$OUTPUT_DIR" -maxdepth 1 -type f \( -name '*.txt' -o -name '*.srt' \) ! -name '*.summary*' ! -name '*.timed*' | head -1)" ]]; then
    echo "⚠️ No subtitle path output; forcing Whisper fallback..."
    rm -rf "$OUTPUT_DIR"
    "$PIPELINE" --video-id "$VIDEO_ID" --force-whisper --model "$MODEL" --no-summary --quiet
fi

if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "❌ Output dir not found: $OUTPUT_DIR" >&2
    exit 1
fi

TXT_FILE=$(find "$OUTPUT_DIR" -maxdepth 1 -type f \( -name "*.zh*.txt" -o -name "*.en.txt" -o -name "*.txt" \) ! -name "*.timed*" ! -name "*.summary*" | head -1)
if [[ -z "$TXT_FILE" || ! -f "$TXT_FILE" ]]; then
    echo "❌ Clean transcript not found in $OUTPUT_DIR" >&2
    ls -la "$OUTPUT_DIR" >&2
    exit 1
fi

# Metadata
META_JSON=$(find "$OUTPUT_DIR" -maxdepth 1 -name "*.json" | head -1)
TITLE=""; CHANNEL=""; DURATION=""; UPLOAD_DATE=""; LANG=""; VIEWS=""
if [[ -n "$META_JSON" && -f "$META_JSON" ]]; then
    TITLE=$(python3 -c "import json; print(json.load(open('$META_JSON')).get('title',''))" 2>/dev/null || true)
    CHANNEL=$(python3 -c "import json; print(json.load(open('$META_JSON')).get('channel',''))" 2>/dev/null || true)
    DURATION=$(python3 -c "import json; print(json.load(open('$META_JSON')).get('duration',''))" 2>/dev/null || true)
    UPLOAD_DATE=$(python3 -c "import json; print(json.load(open('$META_JSON')).get('upload_date',''))" 2>/dev/null || true)
    LANG=$(python3 -c "import json; print(json.load(open('$META_JSON')).get('language',''))" 2>/dev/null || true)
    VIEWS=$(python3 -c "import json; print(json.load(open('$META_JSON')).get('view_count',''))" 2>/dev/null || true)
fi
[[ -z "$TITLE" ]] && TITLE="$VIDEO_ID"
[[ -z "$LANG" ]] && LANG="zh-Hant"

# Fail fast if API key is missing; all PDFs must be Chinese summaries.
if [[ -z "${DISTILL_API_KEY:-}" ]]; then
    echo "❌ DISTILL_API_KEY not set. Add it to /home/ubuntu/scripts/yt-pipeline/.env" >&2
    exit 1
fi

# Generate structured Traditional Chinese summary via LLM distill.
PDF_OUT="$OUTPUT_DIR/$VIDEO_ID.summary.zh-Hant.pdf"
DISTILL_API_KEY="$DISTILL_API_KEY" DISTILL_API_BASE="$DISTILL_API_BASE" DISTILL_MODEL="$DISTILL_MODEL"     "$DISTILL" --video-id "$VIDEO_ID" --title "$TITLE" --duration "${DURATION:-?}"     --lang "zh-Hant" --clean "$TXT_FILE" --output-dir "$OUTPUT_DIR" --llm

if [[ ! -f "$PDF_OUT" ]]; then
    echo "❌ Summary PDF not produced by distill: $PDF_OUT" >&2
    exit 1
fi

echo "✅ PDF generated: $PDF_OUT"

# Send via tg-send-doc.sh (bypass OpenClaw message send-file bug)
CAPTION="$TITLE 中文 PDF 摘要"
"$SEND" "$PDF_OUT" "$CAPTION" "$CHAT_ID"

echo "✅ Sent PDF to chat $CHAT_ID"
