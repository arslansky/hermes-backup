#!/bin/bash
# backup-config.sh — Backup local Hermes + OpenClaw config into hermes-backup/config/<vm-name>/
# Usage: bash backup-config.sh ["description"]
# Pushes config snapshot to GitHub (hermes-backup repo)

set -euo pipefail

DESCRIPTION="${1:-scheduled config backup}"
HOSTNAME=$(hostname -s)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Resolve the hermes-backup repo directory
if [ -d "$HOME/hermes-backup/.git" ]; then
    REPO_DIR="$HOME/hermes-backup"
elif [ -d "$HOME/scripts/.git" ] && [ -L "$HOME/scripts" ]; then
    REPO_DIR=$(readlink -f "$HOME/scripts")
else
    echo "ERROR: hermes-backup repo not found. Run bootstrap first." >&2
    exit 1
fi

CONFIG_DIR="$REPO_DIR/config/$HOSTNAME"
OUTPUT_DIR="$REPO_DIR/config"
METADATA_FILE="$OUTPUT_DIR/.metadata.json"

mkdir -p "$CONFIG_DIR"/{hermes,openclaw,systemd}

echo "=== Config Backup Started ==="
echo "VM: $HOSTNAME"
echo "Repo: $REPO_DIR"
echo "Description: $DESCRIPTION"

# --- Backup Hermes config ---
backup_hermes() {
    echo "[1/3] Backing up Hermes config..."
    [ -f "$HOME/.hermes/config.yaml" ] && cp -f "$HOME/.hermes/config.yaml" "$CONFIG_DIR/hermes/config.yaml" && echo "  ✓ config.yaml"
    [ -f "$HOME/.hermes/auth.json" ] && cp -f "$HOME/.hermes/auth.json" "$CONFIG_DIR/hermes/auth.json" && echo "  ✓ auth.json"
    [ -f "$HOME/.hermes/.env.example" ] && cp -f "$HOME/.hermes/.env.example" "$CONFIG_DIR/hermes/.env.example" && echo "  ✓ .env.example"

    # Do NOT backup .env (secrets)
    if [ -f "$HOME/.hermes/.env" ]; then
        echo "  ⚠ .env skipped (contains secrets)"
    fi
}

# --- Backup OpenClaw config ---
backup_openclaw() {
    echo "[2/3] Backing up OpenClaw config..."
    [ -f "$HOME/.openclaw/openclaw.json" ] && cp -f "$HOME/.openclaw/openclaw.json" "$CONFIG_DIR/openclaw/openclaw.json" && echo "  ✓ openclaw.json"
    [ -f "$HOME/.openclaw/workspace/inventory.yml" ] && cp -f "$HOME/.openclaw/workspace/inventory.yml" "$CONFIG_DIR/openclaw/inventory.yml" && echo "  ✓ inventory.yml"

    # Backup SOUL.md, AGENTS.md, MEMORY.md if present
    for f in SOUL.md AGENTS.md MEMORY.md USER.md; do
        [ -f "$HOME/.openclaw/workspace/$f" ] && cp -f "$HOME/.openclaw/workspace/$f" "$CONFIG_DIR/openclaw/$f" && echo "  ✓ $f"
    done
}

# --- Backup systemd user services ---
backup_systemd() {
    echo "[3/3] Backing up systemd user services..."
    local sysd="$HOME/.config/systemd/user"
    if [ -d "$sysd" ]; then
        for svc in hermes-gateway.service openclaw-gateway.service hermes-gateway-restart.service; do
            [ -f "$sysd/$svc" ] && cp -f "$sysd/$svc" "$CONFIG_DIR/systemd/" && echo "  ✓ $svc"
        done
    fi
    echo "  done"
}

# --- Write metadata ---
write_metadata() {
    cat > "$METADATA_FILE" << EOF
{
  "version": "2.1",
  "created_at": "$(date -Iseconds)",
  "timestamp": "$TIMESTAMP",
  "hostname": "$HOSTNAME",
  "description": "$DESCRIPTION",
  "backup_dir": "$CONFIG_DIR"
}
EOF
}

# --- Update ~/.secure/.env snapshot (local only) ---
update_secure_snapshot() {
    echo "[extra] Updating ~/.secure/.env snapshot..."
    mkdir -p "$HOME/.secure"
    [ -f "$HOME/.hermes/.env" ] && cp -f "$HOME/.hermes/.env" "$HOME/.secure/.env"

    # Regenerate manifest
    if command -v sha256sum >/dev/null 2>&1; then
        cat > "$HOME/.secure/manifest.json" << MANIFEST
{
  "version": "1.0",
  "created_at": "$(date -Iseconds)",
  "hostname": "$HOSTNAME",
  "files": {
    ".env": "$(sha256sum "$HOME/.secure/.env" | awk '{print $1}')"
  }
}
MANIFEST
    fi
    echo "  ✓ ~/.secure/.env snapshot updated"
}

backup_hermes
backup_openclaw
backup_systemd
write_metadata
update_secure_snapshot

# --- Git commit and push ---
cd "$REPO_DIR"
if [ -z "$(git status --short)" ]; then
    echo ""
    echo "=== No changes to commit ==="
    exit 0
fi

git add -A

git commit -m "config: $DESCRIPTION for $HOSTNAME ($TIMESTAMP)" > /dev/null 2>&1

GITHUB_TOKEN=$(grep '^GITHUB_TOKEN=' "$HOME/.hermes/.env" 2>/dev/null | cut -d= -f2-)
if [ -n "$GITHUB_TOKEN" ]; then
    git remote set-url origin "https://${GITHUB_TOKEN}@github.com/arslansky/hermes-backup.git" > /dev/null 2>&1
fi

git push origin main > /dev/null 2>&1

echo ""
echo "=== Config Backup Complete ==="
echo "Config dir: $CONFIG_DIR"
echo "Git commit: $TIMESTAMP"

# EOF
