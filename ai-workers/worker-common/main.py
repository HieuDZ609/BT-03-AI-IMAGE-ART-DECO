"""AI worker local: sinh ảnh Art Deco (stable-diffusion.cpp), lưu metadata vào PostgreSQL,
ack Redis Stream. Có tự phục hồi job kẹt (XAUTOCLAIM + đối soát bảng generation_jobs).

Chạy: AI_CODE=4.1 AI_BACKEND=sd REDIS_URL=... DATABASE_URL=... python main.py
"""
import hashlib
import io
import json
import os
import signal
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import redis
from PIL import Image, ImageDraw
from psycopg import connect

AI_CODE = os.getenv("AI_CODE", "4.1")
REDIS_URL = os.getenv("REDIS_URL", "redis://:B4Deco_Redis_2026!@100.70.241.87:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bt03:B4Deco_Pg_2026!@100.70.241.87:5432/bt03")
LOCAL_DIR = os.getenv("LOCAL_STORAGE_DIR", "/tmp/bt03-images")
STREAM = "jobs:generate"
EVENTS = "job:events"
GROUP = "workers"
CONSUMER = AI_CODE

r = redis.from_url(REDIS_URL, decode_responses=True)
db = connect(DATABASE_URL, autocommit=True)

# resolve worker_id from ai_code
with db.cursor() as cur:
    cur.execute("SELECT worker_id FROM ai_workers WHERE ai_code=%s", (AI_CODE,))
    row = cur.fetchone()
    WORKER_ID = row[0] if row else None


def ensure_group():
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def heartbeat():
    while True:
        try:
            r.set(f"worker:heartbeat:{AI_CODE}", "1", ex=90)
            if WORKER_ID:
                with db.cursor() as cur:
                    cur.execute(
                        "UPDATE ai_workers SET status='ONLINE', last_heartbeat=now(), "
                        "model_name=COALESCE(%s, model_name) WHERE worker_id=%s",
                        (os.getenv("AI_MODEL_NAME"), WORKER_ID),
                    )
        except Exception as e:
            print("heartbeat err:", e)
        time.sleep(30)


def make_image(slug: str):
    """Sinh ảnh 512x512 Art Deco placeholder."""
    img = Image.new("RGB", (512, 512), "#1A1A1A")
    d = ImageDraw.Draw(img)
    # viền vàng
    d.rectangle((16, 16, 495, 495), outline="#C9A227", width=6)
    # ziczac đơn giản
    for i in range(0, 512, 32):
        d.line((i, 256, i + 16, 224), fill="#C9A227", width=2)
        d.line((i + 16, 224, i + 32, 256), fill="#C9A227", width=2)
    # chữ slug
    d.text((32, 40), slug[:40], fill="#F2E8C9")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    return data, "png", 512, 512


def _enqueue(job_id, slug, query, source="RECONCILE"):
    """Đẩy lại job vào stream (dùng cho đối soát job bị mất message)."""
    r.xadd(STREAM, {
        "job_id": str(job_id), "query": query, "slug": slug,
        "source": source, "style_id": "deco-v1",
        "requested_at": datetime.now(timezone.utc).isoformat(),
    })


def reclaim_pending(min_idle_ms=120000, count=5):
    """Nhận lại job bị bỏ dở (worker crash / Redis restart) từ PEL của consumer group."""
    try:
        resp = r.xautoclaim(STREAM, GROUP, CONSUMER, min_idle_time=min_idle_ms,
                            start_id="0-0", count=count)
    except Exception as e:
        print("xautoclaim err:", e)
        return 0
    entries = resp[1] if len(resp) > 1 else resp[0]
    n = 0
    for entry_id, fields in entries or []:
        if not fields:
            continue
        if "payload" in fields:
            data = json.loads(fields["payload"])
        else:
            data = fields
        process(entry_id, data)
        n += 1
    return n


def reconcile_orphans(min_age_s=90, limit=5):
    """Job QUEUED nằm trong DB nhưng chưa từng vào Redis (Redis chết lúc XADD) -> đẩy lại."""
    try:
        with db.cursor() as cur:
            rows = cur.execute(
                "SELECT job_id, query, slug FROM generation_jobs "
                "WHERE status='QUEUED' AND created_at < now() - make_interval(secs => %s) "
                "ORDER BY created_at LIMIT %s",
                (min_age_s, limit),
            ).fetchall()
    except Exception as e:
        print("reconcile err:", e)
        return 0
    for job_id, query, slug in rows:
        _enqueue(job_id, slug, query)
    if rows:
        print(f"reconcile: requeued {len(rows)} orphan job(s)")
    return len(rows)


def process(entry_id, data):
    job_id = data["job_id"]
    slug = data["slug"]
    query = data["query"]
    t0 = time.time()
    try:
        # Nếu (slug, worker) đã có ảnh thì không sinh lại — job coi như xong.
        if WORKER_ID:
            with db.cursor() as cur:
                row = cur.execute(
                    "SELECT image_id, image_name, sha256, storage_key FROM images WHERE slug=%s AND worker_id=%s LIMIT 1",
                    (slug, WORKER_ID)).fetchone()
            if row:
                from storage_sync import verify_remote_image
                verify_remote_image(row[3])

                duration_ms = int((time.time() - t0) * 1000)
                event = {
                    "job_id": job_id, "status": "DONE", "image_id": str(row[0]),
                    "image_name": row[1], "ai_code": AI_CODE, "duration_ms": duration_ms,
                }
                r.xadd(EVENTS, {"payload": json.dumps(event)})
                r.set(f"job:{job_id}:result", json.dumps(event), ex=3600)
                with db.cursor() as cur:
                    cur.execute(
                        """UPDATE generation_jobs SET status='DONE', worker_id=%s, duration_ms=%s,
                           image_id=%s, updated_at=now() WHERE job_id=%s""",
                        (WORKER_ID, duration_ms, str(row[0]), job_id))
                r.xack(STREAM, GROUP, entry_id)
                print("SKIP (already exists)", slug, job_id)
                return

        if os.getenv("AI_BACKEND", "placeholder") == "sd":
            from ai_engine import generate_image
            img_bytes, fmt, w, h = generate_image(query)
        else:
            img_bytes, fmt, w, h = make_image(slug)
        sha = hashlib.sha256(img_bytes).hexdigest()
        storage_key = f"{slug}/{AI_CODE}/{uuid.uuid4().hex}.png"
        os.makedirs(os.path.join(LOCAL_DIR, slug, AI_CODE), exist_ok=True)
        path = os.path.join(LOCAL_DIR, slug, AI_CODE, storage_key.split('/')[-1])
        with open(path, "wb") as f:
            f.write(img_bytes)

        # Chuyển ảnh sang VM4 trước khi ghi PostgreSQL và XACK.
        from storage_sync import sync_image
        sync_image(path, storage_key)

        image_id = str(uuid.uuid4())
        image_name = f"{slug}-{AI_CODE}.png"

        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO images (image_id, image_name, slug, prompt, style_id, worker_id,
                   storage_key, sha256, width, height, format, file_size)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (sha256) DO NOTHING""",
                (image_id, image_name, slug, query, "deco-v1", WORKER_ID,
                 storage_key, sha, w, h, fmt, len(img_bytes)),
            )
            # Kiểm tra metadata ảnh đã lưu.
            cur.execute(
                "SELECT image_id, storage_key, image_name FROM images WHERE sha256=%s",
                (sha,),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Không tìm thấy ảnh trong PostgreSQL sau INSERT")

            if str(row[0]) != image_id or row[1] != storage_key:
                # Ảnh trùng SHA-256: dùng bản ghi đã tồn tại.
                from storage_sync import verify_remote_image
                verify_remote_image(row[1])
                image_id = str(row[0])
                storage_key = row[1]

            image_name = row[2]

        duration_ms = int((time.time() - t0) * 1000)
        event = {
            "job_id": job_id,
            "status": "DONE",
            "image_id": image_id,
            "image_name": image_name,
            "ai_code": AI_CODE,
            "duration_ms": duration_ms,
        }
        if WORKER_ID:
            with db.transaction():
                with db.cursor() as cur:
                    cur.execute(
                        """UPDATE generation_jobs SET status='DONE', worker_id=%s, duration_ms=%s,
                           image_id=%s, updated_at=now()
                           WHERE job_id=%s AND status IS DISTINCT FROM 'DONE'
                           RETURNING job_id""",
                        (WORKER_ID, duration_ms, image_id, job_id),
                    )
                    updated = cur.fetchone()
                    if updated:
                        cur.execute(
                            "UPDATE ai_workers SET total_generated=total_generated+1 WHERE worker_id=%s",
                            (WORKER_ID,),
                        )
        r.xadd(EVENTS, {"payload": json.dumps(event)})
        r.set(f"job:{job_id}:result", json.dumps(event), ex=3600)
        r.xack(STREAM, GROUP, entry_id)
        print("DONE job", job_id, slug)
    except Exception as e:
        print("FAILED job", job_id, e)
        # do not ack -> XAUTOCLAIM will redeliver


def main():
    ensure_group()
    threading.Thread(target=heartbeat, daemon=True).start()
    print(f"worker {AI_CODE} started, worker_id={WORKER_ID}")
    last_recover = 0.0
    while True:
        now = time.time()
        if now - last_recover > 60:
            last_recover = now
            try:
                reclaim_pending()
                reconcile_orphans()
            except Exception as e:
                print("recover err:", e)
        try:
            resp = r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1, block=5000)
        except Exception as e:
            print("xreadgroup err:", e)
            time.sleep(2)
            continue
        if not resp:
            continue
        _, entries = resp[0]
        for entry_id, fields in entries:
            # fields may be {'payload': json} or flat job fields
            if "payload" in fields:
                data = json.loads(fields["payload"])
            else:
                data = fields
                if "requested_at" not in data:
                    data["requested_at"] = datetime.now(timezone.utc).isoformat()
            process(entry_id, data)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
    main()