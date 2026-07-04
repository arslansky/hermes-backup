# Multi-VM Architecture

## Three VM Setup

```
Zeabur-01 (43.156.247.30)
  ├── OpenClaw main agent
  ├── Telegram bot
  ├── WhatsApp bot
  └── Primary (backup priority 1)
        │
        │ SSH + GitHub
        ▼
Oracle-01 (129.80.234.56)
  ├── Hermes Agent
  ├── OpenClaw (secondary)
  ├── Discord bot
  ├── LLM Gateway
  └── Secondary backup (priority 2)
        │
        │ GitHub
        ▼
GitHub (arslansky/hermes-backup)
  └── Single source of truth for:
      ├── scripts/ (shared)
      ├── skills/ (shared knowledge)
      └── config (templates only, no secrets)
```

## Shared Resources

| Resource | Location | Sync Method |
|---|---|---|
| Scripts | `/home/opc/scripts/` (each VM) | `git pull` from GitHub |
| Skills | GitHub `skills/` directory | `git pull` |
| Secrets (.env) | Local on each VM | Manual (NOT in GitHub) |

## SSH Connectivity

- Oracle-01 → Zeabur-01: ✅ (sshpass with password)
- Both → GitHub: ✅ (HTTPS with token)

## Daily Auto-Update

Each VM runs a cron job to `git pull` the shared repo daily at 09:00 UTC.

## Disaster Recovery

If any VM goes down:
1. Clone from GitHub to a new VM
2. Copy `.env` manually (secrets never in GitHub)
3. Setup symlinks to `/home/opc/scripts/`