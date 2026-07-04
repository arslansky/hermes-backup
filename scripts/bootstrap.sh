#!/bin/bash
# bootstrap.sh — 新 VM 第一次 Setup
# 用於全新 VM clone repo 後，一次性建立所有 symlink
# Usage: bash bootstrap.sh

set -e

WORKSPACE="$HOME/.openclaw/workspace"
REPO_CONFIG="$WORKSPACE/config"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=== OpenClaw Workspace Bootstrap ==="
echo ""

# 1. Clone repo (如果未 clone)
if [ ! -d "$WORKSPACE/.git" ]; then
    echo "[1/5] Cloning repo..."
    mkdir -p "$(dirname "$WORKSPACE")"
    git clone https://github.com/arslansky/openclaw-workspace.git "$WORKSPACE"
    echo "  ✓ Repo cloned"
else
    echo "[1/5] Repo already exists, pulling latest..."
    cd "$WORKSPACE" && git pull origin master
    echo "  ✓ Repo updated"
fi

# 2. 建立目錄結構
echo ""
echo "[2/5] Creating directories..."
mkdir -p "$HOME/.openclaw"
mkdir -p "$HOME/.hermes"
mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/.openclaw/workspace/memory"
echo "  ✓ Directories created"

# 3. 建立 Symlinks
echo ""
echo "[3/5] Creating symlinks..."

# OpenClaw
if [ -f "$REPO_CONFIG/openclaw/openclaw.json" ]; then
    ln -sf "$REPO_CONFIG/openclaw/openclaw.json" "$HOME/.openclaw/openclaw.json"
    echo "  ✓ openclaw.json"
fi

# Hermes
if [ -f "$REPO_CONFIG/hermes/config.yaml" ]; then
    ln -sf "$REPO_CONFIG/hermes/config.yaml" "$HOME/.hermes/config.yaml"
    echo "  ✓ config.yaml"
fi

if [ -f "$REPO_CONFIG/hermes/auth.json" ]; then
    ln -sf "$REPO_CONFIG/hermes/auth.json" "$HOME/.hermes/auth.json"
    echo "  ✓ auth.json"
fi

# Systemd
if [ -f "$REPO_CONFIG/systemd/hermes-gateway.service" ]; then
    ln -sf "$REPO_CONFIG/systemd/hermes-gateway.service" "$HOME/.config/systemd/user/hermes-gateway.service"
    echo "  ✓ hermes-gateway.service"
fi

if [ -f "$REPO_CONFIG/systemd/openclaw-gateway.service" ]; then
    ln -sf "$REPO_CONFIG/systemd/openclaw-gateway.service" "$HOME/.config/systemd/user/openclaw-gateway.service"
    echo "  ✓ openclaw-gateway.service"
fi

# 4. Memory/knowledge base
if [ -d "$WORKSPACE/memory" ]; then
    ln -sf "$WORKSPACE/memory" "$HOME/.openclaw/workspace/memory"
    echo "  ✓ memory/ symlink"
fi

# 5. Setup 完成
echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Symlinks created:"
ls -la "$HOME/.openclaw/openclaw.json" 2>/dev/null || true
ls -la "$HOME/.hermes/config.yaml" 2>/dev/null || true
ls -la "$HOME/.config/systemd/user/hermes-gateway.service" 2>/dev/null || true
echo ""
echo "Next steps:"
echo "1. Add your .env file:"
echo "   cp $REPO_CONFIG/hermes/.env.example $HOME/.hermes/.env"
echo "   nano $HOME/.hermes/.env  # add your API keys"
echo ""
echo "2. Reload systemd:"
echo "   systemctl --user daemon-reload"
echo ""
echo "3. Start services:"
echo "   hermes gateway start"
echo ""
echo "4. Check status:"
echo "   hermes gateway status"
