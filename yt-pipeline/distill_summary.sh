#!/usr/bin/env bash
# ============================================================================
# distill_summary.sh — 一鍵出「中文摘要 PDF」（v3.0：新增 --llm 全自動 distill）
# ============================================================================
# 用法：
#   ./distill_summary.sh --video-id <ID> --title <TITLE> --duration <DUR>
#                        --lang <zh-Hant|en> --clean <clean.txt> --output-dir <dir>
#
# 三條摘要路：
#   --summary-body <file>  直接指定已寫好嘅摘要 body 檔（最高品質，人手寫）
#   --llm                  [NEW] 自動用 LLM distill transcript → 結構化中文摘要
#   --auto                  fallback：擷取 transcript 前 N 字做「概覽」（快但粗）
#
# --llm 設計：
#   - 讀 clean transcript（擷取前 MAX_CHARS 字符，避免超 context）
#   - 用 OpenAI-compatible API（chat/completions）distill
#   - 預設 provider: deepseek-official（api.deepseek.com，穩定）
#   - API key 必須由環境變數提供：DISTILL_API_KEY（唔寫死喺 script）
#   - 可經環境變數覆寫：DISTILL_API_BASE / DISTILL_API_KEY / DISTILL_MODEL / DISTILL_MAX_CHARS
# ============================================================================
set -euo pipefail

VIDEO_ID=""; TITLE=""; DURATION=""; LANG="zh-Hant"; CLEAN=""; OUTDIR=""
SUMMARY_BODY=""; USE_LLM=false; AUTO=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --video-id) VIDEO_ID="$2"; shift 2 ;;
        --title) TITLE="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        --lang) LANG="$2"; shift 2 ;;
        --clean) CLEAN="$2"; shift 2 ;;
        --output-dir) OUTDIR="$2"; shift 2 ;;
        --summary-body) SUMMARY_BODY="$2"; shift 2 ;;
        --llm) USE_LLM=true; shift ;;
        --auto) AUTO=true; shift ;;
        *) echo "❌ Unknown: $1"; exit 1 ;;
    esac
done

[[ -z "$VIDEO_ID" || -z "$TITLE" || -z "$OUTDIR" ]] && { echo "❌ need --video-id --title --output-dir"; exit 1; }

RENDER="$HOME/scripts/render_summary_pdf.py"
[[ -f "$RENDER" ]] || { echo "❌ render_summary_pdf.py not found"; exit 1; }

# 自動 load .env（集中管理 API key，如果有嘅話）
# .env 用 600 permissions，含 key，唔好 commit / 同步
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

# --- 摘要 body ---
BODY_TMP=$(mktemp)
if [[ -n "$SUMMARY_BODY" && -f "$SUMMARY_BODY" ]]; then
    cp "$SUMMARY_BODY" "$BODY_TMP"
elif [[ "$USE_LLM" == true ]]; then
    # ====== LLM distill 路 ======
    [[ -n "$CLEAN" && -f "$CLEAN" ]] || { echo "❌ --llm 需要 --clean <file>"; exit 1; }

    # LLM config（可覆寫；API key 只由環境變數提供，唔寫死）
    # 預設 deepseek-official（api.deepseek.com，穩定）
    # 用法：DISTILL_API_KEY=xxx ./distill_summary.sh --llm ...
    # 備選 kimi：DISTILL_API_BASE=https://api.kimi.com/coding/v1 \
    #           DISTILL_API_KEY=xxx DISTILL_MODEL=kimi-for-coding
    API_BASE="${DISTILL_API_BASE:-https://api.deepseek.com/v1}"
    API_KEY="${DISTILL_API_KEY:-}"
    MODEL="${DISTILL_MODEL:-deepseek-chat}"
    MAX_CHARS="${DISTILL_MAX_CHARS:-30000}"

    if [[ -z "$API_KEY" ]]; then
        echo "❌ --llm 需要環境變數 DISTILL_API_KEY（API key 唔寫死喺 script）"
        echo "   例: DISTILL_API_KEY=xxx $0 --llm ..."
        exit 1
    fi

    # 確保 output dir 存在
    mkdir -p "$OUTDIR"

    # 安全擷取 transcript（按字符截斷，避免切喺 UTF-8 中文字中間）
    TRANSCRIPT_TEXT=$(python3 -c "
with open('$CLEAN', encoding='utf-8') as f:
    t = f.read()
print(t[:$MAX_CHARS])")
    echo "🤖 LLM distill: $MODEL（transcript 擷取 ${#TRANSCRIPT_TEXT} 字符）"

    # Build prompt：要求輸出 render_summary_pdf.py 嘅 body 格式
    # body = 交替 H2 section title + 內容段落，空行分節；'• ' 開頭 = bullet
    PROMPT=$(cat <<'PROMPT_EOF'
你是資深內容分析師。請閱讀以下 YouTube 影片字幕，寫一份結構化繁體中文摘要，用作 PDF。

重要規則：
- 不論原文是中文、英文還是其他語言，你都要把內容理解、提煉、翻譯後，用繁體中文輸出。
- 禁止直接複製貼上原文逐字稿；必須是摘要與洞見。

輸出格式必須嚴格符合以下規則：
- 用「段落」結構：第一行係小標題（唔加 # 號），第二行起係內容
- 段落之間用空行分隔
- bullet 用「• 」開頭
- 全部用繁體中文（台灣用字習慣）
- 包含以下部分（如果內容適用）：
  1. 核心思想（2-4 句）
  2. 主要論點 / 章節重點（分點）
  3. 具體做法 / 實用建議
  4. 金句（引用後自行翻譯成繁體中文）

長度：約 400-800 字，要精煉、有 insight，唔好流水帳。

影片字幕開始：
PROMPT_EOF
)

    # call LLM
    RESP=$(curl -sS --max-time 180 "$API_BASE/chat/completions" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$(python3 -c "
import json,sys
sys.stdout.write(json.dumps({
  'model': '$MODEL',
  'messages': [
    {'role':'system','content':'你係專業內容分析師，擅長將長篇影音內容提煉成結構化繁體中文摘要。'},
    {'role':'user','content': '''$PROMPT

$TRANSCRIPT_TEXT'''}
  ],
  'temperature': 0.3
}))")")

    # extract content
    CONTENT=$(echo "$RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(d['choices'][0]['message']['content'])
except Exception as e:
    print('__LLM_ERROR__', e, file=sys.stderr)
    print('')
")
    if [[ -z "$CONTENT" || "$CONTENT" == __LLM_ERROR__* ]]; then
        echo "⚠️ LLM distill failed, fallback to --auto"
        {
            echo "影片概覽"
            echo "（LLM distill 失敗，以下為字幕開頭內容）"
            echo ""
            head -c 3000 "$CLEAN"
        } > "$BODY_TMP"
    else
        # 正規化 LLM 輸出：strip Markdown 標題前綴（# / ## / ###），令 render 當做小標題
        printf '%s\n' "$CONTENT" | python3 -c "
import sys, re
for line in sys.stdin:
    s = line.rstrip('\n')
    s = re.sub(r'^#{1,6}\s+', '', s)   # strip 行首 # 符號
    print(s)
" > "$BODY_TMP"
        echo "✅ LLM distill 完成（$(wc -c < "$BODY_TMP") bytes）"
    fi
elif [[ "$AUTO" == true && -n "$CLEAN" && -f "$CLEAN" ]]; then
    # fallback：擷取 transcript 前 3000 字做概覽
    {
        echo "影片概覽"
        echo "以下係本片字幕開頭內容（未經 LLM distill，僅供快速參考）："
        echo ""
        head -c 3000 "$CLEAN"
    } > "$BODY_TMP"
else
    echo "❌ 需要 --summary-body 或 --llm 或 --auto --clean"; exit 1
fi

mkdir -p "$OUTDIR"
OUT="$OUTDIR/$VIDEO_ID.summary.zh-Hant.pdf"
python3 "$RENDER" \
    --output "$OUT" \
    --title "$TITLE" \
    --subtitle "中文摘要" \
    --video-id "$VIDEO_ID" \
    --channel "YouTube" \
    --duration "${DURATION:-?}" \
    --upload-date "$(date +%Y-%m-%d)" \
    --language "$LANG" \
    --source "yt transcript pipeline v3.0" \
    --tldr "詳見摘要。" \
    --body "$(cat "$BODY_TMP")"

rm -f "$BODY_TMP"
echo "✅ Summary PDF: $OUT"
