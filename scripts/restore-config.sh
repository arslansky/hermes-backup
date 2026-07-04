#!/bin/bash
# restore-config.sh — Restore Hermes + OpenClaw config from hermes-backup/config/<vm>/
# Usage: bash restore-config.sh [vm-hostname] [--dry-run]
# Default: restore config for current hostname

set -euo pipefail

DRY_RUN=false
if [ "$#" -ge 1 ] && [ "$1" == "--dry-run" ]; then
    DRY_RUN=true
    TARGET_VM=$(hostname -s)
else
    TARGET_VM="${1:-$(hostname -s)}"
fi

REPO_DIR="$HOME/hermes-backup"
CONFIG_DIR="$REPO_DIR/config/$TARGET_VM"

echo "=== Config Restore Started ==="
echo "Target VM: $TARGET_VM"
echo "Repo: $REPO_DIR"
echo "Config source: $CONFIG_DIR"
$DRY_RUN && echo "DRY RUN — no files will be changed"

if [ ! -d "$CONFIG_DIR" ]; then
    echo "ERROR: Config not found for $TARGET_VM" >&2
    echo "Available configs:"
    ls -1 "$REPO_DIR/config" 2>/dev/null || echo "  (none)"
    exit 1
fi

apply_or_dry() {
    local cmd="$1"
    if $DRY_RUN; then
        echo "  [DRY] $cmd"
    else
        eval "$cmd"
    fi
}

# --- Restore Hermes ---
restore_hermes() {
    echo ""
    echo "[1/3] Restoring Hermes config..."
    local src="$CONFIG_DIR/hermes"
    mkdir -p "$HOME/.hermes"

    if [ -f "$src/config.yaml" ]; then
        apply_or_dry "cp -f '$src/config.yaml' '$HOME/.hermes/config.yaml'"
        echo "  ✓ config.yaml"
    else
        echo "  ⚠ config.yaml not found"
    fi

    if [ -f "$src/auth.json" ]; then
        apply_or_dry "cp -f '$src/auth.json' '$HOME/.hermes/auth.json'"
        echo "  ✓ auth.json"
    else
        echo "  ⚠ auth.json not found"
    fi

    if [ -f "$src/.env.example" ]; then
        apply_or_dry "cp -f '$src/.env.example' '$HOME/.hermes/.env.example'"
        echo "  ⚠ .env.example copied (you must recreate .env manually)"
    fi

    if [ -f "$HOME/.hermes/.env" ]; then
        echo "  ✓ existing .env preserved (not overwritten)"
    else
        echo "  ⚠ .env NOT present — services may fail until secrets are restored"
    fi
}

# --- Restore OpenClaw ---
restore_openclaw() {
    echo ""
    echo "[2/3] Restoring OpenClaw config..."
    local src="$CONFIG_DIR/openclaw"
    mkdir -p "$HOME/.openclaw"

    if [ -f "$src/openclaw.json" ]; then
        apply_or_dry "cp -f '$src/openclaw.json' '$HOME/.openclaw/openclaw.json'"
        echo "  ✓ openclaw.json"
    else
        echo "  ⚠ openclaw.json not found"
    fi

    if [ -f "$src/inventory.yml" ]; then
        mkdir -p "$HOME/.openclaw/workspace"
        apply_or_dry "cp -f '$src/inventory.yml' '$HOME/.openclaw/workspace/inventory.yml'"
        echo "  ✓ inventory.yml"
    fi

    for f in SOUL.md AGENTS.md MEMORY.md USER.md; do
        if [ -f "$src/$f" ]; then
            mkdir -p "$HOME/.openclaw/workspace"
            apply_or_dry "cp -f '$src/$f' '$HOME/.openclaw/workspace/$f'"
            echo "  ✓ $f"
        fi
    done
}

# --- Restore systemd ---
restore_systemd() {
    echo ""
    echo "[3/3] Restoring systemd user services..."
    local src="$CONFIG_DIR/systemd"
    local sysd="$HOME/.config/systemd/user"
    mkdir -p "$sysd"

    local restored=0
    for svc in hermes-gateway.service openclaw-gateway.service; do
        if [ -f "$src/$svc" ]; then
            apply_or_dry "cp -f '$src/$svc' '$sysd/$svc'"
            echo "  ✓ $svc"
            restored=$((restored+1))
        fi
    done

    if [ "$restored" -gt 0 ] && ! $DRY_RUN; then
        systemctl --user daemon-reload 2>/dev/null || true
        echo "  ✓ systemd daemon-reload"
    fi
}

restore_hermes
restore_openclaw
restore_systemd

echo ""
echo "=== Config Restore Complete ==="
if ! $DRY_RUN; then
    echo ""
    echo "Next steps:"
    echo "  1. Verify .env is present: cat ~/.hermes/.env"
    echo "  2. Restart services if needed:"
    echo "     systemctl --user restart hermes-gateway.service"
    echo "     systemctl --user restart openclaw-gateway.service"
fi
