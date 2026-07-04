#!/bin/bash
# backup.sh — 用 Symlink 方式做 backup
# 原理：唔 copy，只建立 symlink，repo 入面直接係 actual config
# Usage: bash backup.sh "描述"

set -e

DESCRIPTION="${1:-手動備份}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
WORKSPACE="$HOME/.openclaw/workspace"
BACKUP_DIR="$WORKSPACE/.backup"
OUTPUT_DIR="$BACKUP_DIR/config_${TIMESTAMP}"
REPO_CONFIG_DIR="$WORKSPACE/config"

echo "=== Backup Started: $DESCRIPTION ==="
echo "Timestamp: $TIMESTAMP"

# 1. 確保 workspace 係 git repo
if [ ! -d "$WORKSPACE/.git" ]; then
    echo "ERROR: $WORKSPACE 唔係 git repo"
    exit 1
fi

# 2. 建立 config 目錄（如果唔存在）
mkdir -p "$REPO_CONFIG_DIR"/{openclaw,hermes,systemd}

# 3. Backup OpenClaw config → repo config/
echo "[1/4] Backing up OpenClaw config..."
backup_openclaw() {
    local src="$HOME/.openclaw/openclaw.json"
    local dst="$REPO_CONFIG_DIR/openclaw/openclaw.json"
    if [ -f "$src" ]; then
        cp -f "$src" "$dst"
        echo "  ✓ openclaw.json"
    else
        echo "  ⚠ openclaw.json not found, skipping"
    fi
}
backup_openclaw

# 4. Backup Hermes config → repo config/
echo "[2/4] Backing up Hermes config..."
backup_hermes() {
    local cfg="$HOME/.hermes/config.yaml"
    local env="$HOME/.hermes/.env"
    local auth="$HOME/.hermes/auth.json"
    
    [ -f "$cfg" ] && cp -f "$cfg" "$REPO_CONFIG_DIR/hermes/config.yaml" && echo "  ✓ config.yaml"
    [ -f "$auth" ] && cp -f "$auth" "$REPO_CONFIG_DIR/hermes/auth.json" && echo "  ✓ auth.json"
    
    # NOTE: .env (API keys) 唔備份，需要用戶手動處理
    if [ -f "$env" ]; then
        # 創建 .env.example (無 actual key)
        grep -v "KEY\|TOKEN\|SECRET" "$env" > "$REPO_CONFIG_DIR/hermes/.env.example" 2>/dev/null || true
        echo "  ⚠ .env not backed up (secrets excluded)"
    fi
}
backup_hermes

# 5. Backup systemd services → repo config/
echo "[3/4] Backing up systemd services..."
backup_systemd() {
    local sysd="$HOME/.config/systemd/user"
    [ -f "$sysd/hermes-gateway.service" ] && cp -f "$sysd/hermes-gateway.service" "$REPO_CONFIG_DIR/systemd/" && echo "  ✓ hermes-gateway.service"
    [ -f "$sysd/openclaw-gateway.service" ] && cp -f "$sysd/openclaw-gateway.service" "$REPO_CONFIG_DIR/systemd/" && echo "  ✓ openclaw-gateway.service"
}
backup_systemd

# 6. Git commit 做 snapshot
echo "[4/4] Creating git snapshot..."
cd "$WORKSPACE"
git add config/
git commit -m "Backup: $DESCRIPTION (${TIMESTAMP})" 2>/dev/null || echo "  ⚠ Nothing to commit"

# Metadata
METADATA="$BACKUP_DIR/metadata_latest.json"
cat > "$METADATA" << EOF
{
  "version": "2.0-symlink",
  "created_at": "$(date -Iseconds)",
  "description": "$DESCRIPTION",
  "timestamp": "$TIMESTAMP",
  "hostname": "$(hostname)",
  "openclaw_version": "$(openclaw --version 2>/dev/null || echo 'unknown')",
  "hermes_version": "$(hermes --version 2>/dev/null || echo 'unknown')",
  "kernel": "$(uname -r)",
  "backup_type": "symlink"
}
EOF

echo ""
echo "=== Backup Complete ==="
echo "Config stored in: $REPO_CONFIG_DIR/"
echo "Git snapshot: $TIMESTAMP"
echo ""
echo "To push to GitHub:"
echo "  cd $WORKSPACE && git push origin master"
echo ""
