#!/usr/bin/env python3
"""
Fable Light Components — 從 fable_reasoner.py 抽取最有價值的部分

包含：
1. MemoryStore — SQLite 用戶偏好持久化
2. AnswerEvaluator — 答案質量評估
3. Complexity + DomainExpertise 分析

純 stdlib，無外部依賴。
"""

import os
import json
import sqlite3
import re
from typing import Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


# ============================================================
# 複雜度級別
# ============================================================
class Complexity(Enum):
    TRIVIAL = 0
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    VERY_COMPLEX = 4


# ============================================================
# 領域專業度級別
# ============================================================
class DomainExpertise(Enum):
    NOVICE = 0
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


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

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.expanduser("~/.hermes"), "fable_memory.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化數據庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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

        profile = self.get_user_profile(user_id)
        total = profile["total_sessions"] + 1

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
# 答案評估
# ============================================================
class AnswerEvaluator:
    """
    答案質量自動評估
    基於多個維度評分
    """

    @staticmethod
    def evaluate(answer: str, question: str, complexity: Complexity = None) -> dict:
        """
        評估答案質量
        返回分數和改進建議
        """
        scores = {}

        # 1. 完整性評分（是否有結構化輸出）
        structure_markers = ['analysis', 'reasoning', 'answer', 'conclusion', 'summary',
                             '分析', '推理', '答案', '結論', '總結']
        structure_score = sum(1 for marker in structure_markers if marker in answer.lower())
        scores['structure'] = min(structure_score / 3, 1.0) * 10

        # 2. 深度評分（根據複雜度期望）
        expected_length = {
            Complexity.TRIVIAL: 50,
            Complexity.SIMPLE: 150,
            Complexity.MODERATE: 300,
            Complexity.COMPLEX: 500,
            Complexity.VERY_COMPLEX: 800,
        }
        expected = expected_length.get(complexity, 300) if complexity else 300
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
        scores['relevance'] = min(relevance * 15, 10)

        # 4. 實用性評分（是否有行動建議）
        action_markers = ['建議', '推薦', '步驟', '方法', '策略', '總結', '建议', '推荐']
        action_score = sum(1 for marker in action_markers if marker in answer)
        scores['actionability'] = min(action_score / 2, 1.0) * 10

        # 5. 清晰度評分
        clarity_markers = ['首先', '其次', '最後', '1.', '2.', '3.', '總結', '首先', '其次']
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
# 自動複雜度評估
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

    # 決策類問題
    decision_keywords = ['決策', '决策', '選擇', '选择', '應該點', '點樣決定', '邊個好', '定係']
    if any(kw in question_lower for kw in decision_keywords):
        return Complexity.MODERATE

    # 數量/事實類問題
    quantity_keywords = ['幾多', '幾個', '幾時', '幾耐', '邊個', '咩', '係咩']
    if any(kw in question_lower for kw in quantity_keywords) and len(question) > 10:
        return Complexity.SIMPLE

    # 比較類問題
    compare_keywords = ['比較', '比', '邊個好', '定', '定係', '差異', '不同']
    if any(kw in question_lower for kw in compare_keywords):
        return Complexity.MODERATE

    # 學習/方法類問題
    learning_keywords = ['點樣', '點解', '點樣可以', '點解', '點', '方法', '點做']
    if any(kw in question_lower for kw in learning_keywords):
        return Complexity.MODERATE

    # 關鍵詞評分
    simple_keywords = ['係', '係咪', '有冇', '幾時', '邊個', '咩', '點樣', '係邊', '幾多']
    moderate_keywords = ['點解', '為什麼', '點樣可以', '應該點', '有咩好', '分析', '解釋']
    complex_keywords = ['論證', '評估', '策劃', '設計', '比較', '對比']

    simple_score = sum(1 for kw in simple_keywords if kw in question_lower)
    moderate_score = sum(1 for kw in moderate_keywords if kw in question_lower)
    complex_score = sum(1 for kw in complex_keywords if kw in question_lower)

    length_bonus = len(question) // 25
    score = simple_score + moderate_score * 2 + complex_score * 3 + length_bonus

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

    expert_markers = [
        # 精確性標記
        '必須', '必須滿足', '邊界條件', '約束', '限制條件',
        'must', 'constraint', 'boundary', 'threshold',
        # 專業術語
        '優化', '算法複雜度', '時間複雜度', '空間複雜度',
        'big o', 'complexity',
        # 系統性思維
        '架構', '系統設計', '模塊化', '耦合', '內聚',
        # 專業領域
        '對帳', '月結', 'reconciliation', 'closing',
        '風險敞口', '敞口', 'exposure', 'var', '風險價值',
        # 技術深度
        '併發', '高併發', '分散式', '分布式', '微服務',
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

    beginner_markers = [
        '什麼是', '什麼係', '點解', '點樣',
        'what is', 'how to', 'why', 'explain',
        '入門', '新手', 'beginner', '入門',
        '學習', '教學', 'tutorial', 'guide',
        '基礎', 'basic', '簡單', 'simple',
        '介紹', '簡介', '概述', 'overview',
        '第一次', '初學', '開始',
    ]

    expert_score = sum(3 for marker in expert_markers if marker in question_lower)
    intermediate_score = sum(1.5 for marker in intermediate_markers if marker in question_lower)
    beginner_penalty = sum(-1 for marker in beginner_markers if marker in question_lower)

    length_score = min(len(question) // 40, 3)

    structure_score = 0
    if any(marker in question for marker in ['1.', '2.', '3.', '首先', '其次', '最後']):
        structure_score = 2
    if any(marker in question for marker in ['例如', '比如', 'for example', 'e.g.']):
        structure_score += 1

    precision_score = 0
    if any(marker in question for marker in ['必須', '至少', '最多', '不超過', '大於', '小於']):
        precision_score = 2
    if any(marker in question for marker in ['%', 'ms', 'mb', 'gb', 'tb']):
        precision_score += 2
    if re.search(r'\d+\s*[萬千]?\s*[qps|tps|rps|ms|gb|mb|tb]', question_lower):
        precision_score += 3

    total_score = expert_score + intermediate_score + beginner_penalty + length_score + structure_score + precision_score

    if total_score <= 0:
        return DomainExpertise.NOVICE
    elif total_score <= 2:
        return DomainExpertise.BEGINNER
    elif total_score <= 6:
        return DomainExpertise.INTERMEDIATE
    elif total_score <= 10:
        return DomainExpertise.ADVANCED
    else:
        return DomainExpertise.EXPERT


# ============================================================
# 綜合分析
# ============================================================
def analyze_question(question: str) -> dict:
    """
    全面分析問題：複雜度 + 專業度
    返回完整分析報告
    """
    complexity = analyze_complexity(question)
    expertise = assess_domain_expertise(question)

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
    }


# ============================================================
# CLI 測試
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("Fable Light Components 測試")
    print("=" * 50)

    test_questions = [
        "你好嗎？",
        "今日天氣點？",
        "點樣學好 Python？",
        "分析一下香港樓市未來走向",
        "設計一個高併發系統，必須滿足 CAP 定理嘅邊界條件",
    ]

    store = MemoryStore()
    evaluator = AnswerEvaluator()

    for q in test_questions:
        analysis = analyze_question(q)
        print(f"\n問題: {q}")
        print(f"  複雜度: {analysis['complexity']['level']}")
        print(f"  專業度: {analysis['expertise']['level']}")

    print("\n" + "=" * 50)
    print("用戶檔案:")
    profile = store.get_user_profile()
    print(f"  總會話數: {profile['total_sessions']}")
    print(f"  平均複雜度: {profile['avg_complexity']:.2f}")
    print(f"  平均專業度: {profile['avg_expertise']:.2f}")
