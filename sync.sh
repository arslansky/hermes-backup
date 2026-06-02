#!/bin/bash
# hermes-backup sync wrapper — runs as cron job
# Checks if there's anything new to commit, then push

BACKUP_DIR="$HOME/.hermes/hermes-backup"
REPORT_MD="$HOME/.hermes/hermes_agent_evaluation_report.md"
REPORT_PDF="$HOME/.hermes/hermes_agent_evaluation_report.pdf"

# Load token if available
if [ -f "$HOME/.hermes/.env" ]; then
    export GITHUB_TOKEN=$(grep '^GITHUB_TOKEN=' "$HOME/.hermes/.env" 2>/dev/null | cut -d'=' -f2 | tr -d ' 
')
fi

cd "$BACKUP_DIR"

# Copy latest reports if they exist
[ -f "$REPORT_MD" ] && cp "$REPORT_MD" .
[ -f "$REPORT_PDF" ] && cp "$REPORT_PDF" .

# Stage all changes
git add -A

# Check if there are changes
if ! git diff --quiet HEAD 2>/dev/null; then
    echo "Changes detected — committing..."
    git commit -m "Auto-sync: $(date '+%Y-%m-%d %H:%M')"
    
    if [ -n "$GITHUB_TOKEN" ] && [ "$GITHUB_TOKEN" != "***" ] && [ ${#GITHUB_TOKEN} -gt 10 ]; then
        git push origin master && echo "Pushed to GitHub."
    else
        echo "No GitHub token — changes saved locally."
    fi
else
    echo "No changes to sync."
fi
