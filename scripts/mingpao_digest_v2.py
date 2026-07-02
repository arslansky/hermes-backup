#!/usr/bin/env python3
"""
Ming Pao Daily Digest - Smart truncation at sentence boundaries
No AI needed - pure Python text processing with proper sentence-end detection.
"""
import json, os, re, sys
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# ── Config ──────────────────────────────────────────────
SECTIONS = [
    ("要聞", "https://news.mingpao.com/pns/%E8%A6%81%E8%81%9E/section/latest/s00001"),
    ("港聞", "https://news.mingpao.com/pns/%E6%B8%AF%E8%81%AF/section/latest/s00002"),
    ("經濟", "https://news.mingpao.com/pns/%E7%B6%93%E6%BF%9F/section/latest/s00004"),
    ("娛樂", "https://news.mingpao.com/pns/%E5%A8%9B%E6%A8%82/section/latest/s00016"),
    ("副刊", "https://news.mingpao.com/pns/%E5%89%AF%E5%88%8A/section/latest/s00005"),
    ("社評", "https://news.mingpao.com/pns/%E7%A4%BE%E8%A9%95/section/latest/s00003"),
    ("觀點", "https://news.mingpao.com/pns/%E8%A7%82%E9%BB%9E/section/latest/s00012"),
    ("中國", "https://news.mingpao.com/pns/%E4%B8%AD%E5%9C%BD/section/latest/s00013"),
    ("國際", "https://news.mingpao.com/pns/%E5%9C%8B%E9%9A%9B/section/latest/s00014"),
    ("即時港聞", "https://news.mingpao.com/ins/%E6%B8%AF%E8%81%AF/section/latest/s00001"),
    ("即時熱點", "https://news.mingpao.com/ins/%E7%86%B1%E9%BB%9E/section/latest/s00024"),
    ("即時兩岸", "https://news.mingpao.com/ins/%E5%85%A9%E5%B2%B8/section/latest/s00004"),
    ("即時國際", "https://news.mingpao.com/ins/%E5%9C%8B%E9%9A%9B/section/latest/s00005"),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

BASE = "https://news.mingpao.com"
OUT_DIR = os.path.expanduser("~/.hermes/cron/output")

# Proxy config — rotate if one fails (auth: prs:gru)
PROXIES = {
    'http': 'http://prs:gru@c9.hk2.yfip.top:30426',
    'https': 'http://prs:gru@c9.hk2.yfip.top:30426',
}

# ── Sentence-aware truncation ────────────────────────────
SENTENCE_END = set('。！？')
INCOMPLETE = set(',，、；;：:')

def truncate_sentence(text: str, max_len: int = 100) -> str:
    if not text:
        return ""
    text = re.sub(r'[\n\r\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^【明報專訊】\s*', '', text)
    text = re.sub(r'^【.*?】\s*', '', text)
    if len(text) <= max_len and text[-1] in SENTENCE_END:
        return text
    if len(text) <= max_len:
        return text
    end_pos = max_len
    for i in range(max_len - 1, -1, -1):
        if text[i] in SENTENCE_END:
            end_pos = i + 1
            break
    result = text[:end_pos].strip()
    while result and result[-1] in INCOMPLETE:
        result = result[:-1]
    if result and result[-1] not in SENTENCE_END:
        result = result.rstrip() + '…'
    return result

def truncate_sentence_short(text: str, max_len: int = 100) -> str:
    if not text:
        return ""
    text = re.sub(r'[\n\r\t]+', ' ', text).strip()
    text = re.sub(r'^【明報專訊】\s*', '', text)
    if len(text) <= max_len and text[-1] in SENTENCE_END:
        return text
    for i in range(min(len(text)-1, max_len - 1), max(0, max_len - 40), -1):
        if text[i] in SENTENCE_END:
            return text[:i+1]
    result = text[:max_len]
    result = re.sub(r'[，、；:：]$', '', result)
    if result and result[-1] not in SENTENCE_END:
        result = result.rstrip() + '…'
    return result

# ── Scraping ─────────────────────────────────────────────
def fetch_section(name, url):
    """Try proxy first, fallback to direct on failure."""
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=20)
        r.encoding = 'utf-8'
    except Exception as e:
        print(f"  [WARN] Section '{name}' proxy failed ({e}), trying direct...", file=sys.stderr)
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.encoding = 'utf-8'
        except Exception as e2:
            print(f"  [WARN] Section '{name}' direct also failed: {e2}", file=sys.stderr)
            return name, []

    from urllib.parse import urljoin, unquote
    links = re.findall(r'href="(\.\./(?:ins|pns)/[^"]*?article/[^"]+)"', r.text)
    abs_links = []
    for l in links:
        abs_url = urljoin(BASE, l.lstrip('../'))
        title_from_slug = unquote(l.split('/')[-1]).replace('-', '，')
        abs_links.append((abs_url, title_from_slug))
    return name, abs_links

def scrape_article(url, fallback_title):
    """Try proxy first, fallback to direct on failure."""
    try:
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=20)
        r.encoding = 'utf-8'
    except Exception:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.encoding = 'utf-8'
        except Exception:
            return (fallback_title, '', '', url)

    try:
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
    except Exception:
        return (fallback_title, '', '', url)

# ── Main ─────────────────────────────────────────────────
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

    # Phase 3: Generate output
    print("Phase 3: Generating output...", file=sys.stderr)

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

    lines = []
    lines.append('═' * 50)
    lines.append(f'  明報每日精華 — {today}')
    lines.append('═' * 50)
    lines.append('')

    if sections_data.get('要聞') and sections_data['要聞'][0][1]:
        top = sections_data['要聞'][0][1][:60]
        lines.append(f'🔥 今日頭號大事：{top}')
        lines.append('')

    sec_label_map = {
        '中國': '🇨🇳 兩岸中國',
    }

    for sec in ORDER:
        arts = sections_data.get(sec, [])
        if not arts:
            continue

        label = sec_label_map.get(sec, sec)
        lines.append(f'{EMOJI.get(sec, "📌")} {label}')

        is_realtime = sec.startswith('即時')

        for art in arts[:15]:
            sec_name, title, body, summary, url = art

            if is_realtime:
                lines.append(f'  • {title}')
            else:
                text = body if (body and len(body) > len(summary)) else summary
                text = text.strip() if text else ""

                if text:
                    summary_text = truncate_sentence(text, max_len=150)
                else:
                    summary_text = ""

                lines.append(f'  • {title}')
                if summary_text:
                    lines.append(f'    {summary_text}')
                lines.append('')

        lines.append('')

    lines.append('═' * 50)
    lines.append(f'  明報每日精華 {today} | 共 {len(articles_data)} 篇報道')

    content = '\n'.join(lines)
    with open(out_path, 'w') as f:
        f.write(content)

    print(f"\nDone! {len(articles_data)} articles -> {out_path}", file=sys.stderr)
    print(f"File size: {len(content)} chars", file=sys.stderr)

    print("\n── Sample output ──")
    for line in content.split('\n')[8:28]:
        print(line)

if __name__ == '__main__':
    main()