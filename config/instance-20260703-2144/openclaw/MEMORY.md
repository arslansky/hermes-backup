# MEMORY.md — Long-Term Memory

## Infrastructure

### 三個 VM（全部通過 SSH 溝通）

| VM | Public IP / Host | User | Auth | Port | 用途 |
|---|---|---|---|---|---|
| Oracle VM | `161.118.247.199` | `opc` | SSH key `zeabur_key` | 22 | Hermes Gateway, OpenClaw, Discord, LLM |
| Zeabur VM | `43.156.247.30` | `ubuntu` | Password（無 SSH key） | 22 | OpenClaw main, Telegram, WhatsApp |
| ZO VM | `ts8.zocomputer.io` (→ `150.136.143.138`) | `root` | SSH key `zeabur_key` | 10661 | Zo Computer |

**注意：** Oracle 的 `129.80.234.56` 係 private IP，外面 VM 連唔到。SSH 全部用 `161.118.247.199`。

### SSH Key
- `zeabur_key` 在 Oracle: `~/.ssh/zeabur_key`
- ZO 已 authorized: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK3o5EE2Yn5Bn21FIVlYx2Pr6s3UgV5R4aU5FDChrA+w openclaw-zo`
- Zeabur **沒有** `zeabur_key`，如需 Zeabur 主動連接其他 VM，需先 copy key 過去

### Files
- `ops/VM_CONNECTION_MANUAL.md` — AI 用 SSH 對照表
- `inventory.yml` — VM inventory

## User
- Arslan (@Arslansky), Telegram ID: 160408068
- Speaks Cantonese
- Running OpenClaw on Oracle Cloud ARM64 free tier
