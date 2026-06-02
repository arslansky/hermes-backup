#!/bin/bash
# hermes-backup auto-update script
# Run after system evaluation or config changes

BACKUP_DIR="$HOME/.hermes/hermes-backup"
REPORT_MD="$HOME/.hermes/hermes_agent_evaluation_report.md"
REPORT_PDF="$HOME/.hermes/hermes_agent_evaluation_report.pdf"
EVAL_SCRIPT="$HOME/.hermes/hermes-agent/scripts/run_eval.sh"

cd "$BACKUP_DIR"

# Optional: re-run evaluation if script exists
if [ -f "$EVAL_SCRIPT" ]; then
    echo "Running system evaluation..."
    bash "$EVAL_SCRIPT"
fi

# Copy latest report
[ -f "$REPORT_MD" ] && cp "$REPORT_MD" .
[ -f "$REPORT_PDF" ] && cp "$REPORT_PDF" .

# Commit with timestamp
git add -A
git commit -m "System update: $(date '+%Y-%m-%d %H:%M')" || true

# Push (needs GH_TOKEN set)
if [ -n "$GITHUB_TOKEN" ] && [ "$GITHUB_TOKEN" != "***" ]; then
    git push origin main
    echo "Pushed to GitHub."
else
    echo "GITHUB_TOKEN not set — commit saved locally only."
fi
