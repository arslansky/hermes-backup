# News Summary Scripts

自動拎取新聞全文 + 格式化作摘要（時、地、人、事件、重點）。

## 用法

```bash
bash news_summary.sh "<NEWS_URL>"
```

## 輸出格式

```
📰 標題
🕐 時：時間
📍 地：地點  
👤 人：關鍵人物
📋 事件：一句總結
🔑 重點：關鍵重點
📄 正文全文
```

## 支援網站

- 商業電台 881903.com
- on.cc 東網
- 其他 JS 渲染頁面（Vue/JSON embedded content）

## 依賴

- Python 3
- curl

## 更新記錄

- 2026-07-05: 初始版本，支援 881903.com 及 on.cc
