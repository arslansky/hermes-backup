#!/bin/bash
# Create hermes-backup GitHub repo and push
# Usage: GITHUB_TOKEN=ghp_... bash create_github_repo.sh

set -e

GITHUB_TOKEN="${GITHUB_TOKEN:-$(grep '^GITHUB_TOKEN=' ~/.hermes/.env 2>/dev/null | cut -d'=' -f2 | tr -d ' 
')}"

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "***" ] || [ ${#GITHUB_TOKEN} -lt 20 ]; then
    echo "ERROR: Valid GITHUB_TOKEN required."
    echo "Set in ~/.hermes/.env (uncomment GITHUB_TOKEN=...) or pass as env var:"
    echo "  GITHUB_TOKEN=ghp_... bash create_github_repo.sh"
    exit 1
fi

export GH_TOKEN="$GITHUB_TOKEN"

# Authenticate gh
echo "$GITHUB_TOKEN" | gh auth login --with-token

# Create repo via gh
gh repo create hermes-backup --public --confirm

# Push
cd ~/.hermes/hermes-backup
git push -u origin master

echo "SUCCESS: hermes-backup repo created and synced!"
