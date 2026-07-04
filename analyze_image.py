#!/usr/bin/env python3
import urllib.request
import json
import os

API_KEY = os.environ.get('TTK_API_KEY', '')
API_URL = "https://api.ttk.homes/v1/chat/completions"

# Image URL with signature
image_url = "https://minimax-algeng-chat-tts-us.oss-us-east-1.aliyuncs.com/ccv2%2F2026-06-14%2FMiniMax-M2.7%2F2028098220055343266%2F1aaa012bb912d9171d14ae0d85498390781aa490f18a87e72f46aeb24d31f416..jpeg?Expires=1781532552&OSSAccessKeyId=LTAI5tCpJNKCf5EkQHSuL9xg&Signature=SG3xiPfJGk5shGhn6GS4V9RvxHQ%3D"

print("Analyzing with TTK gemini-2.5-pro-cli...")

payload = json.dumps({
    "model": "gemini-2.5-pro-cli",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "詳細分析呢張圖：1. 顏色搭配 2. 排版結構 3. 視覺衝擊力 4. 設計風格 5. 文化特徵。用廣東話回答。"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    ],
    "max_tokens": 4096
}, ensure_ascii=False).encode("utf-8")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

try:
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers=headers,
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
        response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print("="*60)
        print(response_text)
        print("="*60)
        print("\nModel used: gemini-2.5-pro-cli (TTK)")
        
except urllib.error.HTTPError as e:
    try:
        error_body = json.loads(e.read().decode('utf-8'))
        error_msg = error_body.get("error", {}).get("message", "Unknown")
        print(f"Error: {error_msg}")
    except:
        print(f"HTTP Error: {e.code}")
except Exception as e:
    print(f"Error: {str(e)}")
