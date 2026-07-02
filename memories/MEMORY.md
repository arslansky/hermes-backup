TaskForge routing: → skills: hermes-taskforge
§
- **Big VM (Claw Cloud)**: 47.79.224.55 — 💀 已死，Claw Cloud已倒閉，唔再可用
§
每日GitHub報告prefer簡潔（列表式），最多加1個repo深探。Cookies: ~/.hermes/cookies/
§
GitHub: arslansky. Backup: → skills/hermes-backup-sync. Skills: ~/.hermes/skills/. Backups: ~/.hermes/backups/superpowers-*
§
賽後檢討+Memory管理：複雜任務完成後自動檢討，目標memory<70%。
§
Cron Audit: ~/.hermes/cron/audit-YYYY-MM.jsonl，2 jobs
§
## 明報爬蟲
- Script: ~/.hermes/scripts/mingpao_scraper.py ✅ CloakBrowser 做 section pages（sequential）
- AI摘要失效（MiniMax API key問題）
§
## Oracle VM (2026-07-01)
- IP: 140.245.111.2, SSH: ssh -i /root/.ssh/oracle_vm_final.pem opc@140.245.111.2
- Disk: 91% full (27GB/30GB used, only 2.9GB free) — CRITICAL，需要清理
- 網絡: minimax, Google, TTK API 全通；被Block Kimi/Qwen(moyu)/Claude/OpenAI(官)
- /var/log/messages-20260614/21/28 佔 1.6GB; npm cache: 123MB; Docker unused images: 166MB
§
## Zeabur OpenClaw (2026-07-01)
- IP: 43.156.247.30, user=ubuntu, pass=@Q2%YTCbe%)mvSGQ42
- OpenClaw 2026.6.11 installed at /home/ubuntu/.npm-global/bin/openclaw
- Telegram bot @arslanskybot paired (ID: 160408068)
- Workspace restored from arslansky/openclaw-workspace (private, 168MB)
- Git sync active: ~/.openclaw/workspace git repo → arslansky/openclaw-workspace
- Agent config restored: auth-profiles, models.json, config.json, model.json
- Model set to minimax-cn/MiniMax-M2.7 (but log shows gpt-5.5 — config.json may be overridden by openclaw.json)
- OpenClaw gateway PID: 25349, log: /tmp/openclaw/openclaw-2026-07-01.log
- Backup auth tokens: moonsense, minimax (multiple), kimi-coding, ttk, yunyi, kimi, zhi-api
- Skills restored: prism-thinking-refinery (in workspace/skills/)
- Note: log shows "agent model: openai/gpt-5.5" despite config — check if openclaw.json overrides agent config
§
## VMs 登入資料 (2026-07-01)
- **Zeabur VM**: 43.156.247.30, user=ubuntu, pass=@Q2%YTCbe%)mvSGQ42 ✅ 在線，2核/1.9GB/40GB，K3s架構，SG機房
- **ZO VM**: ts8.zocomputer.io:10661, user=opc ✅ 在線
- **Oracle VM**: 140.245.111.2, user=opc ✅ 在線，磁盤91%滿
- **Big VM (Claw Cloud)**: 47.79.224.55 — 💀 已死，Claw Cloud已倒閉
- Big VM同Zeabur VM係兩部唔同嘅機