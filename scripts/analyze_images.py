#!/usr/bin/env python3
import urllib.request
import json
import os
import base64

API_KEY = os.environ.get('TTK_API_KEY', '')
API_URL = "https://api.ttk.homes/v1/chat/completions"

# Images to analyze
images = [
    "/root/.openclaw/media/inbound/34e47b0f-cad2-42c3-9a6a-4fdc7d219d09.jpg",
    "/root/.openclaw/media/inbound/b09a0492-2ea6-4dff-89ca-70c42a0a3db0.jpg"
]

print("Analyzing images with TTK gemini-2.5-pro-cli...")

for i, img_path in enumerate(images, 1):
    print(f"\n{'='*60}")
    print(f"Image {i}: {img_path}")
    print(f"{'='*60}")
    
    # Read and encode image
    with open(img_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    payload = json.dumps({
        "model": "gemini-2.5-pro-cli",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "呢張係咩圖？簡單描述下主要內容。用廣東話。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                ]
            }
        ],
        "max_tokens": 1024
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
            print(response_text)
            
    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode('utf-8'))
            error_msg = error_body.get("error", {}).get("message", "Unknown")
            print(f"Error: {error_msg}")
        except:
            print(f"HTTP Error: {e.code}")
    except Exception as e:
        print(f"Error: {str(e)}")

print("\nDone.")
