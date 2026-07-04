# 🔧 Hermes + OpenClaw Multi-VM Setup Guide

Complete guide for setting up a new VM with Hermes Agent and/or OpenClaw, connected to the shared multi-VM infrastructure.

## Overview

Two agents, two VMs, one shared scripts directory via GitHub:

```
GitHub (arslansky/hermes-backup)  ← Single source of truth
    │
    ├── Oracle-01 (Hermes + OpenClaw)
    │   /home/opc/scripts/  → git repo
    │   Symlinks → ~/.hermes/scripts/ + ~/.openclaw/workspace/ops/scripts/
    │
    └── Zeabur-01 (OpenClaw only)
        /home/ubuntu/scripts/  → git repo
        Symlinks → ~/.openclaw/workspace/ops/scripts/
```

Prerequisites:
- GitHub token with repo scope (stored as `GITHUB_TOKEN` in `.env`)
- SSH password for Zeabur VM (if connecting cross-VM)
- Git installed on all VMs

---

## 1. Initial Setup on a New VM

### 1.1 Clone the shared repo

```bash
cd /home/opc  # or /home/ubuntu depending on OS
git clone https://github.com/arslansky/hermes-backup.git scripts
```

### 1.2 Create symlinks for Hermes (if Hermes is installed)

```bash
# Remove default scripts dirs and replace with symlinks
rm -rf ~/.hermes/scripts
ln -s /home/opc/scripts ~/.hermes/scripts
```

### 1.3 Create symlinks for OpenClaw (if OpenClaw is installed)

```bash
# OpenClaw ops scripts
cd ~/.openclaw/workspace/ops/scripts
for f in /home/opc/scripts/*.py /home/opc/scripts/*.sh /home/opc/scripts/*.js; do
  basename=$(basename "$f")
  [ -f "$basename" ] && rm "$basename"
  ln -s "$f" "$basename"
done
```

### 1.4 Set up daily auto-update

**For Hermes (via hermes cron):**
```bash
hermes cron create \
  --name "Daily scripts sync from GitHub" \
  --schedule "0 9 * * *" \
  --no-agent \
  --script "sync-scripts.sh" \
  --deliver local
```

**For systems without Hermes (via system crontab):**
```bash
(crontab -l 2>/dev/null | grep -v "sync-scripts"; echo "0 9 * * * cd /home/ubuntu/scripts && git pull -q") | crontab -
```

### 1.5 Create the sync script

Save as `~/.hermes/scripts/sync-scripts.sh` (or wherever your agent reads scripts):

```bash
#!/bin/bash
cd /home/opc/scripts || exit 1
git pull -q origin main 2>/dev/null || true
```

Make it executable:
```bash
chmod +x ~/.hermes/scripts/sync-scripts.sh
```

---

## 2. How Script Sharing Works

### Architecture

```
/home/opc/scripts/          ← REAL files (git repo)
    ↑ symlinks
    ├── ~/.hermes/scripts/          ← Hermes reads from here
    └── ~/.openclaw/workspace/ops/scripts/  ← OpenClaw reads from here
```

- **Symlinks, not copies** — edit once, both agents see changes immediately
- **Git is the transport** — push to GitHub, pull on each VM
- **Auto-sync daily** — each VM pulls at 09:00 UTC

### Security Notes

- Deleting a symlink (`rm ~/.hermes/scripts/script.py`) only removes the link, NOT the real file
- Deleting the real file (`rm /home/opc/scripts/script.py`) breaks both agents — be careful
- Secrets (`.env`, API keys) are NEVER stored in this repo
- Each VM maintains its own `.env` locally

---

## 3. VM Inventory Reference

| VM | Hostname | IP | OS | User | Agent | Auth |
|---|---|---|---|---|---|---|
| Zeabur-01 | VM-17-222-ubuntu | 43.156.247.30 | Ubuntu x86_64 | ubuntu | OpenClaw | Password |
| Oracle-01 | instance-20260703-2144 | 129.80.234.56 | OL9 aarch64 | opc | Hermes + OpenClaw | SSH key |

### Roles

- `openclaw-main` — Primary OpenClaw agent
- `hermes` — Hermes Gateway
- `telegram` — Telegram bot
- `whatsapp` — WhatsApp bot
- `discord` — Discord bot
- `llm-gateway` — LLM API endpoint
- `backup` — Backup target
- `primary` — Highest backup priority

---

## 4. SSH Cross-Connection

### Oracle → Zeabur

```bash
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no ubuntu@43.156.247.30
```

Note: `sshpass` may need to be installed first:
```bash
sudo dnf install -y sshpass    # on Oracle Linux
sudo apt install -y sshpass    # on Ubuntu
```

### Recommended: Set up key-based auth for Zeabur

```bash
ssh-keygen -t ed25519 -f ~/.ssh/zeabur -N ""
ssh-copy-id -i ~/.ssh/zeabur.pub ubuntu@43.156.247.30
```

Then add to `~/.ssh/config`:
```
Host zeabur
    HostName 43.156.247.30
    User ubuntu
    IdentityFile ~/.ssh/zeabur
```

Then simply: `ssh zeabur`

---

## 5. Adding a Third VM (VM-3)

1. Choose a name and role (e.g. `cursor-dev`)
2. Add to `inventory.yml` in the shared repo
3. Follow steps in Section 1 on the new VM
4. If it needs an agent, install Hermes or OpenClaw first
5. Set up SSH keys between VMs if cross-communication is needed

---

## 6. Disaster Recovery

If any VM dies:

```bash
# On a fresh VM
git clone https://github.com/arslansky/hermes-backup.git /home/opc/scripts
# Then follow steps 1.2-1.5 above
# Manually copy .env from backup
```

**Remember:** Secrets are NOT in the repo. You must restore `.env` manually.

---

## 7. File Inventory

### Scripts (29 files in `/home/opc/scripts/`)

| File | Purpose | Used By |
|---|---|---|
| `mingpao_scraper.py` | Mingpao news scraper | Hermes cron |
| `run_mingpao_daily.sh` | Cron wrapper | Hermes cron |
| `hermes_overview.py` | Hermes health overview | Hermes |
| `article_analyzer.py` | Article analysis | OpenClaw |
| `news_digest.py` | News digest | OpenClaw |
| `fable_reasoner.py` | Fable reasoning | OpenClaw |
| `tg_bot_zeabur01*.py` | Telegram bots | Zeabur |
| `test_ttk.py` | TTK API test | OpenClaw |
| `sync-vm.sh` | Multi-VM sync | Both |
| `backup.sh` | Workspace backup | Both |
| `restore.sh` | Workspace restore | Both |
| `bootstrap.sh` | Initial setup | Both |
| `sync-scripts.sh` | Daily git pull | Hermes cron |
| `analyze2.py` | Image/MD analyzer | OpenClaw |
| `analyze_image.py` | Image analysis | OpenClaw |
| `analyze_images.py` | Batch image analysis | OpenClaw |
| `hktmall_generator.py` | Content generator | OpenClaw |
| `minimax_demo.py` | MiniMax API demo | OpenClaw |
| `minimax_multidim_demo.py` | MiniMax demo | OpenClaw |
| `multillm_concept_demo.py` | Multi-LLM demo | OpenClaw |
| `reflection_demo.py` | Reflection demo | OpenClaw |
| `news-to-pdf.js` | News to PDF | OpenClaw |
| `moomoo-scrape.js` | Moomoo scraper | OpenClaw |
| `notegpt_extract.js` | NoteGPT extract | OpenClaw |
| `ytpdf.js` | YouTube + PDF | OpenClaw |
| `weekly-skills-backup.sh` | Skills backup | OpenClaw |

### System Services

| Service | VM | Type |
|---|---|---|
| Hermes Gateway | Oracle-01 | systemd user service |
| OpenClaw Gateway | Oracle-01 | systemd user service |
| OpenClaw Gateway | Zeabur-01 | systemd user service |
| OpenClaw Watchdog | Oracle-01 | systemd user service |

### Cron Jobs

| Job | Schedule | VM |
|---|---|---|
| Mingpao daily digest | 06:15 UTC | Oracle-01 (Hermes cron) |
| Scripts git pull | 09:00 UTC | Oracle-01 (Hermes cron) |
| Scripts git pull | 09:00 UTC | Zeabur-01 (system crontab) |
| Skills git pull | 01:00 UTC | Zeabur-01 (system crontab) |

---

## 8. Key Commands Reference

```bash
# Git operations
cd /home/opc/scripts && git pull          # Manual sync
cd /home/opc/scripts && git push          # Push local changes

# SSH to other VM
ssh ubuntu@43.156.247.30                  # To Zeabur

# Check cron jobs
hermes cron list                          # Hermes cron
ssh ubuntu@43.156.247.30 crontab -l       # Zeabur crontab

# Check scripts symlinks
ls -la ~/.hermes/scripts/
ls -la ~/.openclaw/workspace/ops/scripts/
```

---

_Generated: 2026-07-04 | Repo: github.com/arslansky/hermes-backup_