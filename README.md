# GitHub Backup — Hermes Agent + OpenClaw

| VM | Hostname | IP | Agent | Role |
|---|---|---|---|---|
| **Zeabur-01** | VM-17-222-ubuntu | 43.156.247.30 | OpenClaw | Telegram, WhatsApp, Main |
| **Oracle-01** | instance-20260703-2144 | 129.80.234.56 | Hermes + OpenClaw | Discord, LLM, Backup |

## Structure

```
/
├── scripts/           ← Shared scripts (symlinked on each VM)
│   ├── mingpao_scraper.py
│   ├── run_mingpao_daily.sh
│   ├── hermes_overview.py
│   ├── article_analyzer.py
│   ├── news_digest.py
│   ├── tg_bot_zeabur01*.py
│   ├── fable_reasoner.py
│   └── ... (29 files)
├── skills/            ← Shared skills documentation
│   ├── README.md
│   └── multi-vm-setup.md
├── cron-output/       ← Historical cron job outputs
└── README.md          ← This file
```

## How Scripts Sync Works

Two agents (Hermes + OpenClaw) on two VMs share the same scripts via GitHub:

```
GitHub (arslansky/hermes-backup)
    │ git push / git pull
    ├── Oracle-01  →  /home/opc/scripts/     (git repo, symlinked to Hermes & OpenClaw)
    └── Zeabur-01  →  /home/ubuntu/scripts/  (git repo, symlinked to OpenClaw)
```

Each VM has a daily cron job at 09:00 UTC that runs `git pull` to stay in sync.

## Secrets

- `.env` files (API keys, tokens) are **NOT** in this repo
- Each VM maintains its own `.env` locally
- This repo only has `.env.example` templates (to be added)

## Auto-Update Cron

| VM | Schedule | Method |
|---|---|---|
| Oracle-01 | 09:00 UTC daily | Hermes cron (no_agent) |
| Zeabur-01 | 09:00 UTC daily | system crontab |