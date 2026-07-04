#!/bin/bash
# check-secrets.sh — Verify all required secrets are present and match local backup
# Usage: bash check-secrets.sh

set -euo pipefail

ENV_FILE="$HOME/.hermes/.env"
SECURE_DIR="$HOME/.secure"
REQUIRED_KEYS=(
    "TELEGRAM_BOT_TOKEN"
    "TELEGRAM_ALLOWED_USERS"
    "OPENAI_API_KEY"
    "GITHUB_TOKEN"
    "MINIMAX_API_KEY"
    "KIMI_API_KEY"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Secrets Check ==="
echo "Env file: $ENV_FILE"
echo "Backup dir: $SECURE_DIR"
echo ""

missing_in_env=0
missing_in_backup=0
mismatch=0

for key in "${REQUIRED_KEYS[@]}"; do
    env_val=$(grep "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' || true)
    backup_file="$SECURE_DIR/service-keys/${key,,}.txt"
    backup_file2=$(echo "$backup_file" | tr '_' '-')
    backup_val=""
    if [ -f "$backup_file" ]; then
        backup_val=$(grep "^${key}=" "$backup_file" | cut -d= -f2- | tr -d '"' || true)
    elif [ -f "$backup_file2" ]; then
        backup_val=$(grep "^${key}=" "$backup_file2" | cut -d= -f2- | tr -d '"' || true)
    fi

    status=""
    if [ -z "$env_val" ]; then
        echo -e "  ${RED}✗ $key missing in .env${NC}"
        missing_in_env=$((missing_in_env + 1))
    elif [ -z "$backup_val" ]; then
        echo -e "  ${YELLOW}⚠ $key present in .env but no backup${NC}"
        missing_in_backup=$((missing_in_backup + 1))
    elif [ "$env_val" != "$backup_val" ]; then
        echo -e "  ${YELLOW}⚠ $key differs between .env and backup${NC}"
        mismatch=$((mismatch + 1))
    else
        echo -e "  ${GREEN}✓ $key OK${NC}"
    fi
done

echo ""
echo "=== Summary ==="
echo "Missing in .env: $missing_in_env"
echo "Missing backup: $missing_in_backup"
echo "Mismatched: $mismatch"

if [ "$missing_in_env" -gt 0 ]; then
    echo -e "${RED}ERROR: Some secrets are missing from .env.${NC}"
    exit 1
fi

if [ "$missing_in_backup" -gt 0 ] || [ "$mismatch" -gt 0 ]; then
    echo -e "${YELLOW}WARNING: Run backup-config.sh to sync .env to ~/.secure/.${NC}"
    exit 2
fi

echo -e "${GREEN}All secrets present and backed up correctly.${NC}"
exit 0
