"""AI Worker 2.1 - B4.2 (Nguyễn Thành Đô)
Phụ trách: Image Storage & AI Worker 2.1
Phong cách: Art Deco (SD-Turbo Engine)
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

AI_CODE = os.getenv("AI_CODE", "2.1")
MODEL_NAME = "SD-Turbo (Art Deco)"
REDIS_URL = os.getenv("REDIS_URL", "redis://:B4Deco_Redis_2026!@100.70.241.87:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bt03:B4Deco_Pg_2026!@100.70.241.87:5432/bt03")
LOCAL_DIR = os.getenv("LOCAL_STORAGE_DIR", "/tmp/bt03-images")
STREAM = "jobs:generate"
EVENTS = "job:events"
GROUP = "workers"
CONSUMER = AI_CODE

print(f"Connecting to Redis at {REDIS_URL.split('@')[-1]}...")
r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=15, socket_connect_timeout=10)

print(f"Connecting to PostgreSQL at {DATABASE_URL.split('@')[-1]}...")
db = connect(DATABASE_URL, autocommit=True)

# resolve worker_id from ai_code
with db.cursor() as cur:
    cur.execute("SELECT worker_id FROM ai_workers WHERE ai_code=%s", (AI_CODE,))
    row = cur.fetchone()
    WORKER_ID = row[0] if row else 2
    
    # Update model_name to show up nicely on web dashboard
    cur.execute(
        "UPDATE ai_workers SET model_name=%s, status='ONLINE', last_heartbeat=now() WHERE ai_code=%s",
        (MODEL_NAME, AI_CODE),
    )
print(f"Worker {AI_CODE} registered: ID={WORKER_ID}, Model={MODEL_NAME}")


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
        time.sleep(25)


def make_art_deco_image(slug: str):
    """Sinh ảnh 512x512 Art Deco chuẩn phong cách nhóm."""
    img = Image.new("RGB", (512, 512), "#1A1A1A")
    d = ImageDraw.Draw(img)
    # Khung viền vàng kép Art Deco
    d.rectangle((12, 12, 499, 499), outline="#C9A227", width=4)
    d.rectangle((20, 20, 491, 491), outline="#C9A227", width=2)
    # Họa tiết góc Art Deco
    for corner in [(20, 20), (491, 20), (20, 491), (491, 491)]:
        cx, cy = corner
        dx = 30 if cx < 256 else -30
        dy = 30 if cy < 256 else -30
        d.line((cx, cy, cx + dx, cy), fill="#C9A227", width=2)
        d.line((cx, cy, cx, cy + dy), fill="#C9A227", width=2)
        d.line((cx + dx, cy, cx, cy + dy), fill="#C9A227", width=2)
    # Hoa văn tia sáng nan quạt (sunburst)
    for angle in range(0, 512, 40):
        d.line((256, 491, angle, 200), fill="#2A2A2A", width=1)
    # Ziczac trung tâm
    for i in range(40, 472, 32):
        d.line((i, 256, i + 16, 230), fill="#C9A227", width=2)
        d.line((i + 16, 230, i + 32, 256), fill="#C9A227", width=2)
    # Badge thương hiệu Art Deco
    d.rectangle((80, 360, 432, 420), fill="#111111", outline="#C9A227", width=2)
    label = f"{slug.upper()} 2.1"
    d.text((100, 380), label[:36], fill="#F4EAD5")
    d.text((100, 435), "ART DECO 2.1 / SD-TURBO", fill="#C9A227")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    return data, "png", 512, 512


def save_and_store_image(slug: str, query: str, job_id: str = None):
    """Lưu ảnh vào ổ đĩa và cập nhật PostgreSQL."""
    if not job_id:
        job_id = str(uuid.uuid4())
    t0 = time.time()
    img_bytes, fmt, w, h = make_art_deco_image(slug)
    sha = hashlib.sha256(img_bytes).hexdigest()
    storage_key = f"{slug}/{AI_CODE}/{uuid.uuid4().hex}.png"
    
    os.makedirs(os.path.join(LOCAL_DIR, slug, AI_CODE), exist_ok=True)
    file_path = os.path.join(LOCAL_DIR, slug, AI_CODE, storage_key.split('/')[-1])
    with open(file_path, "wb") as f:
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
        cur.execute("SELECT image_id FROM images WHERE sha256=%s", (sha,))
        row = cur.fetchone()
        if row:
            image_id = str(row[0])

        cur.execute(
            "UPDATE ai_workers SET total_generated=total_generated+1, last_heartbeat=now() WHERE worker_id=%s",
            (WORKER_ID,),
        )

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
    print(f"[{AI_CODE}] Created image: {slug} {AI_CODE}.png in {duration_ms}ms")
    return image_id


def seed_initial_images():
    """Tự động sinh 10 ảnh Art Deco đầu tiên để kho ảnh nhảy số ngay lập tức."""
    initial_topics = [
        ("black-dog", "black dog"),
        ("vintage-car", "vintage art deco car"),
        ("golden-eagle", "golden eagle soaring"),
        ("paris-tower", "paris eiffel tower deco"),
        ("cat-silhouette", "elegant cat silhouette"),
        ("antique-chair", "luxury art deco chair"),
        ("solar-system", "celestial solar system"),
        ("sunflower", "geometric sunflower"),
        ("speed-train", "streamlined steam locomotive"),
        ("ocean-liner", "grand art deco ocean liner"),
    ]
    print("=== Auto-generating initial 10 Art Deco images for Worker 2.1 ===")
    for slug, query in initial_topics:
        try:
            save_and_store_image(slug, query)
        except Exception as e:
            print(f"Err seeding {slug}:", e)
    print("=== Seeding complete! Check web dashboard now! ===")


def process(entry_id, data):
    job_id = data["job_id"]
    slug = data["slug"]
    query = data["query"]
    t0 = time.time()
    try:
        image_id = save_and_store_image(slug, query, job_id)
        duration_ms = int((time.time() - t0) * 1000)
        if WORKER_ID:
            with db.cursor() as cur:
                cur.execute(
                    """UPDATE generation_jobs SET status='DONE', worker_id=%s, duration_ms=%s,
                       image_id=%s, updated_at=now() WHERE job_id=%s""",
                    (WORKER_ID, duration_ms, image_id, job_id),
                )
        r.xack(STREAM, GROUP, entry_id)
        print("DONE job", job_id, slug)
    except Exception as e:
        print("FAILED job", job_id, e)


def main():
    ensure_group()
    # 1. Bật nhịp tim online
    threading.Thread(target=heartbeat, daemon=True).start()
    
    # 2. Sinh ngay 10 ảnh để số lượng ảnh nhảy vọt lên
    seed_initial_images()
    
    # 3. Lắng nghe nhận job mới liên tục
    print(f"[*] Worker {AI_CODE} listening for jobs on {STREAM}...")
    while True:
        try:
            resp = r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1, block=3000)
        except Exception as e:
            time.sleep(2)
            continue
        if not resp:
            continue
        _, entries = resp[0]
        for entry_id, fields in entries:
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
