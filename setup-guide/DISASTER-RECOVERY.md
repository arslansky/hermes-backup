# Disaster Recovery Runbook

This document describes how to recover the Hermes + OpenClaw multi-VM setup after a VM failure, accidental deletion, or complete rebuild.

## 1. Overview

- **Single source of truth**: GitHub repo `arslansky/hermes-backup`
- **Shared scripts**: `hermes-backup/scripts/`
- **Config backups**: `hermes-backup/config/<vm-hostname>/`
- **Secrets**: `~/.secure/` (local only, not in git)
- **VM inventory**: `inventory.yml`

## 2. Supported Failure Scenarios

| Scenario | Recovery Method | Data Lost |
|---|---|---|
| Hermes/OpenClaw config corrupted | `restore-config.sh` | None if backup exists |
| `.hermes/.env` deleted | Copy from `~/.secure/.env` | None if backup exists |
| Scripts out of sync | `sync-all-vms.sh sync-all` | None |
| Entire VM lost | `bootstrap.sh` + restore secrets + `restore-config.sh` | Runtime data only |
| GitHub repo lost | Re-clone from local `hermes-backup` on healthy VM | None |

## 3. Quick Recovery Commands

### 3.1 Config only is corrupted

On the affected VM:

```bash
# Preview what will be restored
bash ~/hermes-backup/scripts/restore-config.sh --dry-run

# Actually restore
bash ~/hermes-backup/scripts/restore-config.sh

# Restart services
systemctl --user restart hermes-gateway.service
systemctl --user restart openclaw-gateway.service
```

### 3.2 `.env` is missing or wrong

```bash
# Option A: restore from local secure backup
cp ~/.secure/.env ~/.hermes/.env

# Option B: restore from individual service key files
cat ~/.secure/service-keys/*.txt > ~/.hermes/.env

# Then restart
cd ~/.hermes
# add any missing newlines between concatenated keys
systemctl --user restart hermes-gateway.service
```

### 3.3 Entire VM rebuild

1. **Create new VM**, ensure SSH access and install `git`.
2. **Clone repo** and run bootstrap:

```bash
cd ~
git clone https://github.com/arslansky/hermes-backup.git
bash hermes-backup/scripts/bootstrap.sh both
```

3. **Restore secrets** from another VM or your local backup:

```bash
# From another machine
scp -r user@another-vm:~/.secure ~/.secure

# Or copy ~/.secure/.env to ~/.hermes/.env
cp ~/.secure/.env ~/.hermes/.env
```

4. **Restore config** (optional, if backup exists for this hostname):

```bash
bash ~/hermes-backup/scripts/restore-config.sh
```

5. **Start services**:

```bash
systemctl --user daemon-reload
systemctl --user start hermes-gateway.service
systemctl --user start openclaw-gateway.service
```

6. **Verify**:

```bash
bash ~/hermes-backup/scripts/health-check.sh
bash ~/hermes-backup/scripts/check-secrets.sh
```

## 4. Recovery Checklist

- [ ] New VM has network access and `git` installed
- [ ] `~/.ssh/zeabur_key` (or equivalent) is available for cross-VM sync
- [ ] `~/.hermes/.env` restored with all API keys
- [ ] `~/.hermes/config.yaml` restored
- [ ] `~/.openclaw/openclaw.json` restored
- [ ] `~/.openclaw/workspace/inventory.yml` restored
- [ ] Systemd services reloaded and started
- [ ] Health check passes
- [ ] Secrets check passes
- [ ] Daily cron jobs re-created if needed

## 5. Secrets Recovery Priority

If `~/.secure/` is also lost, regenerate keys in this order:

| Priority | Key | Where to Regenerate |
|---|---|---|
| 1 | `GITHUB_TOKEN` | https://github.com/settings/tokens |
| 2 | `TELEGRAM_BOT_TOKEN` | https://t.me/BotFather |
| 3 | `MINIMAX_API_KEY` | https://www.minimaxi.com/ |
| 4 | `KIMI_API_KEY` | https://platform.moonshot.cn/ |
| 5 | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |

After regenerating, update `~/.hermes/.env` and run `check-secrets.sh`.

## 6. Cross-VM Sync

After recovery, bring all VMs back to the same state:

```bash
bash ~/hermes-backup/scripts/sync-all-vms.sh status
bash ~/hermes-backup/scripts/sync-all-vms.sh sync-all
```

## 7. Contact / Escalation

If recovery fails and this runbook does not help:

- Check `~/.hermes/cron/output/` for latest logs
- Check `~/.secure/README.md` for secret locations
- Verify GitHub repo `arslansky/hermes-backup` is accessible
- Re-run `bootstrap.sh` from a fresh VM if current VM is unrecoverable

Last updated: 2026-07-04
