#!/usr/bin/env bash
# ============================================================================
# yt_pipeline.sh — YouTube Transcript Pipeline v2.0
# ============================================================================
# 統一 Pipeline：直接試 yt-dlp auto-subs (Path A) → 冇先 fallback Whisper (Path B)
# → 分片並行 STT → language auto-detect → dedupe (英文) → 三種 TXT → index update
#
# v2.0 改善 (2026-08-30):
#   ① 唔信 --list-subs，直接 run --write-auto-subs（英文片秒出）
#   ② Whisper language auto-detect（唔再硬編碼 Chinese）
#   ③ 分片並行 STT（用盡 2 core）
#   ④ <videoID> 命名，唔撞舊檔
#   ⑤ 產物統一落 memory/<date>/yt-transcripts/<videoID>/ + del 大 audio + index
#   ⑥ distill_summary 一鍵出摘要 PDF
#
# Usage:
#   ./yt_pipeline.sh --video-id <YT_ID> [--lang <lang>] [--model <tiny|base>]
#                   [--title <title>] [--output-dir <dir>] [--cookies <file>]
#                   [--no-summary] [--quiet]
# ============================================================================
set -euo pipefail

# Ensure PATH for non-login shells (Hermes / OpenClaw tools run bare /bin/sh)
export PATH="$HOME/.local/bin:$PATH"

# --- Global lock + resource guards ---
LOCK_FILE="/var/lock/yt-pipeline.lock"
exec 200>"$LOCK_FILE" || { echo "❌ Cannot open lock file $LOCK_FILE"; exit 1; }
flock -n 200 || { echo "❌ Another yt_pipeline instance is running"; exit 1; }

# Memory guard: require at least 1.5 GB available
AVAILABLE_MB=$(free -m | awk '/^Mem:/ {print $7}')
if [[ -n "$AVAILABLE_MB" && "$AVAILABLE_MB" -lt 1500 ]]; then
    echo "❌ Available memory too low: ${AVAILABLE_MB}MB (need >= 1500MB)"
    exit 1
fi

# Disk guard: require at least 2 GB free on /tmp
TMP_FREE_MB=$(df -m /tmp 2>/dev/null | awk 'NR==2 {print $4}')
if [[ -n "$TMP_FREE_MB" && "$TMP_FREE_MB" -lt 2048 ]]; then
    echo "❌ /tmp free space too low: ${TMP_FREE_MB}MB (need >= 2048MB)"
    exit 1
fi

# --- Config ---
# Load proxy credentials from .env (chmod 600, not in git)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

PROXY_SOCKS5="${SOCKS5_PROXY:-}"
PROXY_HTTP="${HTTP_PROXY:-}"
# yt-dlp works reliably through the HTTP proxy on this host
YTDLP_PROXY="${YTDLP_PROXY:-${PROXY_HTTP:-$PROXY_SOCKS5}}"
WORKSPACE_DIR="$HOME/scripts/yt-pipeline"
MEMORY_ROOT="$HOME/.openclaw/workspace/ds-agent/memory"
CENTRAL_INDEX="$MEMORY_ROOT/yt-transcripts/CENTRAL_INDEX.md"
DEFAULT_COOKIES="$WORKSPACE_DIR/cookies.txt"
PARALLEL_JOBS=1          # 保守：同時只跑 1 個 Whisper 防止 OOM
CHUNK_MINUTES=12         # 每段 ~12 分鐘，55min 片 ≈ 5 段

# --- Logging ---
LOG_DIR="$HOME/.openclaw/workspace/memory/ops"
LOG_FILE="$LOG_DIR/yt-pipeline.log"
mkdir -p "$LOG_DIR"
RUN_ID="pending-$$"
log_run() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

# --- Cookies auto-detect ---
COOKIES_FILE=""
YTDLP_COOKIE_ARGS=(--js-runtimes node)
if [[ -f "$DEFAULT_COOKIES" ]]; then
    COOKIES_FILE="$DEFAULT_COOKIES"
    YTDLP_COOKIE_ARGS=(--js-runtimes node --cookies "$COOKIES_FILE")
fi

# --- Parse args ---
VIDEO_ID=""
LANG=""
MODEL="base"
TITLE=""
OUTPUT_DIR=""
NO_SUMMARY=false
QUIET=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --video-id) VIDEO_ID="$2"; shift 2 ;;
        --lang)     LANG="$2"; shift 2 ;;
        --model)    MODEL="$2"; shift 2 ;;
        --title)    TITLE="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --cookies)  COOKIES_FILE="$2"; YTDLP_COOKIE_ARGS=(--js-runtimes node --cookies "$2"); shift 2 ;;
        --no-summary) NO_SUMMARY=true; shift ;;
        --quiet)    QUIET=true; shift ;;
        --help|-h)  sed -n '/^# Usage:/,/^$/p' "$0"; exit 0 ;;
        *)          echo "❌ Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$VIDEO_ID" ]]; then
    echo "❌ --video-id is required"
    exit 1
fi

log() {
    local msg="[$(date +%H:%M:%S)] $*"
    [[ "$QUIET" != true ]] && echo "$msg"
    log_run "$msg"
}

if [[ -n "$COOKIES_FILE" && -f "$COOKIES_FILE" ]]; then
    log "🍪 Using cookies: $COOKIES_FILE"
fi

# --- Setup working dirs ---
# ④ <videoID> 命名，唔會撞舊檔
TMPDIR="/tmp/yt-pipeline-$VIDEO_ID-$$"
mkdir -p "$TMPDIR"
trap 'rm -rf "$TMPDIR"; flock -u 200 2>/dev/null || true' EXIT

TODAY=$(date +%Y-%m-%d)
if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="$MEMORY_ROOT/$TODAY/yt-transcripts/$VIDEO_ID"
fi
mkdir -p "$OUTPUT_DIR/raw"

# ============================================================================
# Step 1: Fetch metadata
# ============================================================================
log "🔍 Checking video $VIDEO_ID..."

if [[ -z "$TITLE" ]]; then
    TITLE=$(yt-dlp "${YTDLP_COOKIE_ARGS[@]}" --proxy "$YTDLP_PROXY" --print title "https://youtu.be/$VIDEO_ID" 2>/dev/null || echo "Unknown")
fi
log "📺 Title: $TITLE"

DURATION=$(yt-dlp "${YTDLP_COOKIE_ARGS[@]}" --proxy "$YTDLP_PROXY" --print duration_string "https://youtu.be/$VIDEO_ID" 2>/dev/null || echo "?")
log "⏱️ Duration: $DURATION"

# ============================================================================
# Step 2: Try manual subtitles first, then auto-subs, then Whisper
# ============================================================================

# 候選語言優先序：指定 lang > 常見中英
if [[ -n "$LANG" ]]; then
    SUB_LANGS="$LANG"
else
    SUB_LANGS="zh-Hant,zh-Hans,zh,en,en-US,en-GB"
fi

SUBS_AVAILABLE=false
SUBS_LANG=""
RAW_FILE=""

# --- Attempt 1: manual (uploaded) subtitles ---
log "📥 Trying yt-dlp manual subs..."
yt-dlp "${YTDLP_COOKIE_ARGS[@]}" --proxy "$YTDLP_PROXY" \
    --write-subs --sub-langs "$SUB_LANGS" \
    --skip-download --convert-subs srt \
    -o "$TMPDIR/man_$VIDEO_ID.%(ext)s" \
    "https://youtu.be/$VIDEO_ID" 2>&1 | tail -20 | tee -a "$LOG_FILE" >/dev/null || true

RAW_FILE=$(find "$TMPDIR" -maxdepth 1 -name "man_${VIDEO_ID}*.srt" 2>/dev/null | head -1)
if [[ -n "$RAW_FILE" && -f "$RAW_FILE" ]]; then
    SUBS_AVAILABLE=true
    log "✅ Manual subs found"
fi

# --- Attempt 2: auto-generated subtitles ---
if [[ "$SUBS_AVAILABLE" != true ]]; then
    log "📥 Trying yt-dlp auto-subs..."
    yt-dlp "${YTDLP_COOKIE_ARGS[@]}" --proxy "$YTDLP_PROXY" \
        --write-auto-subs --sub-langs "$SUB_LANGS" \
        --skip-download --convert-subs srt \
        -o "$TMPDIR/auto_$VIDEO_ID.%(ext)s" \
        "https://youtu.be/$VIDEO_ID" 2>&1 | tail -20 | tee -a "$LOG_FILE" >/dev/null || true

    RAW_FILE=$(find "$TMPDIR" -maxdepth 1 -name "auto_${VIDEO_ID}*.srt" 2>/dev/null | head -1)
    if [[ -n "$RAW_FILE" && -f "$RAW_FILE" ]]; then
        SUBS_AVAILABLE=true
        log "✅ Auto-subs found"
    fi
fi

if [[ -n "$RAW_FILE" && -f "$RAW_FILE" ]]; then
    SUBS_AVAILABLE=true
    # 由檔名偵測語言
    if [[ "$RAW_FILE" == *.en* ]]; then
        SUBS_LANG="en"
    elif [[ "$RAW_FILE" == *.zh-Hant* || "$RAW_FILE" == *.zh-TW* ]]; then
        SUBS_LANG="zh-Hant"
    elif [[ "$RAW_FILE" == *.zh-Hans* || "$RAW_FILE" == *.zh-CN* ]]; then
        SUBS_LANG="zh-Hans"
    elif [[ "$RAW_FILE" == *.zh.* ]]; then
        SUBS_LANG="zh"
    else
        SUBS_LANG="${LANG:-auto}"
    fi
fi

# ============================================================================
# Step 3: Path A (subs) / Path B (whisper)
# ============================================================================
if [[ "$SUBS_AVAILABLE" == true ]]; then
    # ====== Path A: 有字幕 ======
    log "✅ Path A: subs available ($SUBS_LANG) — converting..."
    cp "$RAW_FILE" "$OUTPUT_DIR/raw/$VIDEO_ID.$SUBS_LANG.srt"
    PIPELINE_PATH="A: yt-dlp subs ($SUBS_LANG)"
    SRT_INPUT="$OUTPUT_DIR/raw/$VIDEO_ID.$SUBS_LANG.srt"
else
    # ====== Path B: Whisper STT（分片並行）=======
    log "⚠️ Path B: no subs — Whisper STT ($MODEL, 分片並行)..."

    # 下載音頻（④ videoID 命名）
    log "⬇️ Downloading audio..."
    yt-dlp "${YTDLP_COOKIE_ARGS[@]}" --proxy "$YTDLP_PROXY" \
        -f "bestaudio[ext=m4a]" \
        -o "$TMPDIR/$VIDEO_ID.m4a" \
        "https://youtu.be/$VIDEO_ID" 2>&1 | tail -20 | tee -a "$LOG_FILE" >/dev/null

    # 轉 16k wav
    log "🔊 Converting to 16k wav..."
    ffmpeg -y -i "$TMPDIR/$VIDEO_ID.m4a" -ar 16000 -ac 1 -c:a pcm_s16le "$TMPDIR/$VIDEO_ID.wav" >/dev/null 2>&1

    # ② language auto-detect：用 ffprobe 拎時長 + whisper 短樣本偵測
    # 簡單啟發：中文片語系偵測太貴，直接用 whisper 首 30 秒 auto-detect
    log "🌐 Detecting language (30s sample)..."
    ffmpeg -y -i "$TMPDIR/$VIDEO_ID.wav" -t 30 -c copy "$TMPDIR/sample.wav" >/dev/null 2>&1
    DETECTED_LANG=$(whisper "$TMPDIR/sample.wav" --model tiny --language auto --task transcribe --output_format txt --output_dir "$TMPDIR/detect" 2>&1 | grep -oP "Detected language: \K\w+" || echo "zh")
    if [[ -z "$DETECTED_LANG" ]]; then DETECTED_LANG="zh"; fi
    log "   Detected language: $DETECTED_LANG"

    # ③ 分片並行
    TOTAL_SEC=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMPDIR/$VIDEO_ID.wav" 2>/dev/null | cut -d. -f1)
    TOTAL_SEC=${TOTAL_SEC:-0}
    CHUNK_SEC=$((CHUNK_MINUTES * 60))
    NUM_CHUNKS=$(( (TOTAL_SEC + CHUNK_SEC - 1) / CHUNK_SEC ))
    [[ $NUM_CHUNKS -lt 1 ]] && NUM_CHUNKS=1
    log "🧩 Splitting into $NUM_CHUNKS chunks (~${CHUNK_MINUTES}min each)..."

    mkdir -p "$TMPDIR/chunks" "$TMPDIR/subs"
    for i in $(seq 0 $((NUM_CHUNKS - 1))); do
        START=$((i * CHUNK_SEC))
        ffmpeg -y -i "$TMPDIR/$VIDEO_ID.wav" -ss "$START" -t "$CHUNK_SEC" -ar 16000 -ac 1 -c:a pcm_s16le "$TMPDIR/chunks/seg_$i.wav" >/dev/null 2>&1 &
    done
    wait
    log "   Chunks split done."

    # 並行跑 whisper（PARALLEL_JOBS 個同時）
    log "🎙️ Running parallel Whisper STT..."
    pids=()
    for i in $(seq 0 $((NUM_CHUNKS - 1))); do
        (
            whisper "$TMPDIR/chunks/seg_$i.wav" \
                --model "$MODEL" \
                --language "$DETECTED_LANG" \
                --output_format srt \
                --output_dir "$TMPDIR/chunks" \
                >/dev/null 2>&1
        ) &
        pids+=($!)
        # 限流：最多 PARALLEL_JOBS 個並行
        if [[ ${#pids[@]} -ge $PARALLEL_JOBS ]]; then
            wait "${pids[0]}" 2>/dev/null || true
            pids=("${pids[@]:1}")
        fi
    done
    wait

    # 合併分片 srt（補 offset）
    log "🔗 Merging chunk SRTs..."
    MERGED="$TMPDIR/subs/$VIDEO_ID.whisper.srt"
    : > "$MERGED"
    SEG_IDX=1
    for i in $(seq 0 $((NUM_CHUNKS - 1))); do
        SEG_SRT="$TMPDIR/chunks/seg_$i.srt"
        [[ -f "$SEG_SRT" ]] || continue
        OFFSET=$((i * CHUNK_SEC))
        python3 - "$SEG_SRT" "$OFFSET" "$SEG_IDX" >> "$MERGED" << 'PYEOF'
import sys, re
path = sys.argv[1]
offset = int(sys.argv[2])
start_idx = int(sys.argv[3])
txt = open(path, encoding='utf-8').read()
blocks = re.split(r'\n\s*\n', txt.strip())
idx = start_idx
for b in blocks:
    lines = b.strip().split('\n')
    # 找時間行
    tline = None
    for ln in lines:
        if '-->' in ln:
            tline = ln
            break
    if tline is None:
        continue
    m = re.match(r'(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})', tline)
    if not m:
        continue
    def add(s):
        h=int(s[0]); mm=int(s[1]); ss=int(s[2])+offset
        mm+=ss//60; ss%=60; h+=mm//60; mm%=60
        return f"{h:02d}:{mm:02d}:{ss:02d}"
    ns = add(m.groups()[0:3])
    ne = add(m.groups()[4:7])
    text = ' '.join([l for l in lines if '-->' not in l and l.strip()])
    if not text.strip():
        continue
    print(f"{idx}\n{ns},000 --> {ne},000\n{text}\n")
    idx += 1
PYEOF
        SEG_IDX=$((SEG_IDX + 1000))
    done

    cp "$MERGED" "$OUTPUT_DIR/raw/$VIDEO_ID.whisper.srt"
    PIPELINE_PATH="B: Whisper ${MODEL} STT (parallel, $DETECTED_LANG)"
    SRT_INPUT="$OUTPUT_DIR/raw/$VIDEO_ID.whisper.srt"
    log "📄 Raw STT: $OUTPUT_DIR/raw/$VIDEO_ID.whisper.srt"
fi

# ============================================================================
# Step 4: Convert to timed.txt + clean.txt（dedupe 英文）
# ============================================================================
log "📝 Converting to timed.txt + clean.txt..."

DEDUPE_FLAG=""
SUBS_LANG_NORM=$(echo "$SUBS_LANG" | tr '[:upper:]' '[:lower:]')
if [[ "$SUBS_LANG_NORM" == en* ]]; then
    DEDUPE_FLAG="--dedupe"
    log "🔁 English — dedupe enabled"
fi

python3 "$WORKSPACE_DIR/srt_to_transcripts.py" "$SRT_INPUT" "$OUTPUT_DIR" $DEDUPE_FLAG

# ============================================================================
# Step 5: ⑤ 清理大 audio（whisper path 先有）
# ============================================================================
if [[ "$SUBS_AVAILABLE" != true ]]; then
    rm -f "$OUTPUT_DIR"/*.wav "$OUTPUT_DIR"/*.m4a 2>/dev/null || true
    log "🧹 Cleaned large audio files"
fi

# ============================================================================
# Step 6: ⑥ 摘要 PDF（除非 --no-summary）
# ============================================================================
if [[ "$NO_SUMMARY" != true ]]; then
    log "📄 Generating summary PDF..."
    CLEAN_FILE=$(find "$OUTPUT_DIR" -name "${VIDEO_ID}.*.txt" ! -name "*.timed*" 2>/dev/null | head -1)
    if [[ -n "$CLEAN_FILE" && -f "$CLEAN_FILE" ]]; then
        bash "$WORKSPACE_DIR/distill_summary.sh" \
            --video-id "$VIDEO_ID" \
            --title "$TITLE" \
            --duration "$DURATION" \
            --lang "${SUBS_LANG:-zh-Hant}" \
            --clean "$CLEAN_FILE" \
            --llm \
            --output-dir "$OUTPUT_DIR" 2>&1 | tail -2 || log "⚠️ Summary generation skipped (no distill_summary.sh or error)"
    fi
fi

# ============================================================================
# Step 7: Update CENTRAL_INDEX.md
# ============================================================================
log "📇 Updating central index..."

TIMED_FILE=$(find "$OUTPUT_DIR" -name "${VIDEO_ID}.timed.*.txt" 2>/dev/null | head -1)
CLEAN_FILE=$(find "$OUTPUT_DIR" -name "${VIDEO_ID}.*.txt" ! -name "*.timed*" ! -name "*.summary*" 2>/dev/null | head -1)
TIMED_SIZE="?"; CLEAN_SIZE="?"
[[ -n "$TIMED_FILE" ]] && TIMED_SIZE=$(wc -c < "$TIMED_FILE" | tr -d ' ')
[[ -n "$CLEAN_FILE" ]] && CLEAN_SIZE=$(wc -c < "$CLEAN_FILE" | tr -d ' ')

mkdir -p "$(dirname "$CENTRAL_INDEX")"
if [[ ! -f "$CENTRAL_INDEX" ]]; then
    cat > "$CENTRAL_INDEX" << 'EOF'
# YT Transcripts Central Index

> 統一 index，記錄所有已處理嘅 YouTube 影片。
> 每次 pipeline run 自動 append。

| # | Date | Video ID | Title | Lang | Duration | Path | Status | Files |
|---|------|----------|-------|------|----------|------|--------|-------|
EOF
fi

ENTRY_COUNT=$(grep -c "^|" "$CENTRAL_INDEX" 2>/dev/null || echo 0)
NEXT_NUM=$((ENTRY_COUNT))
TITLE_SAFE=$(echo "$TITLE" | sed 's/|/\\|/g')
STATUS="✅ done"
FILES="timed.txt (${TIMED_SIZE}B) + clean.txt (${CLEAN_SIZE}B)"

echo "| $NEXT_NUM | $TODAY | $VIDEO_ID | $TITLE_SAFE | ${SUBS_LANG:-?} | $DURATION | $PIPELINE_PATH | $STATUS | $FILES |" >> "$CENTRAL_INDEX"

# ============================================================================
# Done
# ============================================================================
log ""
log "✅ Done! Files in: $OUTPUT_DIR"
log_run "completed video=$VIDEO_ID path=$PIPELINE_PATH duration=$DURATION output=$OUTPUT_DIR"
log "   Pipeline: $PIPELINE_PATH"
log "   Duration: $DURATION"
log ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pipeline: $PIPELINE_PATH"
echo "  Video:    $TITLE"
echo "  Duration: $DURATION"
echo "  Output:   $OUTPUT_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
