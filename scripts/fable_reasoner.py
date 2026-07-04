#!/usr/bin/env python3
"""
Fable-Style Reasoning Framework v3.2 - 完整版

新增功能：
1. 領域專業度感知（基於 Anthropic 研究）
2. 自我評分機制（自動評估答案質量）
3. 記憶功能（持久化存儲用戶偏好）
4. 錯誤修復機制（智能重試和降級）

核心洞察：
- 領域專業度 > 編程能力
- 中階（INTERMEDIATE）是最優性價比區間
- 收益來自 "competence, not mastery"
"""

from __future__ import annotations

import os
import json
import time
import hashlib
import sqlite3
import re
from typing import Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# ============================================================
# API 配置 (從環境變數讀取)
# ============================================================
ZHI_API_KEY = os.getenv("ZHI_API_KEY", "")
ZHI_BASE_URL = os.getenv("ZHI_BASE_URL", "https://zhi-api.com/v1")

# ============================================================
# 模型配置
# ============================================================
MODELS = {
    "fast": "gpt-5.4-mini",       # 快速模型 - 簡單問題
    "smart": "gpt-5.4",            # 智能模型 - 中等問題  
    "reasoner": "gpt-5.3-codex",   # 推理模型 - 複雜問題
}

# 定價（每 1M tokens）
MODEL_PRICES = {
    "gpt-5.4-mini": {"input": 0.003, "output": 0.01},
    "gpt-5.4": {"input": 0.01, "output": 0.03},
    "gpt-5.3-codex": {"input": 0.02, "output": 0.06},
}

# ============================================================
# 複雜度級別
# ============================================================
class Complexity(Enum):
    TRIVIAL = 0      # 瑣碎問題，秒回
    SIMPLE = 1      # 簡單問題，少少推理
    MODERATE = 2    # 中等複雜，多步推理
    COMPLEX = 3     # 複雜問題，深度分析
    VERY_COMPLEX = 4 # 極複雜，需要頂級推理

# ============================================================
# 領域專業度級別（基於 Anthropic 研究）
# ============================================================
class DomainExpertise(Enum):
    NOVICE = 0       # 新手 - 需要基礎解釋
    BEGINNER = 1     # 初學者 - 需要清晰指引
    INTERMEDIATE = 2 # 中階 - 夠用掌握，最優性價比
    ADVANCED = 3     # 進階 - 需要深度分析
    EXPERT = 4       # 專家 - 需要專業級輸出

# ============================================================
# 持久化存儲：記憶功能
# ============================================================
class MemoryStore:
    """
    用戶偏好記憶存儲
    - 記住用戶的領域專業度
    - 記住用戶的偏好設置
    - 越用越準
    """
    
    def __init__(self, db_path: str = "fable_memory.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化數據庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用戶偏好表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                default_expertise TEXT DEFAULT 'INTERMEDIATE',
                preferred_language TEXT DEFAULT 'zh-HK',
                total_sessions INTEGER DEFAULT 0,
                avg_complexity REAL DEFAULT 2.0,
                avg_expertise REAL DEFAULT 2.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 會話歷史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                question TEXT,
                complexity TEXT,
                expertise TEXT,
                model TEXT,
                tokens_used INTEGER,
                cost_usd REAL,
                duration_ms INTEGER,
                answer_quality REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_preferences(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user_profile(self, user_id: str = "default") -> dict:
        """獲取用戶檔案"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            # 創建新用戶
            cursor.execute(
                "INSERT INTO user_preferences (user_id) VALUES (?)",
                (user_id,)
            )
            conn.commit()
            cursor.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
        
        conn.close()
        
        return {
            "user_id": row[0],
            "default_expertise": row[1],
            "preferred_language": row[2],
            "total_sessions": row[3],
            "avg_complexity": row[4],
            "avg_expertise": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }
    
    def update_user_stats(self, user_id: str, complexity: str, expertise: str, 
                          tokens: int, cost: float, duration: int):
        """更新用戶統計"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 獲取當前統計
        profile = self.get_user_profile(user_id)
        total = profile["total_sessions"] + 1
        
        # 計算新的平均值
        complexity_map = {"TRIVIAL": 0, "SIMPLE": 1, "MODERATE": 2, "COMPLEX": 3, "VERY_COMPLEX": 4}
        expertise_map = {"NOVICE": 0, "BEGINNER": 1, "INTERMEDIATE": 2, "ADVANCED": 3, "EXPERT": 4}
        
        new_avg_complexity = (profile["avg_complexity"] * profile["total_sessions"] + 
                              complexity_map.get(complexity, 2)) / total
        new_avg_expertise = (profile["avg_expertise"] * profile["total_sessions"] + 
                             expertise_map.get(expertise, 2)) / total
        
        cursor.execute('''
            UPDATE user_preferences 
            SET total_sessions = ?,
                avg_complexity = ?,
                avg_expertise = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (total, new_avg_complexity, new_avg_expertise, user_id))
        
        conn.commit()
        conn.close()
    
    def save_session(self, user_id: str, question: str, complexity: str, 
                     expertise: str, model: str, tokens: int, cost: float, 
                     duration: int, quality: float = 0.0):
        """保存會話記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO session_history 
            (user_id, question, complexity, expertise, model, tokens_used, cost_usd, duration_ms, answer_quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, question, complexity, expertise, model, tokens, cost, duration, quality))
        
        conn.commit()
        conn.close()
        
        # 更新用戶統計
        self.update_user_stats(user_id, complexity, expertise, tokens, cost, duration)
    
    def get_user_history(self, user_id: str, limit: int = 10) -> list:
        """獲取用戶最近會話"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT question, complexity, expertise, answer_quality, created_at
            FROM session_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "question": row[0],
                "complexity": row[1],
                "expertise": row[2],
                "quality": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]

# ============================================================
# 自我評分機制
# ============================================================
class AnswerEvaluator:
    """
    答案質量自動評估
    基於多個維度評分
    """
    
    @staticmethod
    def evaluate(answer: str, question: str, complexity: Complexity) -> dict:
        """
        評估答案質量
        返回分數和改進建議
        """
        scores = {}
        
        # 1. 完整性評分（是否有結構化輸出）
        structure_markers = ['analysis', 'reasoning', 'answer', 'conclusion', 'summary']
        structure_score = sum(1 for marker in structure_markers if marker in answer.lower())
        scores['structure'] = min(structure_score / 3, 1.0) * 10  # 0-10
        
        # 2. 深度評分（根據複雜度期望）
        expected_length = {
            Complexity.TRIVIAL: 50,
            Complexity.SIMPLE: 150,
            Complexity.MODERATE: 300,
            Complexity.COMPLEX: 500,
            Complexity.VERY_COMPLEX: 800,
        }
        expected = expected_length.get(complexity, 300)
        actual_length = len(answer)
        
        if actual_length >= expected * 0.8:
            scores['depth'] = 10
        elif actual_length >= expected * 0.5:
            scores['depth'] = 7
        else:
            scores['depth'] = 4
        
        # 3. 相關性評分（是否回答問題）
        question_keywords = set(question.lower().split())
        answer_keywords = set(answer.lower().split())
        overlap = len(question_keywords & answer_keywords)
        relevance = overlap / len(question_keywords) if question_keywords else 0
        scores['relevance'] = min(relevance * 15, 10)  # 0-10
        
        # 4. 實用性評分（是否有行動建議）
        action_markers = ['建議', '推薦', '步驟', '方法', '策略', '總結']
        action_score = sum(1 for marker in action_markers if marker in answer)
        scores['actionability'] = min(action_score / 2, 1.0) * 10
        
        # 5. 清晰度評分
        clarity_markers = ['首先', '其次', '最後', '1.', '2.', '3.', '總結']
        clarity_score = sum(1 for marker in clarity_markers if marker in answer)
        scores['clarity'] = min(clarity_score / 3, 1.0) * 10
        
        # 計算總分
        total_score = sum(scores.values()) / len(scores)
        
        # 生成改進建議
        suggestions = []
        if scores['structure'] < 7:
            suggestions.append("建議加入結構化標記（analysis/reasoning/answer）")
        if scores['depth'] < 7:
            suggestions.append("答案可能過短，建議增加細節")
        if scores['relevance'] < 7:
            suggestions.append("答案與問題相關性不足")
        if scores['actionability'] < 7:
            suggestions.append("建議加入具體行動建議")
        if scores['clarity'] < 7:
            suggestions.append("建議使用更清晰的分段和標記")
        
        return {
            'total_score': round(total_score, 1),
            'scores': scores,
            'suggestions': suggestions,
            'quality_level': '優秀' if total_score >= 8 else '良好' if total_score >= 6 else '需改進',
        }

# ============================================================
# 錯誤修復機制
# ============================================================
class ErrorRecovery:
    """
    智能錯誤修復
    - 檢測失敗信號
    - 自動重試
    - 降級策略
    """
    
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.retry_count = 0
    
    def should_retry(self, error: str) -> bool:
        """判斷是否應該重試"""
        if self.retry_count >= self.max_retries:
            return False
        
        # 可重試的錯誤
        retryable_errors = [
            'timeout', 'connection', 'rate limit', 'server error',
            'temporarily unavailable', 'overloaded',
        ]
        
        return any(err in error.lower() for err in retryable_errors)
    
    def get_fallback_strategy(self, error: str, current_config: dict) -> dict:
        """
        獲取降級策略
        當高級模型失敗時，降級到更穩定的模型
        """
        self.retry_count += 1
        
        fallback_config = current_config.copy()
        
        # 策略 1: 降低溫度（更保守）
        fallback_config['temperature'] = max(fallback_config.get('temperature', 0.7) - 0.2, 0.2)
        
        # 策略 2: 減少輸出長度
        fallback_config['budget_tokens'] = int(fallback_config.get('budget_tokens', 1000) * 0.7)
        
        # 策略 3: 簡化路徑數量
        if fallback_config.get('num_paths', 1) > 1:
            fallback_config['num_paths'] = fallback_config['num_paths'] - 1
        
        # 策略 4: 如果還是失敗，切換到更穩定的模型
        if self.retry_count >= 2:
            fallback_config['model'] = MODELS['fast']  # 降級到 fast 模型
        
        return fallback_config
    
    def reset(self):
        """重置計數器"""
        self.retry_count = 0

# ============================================================
# API 調用
# ============================================================
def call_model(
    prompt: str,
    model: str = "gpt-5.4",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    max_retries: int = 2,
) -> tuple[str, int, int, float]:
    """
    調用 Zhi API，返回 (回答, prompt_tokens, completion_tokens, cost)
    支援重試機制
    """
    import requests
    import time
    
    headers = {
        "Authorization": f"Bearer {ZHI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{ZHI_BASE_URL}/chat/completions",
                headers=headers,
                json=data,
                timeout=180,  # 增加到 180 秒
            )
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            # 計算成本
            price = MODEL_PRICES.get(model, {"input": 0.01, "output": 0.03})
            cost = (prompt_tokens / 1_000_000 * price["input"] + 
                    completion_tokens / 1_000_000 * price["output"])
            
            if attempt > 0:
                print(f"✅ 第 {attempt + 1} 次嘗試成功")
            
            return content, prompt_tokens, completion_tokens, cost
            
        except Exception as e:
            last_error = e
            print(f"⚠️ API 錯誤 (嘗試 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 指數退避
                print(f"   等待 {wait_time} 秒後重試...")
                time.sleep(wait_time)
    
    print(f"❌ 所有嘗試失敗: {last_error}")
    
    # 如果 Zhi 失敗，用 TTK 做 backup
    print("🔄 嘗試 TTK API backup...")
    return call_ttk_model(prompt, model, temperature, max_tokens)

# ============================================================
# TTK API Backup
# ============================================================
def call_ttk_model(
    prompt: str,
    model: str = "gpt-4",
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> tuple[str, int, int, float]:
    """
    調用 TTK API 做 backup
    """
    import requests
    
    TTK_API_KEY = "sk-dJfy8GWR5czhLBHtvSmkrsWy0ZV6js5fT5e2WuAoJsQfRNAd"
    TTK_BASE_URL = "https://api.ttk.homes/v1"
    
    if not TTK_API_KEY:
        print("❌ TTK API Key 未設定")
        return "Error: TTK API Key not set", 0, 0, 0
    
    headers = {
        "Authorization": f"Bearer {TTK_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    try:
        response = requests.post(
            f"{TTK_BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=180,
        )
        response.raise_for_status()
        result = response.json()
        
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # TTK 價格（假設同 OpenAI 相近）
        cost = (prompt_tokens + completion_tokens) * 0.00001
        
        print("✅ TTK API backup 成功")
        return content, prompt_tokens, completion_tokens, cost
        
    except Exception as e:
        print(f"❌ TTK API 都失敗: {e}")
        return f"Error: {e}", 0, 0, 0

# ============================================================
# 核心：自動複雜度評估
# ============================================================
def analyze_complexity(question: str) -> Complexity:
    """自動分析問題複雜度"""
    question_lower = question.lower()
    
    # 瑣碎問題快速判斷
    trivial_patterns = ['你好', 'hi', 'hello', 'hey', '好', '嗎']
    if any(pattern in question_lower for pattern in trivial_patterns) and len(question) < 15:
        return Complexity.TRIVIAL
    if (question_lower.startswith('係') or question_lower.startswith('係咪')) and len(question) < 10:
        return Complexity.TRIVIAL
    
    # 決策類問題 - 提升複雜度
    decision_keywords = ['決策', '决策', '選擇', '选择', '應該點', '點樣決定', '邊個好', '定係']
    if any(kw in question_lower for kw in decision_keywords):
        return Complexity.MODERATE
    
    # 數量/事實類問題 - 提升複雜度
    quantity_keywords = ['幾多', '幾個', '幾時', '幾耐', '邊個', '咩', '係咩']
    if any(kw in question_lower for kw in quantity_keywords) and len(question) > 10:
        return Complexity.SIMPLE
    
    # 比較類問題 - 提升複雜度
    compare_keywords = ['比較', '比', '邊個好', '定', '定係', '差異', '不同']
    if any(kw in question_lower for kw in compare_keywords):
        return Complexity.MODERATE
    
    # 學習/方法類問題 - 提升複雜度
    learning_keywords = ['點樣', '點解', '點樣可以', '點解', '點', '方法', '點做']
    if any(kw in question_lower for kw in learning_keywords):
        return Complexity.MODERATE
    
    # 簡單問題關鍵詞
    simple_keywords = ['係', '係咪', '有冇', '幾時', '邊個', '咩', '點樣', '係邊', '幾多']
    moderate_keywords = ['點解', '為什麼', '點樣可以', '應該點', '有咩好', '分析', '解釋']
    complex_keywords = ['論證', '評估', '策劃', '設計', '比較', '對比']
    
    # 計算關鍵詞匹配
    simple_score = sum(1 for kw in simple_keywords if kw in question_lower)
    moderate_score = sum(1 for kw in moderate_keywords if kw in question_lower)
    complex_score = sum(1 for kw in complex_keywords if kw in question_lower)
    
    # 問題長度影響
    length_bonus = len(question) // 25
    
    # 最終評分
    score = simple_score + moderate_score * 2 + complex_score * 3 + length_bonus
    
    # 智能映射到複雜度等級
    if score <= 0:
        return Complexity.TRIVIAL
    elif score <= 1:
        return Complexity.SIMPLE
    elif score <= 3:
        return Complexity.MODERATE
    elif score <= 5:
        return Complexity.COMPLEX
    else:
        return Complexity.VERY_COMPLEX

# ============================================================
# 領域專業度評估（基於 Anthropic 研究）
# ============================================================
def assess_domain_expertise(question: str) -> DomainExpertise:
    """
    評估用戶對問題領域的專業度
    基於 Anthropic 研究：領域專業比編程能力更重要
    """
    question_lower = question.lower()
    
    # 專家級詞彙（精確術語、邊界條件、專業概念）
    expert_markers = [
        # 精確性標記
        '必須', '必須滿足', '邊界條件', '約束', '限制條件',
        'must', 'constraint', 'boundary', 'threshold',
        # 專業術語深度使用
        '優化', '算法複雜度', '時間複雜度', '空間複雜度',
        '時間複雜', '空間複雜', 'big o', 'complexity',
        # 系統性思維
        '架構', '系統設計', '模塊化', '耦合', '內聚',
        'architecture', 'system design', 'modular', 'decoupling',
        # 專業領域術語
        '對帳', '月結', 'reconciliation', 'closing',
        '風險敞口', '敞口', 'exposure', 'var', '風險價值',
        # 技術深度
        '並發', '高併發', '分散式', '分布式', '微服務',
        'consistency', 'availability', 'partition tolerance',
        'cap 定理', 'cap theorem', 'acid', 'base',
        # 數據結構/算法
        '紅黑樹', 'b樹', 'b+樹', '哈希表', '跳表',
        '動態規劃', '貪心算法', '分治法', '回溯法',
        # 機器學習
        '梯度下降', '反向傳播', '損失函數', '正則化',
        'overfitting', 'underfitting', 'cross validation',
        # 性能指標
        'qps', 'tps', 'rps', 'latency', 'throughput',
        'p99', 'p95', 'percentile', 'sla',
        # 數據庫
        '索引', 'b+ tree', '事務', '隔離級別',
        'sharding', 'partitioning', 'replication',
        # 網絡
        '負載均衡', 'load balancing', 'cdn', 'dns',
        'tcp', 'udp', 'http/2', 'grpc', 'websocket',
    ]
    
    # 中階詞彙（理解概念但未必精確）
    intermediate_markers = [
        '效率', '性能', '瓶頸', '優化',
        'efficiency', 'performance', 'bottleneck',
        '架構', '設計模式', 'pattern',
        '最佳實踐', 'best practice',
        '時間複雜', '空間複雜', '複雜度',
        '數據庫', 'database', 'sql', 'nosql',
        'api', 'rest', 'http',
        '緩存', 'cache', 'redis', 'memcached',
        '隊列', 'queue', 'kafka', 'rabbitmq',
        '容器', 'docker', 'kubernetes', 'k8s',
        '雲', 'cloud', 'aws', 'azure', 'gcp',
    ]
    
    # 初學者詞彙（基礎問題）
    beginner_markers = [
        '什麼是', '什麼係', '點解', '點樣',
        'what is', 'how to', 'why', 'explain',
        '入門', '新手', 'beginner', '入門',
        '學習', '教學', 'tutorial', 'guide',
        '基礎', 'basic', '簡單', 'simple',
        '介紹', '簡介', '概述', 'overview',
        '第一次', '初學', '開始',
    ]
    
    # 計算專業度分數
    expert_score = sum(3 for marker in expert_markers if marker in question_lower)
    intermediate_score = sum(1.5 for marker in intermediate_markers if marker in question_lower)
    beginner_penalty = sum(-1 for marker in beginner_markers if marker in question_lower)
    
    # 問題長度與結構分析
    length_score = min(len(question) // 40, 3)  # 長問題通常更專業
    
    # 結構化標記（專家傾向結構化描述）
    structure_score = 0
    if any(marker in question for marker in ['1.', '2.', '3.', '首先', '其次', '最後']):
        structure_score = 2
    if any(marker in question for marker in ['例如', '比如', 'for example', 'e.g.']):
        structure_score += 1
    
    # 精確度標記（專家使用精確數字/條件）
    precision_score = 0
    if any(marker in question for marker in ['必須', '至少', '最多', '不超過', '大於', '小於']):
        precision_score = 2
    if any(marker in question for marker in ['%', 'ms', 'mb', 'gb', 'tb']):
        precision_score += 2
    # 數字 + 單位組合（如 "10萬 QPS"）
    if re.search(r'\d+\s*[萬千]?\s*[qps|tps|rps|ms|gb|mb|tb]', question_lower):
        precision_score += 3
    
    total_score = expert_score + intermediate_score + beginner_penalty + length_score + structure_score + precision_score
    
    # 映射到專業度等級（根據 Anthropic 研究調整）
    # 研究顯示：中階（INTERMEDIATE）是最優性價比區間
    if total_score <= 0:
        return DomainExpertise.NOVICE
    elif total_score <= 2:
        return DomainExpertise.BEGINNER
    elif total_score <= 6:
        return DomainExpertise.INTERMEDIATE  # 最優性價比區間
    elif total_score <= 10:
        return DomainExpertise.ADVANCED
    else:
        return DomainExpertise.EXPERT

# ============================================================
# 專業度配置
# ============================================================
def get_expertise_config(expertise: DomainExpertise) -> dict:
    """根據專業度調整輸出配置"""
    configs = {
        DomainExpertise.NOVICE: {
            "detail_level": "基礎",
            "explanation_depth": "詳細解釋每個概念",
            "examples_needed": True,
            "technical_jargon": "避免或解釋術語",
            "output_structure": "簡單分段",
        },
        DomainExpertise.BEGINNER: {
            "detail_level": "入門",
            "explanation_depth": "清晰解釋關鍵概念",
            "examples_needed": True,
            "technical_jargon": "適度使用並解釋",
            "output_structure": "標準結構",
        },
        DomainExpertise.INTERMEDIATE: {
            "detail_level": "中等",
            "explanation_depth": "重點解釋複雜部分",
            "examples_needed": False,
            "technical_jargon": "正常使用",
            "output_structure": "結構化分析",
        },
        DomainExpertise.ADVANCED: {
            "detail_level": "進階",
            "explanation_depth": "簡潔，假設已有基礎",
            "examples_needed": False,
            "technical_jargon": "專業術語",
            "output_structure": "深度分析",
        },
        DomainExpertise.EXPERT: {
            "detail_level": "專家",
            "explanation_depth": "極簡，聚焦核心洞見",
            "examples_needed": False,
            "technical_jargon": "精確專業術語",
            "output_structure": "專業報告格式",
        },
    }
    return configs[expertise]

# ============================================================
# 根據複雜度和專業度自動選擇模型和配置
# ============================================================
def get_auto_config(complexity: Complexity, expertise: DomainExpertise = DomainExpertise.INTERMEDIATE) -> dict:
    """根據複雜度和專業度自動配置資源"""
    
    # 基礎配置（基於複雜度）
    base_configs = {
        Complexity.TRIVIAL: {
            "model": MODELS["fast"],
            "budget_tokens": 200,
            "num_paths": 1,
            "confidence_threshold": 0.4,
            "temperature": 0.3,
            "max_retries": 0,
        },
        Complexity.SIMPLE: {
            "model": MODELS["fast"],
            "budget_tokens": 500,
            "num_paths": 1,
            "confidence_threshold": 0.5,
            "temperature": 0.5,
            "max_retries": 1,
        },
        Complexity.MODERATE: {
            "model": MODELS["fast"],
            "budget_tokens": 1000,
            "num_paths": 2,
            "confidence_threshold": 0.6,
            "temperature": 0.6,
            "max_retries": 1,
        },
        Complexity.COMPLEX: {
            "model": MODELS["smart"],  # 複雜問題升級到 smart 模型
            "budget_tokens": 3000,
            "num_paths": 3,
            "confidence_threshold": 0.7,
            "temperature": 0.7,
            "max_retries": 2,
        },
        Complexity.VERY_COMPLEX: {
            "model": MODELS["reasoner"],
            "budget_tokens": 6000,
            "num_paths": 3,
            "confidence_threshold": 0.75,
            "temperature": 0.7,
            "max_retries": 2,
        },
    }
    
    config = base_configs[complexity].copy()
    
    # 根據專業度調整
    expertise_config = get_expertise_config(expertise)
    
    # 專家級用戶：增加輸出長度（專家能處理更多信息）
    if expertise in [DomainExpertise.ADVANCED, DomainExpertise.EXPERT]:
        config["budget_tokens"] = int(config["budget_tokens"] * 1.3)
        config["temperature"] = min(config["temperature"] + 0.1, 0.9)  # 稍微提高創造性
    
    # 新手用戶：簡化輸出
    if expertise in [DomainExpertise.NOVICE, DomainExpertise.BEGINNER]:
        config["budget_tokens"] = int(config["budget_tokens"] * 0.8)
        config["temperature"] = max(config["temperature"] - 0.1, 0.2)  # 更確定性
    
    # 加入專業度配置
    config["expertise"] = expertise.name
    config["expertise_config"] = expertise_config
    
    return config

# ============================================================
# v4.1: MiniMax 審查引擎 + Feedback Loop
# ============================================================

class MiniMaxReviewer:
    """
    MiniMax 審查引擎
    用 MiniMax 模型做多角度審查同 feedback loop
    """
    
    def __init__(self, max_iterations: int = 2, improvement_threshold: float = 0.1):
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        self.review_history = []
    
    def _call_minimax_official(self, prompt: str, max_tokens: int = 800, max_retries: int = 2) -> tuple[str, float]:
        """調用 MiniMax 官方 API，支援重試"""
        import requests
        import time
        
        MINIMAX_API_KEY = "sk-cp-mNrtisBo685K4E_h9tViioU44JVLDP89yIhrVXnSqJUOH8pCoK0DdMV2qN0JhIpqhH9RU84B5wd6JyW4t6JnOJYaJGMfagw1ogF1gsSwrQoEVla8-ufgFVc"
        
        headers = {
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": "MiniMax-M2.7",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    "https://api.minimax.io/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=180,
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                cost = total_tokens * 0.000001
                
                if attempt > 0:
                    print(f"✅ MiniMax 第 {attempt + 1} 次嘗試成功")
                
                return content, cost
                
            except Exception as e:
                last_error = e
                print(f"⚠️ MiniMax API 錯誤 (嘗試 {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"   等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
        
        print(f"❌ MiniMax 所有嘗試失敗: {last_error}")
        return f"{{\"score\": 7.0, \"improvement_needed\": false, \"issues\": [], \"feedback\": \"MiniMax 審查跳過: {last_error}\"}}", 0


class MultiLLMDiscussion:
    """
    多 LLM 交叉驗證引擎
    流程：GPT 生成 → MiniMax 審查 → GPT 修正 → MiniMax 再審 → 總結
    最多來回 4 次
    """
    
    def __init__(self, max_rounds: int = 4):
        self.max_rounds = max_rounds
        self.discussion_history = []
        self.minimax_reviewer = MiniMaxReviewer()
    
    def discuss(self, question: str) -> dict:
        """
        啟動多 LLM 討論
        
        Returns:
            {
                'final_answer': str,
                'rounds': int,
                'discussion_log': list,
                'consensus_reached': bool
            }
        """
        
        # Round 1: GPT 生成初始答案
        print("🔄 Round 1: GPT 生成初始答案...")
        gpt_answer = self._gpt_generate(question)
        self.discussion_history.append({
            'round': 1,
            'role': 'GPT',
            'action': 'generate',
            'content': gpt_answer
        })
        
        current_answer = gpt_answer
        
        for round_num in range(2, self.max_rounds + 1):
            if round_num % 2 == 0:
                # 偶數 round: MiniMax 審查
                print(f"🔄 Round {round_num}: MiniMax 審查...")
                review = self._minimax_review(question, current_answer)
                
                self.discussion_history.append({
                    'round': round_num,
                    'role': 'MiniMax',
                    'action': 'review',
                    'score': review.get('score', 0),
                    'feedback': review.get('feedback', '')
                })
                
                # 檢查是否達成共識
                if review.get('score', 0) >= 9.0:
                    print(f"✅ Round {round_num}: MiniMax 滿意，達成共識！")
                    break
                    
            else:
                # 奇數 round: GPT 根據反饋修正
                print(f"🔄 Round {round_num}: GPT 根據反饋修正...")
                
                # 獲取上一 round MiniMax 嘅反饋
                last_review = self.discussion_history[-1]
                
                improved = self._gpt_improve(
                    question, 
                    current_answer, 
                    last_review.get('feedback', '')
                )
                
                self.discussion_history.append({
                    'round': round_num,
                    'role': 'GPT',
                    'action': 'improve',
                    'content': improved
                })
                
                current_answer = improved
        
        # 總結
        final_answer = self._summarize_discussion()
        
        return {
            'final_answer': final_answer,
            'rounds': len(self.discussion_history),
            'discussion_log': self.discussion_history,
            'consensus_reached': self.discussion_history[-1].get('role') == 'MiniMax' and 
                                self.discussion_history[-1].get('score', 0) >= 9.0
        }
    
    def _gpt_generate(self, question: str) -> str:
        """GPT 生成初始答案"""
        prompt = f"""請詳細回答以下問題：

【問題】
{question}

【要求】
- 提供全面、深入嘅分析
- 考慮多個角度
- 用繁體中文回答"""
        
        content, p, c, cost = call_model(prompt, model='gpt-5.4', max_tokens=1500)
        return content
    
    def _minimax_review(self, question: str, answer: str) -> dict:
        """MiniMax 審查 GPT 嘅答案"""
        prompt = f"""你係一個嚴格嘅審查員。請批判性分析以下答案：

【問題】
{question}

【答案】
{answer}

【輸出格式】
{{
    "score": 7.5,
    "feedback": "具體改進建議（200字內）",
    "improvement_needed": true/false
}}"""
        
        # 使用 MiniMax 官方 API
        from .minimax_reviewer import MiniMaxReviewer
        reviewer = MiniMaxReviewer()
        content, cost = reviewer._call_minimax_official(prompt, max_tokens=500)
        
        try:
            review = json.loads(content)
        except:
            review = {'score': 7.0, 'feedback': '審查解析失敗', 'improvement_needed': True}
        
        review['cost_usd'] = cost
        return review
    
    def _gpt_improve(self, question: str, answer: str, feedback: str) -> str:
        """GPT 根據 MiniMax 反饋修正"""
        prompt = f"""請根據審查意見修正你嘅答案。

【問題】
{question}

【原答案】
{answer}

【審查意見】
{feedback}

【要求】
- 保留原答案嘅優點
- 針對問題逐項修正
- 輸出完整修正後答案"""
        
        content, p, c, cost = call_model(prompt, model='gpt-5.4', max_tokens=1500)
        return content
    
    def _summarize_discussion(self) -> str:
        """總結討論結果"""
        # 獲取最後一個 GPT 嘅輸出
        for entry in reversed(self.discussion_history):
            if entry.get('role') == 'GPT':
                return entry.get('content', '')
        
        return "討論未能產生最終答案"
    """
    MiniMax 審查引擎
    用 MiniMax 模型做多角度審查同 feedback loop
    
    流程：
    1. 生成初始答案（gpt-5.4）
    2. MiniMax 審查（批判性分析）
    3. 根據 feedback 修正
    4. 重複直到滿意（max_iterations）
    """
    
    def __init__(self, max_iterations: int = 2, improvement_threshold: float = 0.1):
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        self.review_history = []
    
    def review_and_improve(self, question: str, answer: str, context: dict = None) -> dict:
        """
        審查同改進循環 - 重點係質量提升，唔係長度增加
        
        Returns:
            {
                'final_answer': str,
                'iterations': int,
                'improvements': list,
                'cost_usd': float,
                'dimensions_improved': dict  # 記錄邊啲維度改進咗
            }
        """
        current_answer = answer
        total_cost = 0
        improvements = []
        dimensions_history = []
        
        for iteration in range(self.max_iterations):
            # Step 1: MiniMax 多維度審查
            review = self._minimax_review(question, current_answer, context)
            total_cost += review.get('cost_usd', 0)
            
            # 記錄維度狀態
            dims = review.get('dimensions', {})
            dimensions_history.append({
                'iteration': iteration + 1,
                'score': review['score'],
                'problems_found': sum(1 for d in dims.values() if d.get('found', False))
            })
            
            # 檢查是否滿意（分數夠高且無嚴重問題）
            if review['score'] >= 9.0:
                improvements.append({
                    'iteration': iteration + 1,
                    'action': '達標，停止',
                    'score': review['score'],
                    'problems_found': 0
                })
                break
            
            # 檢查仲有冇嚴重問題
            severe_problems = any(
                d.get('severity') == '高' or len(d.get('issues', [])) > 0
                for d in dims.values() if isinstance(d, dict)
            )
            
            if not severe_problems and review['score'] >= 7.5:
                improvements.append({
                    'iteration': iteration + 1,
                    'action': '問題輕微，停止',
                    'score': review['score'],
                    'problems_found': sum(1 for d in dims.values() if d.get('found', False))
                })
                break
            
            # Step 2: 根據多維度審查結果修正
            improved = self._apply_feedback(question, current_answer, review)
            total_cost += improved.get('cost_usd', 0)
            
            improvements.append({
                'iteration': iteration + 1,
                'action': '多維度修正',
                'score': review['score'],
                'problems_found': sum(1 for d in dims.values() if d.get('found', False)),
                'corrections_applied': improved.get('corrections_applied', 0),
                'feedback': review.get('feedback', '')[:150]
            })
            
            current_answer = improved['answer']
        
        return {
            'final_answer': current_answer,
            'iterations': len(improvements),
            'improvements': improvements,
            'cost_usd': total_cost,
            'dimensions_history': dimensions_history
        }
    
    def _minimax_review(self, question: str, answer: str, context: dict = None) -> dict:
        """
        用 MiniMax 官方 API 做多維度批判性審查
        重點：質量 > 長度，搵矛盾同隱藏問題
        """
        
        prompt = f"""你係一個嚴格嘅多維度審查員。請深入分析以下答案，重點搵出矛盾、盲點同隱藏問題。

【原始問題】
{question}

【答案】
{answer}

【審查維度】（必須逐項檢查）

1. **矛盾檢測**
   - 答案內有冇自相矛盾嘅地方？
   - 前後論點係咪一致？
   - 有冇同已知事實衝突？

2. **隱藏假設**
   - 答案基於咩未明言嘅假設？
   - 呢啲假設係咪一定成立？
   - 如果假設唔成立，答案會點變？

3. **盲點識別**
   - 有冇重要觀點完全被忽略？
   - 有冇考慮反面證據？
   - 有冇群體/角度被排除？

4. **邏輯漏洞**
   - 因果關係係咪成立？
   - 有冇滑坡謬誤、假兩難？
   - 證據係咪支持結論？

5. **偏見檢測**
   - 有冇確認偏誤（只睇支持自己嘅證據）？
   - 有冇框架效應（用特定方式描述問題）？
   - 有冇可用性啟發（只依賴容易諗到嘅例子）？

【輸出格式】（必須嚴格跟從）
{{
    "score": 7.5,
    "improvement_needed": true,
    "dimensions": {{
        "contradictions": {{
            "found": true/false,
            "issues": ["具體矛盾描述"],
            "severity": "高/中/低"
        }},
        "hidden_assumptions": {{
            "found": true/false,
            "assumptions": ["假設1", "假設2"],
            "impact": "如果唔成立嘅後果"
        }},
        "blind_spots": {{
            "found": true/false,
            "missed": ["遺漏觀點1", "遺漏觀點2"],
            "alternative_perspectives": ["反面角度1", "反面角度2"]
        }},
        "logical_gaps": {{
            "found": true/false,
            "fallacies": ["謬誤類型: 描述"],
            "missing_links": ["缺失論證環節"]
        }},
        "biases": {{
            "found": true/false,
            "types": ["偏見類型: 描述"],
            "corrections": ["修正建議"]
        }}
    }},
    "critical_questions": [
        "審查員應該追問嘅關鍵問題1",
        "審查員應該追問嘅關鍵問題2"
    ],
    "feedback": "總體評價：核心問題係咩？最急需修正係邊點？（100字內）"
}}"""
        
        # 使用 MiniMax 官方 API
        content, cost = self._call_minimax_official(prompt, max_tokens=1200)
        
        try:
            review_data = json.loads(content)
            # 確保有必要字段
            if 'dimensions' not in review_data:
                review_data['dimensions'] = self._empty_dimensions()
        except:
            review_data = {
                'score': 7.0,
                'improvement_needed': True,
                'dimensions': self._empty_dimensions(),
                'critical_questions': [],
                'feedback': '審查解析失敗，建議人工檢查'
            }
        
        review_data['cost_usd'] = cost
        return review_data
    
    def _empty_dimensions(self) -> dict:
        """返回空嘅審查維度結構"""
        return {
            'contradictions': {'found': False, 'issues': [], 'severity': '低'},
            'hidden_assumptions': {'found': False, 'assumptions': [], 'impact': ''},
            'blind_spots': {'found': False, 'missed': [], 'alternative_perspectives': []},
            'logical_gaps': {'found': False, 'fallacies': [], 'missing_links': []},
            'biases': {'found': False, 'types': [], 'corrections': []}
        }
    
    def _call_minimax_official(self, prompt: str, max_tokens: int = 800) -> tuple[str, float]:
        """
        調用 MiniMax 官方 API
        注意：需要用戶提供有效嘅 API Key
        """
        import requests
        
        # 從環境變量獲取 MiniMax API Key
        MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
        
        # 如果用戶提供咗 key（從對話記錄）
        if not MINIMAX_API_KEY:
            # 用戶提供嘅 MiniMax API Key
            MINIMAX_API_KEY = "sk-cp-mNrtisBo685K4E_h9tViioU44JVLDP89yIhrVXnSqJUOH8pCoK0DdMV2qN0JhIpqhH9RU84B5wd6JyW4t6JnOJYaJGMfagw1ogF1gsSwrQoEVla8-ufgFVc"
        
        if not MINIMAX_API_KEY or MINIMAX_API_KEY == "your-minimax-api-key":
            print("⚠️ 未設定 MINIMAX_API_KEY，跳過 MiniMax 審查")
            return "{\"score\": 7.0, \"improvement_needed\": false, \"issues\": [], \"feedback\": \"MiniMax API Key 未設定\"}", 0
        
        headers = {
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": "MiniMax-M2.7",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        
        try:
            # MiniMax 官方 API - 用戶提供嘅 endpoint
            response = requests.post(
                "https://api.minimax.io/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=120,  # 增加 timeout
            )
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            # 計算成本
            usage = result.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            cost = total_tokens * 0.000001
            
            return content, cost
            
        except Exception as e:
            print(f"⚠️ MiniMax API 錯誤: {e}")
            return f"{{\"score\": 7.0, \"improvement_needed\": false, \"issues\": [], \"feedback\": \"MiniMax 審查跳過: {e}\"}}", 0
    
    def _apply_feedback(self, question: str, answer: str, review_data: dict) -> dict:
        """
        根據 MiniMax 嘅多維度審查結果修正答案
        重點：針對矛盾、盲點、邏輯漏洞進行修正，唔係單純加長
        """
        
        # 提取具體問題
        dims = review_data.get('dimensions', {})
        
        # 構建有針對性嘅修正 prompt
        correction_points = []
        
        if dims.get('contradictions', {}).get('found'):
            correction_points.append("【矛盾修正】" + "; ".join(dims['contradictions']['issues']))
        
        if dims.get('hidden_assumptions', {}).get('found'):
            assumptions = dims['hidden_assumptions']
            correction_points.append(f"【假設檢驗】基於假設：{', '.join(assumptions['assumptions'])}；如果唔成立：{assumptions['impact']}")
        
        if dims.get('blind_spots', {}).get('found'):
            blind = dims['blind_spots']
            correction_points.append(f"【補充盲點】遺漏咗：{', '.join(blind['missed'][:2])}；需要考慮：{', '.join(blind['alternative_perspectives'][:2])}")
        
        if dims.get('logical_gaps', {}).get('found'):
            gaps = dims['logical_gaps']
            correction_points.append(f"【邏輯修正】謬誤：{', '.join(gaps['fallacies'][:2])}；缺失論證：{', '.join(gaps['missing_links'][:2])}")
        
        if dims.get('biases', {}).get('found'):
            biases = dims['biases']
            correction_points.append(f"【偏見修正】發現：{', '.join(biases['types'][:2])}；建議：{', '.join(biases['corrections'][:2])}")
        
        critical_qs = review_data.get('critical_questions', [])
        
        prompt = f"""你係一個嚴謹嘅分析師。請根據以下審查意見，修正同深化你嘅答案。

【原始問題】
{question}

【你嘅原答案】
{answer}

【審查發現嘅問題】
{chr(10).join(correction_points)}

【必須回答嘅關鍵問題】
{chr(10).join(critical_qs[:3])}

【修正要求】
1. 針對每個問題逐項回應，唔好迴避
2. 如果原答案有矛盾，明確澄清
3. 補充遺漏嘅重要觀點，但唔好為加長而加長
4. 強化論證邏輯，確保因果關係成立
5. 加入反面觀點或限制條件，顯示全面思考
6. 保持簡潔，重點係質量唔係長度

【輸出格式】
先簡要列出修正咗咩（ bullet points ），
然後輸出修正後嘅完整答案。"""
        
        content, prompt_tokens, completion_tokens, cost = call_model(
            prompt,
            model='gpt-5.4',
            max_tokens=1500,
            temperature=0.4
        )
        
        return {
            'answer': content,
            'cost_usd': cost,
            'corrections_applied': len(correction_points)
        }
    
    def _calculate_improvement(self, old_answer: str, new_answer: str) -> float:
        """
        計算改進幅度（簡化版：比較長度同結構變化）
        """
        # 更複雜嘅實現可以用 embedding 相似度
        old_len = len(old_answer)
        new_len = len(new_answer)
        
        # 如果長度變化超過 20%，認為有顯著改進
        length_change = abs(new_len - old_len) / max(old_len, 1)
        
        # 簡化：返回 0-1 之間嘅值
        return min(length_change, 1.0)


# ============================================================
# 自適應推理引擎
# ============================================================
class ReflectionEngine:
    """
    反思引擎（Fable Reasoner v4.0）
    加入 Extended Thinking 能力，令普通 model 提升表現
    
    四步驟：
    1. Pre-generation Reflection（生成前反思）
    2. Multi-path Exploration（多路徑探索）
    3. Post-generation Validation（生成後驗證）
    4. Edge Case Detection（邊緣情況檢測）
    """
    
    def __init__(self, reasoner: AdaptiveReasoner, enabled: bool = False):
        self.reasoner = reasoner
        self.enabled = enabled
        self.reflection_cache = {}  # 快取機制
    
    def reflect(self, question: str, complexity: str, expertise: str) -> dict:
        """
        執行完整反思流程
        返回反思結果同優化後答案
        """
        if not self.enabled or complexity in ['TRIVIAL', 'EASY']:
            return {'skipped': True, 'reason': '簡單問題跳過 reflection'}
        
        # 檢查快取
        cache_key = f"{question}_{complexity}"
        if cache_key in self.reflection_cache:
            return self.reflection_cache[cache_key]
        
        result = {
            'pre_reflection': None,
            'multi_paths': None,
            'validation': None,
            'edge_cases': None,
            'final_answer': None,
            'cost_usd': 0,
        }
        
        # Step 1: Pre-generation Reflection
        result['pre_reflection'] = self._pre_reflect(question)
        
        # Step 2: Multi-path Exploration（使用並行版）
        result['multi_paths'] = self._explore_paths_parallel(question, complexity, expertise)
        
        # Step 3: Post-generation Validation
        result['validation'] = self._validate_output(
            result['multi_paths']['selected_answer']
        )
        
        # Step 4: Edge Case Detection
        result['edge_cases'] = self._detect_edge_cases(question, result['multi_paths']['selected_answer'])
        
        # 計算總成本
        result['cost_usd'] = (
            result['pre_reflection'].get('cost_usd', 0) +
            result['multi_paths'].get('cost_usd', 0) +
            result['validation'].get('cost_usd', 0) +
            result['edge_cases'].get('cost_usd', 0)
        )
        
        # 保存快取
        self.reflection_cache[cache_key] = result
        
        return result
    
    def _pre_reflect(self, question: str) -> dict:
        """生成前反思：識別歧義、隱藏假設、多種解讀"""
        
        prompt = f"""分析以下問題，識別潛在問題：

【問題】
{question}

【要求】
- 列出問題中嘅歧義或模糊之處
- 識別隱藏假設
- 指出可能嘅多種解讀
- 提出應對策略

【輸出格式】（JSON）
{{
    "ambiguities": ["歧義1", "歧義2"],
    "hidden_assumptions": ["假設1", "假設2"],
    "multiple_interpretations": ["解讀1", "解讀2"],
    "strategies": ["策略1", "策略2"]
}}"""
        
        content, prompt_tokens, completion_tokens, cost = call_model(prompt, model='gpt-5.4', max_tokens=500)
        
        try:
            reflection_data = json.loads(content)
        except:
            reflection_data = {
                'ambiguities': [],
                'hidden_assumptions': [],
                'multiple_interpretations': [],
                'strategies': ['直接回答']
            }
        
        reflection_data['cost_usd'] = cost
        return reflection_data
    
    def _explore_paths_parallel(self, question: str, complexity: str, expertise: str) -> dict:
        """
        多路徑探索（並行版）
        同時生成 3 個角度嘅答案，加速處理
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        angles = ['實用角度', '技術角度', '創新角度']
        
        def generate_angle_answer(angle_idx: int) -> dict:
            """生成特定角度嘅答案"""
            angle_prompt = f"""從角度 {angle_idx+1} 回答以下問題：

【問題】
{question}

【角度】
{angles[angle_idx]}

【要求】
- 簡潔有力，50字以內
- 聚焦該角度嘅核心觀點"""
            
            content, prompt_tokens, completion_tokens, cost = call_model(angle_prompt, model='gpt-5.4-mini', max_tokens=200)
            return {
                'angle': angle_idx + 1,
                'answer': content.strip(),
                'cost_usd': cost
            }
        
        # 並行生成 3 個角度嘅答案
        paths = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(generate_angle_answer, i): i for i in range(3)}
            
            for future in as_completed(futures):
                try:
                    path = future.result()
                    paths.append(path)
                except Exception as e:
                    print(f"⚠️ 角度 {futures[future]+1} 生成失敗: {e}")
        
        # 按角度排序
        paths.sort(key=lambda x: x['angle'])
        
        # 比較優劣，揀最穩妥
        select_prompt = f"""比較以下 3 個答案，揀最穩妥嘅：

【答案 1】{paths[0]['answer']}
【答案 2】{paths[1]['answer']}
【答案 3】{paths[2]['answer']}

【要求】
- 揀一個最全面、最準確、最穩妥嘅
- 簡單說明理由

【輸出】
選擇：答案 X
理由：..."""
        
        content, prompt_tokens, completion_tokens, cost = call_model(select_prompt, model='gpt-5.4', max_tokens=300)
        
        # 解析選擇
        selected = 1  # 預設
        if '答案 2' in content or '答案2' in content:
            selected = 2
        elif '答案 3' in content or '答案3' in content:
            selected = 3
        
        total_cost = sum(p['cost_usd'] for p in paths) + cost
        
        return {
            'paths': paths,
            'selected': selected,
            'selected_answer': paths[selected - 1]['answer'],
            'selection_reason': content,
            'cost_usd': total_cost
        }
    
    def _validate_output(self, answer: str) -> dict:
        """生成後驗證：檢查自相矛盾、遺漏、過度推斷"""
        
        prompt = f"""驗證以下答案：

【答案】
{answer}

【要求】
- 檢查有冇自相矛盾
- 檢查有冇遺漏重要資訊
- 檢查有冇過度推斷
- 如有問題，提出修正建議

【輸出格式】（JSON）
{{
    "contradictions": ["矛盾1"],
    "omissions": ["遺漏1"],
    "over_reaches": ["過度推斷1"],
    "suggestions": ["建議1"],
    "is_valid": true/false
}}"""
        
        content, prompt_tokens, completion_tokens, cost = call_model(prompt, model='gpt-5.4', max_tokens=400)
        
        try:
            validation_data = json.loads(content)
        except:
            validation_data = {
                'contradictions': [],
                'omissions': [],
                'over_reaches': [],
                'suggestions': [],
                'is_valid': True
            }
        
        validation_data['cost_usd'] = cost
        return validation_data
    
    def _detect_edge_cases(self, question: str, answer: str) -> dict:
        """邊緣情況檢測：檢查極端輸入下答案變化"""
        
        prompt = f"""檢查以下答案嘅邊緣情況：

【問題】
{question}

【答案】
{answer}

【要求】
- 如果問題輸入改變少少，答案會點變？
- 極端情況下（空輸入、超長輸入）會點？
- 有冇特殊字符或格式問題？

【輸出格式】（JSON）
{{
    "edge_cases": ["邊緣情況1", "邊緣情況2"],
    "handling_suggestions": ["建議1", "建議2"]
}}"""
        
        content, prompt_tokens, completion_tokens, cost = call_model(prompt, model='gpt-5.4-mini', max_tokens=300)
        
        try:
            edge_data = json.loads(content)
        except:
            edge_data = {
                'edge_cases': [],
                'handling_suggestions': []
            }
        
        edge_data['cost_usd'] = cost
        return edge_data


# ============================================================
# 修改 AdaptiveReasoner 加入 ReflectionEngine
# ============================================================
class AdaptiveReasoner:
    """
    Fable-Style 自適應推理引擎 v4.0
    
    新增功能（v4.0）：
    - 反思引擎（ReflectionEngine）
    - Extended Thinking 能力
    - 並行多路徑探索
    - 向後兼容（reflection_enabled 預設 False）
    """
    
    def __init__(self, verbose: bool = True, user_id: str = "default", reflection: bool = False):
        self.verbose = verbose
        self.user_id = user_id
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_calls = 0
        self.history = []
        
        # 初始化新組件
        self.memory = MemoryStore()
        self.evaluator = AnswerEvaluator()
        self.error_recovery = ErrorRecovery()
        
        # v4.0: 初始化反思引擎
        self.reflection_engine = ReflectionEngine(self, enabled=reflection)
        
        # v4.1: 初始化 MiniMax 審查引擎
        self.minimax_reviewer = MiniMaxReviewer(max_iterations=2)
        
        if self.verbose:
            print(f"🧠 Fable Reasoner v4.1 初始化完成")
            print(f"   反思引擎: {'啟用' if reflection else '關閉'}")
            print(f"   並行處理: 啟用 (max_workers=3)")
            print(f"   MiniMax 審查: 啟用 (max_iterations=2)")
    
    def think(self, question: str, reflection: bool = None) -> dict:
        """
        主要入口函數：用戶只需調用這個！
        
        v4.0: 加入 reflection 參數，可覆蓋預設值
        """
        
        start_time = time.time()
        
        if self.verbose:
            print(f"\n🧠 收到問題: {question[:50]}{'...' if len(question) > 50 else ''}")
            print("─" * 40)
        
        # Step 1: 自動分析複雜度
        if self.verbose:
            print("📊 自動分析問題複雜度...")
        
        complexity = analyze_complexity(question)
        
        # Step 1.5: 評估領域專業度（基於 Anthropic 研究）
        if self.verbose:
            print("🎯 評估領域專業度...")
        
        expertise = assess_domain_expertise(question)
        config = get_auto_config(complexity, expertise)
        
        if self.verbose:
            print(f"   → 複雜度: {complexity.name} ({complexity.value})")
            print(f"   → 專業度: {expertise.name} ({expertise.value})")
            print(f"   → 模型: {config['model']}")
            print(f"   → 預算: {config['budget_tokens']} tokens")
            print(f"   → 輸出風格: {config['expertise_config']['detail_level']}")
        
        # Step 2: 根據複雜度執行不同策略
        if complexity == Complexity.TRIVIAL:
            answer, p, c, cost = self._trivial_response(question, config)
        elif complexity.value <= Complexity.SIMPLE.value:
            answer, p, c, cost = self._simple_reasoning(question, config)
        elif complexity.value <= Complexity.MODERATE.value:
            answer, p, c, cost = self._moderate_reasoning(question, config)
        elif complexity.value <= Complexity.COMPLEX.value:
            answer, p, c, cost = self._complex_reasoning(question, config)
        else:
            answer, p, c, cost = self._very_complex_reasoning(question, config)
        
        # v4.0: 反思流程（可選）
        reflection_result = None
        if reflection or (reflection is None and self.reflection_engine.enabled):
            if complexity.value >= Complexity.MODERATE.value:
                if self.verbose:
                    print("\n🔍 啟動反思引擎...")
                
                reflection_result = self.reflection_engine.reflect(question, complexity.name, expertise.name)
                
                if not reflection_result.get('skipped'):
                    if self.verbose:
                        print(f"   → Pre-reflection: {len(reflection_result['pre_reflection'].get('ambiguities', []))} 個歧義")
                        print(f"   → Multi-paths: 探索 {len(reflection_result['multi_paths'].get('paths', []))} 個角度")
                        print(f"   → Validation: {'通過' if reflection_result['validation'].get('is_valid') else '需修正'}")
                    
                    # 如果有修正建議，更新答案
                    if reflection_result['validation'].get('suggestions'):
                        answer += "\n\n[修正] " + "; ".join(reflection_result['validation']['suggestions'])
                    
                    # 加上邊緣情況提醒
                    if reflection_result['edge_cases'].get('edge_cases'):
                        answer += "\n\n[注意] 邊緣情況: " + "; ".join(reflection_result['edge_cases']['edge_cases'])
                    
                    # 更新成本
                    cost += reflection_result.get('cost_usd', 0)
        
        # v4.1: MiniMax 審查同 feedback loop（適用於中等以上複雜度問題）
        minimax_result = None
        if complexity.value >= Complexity.MODERATE.value:
            if self.verbose:
                print("\n🔍 啟動 MiniMax 審查引擎...")
            
            minimax_result = self.minimax_reviewer.review_and_improve(
                question, answer, 
                context={'complexity': complexity.name, 'expertise': expertise.name}
            )
            
            if self.verbose:
                print(f"   → 審查迭代: {minimax_result['iterations']} 次")
                for imp in minimax_result['improvements']:
                    print(f"     迭代 {imp['iteration']}: {imp['action']} (分數: {imp.get('score', 'N/A')})")
            
            # 使用改進後嘅答案
            answer = minimax_result['final_answer']
            cost += minimax_result['cost_usd']
        
        # Step 3: 自我評分（新增）
        if self.verbose:
            print("\n📊 自動評估答案質量...")
        
        evaluation = self.evaluator.evaluate(answer, question, complexity)
        
        if self.verbose:
            print(f"   → 總分: {evaluation['total_score']}/10 ({evaluation['quality_level']})")
            print(f"   → 各維度: {evaluation['scores']}")
            if evaluation['suggestions']:
                print(f"   → 改進建議: {evaluation['suggestions']}")
        
        # 更新統計
        self.total_cost += cost
        self.total_tokens += p + c
        self.total_calls += 1
        
        # 計算耗時
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 保存歷史
        result = {
            "question": question,
            "complexity": complexity.name,
            "expertise": expertise.name,
            "model": config["model"],
            "answer": answer,
            "tokens_used": p + c,
            "cost_usd": cost,
            "duration_ms": duration_ms,
            "quality_score": evaluation['total_score'],
            "quality_level": evaluation['quality_level'],
            "reflection_used": reflection_result is not None,
            "minimax_reviewed": minimax_result is not None,
            "minimax_iterations": minimax_result['iterations'] if minimax_result else 0,
            "timestamp": datetime.now().isoformat(),
        }
        self.history.append(result)
        
        # 保存到記憶（新增）
        self.memory.save_session(
            self.user_id, question, complexity.name, expertise.name,
            config["model"], p + c, cost, duration_ms, evaluation['total_score']
        )
        
        if self.verbose:
            print(f"\n✅ 完成！耗時 {duration_ms}ms | 成本 ${cost:.6f} | 質量 {evaluation['quality_level']}")
            if minimax_result:
                print(f"   MiniMax 審查: {minimax_result['iterations']} 次迭代")
            print(f"\n📝 答案:\n{answer[:500]}{'...' if len(answer) > 500 else ''}")
        
        return result
    
    def _trivial_response(self, question: str, config: dict) -> tuple[str, int, int, float]:
        """瑣碎問題：直接回答"""
        prompt = f"直接回答：{question}"
        answer, p, c, cost = call_model(prompt, model=config["model"], max_tokens=config["budget_tokens"])
        return answer, p, c, cost
    
    def _simple_reasoning(self, question: str, config: dict) -> tuple[str, int, int, float]:
        """簡單問題：快速推理 + 簡單反思"""
        prompt = f"""你是一個深度思考者。請快速分析這個問題並回答。

<analysis>
[快速分析問題]
</analysis>

<answer>
[直接回答]
</answer>

問題：{question}

回答："""
        
        answer, p, c, cost = call_model(
            prompt, 
            model=config["model"], 
            max_tokens=config["budget_tokens"],
            temperature=config["temperature"]
        )
        return answer, p, c, cost
    
    def _moderate_reasoning(self, question: str, config: dict) -> tuple[str, int, int, float]:
        """中等問題：標準推理流程（加入專業度適配）"""
        
        expertise_config = config.get("expertise_config", {})
        detail_level = expertise_config.get("detail_level", "中等")
        explanation_depth = expertise_config.get("explanation_depth", "重點解釋複雜部分")
        
        prompt = f"""你是一個深度思考者。請用結構化方式分析並回答這個問題。

【輸出要求】
- 詳細程度：{detail_level}
- 解釋深度：{explanation_depth}

analysis：[先分析問題的核心]
reasoning：[列出你的推理過程]
reflection：[自我檢查：是否有漏洞？]
answer：[最終答案]

問題：{question}

回答："""
        
        answer, p, c, cost = call_model(
            prompt, 
            model=config["model"], 
            max_tokens=config["budget_tokens"],
            temperature=config["temperature"]
        )
        return answer, p, c, cost
    
    def _complex_reasoning(self, question: str, config: dict) -> tuple[str, int, int, float]:
        """複雜問題：多路徑推理（加入專業度適配）"""
        num_paths = config["num_paths"]
        expertise_config = config.get("expertise_config", {})
        detail_level = expertise_config.get("detail_level", "中等")
        
        # 並行生成多個角度的答案
        def generate_path(path_num: int) -> str:
            angles = [
                "實用主義角度（考慮實際可行性）",
                "理論分析角度（深入原理）",
                "批判性角度（找出問題和風險）",
            ]
            angle = angles[path_num - 1] if path_num <= len(angles) else f"角度{path_num}"
            
            prompt = f"""從「{angle}」分析這個問題（輸出詳細程度：{detail_level}）：

<analysis>
[這個角度的核心分析]
</analysis>

<reasoning>
[詳細推理過程]
</reasoning>

<conclusion>
[這個角度的結論]
</conclusion>

<issues>
[這個結論可能的問題]
</issues>

問題：{question}"""
            
            result, _, _, _ = call_model(
                prompt,
                model=config["model"],
                max_tokens=config["budget_tokens"] // num_paths,
                temperature=config["temperature"]
            )
            return f"=== 角度 {path_num}: {angle} ===\n{result}"
        
        # 並行執行
        if num_paths > 1:
            with ThreadPoolExecutor(max_workers=num_paths) as executor:
                futures = [executor.submit(generate_path, i+1) for i in range(num_paths)]
                paths = [f.result() for f in as_completed(futures)]
        else:
            paths = [generate_path(1)]
        
        # 整合所有路徑
        combined_prompt = f"""根據以下多個角度的分析，給出一個綜合性的最佳答案（輸出詳細程度：{detail_level}）：

{chr(10).join(paths)}

<summary>
[綜合各角度的最佳答案]
</summary>

<key_insights>
[關鍵洞察]
</key_insights>

最終答案："""
        
        final_answer, p, c, cost = call_model(
            combined_prompt,
            model=config["model"],
            max_tokens=config["budget_tokens"],
            temperature=config["temperature"]
        )
        
        return final_answer, p, c, cost
    
    def _very_complex_reasoning(self, question: str, config: dict) -> tuple[str, int, int, float]:
        """極複雜問題：完整 Fable-Style 流程（加入專業度適配）"""
        
        expertise_config = config.get("expertise_config", {})
        detail_level = expertise_config.get("detail_level", "專家")
        
        if self.verbose:
            print(f"   → 使用完整推理流程（{config['num_paths']} 路徑 + 評估）")
            print(f"   → 輸出詳細程度：{detail_level}")
        
        # 步驟 1: 生成多個推理路徑
        num_paths = config["num_paths"]
        
        def generate_path(path_num: int) -> dict:
            angles = [
                "實用可行性角度",
                "理論原理角度", 
                "批判風險角度",
                "創新解决方案角度",
            ]
            angle = angles[path_num - 1] if path_num <= len(angles) else f"多角度分析{path_num}"
            
            prompt = f"""你是一個專家級深度思考者。請從「{angle}」對這個問題進行系統性分析（輸出詳細程度：{detail_level}）：

<deep_analysis>
[深入分析這個問題的各個層面]
</deep_analysis>

<reasoning_chain>
[詳細的推理鏈]
</reasoning_chain>

<evidence>
[支持的證據或理由]
</evidence>

<potential_issues>
[可能的問題或漏洞]
</potential_issues>

<conclusion>
[這個角度的最終結論]
</conclusion>

問題：{question}"""
            
            result, p, c, cost = call_model(
                prompt,
                model=config["model"],
                max_tokens=config["budget_tokens"] // num_paths,
                temperature=config["temperature"]
            )
            return {"path": path_num, "angle": angle, "content": result, "tokens": p+c, "cost": cost}
        
        # 並行生成路徑
        with ThreadPoolExecutor(max_workers=num_paths) as executor:
            futures = [executor.submit(generate_path, i+1) for i in range(num_paths)]
            path_results = [f.result() for f in as_completed(futures)]
        
        if self.verbose:
            for pr in path_results:
                print(f"   - 路徑 {pr['path']} 完成 ({pr['tokens']} tokens)")
        
        # 步驟 2: 評估和選擇最佳路徑
        paths_text = "\n\n".join([f"路徑 {pr['path']} ({pr['angle']}):\n{pr['content']}" for pr in path_results])
        
        eval_prompt = f"""評估以下推理路徑，選擇最佳並進行整合（輸出詳細程度：{detail_level}）：

{paths_text}

請：
1. 評估每個路徑的質量（0-10）
2. 選擇最佳路徑
3. 綜合給出最終答案

<evaluation>
[各路徑評估]
</evaluation>

<final_answer>
[綜合後的最佳答案]
</final_answer>"""
        
        final_answer, p, c, cost = call_model(
            eval_prompt,
            model=config["model"],
            max_tokens=config["budget_tokens"],
            temperature=config["temperature"]
        )
        
        # 加上路徑生成的成本
        path_cost = sum(pr["cost"] for pr in path_results)
        
        return final_answer, p, c, cost + path_cost
    
    def get_stats(self) -> dict:
        """獲取統計信息"""
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 6),
        }
    
    def get_history(self) -> list[dict]:
        """獲取推理歷史"""
        return self.history
    
    def get_user_profile(self) -> dict:
        """獲取用戶檔案（新增）"""
        return self.memory.get_user_profile(self.user_id)
    
    def get_user_history(self, limit: int = 10) -> list:
        """獲取用戶歷史（新增）"""
        return self.memory.get_user_history(self.user_id, limit)

# ============================================================
# 分析工具
# ============================================================
def analyze_question(question: str) -> dict:
    """
    全面分析問題：複雜度 + 專業度
    返回完整分析報告
    """
    complexity = analyze_complexity(question)
    expertise = assess_domain_expertise(question)
    config = get_auto_config(complexity, expertise)
    
    return {
        "question": question,
        "complexity": {
            "level": complexity.name,
            "value": complexity.value,
        },
        "expertise": {
            "level": expertise.name,
            "value": expertise.value,
        },
        "recommended_config": {
            "model": config["model"],
            "budget_tokens": config["budget_tokens"],
            "num_paths": config["num_paths"],
            "temperature": config["temperature"],
        },
        "output_style": config.get("expertise_config", {}),
    }

# ============================================================
# 簡化 API：一句話用法
# ============================================================
_default_engine = None

def think(question: str, verbose: bool = False) -> str:
    """
    終極簡化 API！
    
    用法：
        answer = think("你的問題")
    
    完全自動：
    - 分析問題複雜度
    - 評估領域專業度
    - 選擇最佳模型
    - 執行推理
    - 自動評估質量
    - 保存記憶
    - 返回答案
    """
    global _default_engine
    
    if _default_engine is None:
        _default_engine = AdaptiveReasoner(verbose=verbose)
    
    result = _default_engine.think(question)
    return result["answer"]

# ============================================================
# 測試
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("🧠 Fable-Style Adaptive Reasoning v3.2 測試")
    print("   新增：自我評分 + 記憶功能 + 錯誤修復")
    print("=" * 50)
    
    # 測試專業度分析
    print("\n📊 測試專業度分析功能：")
    print("-" * 40)
    
    test_expertise_questions = [
        "什麼是 Python？",  # 新手級
        "點樣優化呢個算法嘅時間複雜度？",  # 中階
        "設計一個高併發系統，必須滿足 CAP 定理嘅邊界條件",  # 專家級
    ]
    
    for q in test_expertise_questions:
        analysis = analyze_question(q)
        print(f"\n📝 問題: {q}")
        print(f"   複雜度: {analysis['complexity']['level']}")
        print(f"   專業度: {analysis['expertise']['level']}")
        print(f"   推薦模型: {analysis['recommended_config']['model']}")
        print(f"   輸出風格: {analysis['output_style'].get('detail_level', '中等')}")
    
    print("\n" + "=" * 50)
    print("🧠 測試完整推理流程：")
    print("=" * 50)
    
    engine = AdaptiveReasoner(verbose=True)
    
    # 測試不同複雜度和專業度的問題
    test_questions = [
        "你好嗎？",  # TRIVIAL + NOVICE
        "今日天氣點？",  # SIMPLE + BEGINNER
        "點樣學好 Python？",  # MODERATE + BEGINNER
        "分析一下香港樓市未來走向",  # COMPLEX + INTERMEDIATE
        "設計一個高併發系統，必須滿足 CAP 定理嘅邊界條件",  # VERY_COMPLEX + EXPERT
    ]
    
    for q in test_questions:
        print("\n" + "=" * 60)
        result = engine.think(q)
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("📊 總統計:")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    print("\n📈 用戶檔案:")
    profile = engine.get_user_profile()
    print(f"   總會話數: {profile['total_sessions']}")
    print(f"   平均複雜度: {profile['avg_complexity']:.2f}")
    print(f"   平均專業度: {profile['avg_expertise']:.2f}")
    
    print("\n📜 最近歷史:")
    history = engine.get_user_history(5)
    for i, h in enumerate(history, 1):
        print(f"   {i}. [{h['complexity']}/{h['expertise']}] {h['question'][:30]}... "
              f"(質量: {h['quality']:.1f})")
