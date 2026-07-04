# 🗂️ Hermes-Backup Repository

Shared configuration, scripts, skills, and setup guides for the multi-VM Hermes + OpenClaw infrastructure.

## Repository Structure

```
hermes-backup/
├── README.md                              ← This file
├── inventory.yml                          ← All VM inventory (3 VMs)
├── scripts/                               ← Shared executable scripts (symlinked on each VM)
│   ├── mingpao_scraper.py
│   ├── tg_bot_zeabur01.py
│   ├── article_analyzer.py
│   └── ...
├── skills/                                ← Shared skills and knowledge files
│   ├── README.md
│   └── multi-vm-setup.md
├── setup-guide/                           ← Setup and onboarding documentation
│   └── HERMES-OPENCLAW-MULTI-VM-SETUP.md
└── archive/                               ← Old backups and historical files
    └── README.md
```

## VM Inventory

| VM | Host | User | Port | Auth | Primary Role | Scripts Directory |
|---|---|---|---|---|---|---|
| **Oracle-01** | 161.118.247.199 | opc | 22 | `~/.ssh/zeabur_key` | Hermes + OpenClaw | `/home/opc/hermes-backup/scripts/` |
| **Zeabur-01** | 43.156.247.30 | ubuntu | 22 | Password | OpenClaw main | `/home/ubuntu/hermes-backup/scripts/` |
| **ZO-01** | ts8.zocomputer.io | root | 10661 | `~/.ssh/zeabur_key` | Zo Computer VM | `/root/hermes-backup/scripts/` |

## Quick Start

On a new VM:
```bash
# Clone the repo into ~/hermes-backup (NOT ~/scripts)
cd /home/opc   # or /home/ubuntu or /root
git clone https://github.com/arslansky/hermes-backup.git

# Symlink scripts to the agent's expected location
ln -s /home/opc/hermes-backup/scripts ~/.openclaw/workspace/ops/scripts
# For Hermes:
ln -s /home/opc/hermes-backup/scripts ~/.hermes/scripts
```

## Important Notes
- **Active scripts live in `scripts/`**. Do not leave executable scripts at the repository root.
- **Secrets are NOT stored in this repository.** Each VM maintains its own `.env` file.
- **Old backups go in `archive/`**. See `archive/README.md`.

---

_Generated: 2026-07-05 | Maintained by: arslansky_
