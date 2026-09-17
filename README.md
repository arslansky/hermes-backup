# 🗂️ Hermes-Backup Repository — 總索引

Multi-VM Hermes + OpenClaw 基礎設施嘅 **single source of truth**（配置、腳本、技能、維修手冊）。
密碼/金鑰一律唔入 repo（每部 VM 自己管 `.env`）。

---

## 🧭 出問題去邊份文件（分層索引）

| 你而家嘅問題 | 去呢份 | 位置 |
|---|---|---|
| **Bot 唔覆 / 卡死 / 用錯 model / 改編制** | OpenClaw Ops Runbook | [`setup-guide/OPENCLAW-OPS-RUNBOOK.md`](setup-guide/OPENCLAW-OPS-RUNBOOK.md) |
| **網絡：Tailscale、firewall、SSH、跨 VM 連線** | Tailscale Mesh Setup | [`setup-guide/TAILSCALE-MESH-SETUP.md`](setup-guide/TAILSCALE-MESH-SETUP.md) |
| **新 VM 加入（裝 Hermes/OpenClaw、symlink、cron）** | Multi-VM Setup | [`setup-guide/HERMES-OPENCLAW-MULTI-VM-SETUP.md`](setup-guide/HERMES-OPENCLAW-MULTI-VM-SETUP.md) |
| **成部 VM 死咗 / 要重建 / config restore** | Disaster Recovery | [`setup-guide/DISASTER-RECOVERY.md`](setup-guide/DISASTER-RECOVERY.md) |

**維修次序原則**：先讀 Ops Runbook 判斷問題層；搞唔定先上網絡層（Tailscale）；成機冧先走 Disaster Recovery。

---

## 📂 Repository Structure

```
hermes-backup/
├── README.md                    ← 呢個檔案（總索引）
├── inventory.yml                ← 三部 VM 清單（tailnet IP、角色、alias）
├── setup-guide/                 ← 四份手冊（見上表）
├── scripts/                     ← 共享腳本（各 VM symlink 過嚟用）
├── skills/                      ← 共享技能/知識（bot 用）
├── config/                      ← 各 VM config 自動備份（hermes cron 每日 push）
├── news-summary/                ← 新聞摘要工具
├── archive/                     ← 舊文件（歷史參考，唔再更新）
└── minimax-agent/               ← minimax bot 配置
```

---

## 🖥️ VM Inventory（2026-09-17 現況）

| VM | Tailnet IP | SSH（由 Oracle） | User | Role | Repo 位置 |
|---|---|---|---|---|---|
| **Oracle-01** | 100.96.203.104 | `ssh oracle` | opc | Hermes（本機）+ 維修者 | `/home/opc/hermes-backup`（`~/scripts` 係 legacy symlink 指住佢） |
| **Zeabur-01** | 100.121.1.3 | `ssh zeabur` | ubuntu | OpenClaw 主機（6 個 bot） | `/home/ubuntu/hermes-backup` |
| **ZO-01** | —（無 tailnet） | `ssh zo`（公網 :10661） | root | Zo Computer VM | `/root/hermes-backup` |

> 公網 IP 已淘汰——2026-09-14 起全部 tailnet 化，詳情睇 Tailscale runbook。
> SSH alias 定義喺 Oracle `~/.ssh/config`。

---

## ⚡ Quick Reference

```bash
# 任何 VM 更新到最新
cd ~/hermes-backup && git pull

# Oracle 連其他 VM
ssh zeabur          # Zeabur-01
ssh zo              # ZO-01

# OpenClaw 主機（Zeabur）健康檢查
curl -s -m 8 -o /dev/null -w "%{http_code}\n" http://100.121.1.3:18789/health   # 要 200
```

---

## 📏 Golden Rules

1. **Secrets 唔入 repo** — 每 VM 自己 `.env`；OpenClaw secret 走 secret store（write-only）
2. **可執行腳本一律放 `scripts/`** — 唔好放 repo root
3. **舊文件放 `archive/`** — 唔好刪，標日期留底
4. **維修前先讀對應手冊** — 四份手冊互相 cross-link，呢個 README 係入口
5. **改完即 push** — repo 係 SSOT，其他 VM 靠 `git pull` 同步

---

_Maintained by: arslansky（Hermes on Oracle-01 係 designated 最後維修者）_
_Last updated: 2026-09-17_
