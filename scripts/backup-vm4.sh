#!/usr/bin/env bash
# Backup VM4 (core node): PostgreSQL + ảnh + thumbnails.
# Chạy trên VM4 (root):  bash /opt/bt03/backup-vm4.sh
# Kết quả lưu tại BACKUP_DIR (mặc định /var/backups/bt03).
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/bt03}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
TS="$(date +%F_%H%M)"
mkdir -p "$BACKUP_DIR"

# 1. PostgreSQL
sudo -u postgres pg_dump -Fc bt03 > "$BACKUP_DIR/bt03-db-$TS.dump"

# 2. Ảnh + thumbnails
tar czf "$BACKUP_DIR/bt03-images-$TS.tar.gz" -C /var/lib/bt03 images thumbs

# 3. Xoá backup cũ
find "$BACKUP_DIR" -name 'bt03-*' -mtime +"$RETAIN_DAYS" -delete

echo "Backup done: $BACKUP_DIR"
ls -lh "$BACKUP_DIR" | tail -4
"