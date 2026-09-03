# MEMORY.md — Long-Term Memory

## Infrastructure

### 三個 VM（全部通過 SSH 溝通）

| VM | Public IP / Host | User | Auth | Port | 用途 |
|---|---|---|---|---|---|
| Oracle VM | `161.118.247.199` | `opc` | SSH key `zeabur_key` | 22 | Last Keeper (Hermes), OpenClaw |
| Zeabur VM | `43.156.247.30` | `ubuntu` | Password | 22 | 主 OpenClaw、Telegram Bots |
| ZO VM | `ts8.zocomputer.io` (→ `150.136.143.138`) | `root` | SSH key `zeabur_key` | 10661 | Zo Computer |

### SSH Key
- `zeabur_key` 在 Oracle: `~/.ssh/zeabur_key`
- ZO 已 authorized: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK3o5EE2Yn5Bn21FIVlYx2Pr6s3UgV5R4aU5FDChrA+w openclaw-zo`

## Telegram Bots 配置（2026-07-28 更新）

### Oracle VM Bots
| Bot | Username | Token | Agent | Model |
|-----|----------|-------|-------|-------|
| Last Keeper | @Zeabur01Bot | `8755148273:AAEM7NYxmS1SSrSKSQy5XZfIVFOjiDkfx_s` | main | minimax/MiniMax-M2.7 |
| Hermes | @N8NKIMIBOT | `8169863932:AAH2h-W3EzX9SxIgii6zZjrHX3reWKXwFjg` | hermes | minimax/MiniMax-M2.7 |

### Zeabur VM Bots
| Bot | Username | Token | Agent | Model |
|-----|----------|-------|-------|-------|
| Arslansky | @arslanskybot | `8688406477:AAFAvifFZqifVZ2H_V9cBqB_E3vEh-o` | arslansky-agent | minimax/MiniMax-M2.7 |
| Know2Learn | @Know2learn_bot | `8401590390:AAHAl6jUwUqY-E6g7I1mqD1yM4-Nq-jqzc` | minimax-agent | xiongmao/熊猫-按量-gpt-5.6-terra |
| Janzai | @Janzaibot | `8302835438:AAG-fUToH-V8y_Z6gR3zL0D5nQ9-TPepj8` | janzaibot-agent | waninter/gpt-5.6-terra |
| ZO | @ZO_001_bot | `8205470881:AAG9eXIKbxT-G4n_H5jK1C7oJ2-RvmxmgE` | ds-agent | yuanyuaicloud/deepseek-v4-pro |
| DS | @DS_26bot | `8523709022:AAGSZ2EblWuY_K5i_L6kM9E8pS1-Vdf2M` | ds-agent | yuanyuaicloud/deepseek-v4-pro |

## Model Providers

| Provider | Endpoint | API Format | Models |
|----------|----------|------------|--------|
| minimax | `https://api.minimax.io/anthropic` | anthropic-messages | MiniMax-M2.7, MiniMax-M3 |
| yuanyuaicloud | `https://yuanyuaicloud.cn/v1` | openai-completions | deepseek-v4-pro, deepseek-v4-flash |
| kimi | `https://api.kimi.com/coding/v1` | openai-completions | kimi-for-coding, k3, k3-256k |
| xiongmao | `https://api520.pro/v1` | openai-completions | 熊猫-按量-gpt-5.6-terra |
| waninter | `https://api-cn.waninter.com/v1` | openai-completions | gpt-5.6-terra |
| deepseek-official | `https://api.deepseek.com/v1` | openai-completions | deepseek-v4-pro |

## API Keys

### Waninter (Janzaibot)
- **Full key:** `sk-ac69b8cc3152520f483109cfe677abeda86f47a89d003d0119d7d21ba8ece37a` (67 chars)
- **Endpoint:** `https://api-cn.waninter.com`

## ⚠️ SSH Config 注意事項

**千祈唔好喺 `~/.ssh/config` 用 `BatchMode yes` 全域設定！**

Zeabur VM 係密碼登入，沒有 SSH key。`BatchMode yes` 會阻止密碼認證。

正確做法：每個 host 獨立設定。

## Tools Die Bug（未完全解決）

**問題現象：**
- Exec tool 行 1-3 個 command 後，所有 tools 停止返回 output
- Telegram inbound/outbound 仍然正常
- Gateway restart 只能短暫恢復

**懷疑原因：** OpenClaw exec tool PTY state machine bug

## 教訓

1. **Telegram 屏蔽 API keys** — key 被截斷成 `sk-xxx...xxx`，寫入 config 前必須取得完整 key
2. **Tools die 問題** — 可能需要 VM reboot 才能完全解決
3. **每次更新 config 前** — 先讀取確認，避免覆寫錯誤
