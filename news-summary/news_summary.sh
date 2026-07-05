#!/bin/bash
# news_summary.sh - 拎新聞全文 + 格式化作摘要
# Usage: bash news_summary.sh "<URL>"
# 格式：時、地、人、事件、重點

python3 /home/ubuntu/.openclaw/workspace/scripts/news_summary.py "$1"
