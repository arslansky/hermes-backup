#!/bin/bash
# Send a file as Telegram document to specified chat/topic
# Usage: send_file_to_telegram.sh <file_path> <chat_id> <thread_id> <caption>
FILE_PATH="$1"
CHAT_ID="$2"
THREAD_ID="$3"
CAPTION="$4"

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
    echo "Error: File not found: $FILE_PATH"
    exit 1
fi

TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" ~/.hermes/.env | cut -d= -f2 | tr -d ' ')

URL="https://api.telegram.org/bot${TOKEN}/sendDocument"

# Build curl command
if [ -n "$THREAD_ID" ]; then
    curl -s -F "document=@${FILE_PATH}" \
         -F "chat_id=${CHAT_ID}" \
         -F "message_thread_id=${THREAD_ID}" \
         -F "caption=${CAPTION}" \
         "${URL}" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Sent!' if d.get('ok') else f'Error: {d.get(\"description\")}')"
else
    curl -s -F "document=@${FILE_PATH}" \
         -F "chat_id=${CHAT_ID}" \
         -F "caption=${CAPTION}" \
         "${URL}" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Sent!' if d.get('ok') else f'Error: {d.get(\"description\")}')"
fi