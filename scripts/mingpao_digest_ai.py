#!/usr/bin/env python3
"""
Ming Pao Daily Digest - AI-powered news summarization
Scrapes Ming Pao articles and uses MiniMax API to generate Chinese summaries.
"""
import json, os, re, sys
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# ── Config ──────────────────────────────────────────────
SECTIONS = [
    ("要聞", "https://news.mingpao.com/pns/要聞/section/latest/s00001"),
    ("港聞", "https://news.mingpao.com/pns/港聞/section/latest/s00002"),
    ("經濟", "https://news.mingpao.com/pns/經濟/section/latest/s00004"),
    ("娛樂", "https://news.mingpao.com/pns/娛樂/section/latest/s00016"),
    ("副刊", "https://news.mingpao.com/pns/副刊/section/latest/s00005"),
    ("社評", "https://news.mingpao.com/pns/社評/section/latest/s00003"),
    ("觀點", "https://news.mingpao.com/pns/觀點/section/latest/s00012"),
    ("中國", "https://news.mingpao.com/pns/中國/section/latest/s00013"),
    ("國際", "https://news.mingpao.com/pns/國際/section/latest/s00014"),
    ("即時港聞", "https://news.mingpao.com/ins/港聞/section/latest/s00001"),
    ("即時熱點", "https://news.mingpao.com/ins/熱點/section/latest/s00024"),
    ("即時兩岸", "https://news.mingpao.com/ins/兩岸/section/latest/s00004"),
    ("即時國際", "https://news.mingpao.com/ins/國際/section/latest/s00005"),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

BASE = "https://news.mingpao.com"
OUT_DIR = os.path.expanduser("~/.hermes/cron/output")

# ── MiniMax API ─────────────────────────────────────────
def get_minimax_key():
    env_path = os.path.expanduser("~/.hermes/.env")
    with open(env_path) as f:
        for line in f:
            if line.startswith("MINIMAX_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("MINIMAX_API_KEY not found in ~/.hermes/.env")

MINIMAX_KEY = get_minimax_key()
MINIMAX_URL = "https://api.minimax.io/v1/chat/completions"

def summarize_text(text: str, title: str) -> str:
    """Use MiniMax API to summarize text into a complete Chinese sentence ≤100 chars."""
    if not text or len(text.strip()) < 20:
        return ""
    
    # Clean the text
    text = text.replace('\n', ' ').replace('\r', '')
    text = re.sub(r'\s+', ' ', text)
    # Remove 【明報專訊】 prefix if present
    text = re.sub(r'^【明報專訊】\s*', '', text)
    
    prompt = f"""你係一個香港新聞摘要助手。請將以下新聞文章摘要成一段完整嘅中文句子，唔好超過100個字符。

標題：{title}
正文：{text[:1500]}

要求：
- 必須係完整句子，以句號「。」結尾
- 唔准喺句子中途停
- 唔好加入「報道指」、「記者表示」等帽
- 唔好超過100個中文字符

直接輸出摘要，唔好加任何標記或引號。"""

    try:
        resp = requests.post(
            MINIMAX_URL,
            headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
            json={
                "model": "MiniMax-M2",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.3,
            },
            timeout=30,
        )
        data = resp.json()
        if resp.status_code != 200:
            print(f"  [WARN] MiniMax API error {resp.status_code}: {data}", file=sys.stderr)
            return ""
        
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        # Ensure it ends with a proper sentence ending
        if content and content[-1] not in '。！？':
            # Try to find a sentence boundary
            for i in range(len(content)-1, max(0, len(content)-50), -1):
                if content[i] in '。！？':
                    content = content[:i+1]
                    break
        
        # Enforce 100 char limit at sentence boundary
        if len(content) > 100:
            truncated = content[:100]
            for i in range(99, 49, -1):
                if truncated[i] in '。！？':
                    content = truncated[:i+1]
                    break
            else:
                content = truncated[:97] + '…'
        
        return content
    except Exception as e:
        print(f"  [WARN] Summarize error: {e}", file=sys.stderr)
        return ""

def summarize_batch(articles: list) -> list:
    """Summarize a batch of articles concurrently."""
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(summarize_text, art[2], art[1]): art
            for art in articles if art[2] and len(art[2].strip()) > 20
        }
        for f in as_completed(futures):
            art = futures[f]
            summary = f.result()
            results.append((art[0], art[1], summary))  # (section, title, summary)
    
    # For articles without body/summary, use empty summary
    for art in articles:
        if not art[2] or len(art[2].strip()) <= 20:
            results.append((art[0], art[1], ""))
    
    return results

# ── Scraping ────────────────────────────────────────────
def fetch_section(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
        from urllib.parse import urljoin, unquote
        links = re.findall(r'href="(\.\./(?:ins|pns)/[^"]*?article/[^"]+)"', r.text)
        abs_links = []
        for l in links:
            abs_url = urljoin(BASE, l.lstrip('../'))
            title_from_slug = unquote(l.split('/')[-1]).replace('-', '，')
            abs_links.append((abs_url, title_from_slug))
        return name, abs_links
    except Exception as e:
        print(f"  [WARN] Section '{name}' failed: {e}", file=sys.stderr)
        return name, []

def scrape_article(url, fallback_title):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else fallback_title
        og = soup.find('meta', property='og:description')
        summary = og.get('content', '') if og else ''
        paras = []
        for p in soup.find_all('p'):
            t = p.get_text(strip=True)
            if len(t) > 20 and 'outdated browser' not in t.lower():
                paras.append(t)
        body = '\n'.join(paras[:30]) if paras else summary
        return (title, body, summary, url)
    except Exception as e:
        return (fallback_title, '', '', url)

# ── Main ────────────────────────────────────────────────
def main():
    today = date.today().strftime('%Y.%m.%d')
    today_file = date.today().strftime('%Y%m%d')
    out_path = os.path.join(OUT_DIR, f'mingpao_digest_{today_file}.txt')

    print("Phase 1: Fetching section pages...", file=sys.stderr)
    section_articles = {}
    with ThreadPoolExecutor(max_workers=13) as executor:
        futures = {executor.submit(fetch_section, n, u): n for n, u in SECTIONS}
        for f in as_completed(futures):
            name, articles = f.result()
            section_articles[name] = articles

    # Collect unique URLs
    all_urls = {}
    for sec, articles in section_articles.items():
        for url, title in articles:
            if url not in all_urls:
                all_urls[url] = (sec, title)

    total = len(all_urls)
    print(f"  Found {total} unique articles", file=sys.stderr)

    # Phase 2: Scrape article content
    print("Phase 2: Scraping article content...", file=sys.stderr)
    articles_data = []
    urls_list = list(all_urls.items())
    batch_size = 80

    for i in range(0, len(urls_list), batch_size):
        batch = urls_list[i:i+batch_size]
        batch_results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(scrape_article, url, title): (sec, url)
                       for url, (sec, title) in batch}
            for f in as_completed(futures):
                sec, url = futures[f]
                title, body, summary, _ = f.result()
                batch_results.append((sec, title, body, summary, url))
        articles_data.extend(batch_results)
        print(f"  Batch {i//batch_size + 1}/{(total+batch_size-1)//batch_size}: {len(batch_results)} done", file=sys.stderr)

    # Phase 3: AI Summarization
    print("Phase 3: AI Summarization...", file=sys.stderr)
    
    # Group by section
    from collections import defaultdict
    sections_data = defaultdict(list)
    for art in articles_data:
        sections_data[art[0]].append(art)

    ORDER = ['要聞', '港聞', '經濟', '國際', '兩岸中國', '即時港聞', '即時熱點', '即時兩岸', '即時國際', '娛樂', '副刊', '社評', '觀點']
    EMOJI = {
        '要聞': '🔥', '港聞': '🏙️', '經濟': '📉', '娛樂': '🎬',
        '副刊': '📚', '社評': '📝', '觀點': '💭', '中國': '🇨🇳',
        '國際': '🌍', '即時港聞': '📰', '即時熱點': '⚡',
        '即時兩岸': '🌏', '即時國際': '🌐'
    }

    # Build output
    lines = []
    lines.append('══════════════════════════════════')
    lines.append(f'明報每日精華 — {today}')
    lines.append('══════════════════════════════════')
    lines.append('')

    # Top headline from 要聞
    top_headline = None
    if sections_data.get('要聞') and sections_data['要聞'][0][3]:
        top_headline = sections_data['要聞'][0][1][:60]
        lines.append(f'🔥 今日頭號大事：{top_headline}')
        lines.append('')

    # Map section name for display
    sec_label_map = {
        '中國': '🇨🇳 兩岸中國',
    }

    for sec in ORDER:
        arts = sections_data.get(sec, [])
        if not arts:
            continue
        
        label = sec_label_map.get(sec, sec)
        emoji = EMOJI.get(sec, '📌')
        sec_header = f'{emoji} {label}' if '🇨🇳' not in label else f'{label}'
        lines.append(sec_header)

        is_realtime = sec.startswith('即時')

        for art in arts[:15]:
            sec_name, title, body, summary, url = art
            if is_realtime:
                lines.append(f'  • {title}')
            else:
                # Generate AI summary
                ai_summary = summarize_text(body if body else summary, title)
                if not ai_summary:
                    # Fallback: truncate body at sentence boundary
                    text = body if body else summary
                    text = text.replace('\n', ' ').strip()
                    text = re.sub(r'^【明報專訊】\s*', '', text)
                    for i in range(len(text)-1, 49, -1):
                        if text[i] in '。！？':
                            text = text[:i+1]
                            break
                    else:
                        if len(text) > 100:
                            text = text[:97] + '…'
                    ai_summary = text

                lines.append(f'  • {title}')
                if ai_summary:
                    lines.append(f'    {ai_summary}')
        lines.append('')

    lines.append('══════════════════════════════════')
    lines.append(f'明報每日精華 {today} | 共 {len(articles_data)} 篇報道')

    content = '\n'.join(lines)
    with open(out_path, 'w') as f:
        f.write(content)

    print(f"\nDone! {len(articles_data)} articles -> {out_path}", file=sys.stderr)
    print(f"File size: {len(content)} chars", file=sys.stderr)

if __name__ == '__main__':
    main()