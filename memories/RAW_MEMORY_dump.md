# Hermes Raw Memory Dump
# Generated: 2026-06-06 19:20

================================================================================
## MEMORY.md (System Notes)
================================================================================

TaskForge routing: → skills: hermes-taskforge
§
Oracle VM pip quirk: → skills/oracle-vm-setup
§
每日GitHub報告prefer簡潔（列表式），最多加1個repo深探。否則資訊量太大消化唔到。
§
用戶偏好用瀏覽器 cookies 來簡化爬蟲認證流程：俾一次就自動重用，唔使每次都重新俾。存放路徑：~/.hermes/cookies/
§
GitHub: arslansky. Backup: → skills/hermes-backup-sync. Pioneer.ai: → skills/pioneer-ai (when available). Skills: ~/.hermes/skills/. Backups: ~/.hermes/backups/superpowers-*
§
賽後檢討+Memory管理：複雜任務完成後自動檢討，記錄教訓到memory/skill。每加1新entry考慮合併/刪1舊entry，目標保持memory<70%。
§
Cron Job Audit Policy (2026-06-06):
- Design: Append-only JSONL audit log at ~/.hermes/cron/audit-YYYY-MM.jsonl
- Format per line: {"id","name","state","exit_status","completed_at","duration_sec"}
- Retention: 0-3mo=raw, 3-12mo=gzip, >12mo=delete
- 當 active + completed jobs 總數 > 10個時，通知用戶整理
- 目前: 2 jobs，唔需要做任何野
§
## 明報爬蟲 → ~/.hermes/scripts/mingpao_scraper.py (見 KNOWN ISSUES)
§
## Memory Summary for PDF (2026-06-05)

================================================================================
## USER.md (User Profile)
================================================================================

User is trying to access AI research reports from Oracle Cloud infrastructure
§
## User Preferences & Style
- User is "你" (Master), AI is "Hermes" (Oracle VM agent)
- Communicate in Cantonese/mixed Cantonese-Chinese
- Prefers concise, direct answers with clear A/B/C options
- Likes tables and ASCII diagrams for architecture explanations
- Prefers $0 solutions before paid options
- Big VM is his main interaction point (TG bot there)
- Oracle VM is Hermes (me) - the brain
- User wants: Hermes learns skills/workflows → dispatches to workers → evolves over time
§
3 New DSE Projects 2026-05-13:
- Geography: data/dse-geography/ — 5 articles, SQLite+FTS5, 27.7KB notes
- Economics: data/dse-economics/ — 1 article, SQLite, 30.6KB notes
- English: data/dse-english/ — Schema only, 22KB AI gen notes (no public websites found)
§
LightNode Worker added 2026-05-13: 4th TaskForge worker (lightnode). IP乾淨 — crawl結果好（HKEAA/DSE00/DSEPP 200, 明報403 CF阻）。TaskForge已註冊，可直接dispatch。
§
User asked about LightNode - need to check if it needs to be powered on. Tasks might need its clean IP for crawling.
§
長文輸出偏好（2026-05-15）：當回覆內容估計超過5頁A4（或者TG顯示會截斷/打爆context時），自動將完整版本輸出為 .txt + .pdf 檔案，唔好直接喺TG發送長文字。PDF優先，.txt作後備。
