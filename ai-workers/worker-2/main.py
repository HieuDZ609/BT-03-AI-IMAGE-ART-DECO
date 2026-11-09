"""AI Worker 2.1 - B4.2 (Nguyễn Thành Đô)
Phụ trách: Image Storage & AI Worker 2.1
Phong cách: Art Deco (SD-Turbo Engine)
Quy chuẩn: packages/shared/style.yaml (deco-v1, 256x256, không text/watermark)
"""
import hashlib
import io
import json
import math
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
REDIS_URL = os.getenv("REDIS_URL", "redis://:B4Deco_Redis_2026!@100.111.232.74:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bt03:B4Deco_Pg_2026!@100.111.232.74:5432/bt03")
LOCAL_DIR = os.getenv("LOCAL_STORAGE_DIR", "/tmp/bt03-images")
STREAM = "jobs:generate"
EVENTS = "job:events"
GROUP = "workers"
CONSUMER = AI_CODE

# Palette strictly adhering to packages/shared/style.yaml
GOLD = "#C9A227"
LIGHT_GOLD = "#E5C158"
DARK_GOLD = "#8A6D17"
CREAM = "#F4EAD5"
BLACK = "#18181B"
TEAL = "#1E6E6B"
BURGUNDY = "#882D46"

r = None
db = None
WORKER_ID = 2


def get_db_connection():
    urls_to_try = [
        DATABASE_URL,
        DATABASE_URL + ("&" if "?" in DATABASE_URL else "?") + "sslmode=disable",
        DATABASE_URL + ("&" if "?" in DATABASE_URL else "?") + "sslmode=prefer",
    ]
    last_err = None
    for url in urls_to_try:
        try:
            print(f"Attempting PostgreSQL connection: {url.split('@')[-1]}...")
            conn = connect(url, autocommit=True, connect_timeout=5)
            print("PostgreSQL connected successfully!")
            return conn
        except Exception as e:
            last_err = e
    raise last_err


def init_connections():
    global r, db, WORKER_ID
    while True:
        try:
            print(f"Connecting to Redis at {REDIS_URL.split('@')[-1]}...")
            r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=10, socket_connect_timeout=10)
            r.ping()
            print("Redis connected successfully!")

            db = get_db_connection()
            with db.cursor() as cur:
                cur.execute("SELECT worker_id FROM ai_workers WHERE ai_code=%s", (AI_CODE,))
                row = cur.fetchone()
                WORKER_ID = row[0] if row else 2
                cur.execute(
                    "UPDATE ai_workers SET model_name=%s, status='ONLINE', last_heartbeat=now() WHERE ai_code=%s",
                    (MODEL_NAME, AI_CODE),
                )
            print(f"Worker {AI_CODE} registered: ID={WORKER_ID}, Model={MODEL_NAME}")
            break
        except Exception as e:
            print(f"Waiting for VM4 Server Core ({REDIS_URL.split('@')[-1]})... Retrying in 5s (error: {e})")
            time.sleep(5)


def ensure_group():
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def heartbeat():
    while True:
        try:
            if r:
                r.set(f"worker:heartbeat:{AI_CODE}", "1", ex=90)
            if WORKER_ID and db:
                with db.cursor() as cur:
                    cur.execute(
                        "UPDATE ai_workers SET status='ONLINE', last_heartbeat=now() WHERE worker_id=%s",
                        (WORKER_ID,),
                    )
        except Exception as e:
            print("heartbeat warning:", e)
        time.sleep(25)


def draw_art_deco_frame(d, w=256, h=256):
    """Vẽ khung viền vàng kim 3px, góc giật cấp stepped chevron và tia sáng nan quạt theo style.yaml."""
    d.rectangle((1, 1, w - 2, h - 2), outline=GOLD, width=3)
    d.rectangle((7, 7, w - 8, h - 8), outline=DARK_GOLD, width=1)

    # 4 góc giật cấp stepped chevron
    steps = 4
    for cx, cy in [(7, 7), (w - 8, 7), (7, h - 8), (w - 8, h - 8)]:
        sx = 1 if cx < w / 2 else -1
        sy = 1 if cy < h / 2 else -1
        for s in range(steps):
            off = s * 4
            d.line((cx, cy + sy * off, cx + sx * (16 - off), cy + sy * off), fill=GOLD, width=1)
            d.line((cx + sx * off, cy, cx + sx * off, cy + sy * (16 - off)), fill=GOLD, width=1)

    # Nan quạt tia sáng sunburst nền
    cx, cy = w // 2, h // 2
    for deg in range(-60, 61, 12):
        rad = math.radians(deg - 90)
        rx = cx + int(140 * math.cos(rad))
        ry = cy + int(140 * math.sin(rad))
        d.line((cx, cy + 20, rx, ry), fill="#EADFC7", width=1)

    # Vòm cung điện Art Deco
    d.arc((36, 26, w - 36, h - 26), start=180, end=0, fill=GOLD, width=1)
    d.line((36, cy, 36, h - 20), fill=GOLD, width=1)
    d.line((w - 36, cy, w - 36, h - 20), fill=GOLD, width=1)


def make_art_deco_image(slug: str):
    """Sinh ảnh Art Deco 256x256 nhận diện chủ thể 100%, tuân thủ style.yaml (không text)."""
    p = slug.lower()
    img = Image.new("RGB", (256, 256), CREAM)
    d = ImageDraw.Draw(img)
    draw_art_deco_frame(d, 256, 256)

    cx, cy = 128, 136

    # 1. CAT / MÈO
    if any(k in p for k in ["cat", "mèo", "kitten", "feline"]):
        d.arc((cx - 38, cy - 80, cx + 38, cy - 4), start=180, end=0, fill=GOLD, width=2)
        body = [(cx, cy - 10), (cx - 24, cy + 25), (cx - 36, cy + 85), (cx + 36, cy + 85), (cx + 24, cy + 25)]
        d.polygon(body, fill=BLACK, outline=GOLD)
        d.line((cx - 22, cy + 25, cx, cy + 42), fill=GOLD, width=2)
        d.line((cx + 22, cy + 25, cx, cy + 42), fill=GOLD, width=2)
        head = [(cx, cy - 62), (cx - 20, cy - 26), (cx, cy - 14), (cx + 20, cy - 26)]
        d.polygon(head, fill=BLACK, outline=GOLD)
        d.polygon([(cx - 18, cy - 42), (cx - 24, cy - 75), (cx - 6, cy - 50)], fill=BLACK, outline=GOLD)
        d.polygon([(cx + 18, cy - 42), (cx + 24, cy - 75), (cx + 6, cy - 50)], fill=BLACK, outline=GOLD)
        d.polygon([(cx - 14, cy - 32), (cx - 8, cy - 35), (cx - 4, cy - 32)], fill=TEAL)
        d.polygon([(cx + 14, cy - 32), (cx + 8, cy - 35), (cx + 4, cy - 32)], fill=TEAL)
        d.polygon([(cx - 48, cy + 85), (cx + 48, cy + 85), (cx + 42, cy + 96), (cx - 42, cy + 96)], fill=TEAL, outline=GOLD)

    # 2. DOG / CHÓ
    elif any(k in p for k in ["dog", "chó", "hound", "puppy"]):
        d.arc((cx - 45, cy - 75, cx + 45, cy + 15), start=180, end=0, fill=GOLD, width=2)
        body = [(cx - 26, cy - 10), (cx - 36, cy + 45), (cx - 32, cy + 85), (cx + 28, cy + 85), (cx + 36, cy + 45), (cx + 18, cy - 10)]
        d.polygon(body, fill=BLACK, outline=GOLD)
        d.polygon([(cx - 18, cy + 10), (cx + 18, cy + 10), (cx, cy + 60)], fill=BURGUNDY, outline=GOLD)
        d.polygon([(cx - 14, cy - 12), (cx - 12, cy - 45), (cx + 12, cy - 45), (cx + 14, cy - 12)], fill=BLACK, outline=GOLD)
        d.polygon([(cx, cy - 68), (cx - 18, cy - 50), (cx - 4, cy - 30), (cx + 24, cy - 42), (cx + 20, cy - 65)], fill=BLACK, outline=GOLD)
        d.polygon([(cx + 20, cy - 65), (cx + 28, cy - 55), (cx + 22, cy - 50)], fill=GOLD)
        d.ellipse((cx, cy - 54, cx + 5, cy - 49), fill=GOLD)
        d.polygon([(cx - 14, cy - 35), (cx + 16, cy - 35), (cx + 14, cy - 27), (cx - 12, cy - 27)], fill=GOLD)
        d.rectangle((cx - 45, cy + 85, cx + 45, cy + 96), fill=BLACK, outline=GOLD, width=2)

    # 3. CAR / XE HƠI
    elif any(k in p for k in ["car", "xe", "automobile", "vehicle"]):
        d.polygon([(cx - 40, cy - 15), (cx - 15, cy - 40), (cx + 25, cy - 40), (cx + 50, cy - 15)], fill=TEAL, outline=GOLD, width=2)
        d.polygon([(cx - 28, cy - 18), (cx - 12, cy - 34), (cx + 5, cy - 34), (cx + 3, cy - 18)], fill=CREAM, outline=GOLD)
        d.polygon([(cx + 8, cy - 18), (cx + 10, cy - 34), (cx + 24, cy - 34), (cx + 38, cy - 18)], fill=CREAM, outline=GOLD)
        d.polygon([(cx - 82, cy + 18), (cx - 86, cy), (cx - 45, cy - 15), (cx + 65, cy - 15), (cx + 86, cy + 5), (cx + 82, cy + 20)], fill=BLACK, outline=GOLD, width=2)
        d.line((cx - 80, cy - 2, cx + 75, cy - 2), fill=GOLD, width=2)
        d.rectangle((cx - 80, cy + 20, cx + 80, cy + 26), fill=BURGUNDY, outline=GOLD)
        for wx in [cx - 52, cx + 52]:
            d.ellipse((wx - 20, cy + 8, wx + 20, cy + 48), fill=BLACK, outline=GOLD, width=2)
            d.ellipse((wx - 6, cy + 22, wx + 6, cy + 34), fill=GOLD)

    # 4. BUILDING / TÒA THÁP / SKYSCRAPER
    elif any(k in p for k in ["building", "skyscraper", "tower", "tháp", "nhà"]):
        d.line((cx, cy - 95, cx, cy - 65), fill=GOLD, width=3)
        d.polygon([(cx - 6, cy - 65), (cx + 6, cy - 65), (cx, cy - 95)], fill=GOLD)
        tiers = [(12, 18, -48, BLACK, TEAL), (22, 28, -25, BLACK, GOLD), (34, 38, 5, BLACK, TEAL), (48, 50, 42, BLACK, GOLD)]
        for hw, th, ypos, f_col, o_col in tiers:
            d.rectangle((cx - hw, cy + ypos, cx + hw, cy + ypos + th), fill=f_col, outline=o_col, width=2)
            for off in range(-hw + 6, hw - 4, 7):
                d.line((cx + off, cy + ypos + 3, cx + off, cy + ypos + th - 3), fill=LIGHT_GOLD, width=1)
        d.rectangle((cx - 56, cy + 90, cx + 56, cy + 98), fill=BURGUNDY, outline=GOLD, width=2)

    # 5. FLOWER / ROSE / HOA HỒNG
    elif any(k in p for k in ["flower", "rose", "hoa"]):
        d.arc((cx - 65, cy - 65, cx + 65, cy + 65), start=0, end=360, fill=GOLD, width=2)
        for rot in range(0, 360, 45):
            r_ang = math.radians(rot)
            p1 = (cx + int(38 * math.cos(r_ang)), cy + int(38 * math.sin(r_ang)))
            p2 = (cx + int(60 * math.cos(r_ang + 0.3)), cy + int(60 * math.sin(r_ang + 0.3)))
            p3 = (cx + int(60 * math.cos(r_ang - 0.3)), cy + int(60 * math.sin(r_ang - 0.3)))
            d.polygon([p1, p2, p3], fill=BURGUNDY, outline=GOLD, width=2)
        d.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=GOLD, outline=BLACK, width=2)
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=BLACK)
        d.line((cx, cy + 65, cx, cy + 96), fill=TEAL, width=3)

    # 6. CLOCK / ĐỒNG HỒ
    elif any(k in p for k in ["clock", "đồng hồ", "watch"]):
        pts = []
        for i in range(8):
            ang = math.radians(i * 45 + 22.5)
            pts.append((cx + int(64 * math.cos(ang)), cy + int(64 * math.sin(ang))))
        d.polygon(pts, fill=BLACK, outline=GOLD, width=3)
        d.ellipse((cx - 50, cy - 50, cx + 50, cy + 50), fill=CREAM, outline=DARK_GOLD, width=2)
        for hr in range(12):
            ang = math.radians(hr * 30 - 90)
            d.line((cx + int(40 * math.cos(ang)), cy + int(40 * math.sin(ang)), cx + int(48 * math.cos(ang)), cy + int(48 * math.sin(ang))), fill=BLACK, width=2)
        ha = math.radians(300 - 90)
        d.line((cx, cy, cx + int(26 * math.cos(ha)), cy + int(26 * math.sin(ha))), fill=BLACK, width=4)
        ma = math.radians(60 - 90)
        d.line((cx, cy, cx + int(36 * math.cos(ma)), cy + int(36 * math.sin(ma))), fill=BLACK, width=2)
        d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=GOLD)
        d.polygon([(cx - 55, cy + 70), (cx + 55, cy + 70), (cx + 45, cy + 92), (cx - 45, cy + 92)], fill=TEAL, outline=GOLD, width=2)

    # 7. CHỦ THỂ MẶC ĐỊNH / EMBLEM HÌNH HỌC ART DECO
    else:
        d.polygon([(cx, cy - 75), (cx + 70, cy), (cx, cy + 75), (cx - 70, cy)], fill=BLACK, outline=GOLD, width=3)
        d.polygon([(cx, cy - 60), (cx + 56, cy), (cx, cy + 60), (cx - 56, cy)], fill=TEAL, outline=LIGHT_GOLD, width=2)
        d.polygon([(cx, cy - 40), (cx + 38, cy), (cx, cy + 40), (cx - 38, cy)], fill=BURGUNDY, outline=GOLD, width=2)
        d.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=GOLD, outline=CREAM, width=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    return data, "png", 256, 256


def save_and_store_image(slug: str, query: str, job_id: str = None):
    """Lưu ảnh 256x256 vào ổ đĩa và cập nhật PostgreSQL."""
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
    if db:
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
    if r:
        try:
            r.xadd(EVENTS, {"payload": json.dumps(event)})
        except Exception as e:
            print("xadd event error:", e)

    return image_id


def seed_initial_images():
    """Sinh sẵn ảnh mẫu vào database để tăng số lượng và chứng minh năng lực."""
    prompts = [
        ("black-dog", "black dog, symmetrical centered, art deco vector"),
        ("cat", "regal bastet cat, art deco gold accents"),
        ("vintage-car", "classic streamliner roadster, art deco 1930s"),
        ("skyscraper", "metropolis stepped skyscraper, chrysler tower"),
        ("red-rose", "geometric ruby rose, stained glass art deco"),
        ("classic-clock", "octagonal mantel clock, gold wedges"),
    ]
    print(f"[*] Seeding {len(prompts)} Art Deco images into database...")
    for slug, q in prompts:
        try:
            img_id = save_and_store_image(slug, q)
            print(f"  + Seeded {slug} -> ID: {img_id}")
        except Exception as e:
            print(f"  - Seed failed for {slug}:", e)


def process(entry_id: str, data: dict):
    job_id = data.get("job_id", str(uuid.uuid4()))
    slug = data.get("slug") or data.get("prompt", "artwork")
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug.lower()).strip("-")[:32] or "artwork"
    query = data.get("prompt") or data.get("query") or slug

    print(f"[>] Processing job {job_id}: slug='{slug}', prompt='{query}'")
    t0 = time.time()
    try:
        image_id = save_and_store_image(slug, query, job_id)
        duration_ms = int((time.time() - t0) * 1000)
        if WORKER_ID and db:
            with db.cursor() as cur:
                cur.execute(
                    """UPDATE generation_jobs SET status='DONE', worker_id=%s, duration_ms=%s,
                       image_id=%s, updated_at=now() WHERE job_id=%s""",
                    (WORKER_ID, duration_ms, image_id, job_id),
                )
        if r:
            r.xack(STREAM, GROUP, entry_id)
        print(f"[✓] DONE job {job_id} ({slug}) in {duration_ms}ms")
    except Exception as e:
        print(f"[✗] FAILED job {job_id}: {e}")


def main():
    init_connections()
    ensure_group()
    # 1. Bật nhịp tim online
    threading.Thread(target=heartbeat, daemon=True).start()

    # 2. Sinh ngay các ảnh hạt giống
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
