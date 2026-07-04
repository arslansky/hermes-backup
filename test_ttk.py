#!/usr/bin/env python3
"""
Test TTK API - Vision Analysis for JD Ad Image
"""

import urllib.request
import json
import base64
import sys

API_KEY = "sk-dJfy8GWR5czhLBHtvSmkrsWy0ZV6js5fT5e2WuAoJsQfRNAd"
API_URL = "https://api.ttk.homes/v1/chat/completions"

def test_ttk_text():
    """Test basic text API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": "Say 'TTK API is working!'"}
        ]
    }
    
    try:
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("✅ TTK Text API OK!")
            print(f"Response: {data['choices'][0]['message']['content']}")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_ttk_vision(image_path=None, image_url=None):
    """Test vision API with image"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Prepare image content
    image_content = None
    
    if image_path:
        # Read local image and convert to base64
        with open(image_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode('utf-8')
        image_content = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }
    elif image_url:
        image_content = {
            "type": "image_url",
            "image_url": {"url": image_url}
        }
    else:
        print("❌ No image provided")
        return False
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "分析呢張廣告圖嘅設計：1. 顏色搭配 2. 排版結構 3. 視覺衝擊力 4. 文化風格特徵。用廣東話回答。"
                    },
                    image_content
                ]
            }
        ]
    }
    
    try:
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("✅ TTK Vision API OK!")
            print("\n🎨 分析結果:\n")
            print(data['choices'][0]['message']['content'])
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing TTK API...\n")
    
    # Test 1: Basic text
    if test_ttk_text():
        print("\n" + "="*50 + "\n")
        
        # Test 2: Vision (if image provided)
        if len(sys.argv) > 1:
            image_path = sys.argv[1]
            print(f"📸 Testing vision with: {image_path}\n")
            test_ttk_vision(image_path=image_path)
        else:
            print("ℹ️  Usage: python3 test_ttk.py <image_path>")
            print("   or provide image_url in code")
