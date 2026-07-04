#!/bin/bash
# bootstrap.sh — 新 VM 一鍵 setup (Hermes + OpenClaw multi-VM)
# 用途：全新 VM 上快速建立 hermes-backup repo、symlinks、config
# Usage: bash bootstrap.sh [hermes|openclaw|both]

set -euo pipefail

ROLE="${1:-both}"
REPO_URL="https://github.com/arslansky/hermes-backup.git"
REPO_DIR="$HOME/hermes-backup"

color_ok()  { echo -e "\033[0;32m$1\033[0m"; }
color_warn(){ echo -e "\033[1;33m$1\033[0m"; }
color_err() { echo -e "\033[0;31m$1\033[0m"; }

echo "=== Multi-VM Bootstrap ==="
echo "Role: $ROLE"
echo "Hostname: $(hostname -s)"
echo ""

# 1. Install required packages
if ! command -v git &> /dev/null; then
    echo "[1/6] Installing git..."
    if command -v dnf &> /dev/null; then
        sudo dnf install -y git
    elif command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y git
    else
        color_err "ERROR: Cannot install git automatically. Install it manually."
        exit 1
    fi
else
    echo "[1/6] git already installed"
fi

# 2. Clone or update repo
echo ""
echo "[2/6] Cloning/updating hermes-backup repo..."
if [ -d "$REPO_DIR/.git" ]; then
    cd "$REPO_DIR"
    git pull origin main
    color_ok "  ✓ Updated $REPO_DIR"
else
    rm -rf "$REPO_DIR"
    git clone "$REPO_URL" "$REPO_DIR"
    color_ok "  ✓ Cloned to $REPO_DIR"
fi

# 3. Create symlinks for scripts
echo ""
echo "[3/6] Creating script symlinks..."
mkdir -p "$HOME/.hermes" "$HOME/.openclaw/workspace" "$HOME/.config/systemd/user"

if [ "$ROLE" == "hermes" ] || [ "$ROLE" == "both" ]; then
    if [ -e "$HOME/.hermes/scripts" ] && [ ! -L "$HOME/.hermes/scripts" ]; then
        rm -rf "$HOME/.hermes/scripts"
    fi
    ln -sfn "$REPO_DIR/scripts" "$HOME/.hermes/scripts"
    color_ok "  ✓ ~/.hermes/scripts → $REPO_DIR/scripts"
fi

if [ "$ROLE" == "openclaw" ] || [ "$ROLE" == "both" ]; then
    if [ -e "$HOME/.openclaw/workspace/ops/scripts" ] && [ ! -L "$HOME/.openclaw/workspace/ops/scripts" ]; then
        rm -rf "$HOME/.openclaw/workspace/ops/scripts"
    fi
    mkdir -p "$HOME/.openclaw/workspace/ops"
    ln -sfn "$REPO_DIR/scripts" "$HOME/.openclaw/workspace/ops/scripts"
    color_ok "  ✓ ~/.openclaw/workspace/ops/scripts → $REPO_DIR/scripts"
fi

# 4. Restore config (if available in repo)
echo ""
echo "[4/6] Restoring config from backup..."
HOSTNAME=$(hostname -s)
CONFIG_DIR="$REPO_DIR/config/$HOSTNAME"

if [ -d "$CONFIG_DIR" ]; then
    if [ "$ROLE" == "hermes" ] || [ "$ROLE" == "both" ]; then
        mkdir -p "$HOME/.hermes"
        [ -f "$CONFIG_DIR/hermes/config.yaml" ] && cp -f "$CONFIG_DIR/hermes/config.yaml" "$HOME/.hermes/config.yaml" && color_ok "  ✓ config.yaml"
        [ -f "$CONFIG_DIR/hermes/auth.json" ] && cp -f "$CONFIG_DIR/hermes/auth.json" "$HOME/.hermes/auth.json" && color_ok "  ✓ auth.json"
        [ -f "$CONFIG_DIR/hermes/.env.example" ] && cp -f "$CONFIG_DIR/hermes/.env.example" "$HOME/.hermes/.env.example" && color_warn "  ⚠ .env.example copied (add real secrets)"
    fi

    if [ "$ROLE" == "openclaw" ] || [ "$ROLE" == "both" ]; then
        mkdir -p "$HOME/.openclaw"
        [ -f "$CONFIG_DIR/openclaw/openclaw.json" ] && cp -f "$CONFIG_DIR/openclaw/openclaw.json" "$HOME/.openclaw/openclaw.json" && color_ok "  ✓ openclaw.json"
        [ -f "$CONFIG_DIR/openclaw/inventory.yml" ] && cp -f "$CONFIG_DIR/openclaw/inventory.yml" "$HOME/.openclaw/workspace/inventory.yml" && color_ok "  ✓ inventory.yml"
        for f in SOUL.md AGENTS.md MEMORY.md USER.md; do
            [ -f "$CONFIG_DIR/openclaw/$f" ] && cp -f "$CONFIG_DIR/openclaw/$f" "$HOME/.openclaw/workspace/$f" && color_ok "  ✓ $f"
        done
    fi

    if [ "$ROLE" == "hermes" ] || [ "$ROLE" == "both" ] || [ "$ROLE" == "openclaw" ]; then
        local sysd="$HOME/.config/systemd/user"
        mkdir -p "$sysd"
        [ -f "$CONFIG_DIR/systemd/hermes-gateway.service" ] && cp -f "$CONFIG_DIR/systemd/hermes-gateway.service" "$sysd/" && color_ok "  ✓ hermes-gateway.service"
        [ -f "$CONFIG_DIR/systemd/openclaw-gateway.service" ] && cp -f "$CONFIG_DIR/systemd/openclaw-gateway.service" "$sysd/" && color_ok "  ✓ openclaw-gateway.service"
    fi
else
    color_warn "  ⚠ No config found for $HOSTNAME in repo. Using defaults."
fi

# 5. Restore .env if present in secure local location
SECRETS_DIR="$HOME/.secure"
if [ -f "$SECRETS_DIR/.env" ]; then
    cp -f "$SECRETS_DIR/.env" "$HOME/.hermes/.env"
    color_ok "  ✓ .env restored from $SECRETS_DIR/.env"
fi

# 6. Setup systemd reload
if [ -d "$HOME/.config/systemd/user" ] && [ -n "$(ls -A "$HOME/.config/systemd/user"/*.service 2>/dev/null)" ]; then
    systemctl --user daemon-reload 2>/dev/null || true
    color_ok "  ✓ systemd daemon-reload"
fi

# 7. Create backward-compat symlink
if [ -e "$HOME/scripts" ] && [ ! -L "$HOME/scripts" ]; then
    rm -rf "$HOME/scripts"
fi
ln -sfn "$REPO_DIR" "$HOME/scripts"

# 8. Schedule auto-sync cron
if [ "$ROLE" == "hermes" ] || [ "$ROLE" == "both" ]; then
    echo ""
    echo "[5/6] Hermes auto-sync can be scheduled with:"
    echo "  hermes cron create --name 'Daily scripts sync' --schedule '0 9 * * *' --no-agent --script sync-scripts.sh --deliver local"
    echo "  hermes cron create --name 'Daily config backup' --schedule '0 2 * * *' --no-agent --script backup-config.sh --deliver local"
    echo "  hermes cron create --name 'Health check' --schedule '0 8 * * *' --no-agent --script health-check.sh --deliver local"
fi

if [ "$ROLE" == "openclaw" ] || [ "$ROLE" == "both" ]; then
    echo ""
    echo "[6/6] System crontab auto-sync can be added with:"
    echo "  (crontab -l 2>/dev/null; echo '0 9 * * * cd $REPO_DIR && git pull -q origin main') | crontab -"
fi

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Next steps:"
if [ ! -f "$HOME/.hermes/.env" ]; then
    color_warn "  ⚠ ~/.hermes/.env is missing. Add secrets before starting Hermes."
fi
echo "  1. Verify config:  ls -la ~/.hermes/ ~/.openclaw/"
echo "  2. Start services:"
if [ "$ROLE" == "hermes" ] || [ "$ROLE" == "both" ]; then
    echo "     systemctl --user start hermes-gateway.service"
fi
if [ "$ROLE" == "openclaw" ] || [ "$ROLE" == "both" ]; then
    echo "     systemctl --user start openclaw-gateway.service"
fi
echo "  3. Check health:   bash $REPO_DIR/scripts/health-check.sh"
