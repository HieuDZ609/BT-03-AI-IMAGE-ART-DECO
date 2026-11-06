"""Fake AI worker: sinh ảnh placeholder Art Deco, lưu metadata vào PostgreSQL, ack Redis Stream.

Chạy: AI_CODE=4.1 REDIS_URL=... DATABASE_URL=... python main.py
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
                        "UPDATE ai_workers SET status='ONLINE', last_heartbeat=now() WHERE worker_id=%s",
                        (WORKER_ID,),
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


def process(entry_id, data):
    job_id = data["job_id"]
    slug = data["slug"]
    query = data["query"]
    t0 = time.time()
    try:
        img_bytes, fmt, w, h = make_image(slug)
        sha = hashlib.sha256(img_bytes).hexdigest()
        storage_key = f"{slug}/{AI_CODE}/{uuid.uuid4().hex}.png"
        os.makedirs(os.path.join(LOCAL_DIR, slug, AI_CODE), exist_ok=True)
        path = os.path.join(LOCAL_DIR, slug, AI_CODE, storage_key.split('/')[-1])
        with open(path, "wb") as f:
            f.write(img_bytes)

        image_id = str(uuid.uuid4())
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO images (image_id, image_name, slug, prompt, style_id, worker_id,
                   storage_key, sha256, width, height, format, file_size)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (sha256) DO NOTHING""",
                (image_id, f"{slug} {AI_CODE}.png", slug, query, "deco-v1", WORKER_ID,
                 storage_key, sha, w, h, fmt, len(img_bytes)),
            )
            # fetch actual image_id if conflict
            cur.execute("SELECT image_id FROM images WHERE sha256=%s", (sha,))
            image_id = str(cur.fetchone()[0])

        duration_ms = int((time.time() - t0) * 1000)
        event = {
            "job_id": job_id,
            "status": "DONE",
            "image_id": image_id,
            "image_name": f"{slug} {AI_CODE}.png",
            "ai_code": AI_CODE,
            "duration_ms": duration_ms,
        }
        r.xadd(EVENTS, {"payload": json.dumps(event)})
        r.set(f"job:{job_id}:result", json.dumps(event), ex=3600)
        if WORKER_ID:
            with db.cursor() as cur:
                cur.execute(
                    """UPDATE generation_jobs SET status='DONE', worker_id=%s, duration_ms=%s,
                       image_id=%s, updated_at=now() WHERE job_id=%s""",
                    (WORKER_ID, duration_ms, image_id, job_id),
                )
                cur.execute(
                    "UPDATE ai_workers SET total_generated=total_generated+1 WHERE worker_id=%s",
                    (WORKER_ID,),
                )
        r.xack(STREAM, GROUP, entry_id)
        print("DONE job", job_id, slug)
    except Exception as e:
        print("FAILED job", job_id, e)
        # do not ack -> XAUTOCLAIM will redeliver


def main():
    ensure_group()
    threading.Thread(target=heartbeat, daemon=True).start()
    print(f"worker {AI_CODE} started, worker_id={WORKER_ID}")
    while True:
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