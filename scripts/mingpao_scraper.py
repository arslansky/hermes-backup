#!/usr/bin/env python3
"""Ming Pao daily scraper v2 — dual-track, ProcessPoolExecutor for sections, MiniMax AI summary

Phase 1: Section pages → CloakBrowser (JS rendering, bypass Cloudflare)
Phase 2: Article content → requests (fast, no CF block)
Phase 3: AI summary → MiniMax-M2.7

Usage: python3 mingpao_scraper.py [YYYYMMDD]
"""

import json
import re
import sys
import os
import time
import subprocess
from datetime import datetime
from urllib.parse import urljoin, unquote
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
from bs4 import BeautifulSoup

# ==== CONFIG ====
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
}

BASE = "https://news.mingpao.com"

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

# MiniMax API (from .env)
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
# Confirmed working endpoint (2026-06-13): https://api.minimax.io/v1/chat/completions
MINIMAX_API_URL = "https://api.minimax.io/v1/chat/completions"

MAX_SECTION_WORKERS = 4  # ProcessPoolExecutor workers
MAX_ARTICLE_WORKERS = 10  # ThreadPoolExecutor workers

# ==== PHASE 1: Fetch section pages via CloakBrowser (subprocess per section group) ====

def _fetch_section_py(name, url):
    """Single section fetch — runs in subprocess, uses CloakBrowser"""
    # This runs in a subprocess — import here
    try:
        from cloakbrowser import launch
        import time as t
        
        browser = launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=45000, wait_until='domcontentloaded')
        t.sleep(2)
        
        # Cookie consent
        try:
            accept_btn = page.locator('text="接受"').first
            if accept_btn.is_visible():
                accept_btn.click()
                t.sleep(1)
        except Exception:
            pass
        
        html = page.content()
        browser.close()
        
        # Extract article links
        links_rel = re.findall(r'href=\"(\.\./(?:ins|pns)/[^"]*?article[^"]+)\"', html)
        links_abs = re.findall(r'href=\"(https://news\.mingpao\.com/(?:ins|pns)/[^"]*?article[^"]+)\"', html)
        all_links = links_rel + links_abs
        
        articles = []
        for l in all_links:
            abs_url = l if l.startswith('https://') else urljoin("https://news.mingpao.com", l.lstrip('../'))
            slug = abs_url.split('/')[-1]
            title_from_slug = unquote(re.sub(r'-[^-]+$', '', slug)).replace('-', '，')
            articles.append((abs_url, title_from_slug))
        
        return name, articles, None
    except Exception as e:
        return name, [], str(e)

def _fetch_section_group_py(args):
    """Process a group of sections (for ProcessPoolExecutor)"""
    name_url_list = args
    results = {}
    for name, url in name_url_list:
        nm, arts, err = _fetch_section_py(name, url)
        results[nm] = (arts, err)
        print(f"  [{nm}] {len(arts)} articles" + (f" ERROR: {err}" if err else ""), flush=True)
    return results

def phase1_fetch_sections():
    """Fetch all section pages using ProcessPoolExecutor (bypasses Playwright asyncio conflict)"""
    print("Phase 1: Fetching section pages (ProcessPoolExecutor, max_workers=4)...")
    
    # Split sections into groups for parallel processing
    # Each worker gets 3-4 sections and processes them sequentially (CloakBrowser must be sequential within worker)
    n_workers = min(MAX_SECTION_WORKERS, len(SECTIONS))
    sections_per_worker = len(SECTIONS) // n_workers + 1
    
    section_groups = []
    for i in range(n_workers):
        start = i * sections_per_worker
        end = min(start + sections_per_worker, len(SECTIONS))
        if start < len(SECTIONS):
            section_groups.append(SECTIONS[start:end])
    
    print(f"  Split into {n_workers} worker groups, {sections_per_worker} sections each")
    
    all_results = {}
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(_fetch_section_group_py, grp): i for i, grp in enumerate(section_groups)}
        for fut in as_completed(futures):
            worker_results = fut.result()
            all_results.update(worker_results)
    
    # Collect all article URLs
    all_urls = {}
    section_counts = {}
    for name in [n for n, _ in SECTIONS]:
        articles, err = all_results.get(name, ([], "not processed"))
        section_counts[name] = len(articles)
        for url, title in articles:
            if url not in all_urls:
                all_urls[url] = (title, name)
    
    total = len(all_urls)
    print(f"  Total: {total} unique articles across {len(SECTIONS)} sections")
    for n, cnt in section_counts.items():
        print(f"    {n}: {cnt}")
    
    return all_urls

# ==== PHASE 2: Scrape article content (parallel requests) ====

def scrape_article(url, fallback_title, section_name):
    """Scrape single article content"""
    try:
        import requests
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.encoding = 'utf-8'
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
        
        return {'url': url, 'title': title, 'section': section_name, 'body': body[:500], 'summary': summary[:300]}
    except Exception as e:
        return {'url': url, 'title': fallback_title, 'section': section_name, 'body': '', 'summary': '', 'error': str(e)[:100]}

def phase2_scrape_articles(all_urls):
    """Scrape all article content using ThreadPoolExecutor"""
    print(f"Phase 2: Scraping {len(all_urls)} articles (ThreadPoolExecutor, max_workers={MAX_ARTICLE_WORKERS})...")
    
    urls_list = list(all_urls.items())
    results = []
    
    # Batch processing with progress
    batch_size = 80
    for i in range(0, len(urls_list), batch_size):
        batch = urls_list[i:i+batch_size]
        batch_results = []
        
        with ThreadPoolExecutor(max_workers=MAX_ARTICLE_WORKERS) as executor:
            futures = {executor.submit(scrape_article, url, title, sec): url
                       for url, (title, sec) in batch}
            for f in as_completed(futures):
                result = f.result()
                batch_results.append(result)
        
        results.extend(batch_results)
        print(f"  Batch {i//batch_size + 1}: {len(batch_results)} done (total: {len(results)})")
    
    # Retry failed
    failed = [r for r in results if r.get('error')]
    if failed:
        print(f"Phase 2b: Retrying {len(failed)} failed articles...")
        retry_results = []
        with ThreadPoolExecutor(max_workers=MAX_ARTICLE_WORKERS) as executor:
            futures = {executor.submit(scrape_article, r['url'], r['title'], r['section']): r['url']
                       for r in failed}
            for f in as_completed(futures):
                retry_results.append(f.result())
        
        failed_urls = {r['url'] for r in failed}
        results = [r for r in results if r['url'] not in failed_urls]
        results.extend(retry_results)
        ok = sum(1 for r in retry_results if not r.get('error'))
        print(f"  Retry: {ok}/{len(failed)} recovered")
    
    return results

# ==== PHASE 3: AI Summary via MiniMax ====

INSTANT_SECTIONS = {"即時港聞", "即時熱點", "即時兩岸", "即時國際"}
# AI summary only for these 3 sections; all others get title lists only
AI_SUMMARY_SECTIONS = {"要聞", "經濟", "國際"}
# Title-list only sections (no AI summary)
TITLE_LIST_SECTIONS = {"港聞", "娛樂", "副刊", "社評", "觀點", "中國"}

def generate_ai_summary(articles, date_str):
    """Generate daily digest — clean format

    - 即時* 版塊：純標題列表（加時間）
    - 要聞/經濟/國際：AI 完整句子摘要
    - 港聞/娛樂/副刊/社評/觀點/中國：純標題列表
    """
    if not articles:
        return "（今日無文章）"

    def group_by_section(arts):
        sections = {}
        for a in arts:
            sec = a.get('section', 'Unknown')
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(a)
        return sections

    def extract_time(title):
        """從標題擷取時間（如有）"""
        # 匹配如 (15:54) 或（15:54）或 [15:54]
        m = re.search(r'[（\[(](\d{2}:\d{2})[)\]]', title)
        return m.group(1) if m else None

    def clean_title(title):
        """移除標題中的時間標記，保留乾淨標題"""
        return re.sub(r'[（\[(]\d{2}:\d{2}[)\]]', '', title).strip()

    output_lines = []

    # ══════════════════════════════════════════════
    # Section 1: 【即時新聞】— 即時港聞/即時熱點/即時兩岸/即時國際 純標題列表
    # ══════════════════════════════════════════════
    instant_articles = [a for a in articles if a.get('section', '') in INSTANT_SECTIONS]
    if instant_articles:
        output_lines.append("【即時新聞】")
        inst_sections = group_by_section(instant_articles)
        for sec, arts in inst_sections.items():
            output_lines.append(f"\n◆ {sec}（{len(arts)}則）")
            for a in arts:
                title = a.get('title', 'N/A')
                time_str = extract_time(title)
                clean_t = clean_title(title)
                if time_str:
                    output_lines.append(f"・{clean_t}（{time_str}）")
                else:
                    output_lines.append(f"・{clean_t}")
        output_lines.append("")

    # ══════════════════════════════════════════════
    # Section 2: 純標題列表 — 港聞/娛樂/副刊/社評/觀點/中國
    # ══════════════════════════════════════════════
    title_list_articles = [a for a in articles if a.get('section', '') in TITLE_LIST_SECTIONS]
    if title_list_articles:
        sections = group_by_section(title_list_articles)
        for sec, arts in sections.items():
            output_lines.append(f"\n◆ {sec}（{len(arts)}則）")
            for a in arts:
                output_lines.append(f"・{a.get('title', 'N/A')}")
        output_lines.append("")

    # ══════════════════════════════════════════════
    # Section 3: 要聞 — 標題列表
    # ══════════════════════════════════════════════
    yaowen_articles = [a for a in articles if a.get('section', '') == "要聞"]
    if yaowen_articles:
        output_lines.append(f"\n◆ 要聞（{len(yaowen_articles)}則）")
        for a in yaowen_articles:
            output_lines.append(f"・{a.get('title', 'N/A')}")
        output_lines.append("")

    # ══════════════════════════════════════════════
    # Section 4: 【AI 摘要】— 要聞 + 經濟 + 國際 AI摘要
    # ══════════════════════════════════════════════
    ai_sections_articles = {sec: [] for sec in AI_SUMMARY_SECTIONS}
    for a in articles:
        if a.get('section', '') in AI_SUMMARY_SECTIONS:
            ai_sections_articles[a.get('section', '')].append(a)

    ai_arts_for_summary = [a for arts in ai_sections_articles.values() for a in arts]

    if not ai_arts_for_summary:
        summary_text = "（今日無需AI摘要的版塊）"
    elif not MINIMAX_API_KEY:
        # Fallback：無 API key，改用 article body 摘要
        sections = group_by_section(ai_arts_for_summary)
        summary_parts = []
        for sec, arts in sections.items():
            summary_parts.append(f"\n【{sec}】")
            for a in arts[:8]:
                body = a.get('body', '') or a.get('summary', '')
                if body:
                    # 取 body 前100字作為摘要
                    summary_parts.append(f"・{body[:100]}...")
        summary_text = '\n'.join(summary_parts) if summary_parts else "（暫無內容）"
    else:
        sections = group_by_section(ai_arts_for_summary)

        # Build prompt — 強調完整句子
        prompt = f"你係香港明報編輯，幫我摘要今日（{date_str}）重點新聞。\n\n"
        prompt += "【重要要求】\n"
        prompt += "1. 每句說話必須係完整句子，以句號（。）結尾，唔好中途截斷。\n"
        prompt += "2. 用廣東話/中文書面語，組織成幾段清晰嘅每日摘要。\n"
        prompt += "3. 每個版塊起碼講2-3個重點，唔好只用幾個字就完結。\n\n"

        for sec in AI_SUMMARY_SECTIONS:
            arts = sections.get(sec, [])
            if not arts:
                continue
            prompt += f"\n## {sec}（{len(arts)} 篇）\n"
            for a in arts[:12]:
                title = a.get('title', '')
                summary = a.get('summary', '') or a.get('body', '')[:300]
                prompt += f"標題：{title}\n  內容：{summary}\n\n"

        prompt += "\n請寫出完整摘要，確保每句都以句號結尾，唔好出現未完成嘅句子。"

        print(f"Phase 3: Generating AI summary ({len(prompt)} chars prompt)...")

        try:
            import urllib.request

            payload = json.dumps({
                "model": "MiniMax-M2.7",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 6000
            }).encode('utf-8')

            req = urllib.request.Request(
                MINIMAX_API_URL,
                data=payload,
                headers={
                    'Authorization': f'Bearer {MINIMAX_API_KEY}',
                    'Content-Type': 'application/json'
                },
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=150) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                raw_summary = result['choices'][0]['message']['content']

                # 清理摘要：移除 MiniMax reasoning artifacts
                # 模型輸出包含大量 <think>...</think> 內部推理，但真正摘要喺外面
                # 策略：移除所有 thinking blocks，再提取含中文的連續內容
                text = raw_summary

                # 移除 <think>...</think> 區塊（多次替換確保完全移除）
                for _ in range(3):
                    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

                # 移除 <result>...</result> 區塊
                text = re.sub(r'<result>.*?</result>', '', text, flags=re.DOTALL)

                # 移除 【...】 評語標籤
                text = re.sub(r'【[^】]*】', '', text)

                # 移除 markdown code blocks
                text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

                # 移除無中文的孤立英文行（但保留含中文摻英文的行）
                lines = text.split('\n')
                cleaned_lines = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    # 跳過無中文既純英文行
                    if not re.search(r'[\u4e00-\u9fff]', stripped):
                        # 但保留含中文既混合行
                        cleaned_lines.append(stripped)
                    else:
                        cleaned_lines.append(stripped)

                # 重新合併，移除多餘空行
                text = '\n'.join(cleaned_lines).strip()

                # 如果清理後文字太短（<50字），說明清理過度，用 fallback
                if len(text) < 50:
                    summary_text = "（AI摘要稍後重試）"
                else:
                    summary_text = text

        except Exception as e:
            summary_text = f"（AI摘要生成失敗，稍後重試）"

    output_lines.append("【AI 摘要】")
    output_lines.append(summary_text)

    return '\n'.join(output_lines)

# ==== MAIN ====

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y%m%d')
    output_json = f"/tmp/mingpao_{date_str}.json"
    output_txt = f"{os.path.expanduser('~')}/.hermes/cron/output/mingpao_digest_{date_str}.txt"
    
    print(f"=== Ming Pao Scraper v2 | Date: {date_str} | MiniMax: {'YES' if MINIMAX_API_KEY else 'NO (fallback)'} ===")
    
    # Phase 1: Section URLs
    start_p1 = time.time()
    all_urls = phase1_fetch_sections()
    p1_time = time.time() - start_p1
    print(f"Phase 1 done: {p1_time:.1f}s")
    
    if not all_urls:
        print("ERROR: No articles found!")
        return
    
    # Phase 2: Article content
    start_p2 = time.time()
    results = phase2_scrape_articles(all_urls)
    p2_time = time.time() - start_p2
    print(f"Phase 2 done: {p2_time:.1f}s ({len(results)} articles)")
    
    # Save raw JSON
    output = {
        'date': date_str,
        'scraped_at': datetime.now().isoformat(),
        'phase1_time_sec': round(p1_time, 1),
        'phase2_time_sec': round(p2_time, 1),
        'total_articles': len(results),
        'sections': {s: len([r for r in results if r['section'] == s]) for s in dict.fromkeys(r['section'] for r in results)},
        'articles': results
    }
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Raw JSON: {output_json}")
    
    # Phase 3: AI Summary
    start_p3 = time.time()
    summary = generate_ai_summary(results, date_str)
    p3_time = time.time() - start_p3
    print(f"Phase 3 done: {p3_time:.1f}s")
    
    # Save output
    os.makedirs(os.path.dirname(output_txt), exist_ok=True)
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(f"明報每日摘要 {date_str}\n")
        f.write(f"=== Scraped: {len(results)} articles | Phase1: {p1_time:.0f}s | Phase2: {p2_time:.0f}s | Phase3: {p3_time:.0f}s ===\n\n")
        f.write(summary)
    
    print(f"\n✅ Done! {len(results)} articles → {output_txt}")
    print(f"   Sections: {output['sections']}")
    
    return output

if __name__ == "__main__":
    main()