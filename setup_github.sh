#!/bin/bash
# hermes-backup GitHub setup script
# Run with: GITHUB_TOKEN=your_pat_here bash ~/.hermes/hermes-backup/setup_github.sh
# Or just source ~/.hermes/.env and run: gh auth setup

set -e

GITHUB_TOKEN="${GITHUB_TOKEN:-$(grep GITHUB_TOKEN ~/.hermes/.env 2>/dev/null | cut -d'=' -f2 | tr -d ' 
')}"

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "***" ]; then
    echo "ERROR: GITHUB_TOKEN not set or still masked."
    echo "Please set your GitHub PAT in ~/.hermes/.env (uncomment GITHUB_TOKEN=)"
    echo "Then run: bash ~/.hermes/hermes-backup/setup_github.sh"
    exit 1
fi

echo "Authenticating gh with GitHub..."
echo "$GITHUB_TOKEN" | gh auth login --with-token

echo "Pushing to GitHub..."
git -C ~/.hermes/hermes-backup push -u origin main

echo "Done! hermes-backup synced to GitHub."
