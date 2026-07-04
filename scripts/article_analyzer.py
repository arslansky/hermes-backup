#!/usr/bin/env python3
"""
Article Analyzer - 文章分析工具
專門處理新聞、文章、長文分析

輸出結構：
1. 內容要點總結
2. 事實核查 + 概念解釋
3. 核心觀點補充
4. 評論分析
5. 進一步研究方向
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fable_reasoner import AdaptiveReasoner, analyze_question, Complexity, DomainExpertise
from typing import Optional
import json

# ============================================================
# 新增：URL 內容獲取（用 Python 標準庫）
# ============================================================
def fetch_url_content(url: str, max_chars: int = 8000) -> str:
    """
    從 URL 獲取文章內容
    使用 urllib 標準庫
    """
    try:
        import urllib.request
        from urllib.parse import urlparse
        
        # 設置 User-Agent 避免被拒絕
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            # 嘗試解碼
            content = response.read()
            try:
                text = content.decode('utf-8')
            except:
                text = content.decode('utf-8', errors='ignore')
            
            # 簡單清理 HTML 標籤
            import re
            # 移除 script 和 style
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            # 移除 HTML 標籤
            text = re.sub(r'<[^>]+>', ' ', text)
            # 清理多餘空白
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text[:max_chars]
            
    except Exception as e:
        return f"[獲取失敗: {e}]"

class ArticleAnalyzer:
    """
    文章分析器
    系統性輸出結構化分析
    """
    
    def __init__(self, verbose: bool = True):
        self.engine = AdaptiveReasoner(verbose=verbose)
        self.verbose = verbose
    
    def analyze_url(self, url: str, title: str = "") -> dict:
        """
        分析 URL 文章
        自動爬取內容再分析
        """
        if self.verbose:
            print(f"\n🌐 正在獲取: {url}")
        
        # 獲取內容
        content = fetch_url_content(url)
        
        if content.startswith("[獲取失敗"):
            # 如果自動獲取失敗，返回錯誤
            return {
                'error': content,
                'url': url,
            }
        
        # 分析獲取到的內容
        return self.analyze(content, title=title or url, source=url)
    
    def analyze(self, article: str, title: str = "", source: str = "") -> dict:
        """
        完整分析文章
        返回結構化結果
        """
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"📰 文章分析開始")
            if title:
                print(f"標題: {title}")
            if source:
                print(f"來源: {source}")
            print(f"{'='*60}")
        
        # Step 1: 分析文章複雜度和專業度
        analysis = analyze_question(article[:1000])  # 用前1000字分析
        complexity = analysis['complexity']['level']
        expertise = analysis['expertise']['level']
        
        if self.verbose:
            print(f"\n📊 文章分析:")
            print(f"   複雜度: {complexity}")
            print(f"   專業度: {expertise}")
        
        # Step 2: 生成結構化分析
        result = self._generate_full_analysis(article, title, source)
        
        return result
    
    def _generate_full_analysis(self, article: str, title: str, source: str) -> dict:
        """生成完整結構化分析"""
        
        # 構建專業提示詞
        prompt = self._build_analysis_prompt(article, title, source)
        
        # 使用 Fable Reasoner 生成分析
        result = self.engine.think(prompt)
        
        # 解析結果
        parsed = self._parse_analysis(result['answer'])
        parsed['metadata'] = {
            'complexity': result['complexity'],
            'expertise': result['expertise'],
            'model': result['model'],
            'cost_usd': result['cost_usd'],
            'duration_ms': result['duration_ms'],
            'quality_score': result['quality_score'],
        }
        
        return parsed
    
    def _build_analysis_prompt(self, article: str, title: str, source: str) -> str:
        """構建分析提示詞"""
        
        header = ""
        if title:
            header += f"標題: {title}\n"
        if source:
            header += f"來源: {source}\n"
        
        prompt = f"""你係一個專業嘅文章分析師。請對以下文章進行系統性分析。

{header}

【文章內容】
{article}

【輸出要求】
請用以下結構輸出分析：

=== 1. 內容要點總結 ===
- 用 3-5 個 bullet points 總結核心內容
- 每點 20-30 字

=== 2. 事實與概念解釋 ===
- 列出文章提及嘅關鍵事實
- 解釋專業概念（用簡單語言）
- 標註需要核查嘅聲稱

=== 3. 核心觀點補充 ===
- 文章嘅主要論點
- 支持論點嘅證據
- 缺失嘅背景資訊

=== 4. 評論分析 ===
- 文章嘅立場/偏向
- 論證嘅強弱點
- 潛在嘅偏見或誤導

=== 5. 進一步研究方向 ===
- 相關議題
- 可以深入嘅角度
- 建議閱讀嘅資源

請確保輸出結構清晰，易於閱讀。"""
        
        return prompt
    
    def _parse_analysis(self, answer: str) -> dict:
        """解析分析結果"""
        
        sections = {
            'summary': '',
            'facts_concepts': '',
            'core_arguments': '',
            'commentary': '',
            'further_research': '',
            'raw_answer': answer,
        }
        
        # 簡單解析各個部分
        current_section = None
        lines = answer.split('\n')
        buffer = []
        
        for line in lines:
            if '1. 內容要點總結' in line or '內容要點總結' in line:
                if current_section and buffer:
                    sections[current_section] = '\n'.join(buffer).strip()
                current_section = 'summary'
                buffer = []
            elif '2. 事實與概念解釋' in line or '事實與概念解釋' in line:
                if current_section and buffer:
                    sections[current_section] = '\n'.join(buffer).strip()
                current_section = 'facts_concepts'
                buffer = []
            elif '3. 核心觀點補充' in line or '核心觀點補充' in line:
                if current_section and buffer:
                    sections[current_section] = '\n'.join(buffer).strip()
                current_section = 'core_arguments'
                buffer = []
            elif '4. 評論分析' in line or '評論分析' in line:
                if current_section and buffer:
                    sections[current_section] = '\n'.join(buffer).strip()
                current_section = 'commentary'
                buffer = []
            elif '5. 進一步研究方向' in line or '進一步研究方向' in line:
                if current_section and buffer:
                    sections[current_section] = '\n'.join(buffer).strip()
                current_section = 'further_research'
                buffer = []
            elif current_section:
                buffer.append(line)
        
        # 保存最後一個部分
        if current_section and buffer:
            sections[current_section] = '\n'.join(buffer).strip()
        
        return sections
    
    def format_output(self, result: dict) -> str:
        """格式化輸出為易讀格式（混合版：快速概覽 + 深入分析）"""
        
        output = []
        
        # ========== 快速概覽區（30秒版本）==========
        output.append("=" * 60)
        output.append("📰 文章分析報告")
        output.append("=" * 60)
        
        # 元數據
        if 'metadata' in result:
            meta = result['metadata']
            output.append(f"\n📊 分析元數據:")
            output.append(f"   複雜度: {meta.get('complexity', 'N/A')}")
            output.append(f"   專業度: {meta.get('expertise', 'N/A')}")
            output.append(f"   質量評分: {meta.get('quality_score', 'N/A')}/10")
            output.append(f"   成本: ${meta.get('cost_usd', 0):.6f}")
        
        # 核心結論（一句話）
        output.append(f"\n{'='*60}")
        output.append("⚡ 快速概覽（30秒版本）")
        output.append("=" * 60)
        
        # 從 summary 提取核心結論
        if result.get('summary'):
            lines = result['summary'].strip().split('\n')
            # 取第一點作為核心結論
            for line in lines:
                line = line.strip()
                if line and line.startswith('-'):
                    output.append(f"\n🎯 核心結論: {line[1:].strip()}")
                    break
        
        # 關鍵數據（表格）
        output.append(f"\n📈 關鍵數據:")
        
        # 嘗試從 facts_concepts 提取數據
        if result.get('facts_concepts'):
            facts_lines = result['facts_concepts'].split('\n')
            key_metrics = []
            for line in facts_lines:
                line = line.strip()
                # 提取包含數字的行
                if any(char.isdigit() for char in line) and ('%' in line or '倍' in line or 'x' in line.lower() or '萬' in line):
                    # 清理並格式化
                    clean_line = line.lstrip('- ').lstrip('* ')
                    if clean_line and len(clean_line) < 100:
                        key_metrics.append(clean_line)
            
            # 顯示前 5 個關鍵數據
            for i, metric in enumerate(key_metrics[:5], 1):
                output.append(f"   {i}. {metric}")
        
        # 三大要點
        output.append(f"\n💡 三大要點:")
        if result.get('summary'):
            lines = [l.strip() for l in result['summary'].split('\n') if l.strip().startswith('-')]
            for i, line in enumerate(lines[:3], 1):
                clean = line.lstrip('- ').strip()
                output.append(f"   {i}. {clean}")
        
        # ========== 深入分析區（5部分結構）==========
        output.append(f"\n{'='*60}")
        output.append("🔍 深入分析")
        output.append("=" * 60)
        
        # 1. 內容要點總結
        if result.get('summary'):
            output.append(f"\n📌 1. 內容要點總結")
            output.append("-" * 40)
            output.append(result['summary'])
        
        # 2. 事實與概念解釋
        if result.get('facts_concepts'):
            output.append(f"\n{'='*60}")
            output.append("🔍 2. 事實與概念解釋")
            output.append("=" * 60)
            output.append(result['facts_concepts'])
        
        # 3. 核心觀點補充
        if result.get('core_arguments'):
            output.append(f"\n{'='*60}")
            output.append("💡 3. 核心觀點補充")
            output.append("=" * 60)
            output.append(result['core_arguments'])
        
        # 4. 評論分析
        if result.get('commentary'):
            output.append(f"\n{'='*60}")
            output.append("🗣️ 4. 評論分析")
            output.append("=" * 60)
            output.append(result['commentary'])
        
        # 5. 進一步研究方向
        if result.get('further_research'):
            output.append(f"\n{'='*60}")
            output.append("🔬 5. 進一步研究方向")
            output.append("=" * 60)
            output.append(result['further_research'])
        
        # ========== 行動建議區 ==========
        output.append(f"\n{'='*60}")
        output.append("⚡ 行動建議")
        output.append("=" * 60)
        
        # 信賴度評估
        if result.get('commentary'):
            commentary_lower = result['commentary'].lower()
            if '偏見' in commentary_lower or '誤導' in commentary_lower or '核查' in commentary_lower:
                output.append(f"\n⚠️ 信賴度: 需審慎（文章有潛在偏見或需核查聲稱）")
            elif '強點' in commentary_lower and '弱點' in commentary_lower:
                output.append(f"\n✅ 信賴度: 中等（論證有強有弱）")
            else:
                output.append(f"\n✅ 信賴度: 較高")
        
        # 建議下一步
        output.append(f"\n📋 建議下一步:")
        output.append(f"   • 如需快速決策：參考「快速概覽」即可")
        output.append(f"   • 如需深入理解：閱讀「深入分析」各部份")
        if result.get('facts_concepts') and '需要核查' in result['facts_concepts']:
            output.append(f"   • ⚠️ 建議核查「事實與概念解釋」中標註嘅聲稱")
        
        return '\n'.join(output)


# ============================================================
# 異步分析功能（Background Processing）
# ============================================================
import threading
import queue

class AsyncArticleAnalyzer:
    """
    異步文章分析器
    - 收到連結即刻回覆確認
    - 背景處理分析
    - 完成後通知用戶
    """
    
    def __init__(self, verbose: bool = False):
        self.analyzer = ArticleAnalyzer(verbose=verbose)
        self.task_queue = queue.Queue()
        self.results = {}
        self._start_worker()
    
    def _start_worker(self):
        """啟動背景工作線程"""
        def worker():
            while True:
                try:
                    task_id, url, title, callback = self.task_queue.get(timeout=1)
                    if task_id is None:  # 結束信號
                        break
                    
                    # 執行分析
                    result = self.analyzer.analyze_url(url, title)
                    self.results[task_id] = result
                    
                    # 呼叫回調函數通知完成
                    if callback:
                        callback(task_id, result)
                    
                    self.task_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[AsyncWorker] 錯誤: {e}")
        
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
    
    def submit(self, url: str, title: str = "", callback=None) -> str:
        """
        提交分析任務
        返回 task_id，用戶可以憑此查詢結果
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        self.task_queue.put((task_id, url, title, callback))
        return task_id
    
    def get_result(self, task_id: str) -> Optional[dict]:
        """獲取分析結果"""
        return self.results.get(task_id)
    
    def is_ready(self, task_id: str) -> bool:
        """檢查任務是否完成"""
        return task_id in self.results

# 全局異步分析器實例
_async_analyzer = None

def get_async_analyzer() -> AsyncArticleAnalyzer:
    """獲取全局異步分析器"""
    global _async_analyzer
    if _async_analyzer is None:
        _async_analyzer = AsyncArticleAnalyzer()
    return _async_analyzer

# ============================================================
# 同步分析（即時返回，適合短文章）
# ============================================================
_default_analyzer = None

def analyze_article(article: str, title: str = "", source: str = "", verbose: bool = False) -> str:
    """
    同步分析文章（即時返回）
    
    用法：
        result = analyze_article("文章內容", "標題", "來源")
        print(result)
    """
    global _default_analyzer
    
    if _default_analyzer is None:
        _default_analyzer = ArticleAnalyzer(verbose=verbose)
    
    result = _default_analyzer.analyze(article, title, source)
    return _default_analyzer.format_output(result)

# ============================================================
# 異步分析（背景處理，適合長文章）
# ============================================================
def analyze_article_async(url: str, title: str = "", callback=None) -> str:
    """
    異步分析文章
    
    用法：
        task_id = analyze_article_async("https://xxx.com/article")
        # 即刻返回，唔使等
        # 之後用 get_article_result(task_id) 查結果
    """
    analyzer = get_async_analyzer()
    return analyzer.submit(url, title, callback)

def get_article_result(task_id: str) -> Optional[dict]:
    """獲取異步分析結果"""
    analyzer = get_async_analyzer()
    return analyzer.get_result(task_id)

def is_analysis_ready(task_id: str) -> bool:
    """檢查分析是否完成"""
    analyzer = get_async_analyzer()
    return analyzer.is_ready(task_id)


# ============================================================
# 測試
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("📰 Article Analyzer 測試")
    print("=" * 60)
    
    # 測試文章
    test_article = """
    人工智能（AI）技術近年發展迅速，大型語言模型（LLM）如 GPT-4、Claude 等已經能夠處理複雜嘅語言任務。
    然而，有專家警告話 AI 可能會取代大量白領工作，特別係文案、客服、翻譯等行業。
    另一方面，支持者認為 AI 會創造新嘅工作崗位，提高生產力。
    目前各國政府都在制定 AI 監管政策，歐盟已經通過咗 AI Act。
    """
    
    print("\n測試文章分析...")
    result = analyze_article(
        test_article, 
        title="AI 發展與就業市場影響",
        source="測試新聞",
        verbose=True
    )
    
    print("\n" + result)
    
    print("\n" + "=" * 60)
    print("✅ 測試完成！")
    print("=" * 60)
