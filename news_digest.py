#!/usr/bin/env python3
"""
News Digest - 短新聞簡潔摘要
針對短新聞（<1000字）優化，快速輸出核心資訊

輸出格式：
1. 標題
2. 一句話摘要
3. 關鍵資訊（時間/地點/人物/事件）
4. 來源
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fable_reasoner import AdaptiveReasoner, analyze_question
from typing import Optional
import json

class NewsDigest:
    """
    短新聞簡潔摘要器
    """
    
    def __init__(self, verbose: bool = False):
        self.engine = AdaptiveReasoner(verbose=verbose)
        self.verbose = verbose
    
    def digest(self, article: str, title: str = "", source: str = "", url: str = "") -> dict:
        """
        生成簡潔摘要
        """
        
        # 分析複雜度（本地，唔調用 API）
        analysis = analyze_question(article[:500])
        complexity = analysis['complexity']['level']
        expertise = analysis['expertise']['level']
        
        # 生成簡潔摘要（用極簡 prompt）
        prompt = self._build_digest_prompt(article, title)
        result = self.engine.think(prompt)
        
        return {
            'title': title or '無標題',
            'source': source or '未知來源',
            'url': url or '',
            'summary': result['answer'].strip(),
            'complexity': complexity,
            'expertise': expertise,
            'cost_usd': result['cost_usd'],
            'duration_ms': result['duration_ms'],
        }
    
    def _build_digest_prompt(self, article: str, title: str) -> str:
        """構建3-5句摘要提示詞"""
        
        prompt = f"""請對以下短新聞生成3-5句摘要。

【要求】
- 3-5句，每句20-30字
- 包含：人物、時間、地點、事件、關鍵細節
- 直接陳述內容，唔好解釋、唔好評論
- 唔好輸出「analysis」「reasoning」等字
- 目的：讓人唔使打開連結都知道發生咩事

【新聞】
{article}

【輸出】（只輸出3-5句）"""
        
        return prompt
    
    def format_digest(self, result: dict) -> str:
        """格式化簡潔摘要（3-5句，唔顯示連結）"""
        
        lines = []
        
        # 標題
        lines.append(f"📰 {result['title']}")
        lines.append(f"📍 {result['source']}")
        lines.append("")  # 空行
        
        # 3-5句摘要（直接內容）
        lines.append(result['summary'])
        
        return '\n'.join(lines)


# ============================================================
# 簡化 API
# ============================================================
_default_digest = None

def digest_news(article: str, title: str = "", source: str = "", url: str = "") -> str:
    """
    極簡短新聞摘要
    
    用法：
        result = digest_news("新聞內容", "標題", "HK01", "https://...")
        print(result)
    """
    global _default_digest
    
    if _default_digest is None:
        _default_digest = NewsDigest(verbose=False)
    
    result = _default_digest.digest(article, title, source, url)
    return _default_digest.format_digest(result)


# ============================================================
# 測試
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("📰 News Digest 測試")
    print("=" * 60)
    
    # 測試文章
    test_article = """
    亞馬遜創辦人貝佐斯（Jeff Bezos）周三（6月17日）樂觀地預測，人工智能（AI）將導致勞動力短缺，而非取代人類。
    
    貝佐斯在巴黎VivaTech科技大會上直言：「我知道很多人，包括許多聰明人，都擔心AI會使人類變得可有可無，但我完全不同意這種觀點。事實上，我認為AI反而會創造勞動力短缺。」
    
    他主張，人類有「無窮無盡」的事可做，而AI將降低目前阻礙人們創造與建設的門檻。
    """
    
    result = digest_news(
        test_article,
        title="貝佐斯樂觀預測：AI不會取代人類　反而將導致勞動力短缺",
        source="HK01",
        url="https://www.hk01.com/..."
    )
    
    print(result)
    print("\n" + "=" * 60)
    print("✅ 測試完成！")
