#!/usr/bin/env bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <directory_to_backup> <target_location>"
    exit 1
fi

SOURCE_DIR="$1"
TARGET_LOCATION="$2"
BACKUP_FILENAME="$(date +%Y-%m-%d)-$(hostname)-$(basename "$SOURCE_DIR")-backup.tar.gz"

tar -czf "$TARGET_LOCATION/$BACKUP_FILENAME" -C "$(dirname "$SOURCE_DIR")" "$(basename "$SOURCE_DIR")" && \
echo "Backup successful: $TARGET_LOCATION/$BACKUP_FILENAME" || \
echo "Backup failed"
