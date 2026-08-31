# TOOLS.md - Local Cheat Sheet

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

---

## 🌐 Network / Proxy

### 預設 Proxy（公開，用完即 unset）
- **Host**: `47.76.184.24`
- **Port**: `11908`
- **User**: `cwb`
- **Pass**: `rvn`
- **到期**: `2026-09-01 22:11:30`
- **Protocol**: HTTP + SOCKS5 都 work
- **⚠️ 唔好用嚟過真密碼 / 真 API key**（public proxy 唔知 operator）
- **✅ OK 嚟 download public content**（YouTube audio、wiki、github release）
- **⚠️ 實測 (2026-08-02)**: 通 internet (curl 200) 但 **YouTube 仍 bot-block**（datacenter IP，需 cookies）— L#23
- **舊 proxy**: `s4.hk38.ltip.xyz:20105` (utl/mhd) 已死 (connection refused, 2026-08-02 起) — 唔再用

### Set / Unset
```bash
# Set
export http_proxy="http://cwb:***@47.76.184.24:11908"
export https_proxy="http://cwb:***@47.76.184.24:11908"
export all_proxy="socks5://cwb:***@47.76.184.24:11908"

# Unset
unset http_proxy https_proxy all_proxy
```

### yt-dlp 用 proxy

⚠️ **HTTPS over HTTP proxy 會撞 407**：public proxy 唔 support HTTPS CONNECT method

```bash
# HTTP proxy 過一般 webpage OK，但 yt-dlp 過 YouTube 會 407
yt-dlp --proxy "http://cwb:***@47.76.184.24:11908" -f "bestaudio[ext=m4a]" "URL"
# ❌ Tunnel connection failed: 407 Proxy Authentication Required

# ✅ Workaround：改用 SOCKS5（HTTPS over SOCKS 唔需要 CONNECT）
yt-dlp --proxy "socks5://cwb:rvn@47.76.184.24:11908" -f "bestaudio[ext=m4a]" "URL"
```

**Default 順序**：HTTP 試一次 → fail 即 fallback SOCKS5

### curl 用 proxy
```bash
curl -x "http://cwb:***@47.76.184.24:11908" https://api.ipify.org
```

---

## 🎙️ YouTube Transcript Pipeline（已驗證 work，2026-08-25 更新）

### 🔑 YouTube 登入 + Cookies（2026-08-25 新增）

**問題**：Cloud VM IP 被 YouTube bot-block，cookies 必須先 login 先 download 到。

### 一行 command（推薦用 cookies + deno 版）
```bash
export PATH="/home/ubuntu/.deno/bin:$PATH" && \
yt-dlp --cookies /home/ubuntu/scripts/yt-pipeline/cookies.txt \
  -f "bestaudio[ext=m4a]" -o "/tmp/audio.%(ext)s" "URL" && \
ffmpeg -i /tmp/audio.m4a -ar 16000 -ac 1 -c:a pcm_s16le /tmp/audio.wav -y && \
whisper /tmp/audio.wav --model base --language Chinese --output_format srt --output_dir /tmp/subs
```

### 性能（部機 2 cores + 7.4GB RAM）
- 8 min video download: ~10s
- ffmpeg convert: ~5s
- whisper base STT: ~123s
- whisper small STT: ~7+ min（**唔好用**呢部機行 small）
- whisper medium STT: 估 15+ min（**唔好用**）

### 模型 cache
- `~/.cache/whisper/base.pt` 139MB
- `~/.cache/whisper/small.pt` 462MB
- base 已下載，立即可用

---

## 🔑 Google API Status

### 已 paste 過 chat log（要 revoke）
- `AIzaSy[REDACTED]`
- YouTube Data API: ✓ work
- Gemini API: ✗ `API_KEY_SERVICE_BLOCKED`

### GCP Project
- ID: `906487414422`
- Enable Gemini API: `https://console.developers.google.com/apis/api/generativelanguage.googleapis.com/overview?project=906487414422`

### YouTube Data API 範本
```bash
API_KEY="<新 key>"
# Video metadata
curl "https://www.googleapis.com/youtube/v3/videos?part=snippet&id=VIDEO_ID&key=***}"
# Captions list
curl "https://www.googleapis.com/youtube/v3/captions?part=snippet&videoId=VIDEO_ID&key=***}"
```

---

## 💻 部機 Specs
- **Hostname**: `VM-17-222-ubuntu`（**cloud VM = YouTube block**）
- **Public IP**: `183.60.82.98`（中國雲）
- **Private IP**: `10.3.17.222`
- **RAM**: 7.4GB
- **CPU**: 2 cores
- **Disk**: 21GB available
- **OS**: Ubuntu 22.04 (kernel 6.8.0-51-generic)
- **特殊**: k3s 已裝

---

## 🛠 Installed tools
- `yt-dlp 2026.06.09` ✓
- `youtube-transcript-api` ✓（但 block 用）
- `whisper` (openai-whisper) ✓
- `ffmpeg 6.1.1` ✓
- `firecrawl` ✓
- `web_search` / `web_fetch` / `firecrawl_*` tools ✓

---

## 📂 重要文件
- `~/repos/openhuman/` — OpenHuman clone（125MB）
- `~/MEMORY.md` — long-term memory（永久）
- `~/memory/YYYY-MM-DD.md` — 今日 raw log
- `~/TOOLS.md` — 呢個 file

---

## 🦞 重要教訓（唔好再犯）

1. **先 recall tool / proxy / API key** — 唔好由零開始
2. **唔好「冇就 over」** — 試 4-5 個 method
3. **唔好交波畀用戶** — recall + prompt
4. **每次 session 開頭 read MEMORY.md** — 唔好由零開始
5. **API key 一 paste 就當 exposed** — 提示 user revoke
6. **🔴 嚴禁 truncated fake key**（用戶 2026-07-09 #7176 明令）：
   - 凡係 `xxx…yyy` 形式、`…` 係 unicode 字符（U+2026）或 heredoc 被 truncate、shell filter 補字符號嘅 key，都屬 truncated
   - 遇上 truncated key → **重搵完整 key**，**唔好將就**
   - **冇完整 key → 直接報錯、唔好誤判 backend 壞 / endpoint 死**
   - 浪費 call 浪費 token 之餘，仲會出錯結論（例如誤判 API key revoked）


## 📤 Outbound Protocol (Telegram)

**⚠️ OpenClaw `message` tool has a confirmed bug**: `action=send` with `file=` returns `ok: true` but the file is NOT actually delivered. Always use `curl` direct to Bot API instead.**

### Bot Token
- Read from: `~/.openclaw/credentials/telegram-know2learn-token.txt` (chmod 600)
- NEVER pass token as CLI arg, NEVER paste in chat
- Bot: `@know2learn_bot` (account: `know2learn`)

### Send File (confirmed working)
```bash
~/.openclaw/scripts/tg-send-doc.sh <file_path> <caption> [chat_id]
```
Example:
```bash
~/.openclaw/scripts/tg-send-doc.sh /path/to/file.pdf "PDF summary" 160408068
```

### Manual curl (without script)
```bash
TOKEN=$(cat ~/.openclaw/credentials/telegram-know2learn-token.txt)
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendDocument" \
  -F "chat_id=160408068" \
  -F "document=@/path/to/file.pdf" \
  -F "caption=File name"
```

**When outbound TG send is allowed:**
- User explicitly requests file send to a specific Telegram chat (DM/group/channel) for a stated purpose.
- Token read from credentials file, never from CLI args or pasted in chat.
- Audit log entry written before send (chat_id, file_path, byte_count, timestamp).

**When outbound TG send is NOT allowed (hard-block):**
- Sending agent-generated self-introductions / agent self-representation without explicit approval.
- Sending to a target the user has not verified (unknown chat_id, unverified group).
- Sending using a token that has been pasted in chat logs / Telegram server-side retention.
- Sending in response to a request that conflicts with any SOUL.md Core Truth / Boundary.

If any condition is unmet → refuse and ask user to supply the missing piece.


---

## 📧 Zoho Email (kimbot247@zohomail.com)

### SMTP Config
- **Server**: `smtp.zoho.com:465` (SSL)
- **Username**: `kimbot247@zohomail.com`
- **From**: `KimBot <kimbot247@zohomail.com>`

### Usage
Use via skill `zoho-email-send`. Python SMTP template available in skill.
Credentials stored in skill definition. DO NOT paste in chat.

### Safety
1. Never paste password in chat — if exposed, request new app password from Zoho
2. Ask user before sending to unverified recipients
3. Ops log entry before every send (to, subject, byte_count)


## 🤖 @Know2learn_bot YouTube → 中文 PDF  workflow

When user sends a YouTube link to `@Know2learn_bot` and asks for a Chinese summary PDF, use this exact script instead of OpenClaw `message(action="send", file=...)` (which has a confirmed send-file bug).

### One-liner
```bash
~/.openclaw/workspace/minimax-agent/scripts/yt_summary_to_tg.sh "<youtube_url>" [chat_id] [whisper_model]
```

### Defaults
- chat_id: `160408068` (Arslan DM)
- whisper_model: `tiny`

### Example
```bash
~/.openclaw/workspace/minimax-agent/scripts/yt_summary_to_tg.sh "https://youtu.be/fQbSQCjyI38"
```

### What it does
1. Extracts video ID from any YouTube URL format.
2. Tries `yt-dlp` subtitles first (Path A); if none exist, falls back to Whisper STT (Path B).
3. Builds a structured Chinese bullet summary from the transcript.
4. Renders a PDF with `render_summary_pdf.py`.
5. Sends the PDF via `tg-send-doc.sh` directly to Telegram Bot API.

### Agent handling rule
When the user sends a YouTube link to this bot, **run this script directly** and wait for `ok`. Do not attempt the pipeline steps manually.

### Important
- Do NOT use `message(action="send", file=...)` for PDF delivery.
- The script already handles the file send; only reply with a short confirmation text AFTER it reports `ok`.
- If the user did not explicitly mention "PDF" but only sent a link, confirm intent first.
