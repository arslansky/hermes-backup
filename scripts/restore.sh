#!/bin/bash
# restore.sh — 用 Symlink 方式還原
# 原理：config 已經喺 repo 入面，還原 = 建立 symlink 去實際位置
# Usage: bash restore.sh [--component openclaw|hermes|systemd|all] [backup_path]
# Default: restore all from latest backup

set -e

COMPONENT="${1:-all}"
BACKUP_PATH="${2:-$HOME/.openclaw/workspace/config}"
WORKSPACE="$HOME/.openclaw/workspace"
SRC_OPENCLAW="$BACKUP_PATH/openclaw"
SRC_HERMES="$BACKUP_PATH/hermes"
SRC_SYSTEMD="$BACKUP_PATH/systemd"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()  { echo -e "${GREEN}✓${NC} $1"; }
log_warn(){ echo -e "${YELLOW}⚠${NC} $1"; }
log_err(){ echo -e "${RED}✗${NC} $1"; }

# Check backup exists
check_backup() {
    if [ ! -d "$BACKUP_PATH" ]; then
        log_err "Backup not found at: $BACKUP_PATH"
        echo "Available backups:"
        ls -la "$WORKSPACE/.backup/" 2>/dev/null || echo "  No .backup directory"
        exit 1
    fi
    log_ok "Backup found: $BACKUP_PATH"
}

# Restore OpenClaw
restore_openclaw() {
    echo ""
    echo "=== Restoring OpenClaw ==="
    
    # Ensure directories exist
    mkdir -p "$HOME/.openclaw"
    
    # Symlink openclaw.json
    if [ -f "$SRC_OPENCLAW/openclaw.json" ]; then
        ln -sf "$SRC_OPENCLAW/openclaw.json" "$HOME/.openclaw/openclaw.json"
        log_ok "openclaw.json linked"
    else
        log_err "openclaw.json not found in backup"
    fi
    
    log_ok "OpenClaw restored (symlink mode)"
}

# Restore Hermes
restore_hermes() {
    echo ""
    echo "=== Restoring Hermes ==="
    
    mkdir -p "$HOME/.hermes"
    
    # Symlink config.yaml
    if [ -f "$SRC_HERMES/config.yaml" ]; then
        ln -sf "$SRC_HERMES/config.yaml" "$HOME/.hermes/config.yaml"
        log_ok "config.yaml linked"
    fi
    
    # Symlink auth.json
    if [ -f "$SRC_HERMES/auth.json" ]; then
        ln -sf "$SRC_HERMES/auth.json" "$HOME/.hermes/auth.json"
        log_ok "auth.json linked"
    fi
    
    # .env 唔自動還原（secrets）
    if [ -f "$SRC_HERMES/.env.example" ]; then
        log_warn ".env NOT restored (secrets). Copy manually if needed:"
        echo "  cp $SRC_HERMES/.env.example $HOME/.hermes/.env"
    fi
    
    log_ok "Hermes restored (symlink mode)"
    echo ""
    echo "⚠️  IMPORTANT: After restore, run:"
    echo "   hermes gateway restart"
}

# Restore systemd
restore_systemd() {
    echo ""
    echo "=== Restoring systemd services ==="
    
    mkdir -p "$HOME/.config/systemd/user"
    
    [ -f "$SRC_SYSTEMD/hermes-gateway.service" ] && \
        ln -sf "$SRC_SYSTEMD/hermes-gateway.service" "$HOME/.config/systemd/user/hermes-gateway.service" && \
        log_ok "hermes-gateway.service linked"
    
    [ -f "$SRC_SYSTEMD/openclaw-gateway.service" ] && \
        ln -sf "$SRC_SYSTEMD/openclaw-gateway.service" "$HOME/.config/systemd/user/openclaw-gateway.service" && \
        log_ok "openclaw-gateway.service linked"
    
    systemctl --user daemon-reload 2>/dev/null || true
    log_ok "Systemd restored"
}

# Full restore summary
full_restore() {
    check_backup
    restore_openclaw
    restore_hermes
    restore_systemd
    
    echo ""
    echo "=== Restore Complete ==="
    echo ""
    echo "Next steps:"
    echo "1. Verify symlinks: ls -la ~/.hermes/"
    echo "2. Check .env: cat ~/.hermes/.env"
    echo "3. Restart: hermes gateway restart"
    echo ""
    echo "To push this restore to GitHub:"
    echo "  cd $WORKSPACE && git add -A && git commit -m 'Restored from backup' && git push"
}

# Main
case "$COMPONENT" in
    openclaw)
        check_backup
        restore_openclaw
        ;;
    hermes)
        check_backup
        restore_hermes
        ;;
    systemd)
        check_backup
        restore_systemd
        ;;
    all)
        full_restore
        ;;
    *)
        echo "Usage: bash restore.sh [openclaw|hermes|systemd|all] [backup_path]"
        echo "  Default: all"
        echo "  Example: bash restore.sh hermes /path/to/backup"
        exit 1
        ;;
esac
