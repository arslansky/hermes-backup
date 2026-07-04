#!/usr/bin/env bash
set -euo pipefail

export HOME="/home/opc"
export HERMES_HOME="/home/opc/.hermes"
export PATH="/home/opc/.local/bin:/home/opc/.nvm/versions/node/v22.23.1/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
export CLOAKBROWSER_SUPPRESS_FONT_WARNING=1

DATE="$(date +%Y%m%d)"
OUT="/home/opc/.hermes/cron/output/mingpao_digest_${DATE}.txt"
LOG="/home/opc/.hermes/cron/output/mingpao_run_${DATE}.log"

mkdir -p /home/opc/.hermes/cron/output

python3.11 /home/opc/.hermes/scripts/mingpao_scraper.py "$DATE" >"$LOG" 2>&1

if [[ ! -s "$OUT" ]]; then
  echo "Mingpao job ran but output file missing or empty: $OUT"
  echo "Log: $LOG"
  tail -80 "$LOG" || true
  exit 1
fi

printf '明報每日摘要完成：%s\n' "$DATE"
printf 'Log: %s\n' "$LOG"
printf 'MEDIA:%s\n' "$OUT"
