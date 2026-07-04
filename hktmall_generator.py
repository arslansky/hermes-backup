#!/usr/bin/env python3
"""
HKTmall Ad Generator - Optimized version
- Longer timeout (600s)
- Better prompts
- Progress updates
"""
import urllib.request
import json
import os
import base64
import time

import os
API_KEY = os.environ.get('TTK_API_KEY', '')
API_URL = "https://api.ttk.homes/v1/images/generations"

def generate_hktmall_ad(style="black_orange", output_path=None):
    """Generate HKTmall ad with specified style"""
    
    styles = {
        "black_orange": {
            "prompt": """
Create a Hong Kong shopping mall advertisement poster with black and orange color scheme (chocolate orange theme).

Design requirements:
- Color palette: BLACK + HIGH SATURATION ORANGE (dominant orange with black accents)
- Background: Realistic Hong Kong shopping mall interior/exterior scene
- Main headline: "HKTmall" in VERY LARGE, BOLD typography, orange with black outline
- Secondary text: "爆款限時優惠" (Limited time hot deals)
- Tagline: "全場低價保證" (Price match guarantee)
- Urgency text: "限時搶購" (Limited time purchase)
- Text style: Bold "大字報" style with thick black outlines
- Layout: Dense, information-packed, minimal whitespace
- Dynamic tilted typography for energy and movement
- Shopping elements: storefronts, escalators, shopping bags
- Style: Hong Kong e-commerce hard-sell aesthetic, modern Asian commercial design
- High visual impact, eye-catching, promotional energy
- Quality: Photorealistic, high resolution, professional design
""",
            "filename": "hktmall_black_orange_ad.png"
        },
        "green_white": {
            "prompt": """
Create a Hong Kong shopping mall advertisement poster with HKTVmall green and white color scheme.

Design requirements:
- Color palette: GREEN + WHITE (like HKTVmall branding, green dominant with white)
- Background: Realistic Hong Kong shopping mall interior/exterior scene
- Main headline: "HKTmall" in VERY LARGE, BOLD typography, green color
- Secondary text: "爆款限時優惠" (Limited time hot deals)
- Tagline: "全場低價保證" (Price match guarantee)
- Urgency text: "限時搶購" (Limited time purchase)
- Text style: Bold promotional style with white accents
- Layout: Dense, information-packed, minimal whitespace
- Shopping elements: storefronts, escalators, shopping bags
- Style: Hong Kong e-commerce hard-sell aesthetic, HKTVmall brand style
- High visual impact, professional commercial design
- Quality: Photorealistic, high resolution, professional design
""",
            "filename": "hktmall_green_white_ad.png"
        }
    }
    
    config = styles.get(style, styles["black_orange"])
    
    if output_path is None:
        output_path = f"/root/.openclaw/workspace/{config['filename']}"
    
    print(f"Generating HKTmall ad ({style})...")
    print(f"Timeout: 600 seconds (10 minutes)")
    
    payload = json.dumps({
        "model": "gpt-image-2",
        "prompt": config["prompt"],
        "n": 1,
        "size": "1024x1024",
        "quality": "high"
    }, ensure_ascii=False).encode("utf-8")
    
    headers = {
        "Authorization": "Bearer " + API_KEY,
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    try:
        req = urllib.request.Request(
            API_URL,
            data=payload,
            headers=headers,
            method="POST"
        )
        
        print("Sending request to TTK gpt-image-2...")
        print("This may take up to 10 minutes for high quality generation...")
        
        with urllib.request.urlopen(req, timeout=600) as response:
            elapsed = time.time() - start_time
            print(f"Generation completed in {elapsed:.1f} seconds")
            
            data = json.loads(response.read().decode("utf-8"))
            
            if "data" in data and len(data["data"]) > 0:
                image_data = data["data"][0]
                
                if "b64_json" in image_data:
                    b64_data = image_data["b64_json"]
                    img_data = base64.b64decode(b64_data)
                    
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    
                    print(f"✅ Image saved: {output_path}")
                    print(f"✅ Size: {len(img_data)} bytes ({len(img_data)/1024/1024:.2f} MB)")
                    
                    if "revised_prompt" in image_data:
                        print(f"📝 AI revised prompt: {image_data['revised_prompt'][:100]}...")
                    
                    return output_path
                else:
                    print("❌ No image data in response")
                    return None
            else:
                print("❌ Error:", data)
                return None
                
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Error after {elapsed:.1f}s: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    style = sys.argv[1] if len(sys.argv) > 1 else "black_orange"
    
    result = generate_hktmall_ad(style)
    
    if result:
        print(f"\n✅ Success! Image: {result}")
    else:
        print("\n❌ Failed")