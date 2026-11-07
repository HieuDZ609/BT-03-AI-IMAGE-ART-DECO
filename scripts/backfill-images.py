"""Sinh lại toàn bộ ảnh trong kho bằng AI thật (một lần), cập nhật tại chỗ.

Dùng khi cần thay ảnh placeholder hoặc đổi hậu kỳ (palette/viền/bảng tên).
Ảnh cũ được giữ cho tới khi ảnh mới ghi xong; storage_key đổi mới nên thumbnail
WebP tự sinh lại, không bị cache cũ.

Chạy trên VM4:
    systemctl stop bt03-worker
    /opt/bt03/venv/bin/python /opt/bt03/worker/backfill-images.py
    systemctl start bt03-worker
"""
import hashlib
import os
import sys
import time
import uuid

from psycopg import connect

sys.path.insert(0, "/opt/bt03/worker")
from ai_engine import generate_image  # noqa: E402

DB = os.getenv("DATABASE_URL", "postgresql://bt03:B4Deco_Pg_2026!@100.70.241.87:5432/bt03")
IMAGES_DIR = os.getenv("LOCAL_STORAGE_DIR", "/var/lib/bt03/images")
WORKER = os.getenv("AI_CODE", "4.1")


def main():
    conn = connect(DB, autocommit=True)
    with conn.cursor() as cur:
        rows = cur.execute(
            "SELECT image_id, slug, prompt, storage_key FROM images ORDER BY created_at"
        ).fetchall()
    print(f"backfill: {len(rows)} ảnh", flush=True)
    ok = fail = 0
    for idx, (image_id, slug, prompt, old_key) in enumerate(rows, 1):
        query = (prompt or slug.replace("-", " ")).strip()
        t0 = time.time()
        try:
            data, fmt, w, h = generate_image(query)
            sha = hashlib.sha256(data).hexdigest()
            key = f"{slug}/{WORKER}/{uuid.uuid4().hex}.png"
            path = os.path.join(IMAGES_DIR, slug, WORKER, key.split("/")[-1])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE images SET storage_key=%s, sha256=%s, width=%s, height=%s, "
                    "format=%s, file_size=%s, prompt=%s WHERE image_id=%s",
                    (key, sha, w, h, fmt, len(data), query, image_id),
                )
            old_path = os.path.join(IMAGES_DIR, old_key)
            if old_key != key and os.path.isfile(old_path):
                os.remove(old_path)
            ok += 1
            print(f"[{idx}/{len(rows)}] OK {slug} {w}x{h} {len(data)}B {time.time()-t0:.1f}s", flush=True)
        except Exception as e:
            fail += 1
            print(f"[{idx}/{len(rows)}] FAIL {slug}: {e}", flush=True)
    print(f"backfill done: ok={ok} fail={fail}", flush=True)


if __name__ == "__main__":
    main()
