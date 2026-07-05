#!/usr/bin/env python3
"""news_summary.py - 拎新聞全文 + 格式化作摘要
Usage: python3 news_summary.py "<URL>"
Output: 時、地、人、事件、重點、正文
"""
import subprocess, re, html, sys, time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = ["Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language: zh-HK,zh-TW,zh;q=0.9,en;q=0.8"]

def log(msg):
    print(msg, file=sys.stderr)

def fetch_html(url):
    cmd = ["curl", "-s", "-A", UA, "-H", HEADERS[0], "-H", HEADERS[1],
           "-L", "--compressed", url]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    out, _ = p.communicate(timeout=15)
    return out.decode("utf-8", errors="ignore")

def extract_meta(html_str, name):
    """Extract meta tag content"""
    m = re.search(rf'<meta\s+name="{name}"\s+content="([^"]+)"', html_str, re.IGNORECASE)
    return html.unescape(m.group(1)) if m else ""

def extract_text(html_str):
    candidates = []

    # Method A: "content" field in JSON (Doubao, 881903)
    for m in re.finditer(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', html_str):
        raw = m.group(1)
        clean = re.sub(r'<[^>]*>', '', raw)
        clean = html.unescape(clean)
        clean = clean.replace('\\n', ' ').replace('\\r', '').replace('\\t', ' ')
        clean = re.sub(r'\\u[0-9a-fA-F]{4}', '', clean)
        clean = ' '.join(clean.split())
        if len(clean) > 100:
            candidates.append(clean)

    # Method B: article_contents block
    m = re.search(r'<article[^>]*data-content[^>]*>', html_str, re.IGNORECASE)
    if m:
        block = m.group(0)
        m2 = re.search(r'data-content="([^"]+)"', block)
        if m2:
            clean = re.sub(r'<[^>]*>', '', m2.group(1))
            clean = html.unescape(clean)
            clean = ' '.join(clean.split())
            if len(clean) > 50:
                candidates.append(clean)

    if candidates:
        return max(candidates, key=len)

    # Method C: meta description
    desc = extract_meta(html_str, "description")
    if desc and len(desc) > 50:
        return desc

    return ""

def extract_title(html_str):
    m = re.search(r'<title>([^<]+)</title>', html_str)
    if m:
        return m.group(1).split(' - ')[0].split(' | ')[0].strip()
    for pat in [r'"title"\s*:\s*"([^"]+)"',
                r'"og:title"\s*content="([^"]+)"',
                r'property="og:title"\s*content="([^"]+)"']:
        m = re.search(pat, html_str, re.IGNORECASE)
        if m:
            return m.group(1)
    return "(無標題)"

def extract_date(html_str):
    # published time - multiple formats
    for pat, grp in [
        (r'"datePublished"\s*:\s*"([^"]+)"', 1),
        (r'"create_datetime"\s*:\s*"([^"]+)"', 1),
        (r'"display_ts"\s*:\s*(\d+)', 9),   # special: timestamp
        (r'<meta\s+property="article:published_time"\s+content="([^"]+)"', 1),
    ]:
        m = re.search(pat, html_str, re.IGNORECASE)
        if m:
            if grp == 9:
                return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(m.group(1))))
            return m.group(1).replace("T", " ").replace("+08:00", "").strip()
    return ""

def extract_keywords(text):
    """Simple keyword extraction from first 3 sentences"""
    if not text:
        return []
    # Get first 200 chars
    first = text[:200]
    # Look for title-like patterns or named entities
    keywords = []
    # Extract quoted terms
    keywords.extend(re.findall(r'「([^」]*)」', first))
    # Named entities
    names = re.findall(r'(?:CEO|總裁|主席|創辦人|部長|主任)\s*([\u4e00-\u9fff]{2,4})', first)
    keywords.extend([n for n in names if len(n) > 1])
    return keywords[:5]

def generate_summary(text, title):
    """Generate structured summary from news text"""
    if not text or len(text) < 50:
        return {}

    summary = {}
    lines = text.split('。')

    # 時 - taken from date

    # 地 - extract location from first paragraphs
    locations = set()
    for loc_pat in ['香港', '內地', '中國', '美國', '台灣', '北京', '上海', '深圳', '廣州',
                    '日本', '南韓', '英國', '法國', '德國', '歐洲', '亞洲', '華盛頓', '倫敦',
                    '巴黎', '東京']:
        if loc_pat in text[:300]:
            locations.add(loc_pat)
    summary['地'] = '、'.join(sorted(locations, key=lambda x: -text[:300].index(x)))

    # 人 - extract names from first paragraphs
    # Priority 1: Title + Name pattern (most reliable)
    people = []
    seen = set()
    for m in re.finditer(r'(?:CEO|總裁|主席|創辦人|部長|主任)([\u4e00-\u9fff]{2,3})(?=[^\u4e00-\u9fff]|$)', text[:500]):
        p = m.group(1)
        if p not in seen:
            seen.add(p)
            people.append(p)
    # Priority 2: Org + Name. We strip trailing noise.
    for m in re.finditer(r'[\u4e00-\u9fff]{4,}(?:CEO|總裁|主席|創辦人|部長|主任)([\u4e00-\u9fff]{2,4})', text[:500]):
        raw = m.group(1)
        # Strip trailing CJK particles (之、的、與、和、或等)
        p = re.sub(r'[之的與和或於、，。]$', '', raw)[:3]
        if p not in seen and len(p) >= 2:
            seen.add(p)
            people.append(p)
        # Also try stripping org suffix from match context
        # '總裁余偉文' → P1 should catch '余偉文'
    # Priority 3: Quoted speaker (name says)
    common = {'同時','方面','平台','通知','業界','用戶','官方','最後','報告','首先',
              '其次','第三','代理','方面則','下線','報道','說明','引述','顯示','預計',
              '提到','首席','之前','季度','日前','同樣','如何','近日','今年','今日',
              '昨日','市民','組織','機構','官員','記者','媒體','官方還','同時宣布',
              '幾乎同時','通義千問','千問同樣','業界分析','分析','裁余偉文','五五規劃',
              '規劃','金管局','局方'}
    for m in re.finditer(r'([\u4e00-\u9fff]{2,4})(?:表示|指出|說|強調|宣布|透露|提到|稱|認為|呼籲)', text[:500]):
        p = m.group(1)
        if p not in seen and p not in common:
            seen.add(p)
            people.append(p)
    if people:
        summary['人'] = '、'.join(people[:3])

    # 事件 - first paragraph as event
    for line in lines[:3]:
        line = line.strip()
        if len(line) > 20:
            summary['事件'] = line
            break

    # 重點 - key points
    key_points = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # Look for marker words
        if any(kw in line for kw in ['首先', '其次', '第三', '最後', '業界認為', '分析指出',
                                     '報告顯示', '原因', '影響', '預測', '意味']):
            key_points.append(line)
        elif line.startswith('「') and len(line) > 15:
            key_points.append(line)
        elif any(kw in line for kw in ['下線', '停用', '刪除', '約束', '聚焦', '剝離']):
            key_points.append(line)

    # If few markers, take first lines as fallback
    if not key_points:
        key_points = [l.strip() for l in lines[:3] if len(l.strip()) > 15][:3]
    summary['重點'] = ' | '.join(key_points[:3])

    return summary

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        print("Usage: python3 news_summary.py <URL>")
        sys.exit(1)

    log(f"Fetching: {url}")
    html_str = fetch_html(url)
    title = extract_title(html_str)
    date_str = extract_date(html_str)
    text = extract_text(html_str)

    if not text or len(text) < 50:
        print(f"❌ 未能提取正文（length={len(text) if text else 0}）")
        sys.exit(1)

    # ├─ 結構化摘要 ──────────────────────────
    s = generate_summary(text, title)
    loc = s.get('地', '—')
    people = s.get('人', '—')
    event_desc = s.get('事件', title)
    key_points = s.get('重點', '—')

    print("=" * 50)
    print(f"📰 {title}")
    print("=" * 50)
    print()
    print(f"🕐 時：{date_str or '—'}")
    print(f"📍 地：{loc}")
    print(f"👤 人：{people}")
    print(f"📋 事件：{event_desc}。")
    print(f"🔑 重點：{key_points}")
    print()
    print(f"🔗 {url}")
    print()

    print("-" * 50)
    print("📄 正文全文：")
    print(text)
    print()
    print("-" * 50)
    print(f"✅ 提取成功（{len(text)}字）")

if __name__ == "__main__":
    main()