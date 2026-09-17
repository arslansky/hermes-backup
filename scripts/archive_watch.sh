#!/bin/bash
# archive_watch.sh — 7 晚觀察期：三個歸檔候選有冇人仲用緊
# 候選：A) minimax-agent/ + openclaw/minimax-agent/  B) repo root 散件 + scratch 腳本  C) news-summary/
# 每晚 00:00 行一次，--repeat 7 期滿自動停用。第 7 晚輸出 7 日總結俾用戶決定。
LOGDIR="$HOME/.hermes/archive-watch"
mkdir -p "$LOGDIR"
TODAY=$(date +%F)
NIGHT=$(find "$LOGDIR" -name "watch-*.log" 2>/dev/null | wc -l)
NIGHT=$((NIGHT + 1))
REPO="$HOME/hermes-backup"
OUT="$LOGDIR/watch-$TODAY.log"

refs() {  # refs <pattern> — 喺本地所有可達地方搵引用，回傳總數
  local p="$1"
  echo $(( $(crontab -l 2>/dev/null | grep -c "$p") + $(hermes cron list 2>/dev/null | grep -c "$p") + $(ps aux | grep -v grep | grep -c "$p") ))
}

mtime_of() { stat -c %y "$1" 2>/dev/null | cut -d' ' -f1 || echo "不存在"; }

# --- Zeabur 側（openclaw cron / crontab / symlinks），timeout 容忍斷線 ---
ZEABUR=$(ssh -o ConnectTimeout=5 -o BatchMode=yes zeabur '
  export PATH="$HOME/.npm-global/bin:$PATH"
  openclaw cron list 2>/dev/null | grep -ciE "news_summary|yt_summary|minimax-agent|render_summary|moomoo|hktmall"
  crontab -l 2>/dev/null | grep -ciE "news_summary|yt_summary|minimax-agent|render_summary|moomoo|hktmall"
  find ~/.openclaw/workspace -maxdepth 3 -type l 2>/dev/null | grep -ciE "news-summary|minimax-agent"
' 2>/dev/null | paste -sd+ | bc 2>/dev/null || echo "?")

# --- 三候選證據 ---
A_LOCAL=$(refs "minimax-agent\|yt_summary_to_tg")
A_MTIME=$(mtime_of "$REPO/minimax-agent/AGENTS.md")
B_LOCAL=$(refs "render_summary_pdf\|moomoo-scrape\|hktmall_generator\|fable_reasoner\|analyze2\|analyze_image")
C_LOCAL=$(refs "news-summary\|news_summary")
C_MTIME=$(mtime_of "$REPO/news-summary/news_summary.py")
# 已知使用中除外：run_mingpao_daily.sh（active cron，唔係候選）

HEALTH=$(curl -s -m 8 -o /dev/null -w "%{http_code}" http://100.121.1.3:18789/health 2>/dev/null || echo "斷")
DISK=$(df -h / | awk 'NR==2{print $5}')

{
  echo "date=$TODAY night=$NIGHT/7"
  echo "A_minimax_refs=$A_LOCAL zeabur_refs=$ZEABUR mtime=$A_MTIME"
  echo "B_scratch_refs=$B_LOCAL"
  echo "C_newssum_refs=$C_LOCAL mtime=$C_MTIME"
  echo "health=$HEALTH disk=$DISK"
} > "$OUT"

if [ "$NIGHT" -ge 7 ]; then
  echo "📋 **歸檔觀察期滿（7/7 晚）自動停用**"
  echo ""
  echo "三候選 7 晚總結："
  echo ""
  grep -h "refs=" "$LOGDIR"/watch-*.log | sort | uniq -c | sort -rn | head -6
  echo ""
  echo "每日明細：$LOGDIR/watch-*.log"
  echo "請你決定邊啲入 archive（我唔會自動郁）。"
else
  echo "📋 歸檔觀察 第 $NIGHT/7 晚（$TODAY）"
  echo "A minimax-agent/：本地引用 $A_LOCAL 次｜Zeabur 引用 $ZEABUR 次｜最後改動 $A_MTIME"
  echo "B scratch 散件：引用 $B_LOCAL 次"
  echo "C news-summary/：引用 $C_LOCAL 次｜最後改動 $C_MTIME"
  echo "健康：Zeabur gateway $HEALTH｜磁碟 $DISK"
fi
