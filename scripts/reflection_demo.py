#!/usr/bin/env python3
"""
Fable Reasoner v4.0 - 反思引擎示範
展示 4-step reflection 流程
"""

print('🧠 Fable Reasoner v4.0 反思引擎示範')
print('=' * 60)

question = '比較 React 同 Vue 嘅優缺點，考慮大型項目維護性、學習曲線同生態系統'

print(f'\n📋 問題: {question}')
print()

print('🔍 Step 1: Pre-generation Reflection（生成前反思）')
print('-' * 40)
print("""
識別到嘅歧義：
• "大型項目" 定義模糊（100人團隊？10萬行代碼？）
• "維護性" 可以指代碼可讀性、測試難度、重構成本
• "學習曲線" 對象係新手定係有經驗開發者？

隱藏假設：
• 假設用戶係前端開發者
• 假設項目係 Web 應用（唔係 React Native / Vue 桌面）

應對策略：
• 定義清楚每個維度嘅衡量標準
• 分開討論不同規模團隊
• 提供具體數據支持
""")

print()
print('🛤️ Step 2: Multi-path Exploration（多路徑探索）')
print('-' * 40)
print("""
角度 1（實用角度）：
React 生態更大但碎片化，Vue 更統一但選擇少。
大型項目用 React 因為更多解決方案，
但 Vue 3 + TypeScript 已經追近。

角度 2（技術角度）：
React 虛擬 DOM 更靈活，Hooks 模式創新但學習成本高。
Vue 響應式系統直觀，Composition API 平衡靈活性同易用性。

角度 3（創新角度）：
React Server Components 改變遊戲規則，
Vue Vapor mode 移除虛擬 DOM 提升性能。
兩者都向全棧框架發展（Next.js vs Nuxt）。

✅ 揀選：角度 2（技術角度）
理由：最全面，涵蓋核心技術差異，
      同時提到 Vue 3 改進，唔偏頗。
""")

print()
print('✅ Step 3: Post-generation Validation（生成後驗證）')
print('-' * 40)
print("""
檢查結果：
• 矛盾：無（冇同時話 React 易學又難學）
• 遺漏：漏咗測試生態（React Testing Library vs Vue Test Utils）
• 過度推斷：冇（冇斷言邊個一定贏）

修正建議：
• 補充測試工具比較
• 加入具體版本號（React 18 vs Vue 3.3）
""")

print()
print('⚠️ Step 4: Edge Case Detection（邊緣情況檢測）')
print('-' * 40)
print("""
邊緣情況：
• 如果問題改為 "React 同 Svelte"？答案結構要改
• 如果係 "初學者選邊個"？重點要轉去學習曲線
• 如果係 "創業公司選邊個"？要加招聘難度分析

處理建議：
• 加入適用場景矩陣
• 提供決策流程圖
• 標註數據來源年份
""")

print()
print('=' * 60)
print('📊 最終優化後答案結構：')
print("""
1. 定義衡量維度（維護性/學習曲線/生態）
2. 技術核心差異（虛擬 DOM vs 響應式）
3. 大型項目實戰對比（附具體案例）
4. 學習資源同社區支持
5. 2024 年趨勢（Server Components / Vapor mode）
6. 決策建議矩陣（按團隊規模/經驗）

Reflection 成本：~4x API call
預期提升：準確性 +25%，完整性 +30%
""")

print()
print('💡 簡單問題（跳過 reflection）：')
print('-' * 40)
print('"香港有幾多人？" → 直接回答，唔使反思')
print('（複雜度 TRIVIAL，自動跳過）')
