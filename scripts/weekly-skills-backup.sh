#!/bin/bash
# weekly-skills-backup.sh
# Backup all OpenClaw skills to a tar.gz archive and upload to Google Drive

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="openclaw-skills-${TIMESTAMP}"
BACKUP_DIR="/tmp/${BACKUP_NAME}"
ARCHIVE_PATH="/tmp/${BACKUP_NAME}.tar.gz"
GDRIVE_FOLDER="gdrive:Backups/OpenClaw/Skills"

echo "📦 Creating skills backup: ${BACKUP_NAME}"

mkdir -p "${BACKUP_DIR}"

# Copy all skills directories
cp -r ~/.nvm/versions/node/v22.22.1/lib/node_modules/openclaw/skills/* "${BACKUP_DIR}/" 2>/dev/null || true
cp -r ~/.openclaw/plugin-skills/* "${BACKUP_DIR}/" 2>/dev/null || true
cp -r ~/.agents/skills/* "${BACKUP_DIR}/" 2>/dev/null || true

# Create archive
tar -czf "${ARCHIVE_PATH}" -C /tmp "${BACKUP_NAME}"
ARCHIVE_SIZE=$(du -h "${ARCHIVE_PATH}" | cut -f1)

echo "✅ Archive created: ${ARCHIVE_PATH} (${ARCHIVE_SIZE})"

# Upload to Google Drive
echo "☁️ Uploading to Google Drive: ${GDRIVE_FOLDER}"
rclone copy "${ARCHIVE_PATH}" "${GDRIVE_FOLDER}/"

echo "✅ Upload complete!"

# Cleanup local archive
rm -rf "${BACKUP_DIR}" "${ARCHIVE_PATH}"

echo "🧹 Local cleanup done"
echo "📅 Backup completed: ${TIMESTAMP}"
