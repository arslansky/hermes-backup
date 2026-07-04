# 🧠 Shared Skills & Knowledge

Shared workflows, skills, and knowledge files for all VMs.

## Structure

```
skills/
├── README.md                 ← 呢個檔案
├── multi-vm-setup.md         ← Multi-VM 架構設計 (from OpenClaw)
├── hermes-maintenance.md     ← Hermes maintenance workflow
├── vm-clone-hygiene.md       ← VM clone cleanup procedure
├── mingpao-daily-cron.md     ← Mingpao daily cron setup
└── ...
```

## How it works

Each VM can git pull this repo to get the latest skills/knowledge:

```bash
cd /home/ubuntu/scripts  # or ~/hermes-backup
git pull
```

For Hermes: skills are loaded via `skill_view()` tool.
For OpenClaw: skills are read as reference files.

## Related

- `/home/ubuntu/scripts/` — shared scripts directory on each VM
- `/home/ubuntu/.openclaw/workspace/` — OpenClaw workspace on each VM
- `inventory.yml` — VM inventory with roles and SSH info

## VM Inventory

| VM | Hostname | IP | Role | Agent |
|---|---|---|---|---|
| Zeabur-01 | VM-17-222-ubuntu | 43.156.247.30 | OpenClaw main, TG, WhatsApp | OpenClaw |
| Oracle-01 | instance-20260703-2144 | 129.80.234.56 | Hermes, Discord, LLM | Hermes + OpenClaw |
| VM-3 | TBD | TBD | Future | TBD |