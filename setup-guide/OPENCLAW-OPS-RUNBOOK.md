# OpenClaw 模型 / 會話維修手冊（Ops Runbook）

Zeabur OpenClaw 日常運維、故障排查、手術修復嘅**統一入口**。維修前先讀呢份。
配 `TAILSCALE-MESH-SETUP.md`（網絡層）同 `DISASTER-RECOVERY.md`（VM 重建層）一齊用。

Last updated: 2026-09-17

---

## 1. 關鍵路徑（Zeabur 主機）

| 嘢 | 位置 |
|---|---|
| 主配置 | `~/.openclaw/openclaw.json` |
| Secret store | `~/.openclaw/state/openclaw.sqlite`（表 `secret_store_entries`，write-only，用 CLI 管理） |
| Agent DB（每個 agent 獨立） | `~/.openclaw/agents/<agent>/agent/openclaw-agent.sqlite` |
| 入站媒體 | `~/.openclaw/media/inbound/<uuid>.<ext>` |
| Log | `/tmp/openclaw/openclaw-<日期>.log`（每日一個，舊嘅會被清） |
| Skills | `~/.openclaw/skills/<name>/`（全局，全部 agent 共用） |
| Telegram ingress spool | state db 表 `channel_ingress_events` |

Gateway 管理：

```bash
export PATH="$HOME/.npm-global/bin:$PATH"
systemctl --user restart openclaw-gateway     # restart（清僵屍 worker 最有效）
curl -s -m 8 -o /dev/null -w "%{http_code}\n" http://100.121.1.3:18789/health   # 要 200
openclaw doctor                                # config 驗證（報 0 即 valid）
```

---

## 2. 系統現況（2026-09-17 編制）

### 2.1 Agent 編制表

| Agent | Primary | Fallback 鏈 |
|---|---|---|
| arslansky-agent | minimax/MiniMax-M2.7 | → kimi/kimi-k2.6 |
| know2learn-agent | minimax/MiniMax-M2.7 | → kimi/kimi-k2.6 → zhi-api/gpt-5.6-luna |
| janzaibot-agent | kimi/kimi-k2.6 | → minimax/M2.7 → luna → chatfire（**chatfire 曾 hang 死全軍，排最尾**） |
| ds-agent | chatfire/deepseek-v4-pro | → kimi/kimi-k2.6 → minimax/M2.7 → luna |
| minimax-agent | chatfire/deepseek-v4-pro | → kimi/kimi-k2.6 → minimax/M2.7 → luna |
| zo-agent | chatfire/deepseek-v4-pro | → kimi/kimi-k2.6 → minimax/M2.7 → luna |

改法（python 直改 openclaw.json，`openclaw config set` 搞唔到 nested array）：

```python
import json
p = "/home/ubuntu/.openclaw/openclaw.json"
d = json.load(open(p))
d["agents"]["entries"]["<agent>"]["model"] = {"primary": "...", "fallbacks": [...]}
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
```

改完 `openclaw doctor` + gateway 會 hot reload（log 有 `config hot reload applied`）。

### 2.2 Provider 一覽

| Provider | Endpoint | 性質 | Key |
|---|---|---|---|
| minimax | api.minimax.io/anthropic | **官方** | MINIMAX_API_KEY（store） |
| kimi | api.kimi.com/coding/v1 | **官方**（SSOT，同 Hermes 共用） | KIMI_API_KEY（store，有 --allow-host） |
| zhi-api | zhi-api.com/v1 | **中轉**（預設全部行 luna，生圖除外） | ZHI_API_API_KEY（store） |
| chatfire | api-mall.chatfire.cn/v1 | **免費中轉**（冇 SLA，會整個 hang 死） | inline config |
| deepseek / waninter | — | 後備 | — |

### 2.3 三大決策原則（唔好違反）

1. **SSOT**：Kimi 一條 key 通 Hermes + OpenClaw；kimi provider 只行 official
2. **zhi 預設 = gpt-5.6-luna**（穩定平易）；**唯一例外**：生圖 `zhi-api/gpt-image-2`
3. **免費 relay（chatfire）唔做關鍵路徑**——hang 唔會觸發 failover，隨時卡死全軍

### 2.4 Vision 架構

- 多模態 model（minimax/M2.7、kimi/k2.6）原生睇圖
- text-only model 收圖 → OpenClaw offload 落 `media/inbound/` 留 ref
- **kimi-look skill**（`~/.openclaw/skills/kimi-look/`）= 睇圖唯一入口：bot 用 script call k2.6 睇
- media-understanding 用 `agents.defaults.imageModel`（= kimi/k2.6 → gpt-image-2 生圖後備），**生圖 model 唔可以做 caption**（gpt-image-2 收 chat completion 會 400）

---

## 3. 排查 SOP（bot 唔覆 / 卡死，跟次序做）

### Step 1 — Gateway 死未

```bash
curl -s -m 8 -o /dev/null -w "%{http_code}\n" http://100.121.1.3:18789/health   # 要 200
```

### Step 2 — Log 睇卡死徵狀

```bash
L=/tmp/openclaw/openclaw-$(date +%F).log
grep -E "without_progress|long-running" $L | tail -5        # 有 = 有 call hang 緊
grep "<agent-name>" $L | grep "message processed" | tail -3 # 睇 outcome=ok/error
grep "model-fetch" $L | tail -20                            # 邊個 provider 郁緊
```

- `active_model_call_without_progress` = 個 call hang 咗冇進度（通常 relay 死）
- `duration=14xxxxxms`（20+ 分鐘）先 error = zombie call

### Step 3 — 探測個 provider 死未（8 秒超時）

```bash
# zhi 例：key 由 store 攞（其他 provider 類推）
python3 -c "
import sqlite3
con=sqlite3.connect('/home/ubuntu/.openclaw/state/openclaw.sqlite')
k=[r[0] for r in con.execute(\"SELECT value FROM secret_store_entries WHERE name='ZHI_API_API_KEY' AND deleted_at_ms IS NULL\")][0]
open('/tmp/k','w').write(k.strip())"
curl -sS -m 8 -o /dev/null -w "%{http_code} in %{time_total}s\n" \
  https://zhi-api.com/v1/chat/completions \
  -H "Authorization: Bearer $(cat /tmp/k)" -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.6-luna","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' || echo "HANG/DEAD"
rm -f /tmp/k
```

`HTTP 000` / timeout / 0 bytes = relay 死。**注意：hang 唔會觸發 failover**，primary 用死咗嘅 relay = bot 卡到 timeout。

### Step 4 — Session sticky / pin 檢查

```bash
python3 - <<'EOF'
import sqlite3, json
con = sqlite3.connect("/home/ubuntu/.openclaw/agents/<agent>/agent/openclaw-agent.sqlite")
for row in con.execute("SELECT session_key, entry_json FROM session_nodes WHERE entry_json LIKE '%modelProvider%'"):
    d = json.loads(row[1])
    if d.get("modelProvider"):
        print(row[0][:60], "->", d["modelProvider"], "/", d["model"])
con.close()
EOF
```

**機制**：session 用過邊個 model 就 sticky 邊個（自動寫入 entry_json），會**冚咗 agent fallback 鏈**。即係話：改咗 agent 配置後，**舊 session 繼續行舊 model**，要剷先生效。

### Step 5 — Ingress spool 死鎖

特徵：`telegram dispatch failed: Session ... changed while starting work` 每 3 分鐘 loop。

```bash
python3 -c "
import sqlite3
con=sqlite3.connect('/home/ubuntu/.openclaw/state/openclaw.sqlite')
for r in con.execute(\"SELECT event_id, status, received_at FROM channel_ingress_events WHERE account_id='<bot-account>' AND status='pending'\"):
    print(r)"
# 棄掉舊 spool（留一條最新嘅）
# UPDATE channel_ingress_events SET status='failed' WHERE event_id='0000000XXXXXXXXX'
```

### Step 6 — FK 檢查（gateway 弹 `foreign_key_check failed` 時）

```bash
python3 -c "
import sqlite3
con=sqlite3.connect('/home/ubuntu/.openclaw/agents/<agent>/agent/openclaw-agent.sqlite')
print(len(list(con.execute('PRAGMA foreign_key_check'))))"
# 0 = clean；有違規睇下面第 5 節 repair
```

### Step 7 — Cron / 全面狀態

```bash
openclaw cron list
openclaw agents list
openclaw status
```

---

## 4. 故障類型 × 修法對照表

| # | 類型 | 特徵 | 修法 |
|---|---|---|---|
| A | **Relay hang**（chatfire 型） | provider 探測 000/timeout；`without_progress` loop；卡 20+ 分鐘先 error | 1) 探測確認 2) 臨時將受影響 agent primary 轉去 kimi/k2.6 3) relay 復活後想郁返先郁 |
| B | **Session sticky** | 改咗配置但 bot 仲行舊 model | `openclaw sessions delete <session_key> --yes`（transcript 自動封存 .zst） |
| C | **Ingress 死鎖** | `Session changed while starting work` 每 3 分鐘 loop | 棄舊 spool（Step 5）→ restart gateway → 剷 session（Step B）→ 叫用戶 send 新訊息 |
| D | **FK violation** | gateway 每個 commit 弹 `foreign_key_check failed`；spooled update 失敗 | 遞歸 repair（第 5 節） |
| E | **Model metadata lag** | 明明係多模態但 OpenClaw 標 `text`（會剷圖） | 喺 provider models 條目補 `"input": ["text","image"]`；catalog refresh 可能會冚，要覆查 |
| F | **生圖 model 做 caption** | media-understanding `Image model failed (zhi-api/gpt-image-2)` 400 | `agents.defaults.imageModel` primary 用識睇圖嘅（kimi/k2.6），gpt-image-2 只留生圖 |

---

## 5. 手術安全規則（DO / DON'T）

**DO：**
- 剷 session 一律用 `openclaw sessions delete <key> --yes`
- 官方渠道唔通 → restart gateway 先再試（清僵屍 worker）
- 真係要動 DB：事前 `cp <db> /tmp/<名>_backup.sqlite`；用 python 腳本經 stdin 執行（唔好 ssh 嵌引號地獄）
- 改 entry_json 摘 pin（保留 row 只清 model 欄）係安全手術
- 遞歸 FK repair：

```python
import sqlite3
from collections import defaultdict
con = sqlite3.connect("<db>")
for it in range(20):
    rows = list(con.execute("PRAGMA foreign_key_check"))
    if not rows: break
    to_del = defaultdict(list)
    for t, rid, p, f in rows: to_del[t].append(rid)
    for t, ids in to_del.items():
        u = sorted(set(ids))
        con.execute(f"DELETE FROM {t} WHERE rowid IN ({','.join('?'*len(u))})", u)
    con.commit()
con.close()
```

**DON'T（全部有前科）：**
- ❌ **直 DELETE `session_nodes` rows**——違反 FK，搞到 100 個 orphan、gateway commit 全弹、要遞歸清（2026-09-17 前科）
- ❌ 用 `cat <<EOF` heredoc 經 ssh 改檔（引號地獄）——本地 write_file 寫 python 再 `ssh python3 - <` 餵入
- ❌ secret 值 print 出嚟貼 chat——store 係 write-only，要用 `--value-file -` 由 stdin 寫
- ❌ `secrets store set` 用帶尾換行嘅檔案（awk 輸出有 \n）——provider runtime header 會炸；寫入前 `.strip()`

---

## 6. 過去教訓（Incident Log）

| 日期 | 事件 | 根因 | 修法 |
|---|---|---|---|
| 2026-09-12 | MiniMax 529 死訊息、failover 冇郁 | session pin 裸 model 冚咗 agent fallback 鏈 | `sessions delete` 清 pin；教訓入 memory |
| 2026-09-12 | `openclaw doctor` 報 config invalid | plugins 更新遺留 `tools.firecrawl` key | python 刪 key |
| 2026-09-12 | arslansky 睇唔到圖 | zhi relay 全部 text-only，唔 forward 圖 | minimax 直連（多模態）+ 後來補埋 kimi-look skill |
| 2026-09-12 | bot 畫唔到圖 | kimi-for-coding 唔識生圖 | imageModel 轉 zhi-api/gpt-image-2（但引發下面 9/14 單） |
| 2026-09-14 | media-understanding 400 loop | imageModel（gpt-image-2）被挪用做 caption | imageModel.primary = kimi/k2.6 |
| 2026-09-14 | kimi provider 一直唔 work | store KIMI_API_KEY 係 13 字節 placeholder + baseUrl 缺 `/coding` | 換 SSOT key（記得 `.strip()` 同 `--allow-host api.kimi.com`）+ 改 baseUrl |
| 2026-09-14 | k2.6 被標 text-only | upstream catalog metadata lag | provider models 補 `"input": ["text","image"]` |
| 2026-09-16 | chatfire 全日 hang，janzaibot 卡 24 分鐘 loop | 免費 relay 整個死；hang 唔觸發 failover | janzaibot 轉 k2.6 做頭；chatfire 軍團暫時照舊等復活 |
| 2026-09-16/17 | **FK 災難 + ingress 死鎖** | 手術直 DELETE session_nodes rows → FK violation → spooled update 死鎖 | 遞歸 FK repair + 棄 spool + restart + 官方渠道剷 session |

---

## 7. 定期維護 Checklist

每週（或出現「bot 怪怪哋」時）行一次：

- [ ] `curl health` = 200；`openclaw doctor` 零 invalid
- [ ] `grep -c without_progress` 今日 log = 0
- [ ] 各 agent session pins 抽查（Step 4）——有異常 sticky 先剷
- [ ] chatfire 探測（免費 relay 隨時死，Step 3）
- [ ] `channel_ingress_events` 冇長期 pending
- [ ] FK check 六個 agent DB 全零
- [ ] `openclaw cron list` 冇 error status
- [ ] 新 model 想加入：provider models + `agents.defaults.modelPolicy.allow` 兩邊都要加；先用 curl 實測 endpoint

---

## 8. 相關文件

- `TAILSCALE-MESH-SETUP.md` — 網絡層（tailnet、firewall、serve、SSH alias）
- `DISASTER-RECOVERY.md` — VM 層（重建、config restore、secrets 優先級）
- Hermes memory（Oracle）— 有本手冊存在嘅指針同精簡版教訓
