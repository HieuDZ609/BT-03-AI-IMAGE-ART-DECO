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
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone

import redis
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
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

# SSH sync sang VM4 (giống B4.1)
STORAGE_SSH_TARGET = os.getenv("STORAGE_SSH_TARGET", "root@100.111.232.74")
STORAGE_REMOTE_DIR = os.getenv("STORAGE_REMOTE_DIR", "/var/lib/bt03/images")

# Palette strictly adhering to packages/shared/style.yaml
GOLD = "#C9A227"
LIGHT_GOLD = "#E5C158"
DARK_GOLD = "#8A6D17"
CREAM = "#F4EAD5"
BLACK = "#18181B"
TEAL = "#1E6E6B"
DARK_TEAL = "#0F3D3B"
BURGUNDY = "#882D46"
PALE_GOLD = "#F0E0A0"

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


def draw_sunburst_bg(d, cx=128, cy=128):
    """Nền tia sáng nan quạt xen kẽ 2 màu, đẹp hơn hẳn."""
    for i in range(72):
        a_start = i * 5
        a_end = a_start + 5
        col = "#EDE3CA" if i % 2 == 0 else CREAM
        pts = [(cx, cy)]
        for a in range(a_start, a_end + 1):
            rad = math.radians(a)
            pts.append((int(cx + 200 * math.cos(rad)), int(cy + 200 * math.sin(rad))))
        if len(pts) > 2:
            d.polygon(pts, fill=col)


def draw_art_deco_border(d, w=256, h=256):
    """Khung Art Deco 5 lớp, góc giật cấp 6 bước, hoa văn ở cạnh."""
    layers = [
        (0, 0, w - 1, h - 1, GOLD, 4),
        (5, 5, w - 6, h - 6, BLACK, 1),
        (7, 7, w - 8, h - 8, GOLD, 2),
        (11, 11, w - 12, h - 12, DARK_GOLD, 1),
        (14, 14, w - 15, h - 15, GOLD, 1),
    ]
    for x0, y0, x1, y1, col, width in layers:
        d.rectangle((x0, y0, x1, y1), outline=col, width=width)
    # Corner stepped chevrons
    for fcx, fcy in [(16, 16), (w - 16, 16), (16, h - 16), (w - 16, h - 16)]:
        sx = 1 if fcx < w / 2 else -1
        sy = 1 if fcy < h / 2 else -1
        for s in range(6):
            off = s * 4
            ln = 24 - off
            if ln <= 0:
                break
            d.line([(fcx, fcy + sy * off), (fcx + sx * ln, fcy + sy * off)], fill=GOLD, width=1)
            d.line([(fcx + sx * off, fcy), (fcx + sx * off, fcy + sy * ln)], fill=GOLD, width=1)
        d.polygon([(fcx - 4, fcy), (fcx, fcy - 4), (fcx + 4, fcy), (fcx, fcy + 4)], fill=GOLD)
    # Mid-side diamond ornaments
    for px, py in [(w // 2, 7), (w // 2, h - 8), (7, h // 2), (w - 8, h // 2)]:
        d.polygon([(px, py - 5), (px + 5, py), (px, py + 5), (px - 5, py)], fill=GOLD)


def generate_sd_image(query: str, slug: str = None):
    """Sinh ảnh bằng SD-Turbo GGUF qua SSH trực tiếp trên VM4 (tránh lỗi GLIBC_2.38)."""
    clean_concept = query.replace("-", " ").replace("_", " ").strip()
    positive = (
        f"Premium professional illustration of {clean_concept}, subject immediately recognizable, "
        f"natural proportions, rich details and textures, vibrant harmonious colors, "
        f"beautiful Art Deco poster design, elegant geometric ornaments, subtle retro pop art accents, "
        f"refined lighting, crisp detailed artwork, sophisticated composition, strong focal point, "
        f"polished commercial illustration, clean complementary background, no text, no watermark"
    )
    negative = (
        "blurry, low quality, distorted, messy, complex background, extra objects, "
        "multiple subjects, text, letters, watermark, signature, bad proportions, "
        "noisy details, oversaturated"
    )

    remote_tmp = f"/tmp/sd_{uuid.uuid4().hex[:8]}.png"
    sd_cmd = (
        f"LD_LIBRARY_PATH=/opt/bt03/ai/bin /opt/bt03/ai/bin/sd-cli "
        f"-m /opt/bt03/ai/models/sd-turbo-q8_0.gguf "
        f"-W 512 -H 512 --cfg-scale 1.0 --steps 4 --sampling-method euler "
        f"-t 4 -s -1 -o {remote_tmp} "
        f"-p \"{positive}\" -n \"{negative}\""
    )

    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        STORAGE_SSH_TARGET, sd_cmd
    ]

    try:
        print(f"  [SD-Turbo 🎨] Calling SD-Turbo on VM4 for '{clean_concept}'...")
        proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            err = proc.stderr[-200:] if proc.stderr else proc.stdout[-200:]
            print(f"  [SD-Turbo ⚠️] Remote SD failed: {err}")
            return None

        # Kéo ảnh kết quả về để hậu kỳ Pillow
        with tempfile.TemporaryDirectory(prefix="bt03-sd-") as td:
            local_tmp = os.path.join(td, "out.png")
            scp_cmd = [
                "scp", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                f"{STORAGE_SSH_TARGET}:{remote_tmp}", local_tmp
            ]
            subprocess.run(scp_cmd, check=True, timeout=20, capture_output=True)
            # Dọn dẹp file tạm trên VM4
            subprocess.run(
                ["ssh", "-o", "BatchMode=yes", STORAGE_SSH_TARGET, f"rm -f {remote_tmp}"],
                check=False, timeout=10
            )

            with Image.open(local_tmp) as im:
                im = im.convert("RGB")
                # Hậu kỳ Pillow theo chuẩn Worker 1.1:
                im = ImageOps.autocontrast(im, cutoff=0.2)
                im = ImageEnhance.Color(im).enhance(1.15)
                im = ImageEnhance.Contrast(im).enhance(1.07)
                im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))

                # Viền vàng Art Deco sang trọng quanh ảnh
                w, h = im.size
                d = ImageDraw.Draw(im)
                d.rectangle((1, 1, w - 2, h - 2), outline="#C9A227", width=4)
                d.rectangle((6, 6, w - 7, h - 7), outline="#8A6D17", width=1)
                d.rectangle((8, 8, w - 9, h - 9), outline="#C9A227", width=1)

                buf = io.BytesIO()
                im.save(buf, format="PNG", optimize=True)
                print(f"  [SD-Turbo ✨] Masterpiece sinh thành công ({w}x{h})!")
                return buf.getvalue(), "png", w, h
    except Exception as e:
        print(f"  [SD-Turbo ⚠️] Exception: {e}")
        return None


def make_art_deco_image(slug: str, query: str = None):
    """Sinh ảnh Art Deco: ưu tiên SD-Turbo thật (qua VM4), fallback sang procedural vector."""
    concept = query or slug
    sd_res = generate_sd_image(concept, slug)
    if sd_res:
        return sd_res

    p = slug.lower()
    img = Image.new("RGB", (256, 256), CREAM)
    d = ImageDraw.Draw(img)
    # Nền sunburst trước, rồi vẽ border lên
    draw_sunburst_bg(d, 128, 128)
    draw_art_deco_border(d, 256, 256)

    cx, cy = 128, 136

    # 1. CAT — Egyptian Bastet Art Deco
    if any(k in p for k in ["cat", "mèo", "kitten", "feline", "bastet"]):
        # Body — elegant vase silhouette
        body = [(cx, cy - 20), (cx - 16, cy - 10), (cx - 28, cy + 20),
                (cx - 32, cy + 70), (cx - 36, cy + 85), (cx + 36, cy + 85),
                (cx + 32, cy + 70), (cx + 28, cy + 20), (cx + 16, cy - 10)]
        d.polygon(body, fill=BLACK, outline=GOLD, width=2)
        # Chest jewel
        d.polygon([(cx, cy + 15), (cx - 10, cy + 35), (cx, cy + 50), (cx + 10, cy + 35)],
                  fill=BURGUNDY, outline=GOLD, width=1)
        # Gem collar
        gem_colors = [TEAL, GOLD, BURGUNDY, GOLD, TEAL, GOLD, BURGUNDY]
        for i, offset in enumerate(range(-3, 4)):
            x = cx + offset * 8
            d.ellipse((x - 5, cy - 18, x + 5, cy - 8), fill=gem_colors[i], outline=GOLD, width=1)
        # Head
        d.ellipse((cx - 28, cy - 78, cx + 28, cy - 28), fill=BLACK, outline=GOLD, width=2)
        # Ears
        d.polygon([(cx - 16, cy - 72), (cx - 28, cy - 98), (cx - 6, cy - 74)], fill=BLACK, outline=GOLD, width=1)
        d.polygon([(cx + 16, cy - 72), (cx + 28, cy - 98), (cx + 6, cy - 74)], fill=BLACK, outline=GOLD, width=1)
        d.polygon([(cx - 14, cy - 73), (cx - 22, cy - 90), (cx - 8, cy - 73)], fill=BURGUNDY)
        d.polygon([(cx + 14, cy - 73), (cx + 22, cy - 90), (cx + 8, cy - 73)], fill=BURGUNDY)
        # Almond eyes
        d.polygon([(cx - 20, cy - 54), (cx - 12, cy - 60), (cx - 4, cy - 54), (cx - 12, cy - 48)],
                  fill=TEAL, outline=GOLD, width=1)
        d.polygon([(cx + 4, cy - 54), (cx + 12, cy - 60), (cx + 20, cy - 54), (cx + 12, cy - 48)],
                  fill=TEAL, outline=GOLD, width=1)
        d.ellipse((cx - 14, cy - 56, cx - 10, cy - 52), fill=BLACK)
        d.ellipse((cx + 10, cy - 56, cx + 14, cy - 52), fill=BLACK)
        d.ellipse((cx - 13, cy - 55, cx - 12, cy - 54), fill=CREAM)
        d.ellipse((cx + 12, cy - 55, cx + 13, cy - 54), fill=CREAM)
        # Nose
        d.polygon([(cx, cy - 45), (cx - 4, cy - 40), (cx + 4, cy - 40)], fill=BURGUNDY)
        # Crown
        for i in range(5):
            x = cx + (i - 2) * 10
            d.polygon([(x, cy - 80), (x - 4, cy - 93), (x + 4, cy - 93)], fill=GOLD)
        d.line([(cx - 24, cy - 80), (cx + 24, cy - 80)], fill=GOLD, width=2)
        # Base plinth
        d.rectangle((cx - 40, cy + 85, cx + 40, cy + 97), fill=BLACK, outline=GOLD, width=2)
        d.rectangle((cx - 35, cy + 90, cx + 35, cy + 97), fill=TEAL, outline=GOLD, width=1)
        d.ellipse((cx - 36, cy + 80, cx - 20, cy + 88), fill=BLACK, outline=GOLD, width=1)
        d.ellipse((cx + 20, cy + 80, cx + 36, cy + 88), fill=BLACK, outline=GOLD, width=1)

    # 2. DOG — Art Deco Noble Hound
    elif any(k in p for k in ["dog", "chó", "hound", "puppy"]):
        # Body
        body = [(cx - 28, cy - 15), (cx - 32, cy + 20), (cx - 28, cy + 70),
                (cx + 28, cy + 70), (cx + 32, cy + 20), (cx + 28, cy - 15),
                (cx + 20, cy - 25), (cx - 20, cy - 25)]
        d.polygon(body, fill=BLACK, outline=GOLD, width=2)
        # Chest shield
        d.polygon([(cx, cy - 10), (cx - 15, cy + 20), (cx, cy + 45), (cx + 15, cy + 20)],
                  fill=BURGUNDY, outline=GOLD, width=1)
        # Collar
        d.rectangle((cx - 24, cy - 30, cx + 24, cy - 20), fill=TEAL, outline=GOLD, width=2)
        d.ellipse((cx - 5, cy - 26, cx + 5, cy - 16), fill=GOLD, outline=DARK_GOLD, width=1)
        # Head
        d.ellipse((cx - 26, cy - 80, cx + 26, cy - 25), fill=BLACK, outline=GOLD, width=2)
        # Muzzle
        d.ellipse((cx - 14, cy - 55, cx + 14, cy - 36), fill=BLACK, outline=GOLD, width=1)
        d.ellipse((cx - 8, cy - 54, cx + 8, cy - 46), fill="#333340", outline=GOLD, width=1)
        # Eyes
        d.ellipse((cx - 20, cy - 72, cx - 10, cy - 62), fill=GOLD, outline=DARK_GOLD, width=1)
        d.ellipse((cx + 10, cy - 72, cx + 20, cy - 62), fill=GOLD, outline=DARK_GOLD, width=1)
        d.ellipse((cx - 17, cy - 69, cx - 13, cy - 65), fill=BLACK)
        d.ellipse((cx + 13, cy - 69, cx + 17, cy - 65), fill=BLACK)
        d.ellipse((cx - 16, cy - 68, cx - 15, cy - 67), fill=CREAM)
        d.ellipse((cx + 15, cy - 68, cx + 16, cy - 67), fill=CREAM)
        # Ears
        d.polygon([(cx - 18, cy - 72), (cx - 30, cy - 45), (cx - 20, cy - 25), (cx - 14, cy - 55)],
                  fill=BLACK, outline=GOLD, width=1)
        d.polygon([(cx + 18, cy - 72), (cx + 30, cy - 45), (cx + 20, cy - 25), (cx + 14, cy - 55)],
                  fill=BLACK, outline=GOLD, width=1)
        # Legs + paws
        for lx in [cx - 20, cx + 20]:
            d.rectangle((lx - 8, cy + 70, lx + 8, cy + 90), fill=BLACK, outline=GOLD, width=1)
            d.ellipse((lx - 10, cy + 86, lx + 10, cy + 96), fill=BLACK, outline=GOLD, width=1)
        d.rectangle((cx - 42, cy + 94, cx + 42, cy + 102), fill=TEAL, outline=GOLD, width=2)

    # 3. CAR — Art Deco Streamliner
    elif any(k in p for k in ["car", "xe", "automobile", "vehicle"]):
        # Road base
        d.rectangle((cx - 90, cy + 42, cx + 90, cy + 52), fill=DARK_GOLD, outline=GOLD, width=1)
        # Shadow
        d.ellipse((cx - 60, cy + 36, cx + 60, cy + 48), fill=DARK_GOLD)
        # Body streamlined
        body = [(cx - 85, cy + 30), (cx - 70, cy + 10), (cx - 30, cy - 25),
                (cx + 20, cy - 30), (cx + 65, cy - 20), (cx + 90, cy + 5),
                (cx + 90, cy + 32), (cx - 85, cy + 32)]
        d.polygon(body, fill=BLACK, outline=GOLD, width=2)
        # Cabin
        cabin = [(cx - 20, cy + 10), (cx - 10, cy - 22),
                 (cx + 30, cy - 26), (cx + 55, cy + 10)]
        d.polygon(cabin, fill=TEAL, outline=GOLD, width=2)
        # Windows
        d.polygon([(cx - 5, cy + 8), (cx + 2, cy - 18),
                   (cx + 22, cy - 22), (cx + 25, cy + 8)], fill=DARK_TEAL, outline=GOLD, width=1)
        d.polygon([(cx + 28, cy + 8), (cx + 30, cy - 20),
                   (cx + 50, cy - 15), (cx + 52, cy + 8)], fill=DARK_TEAL, outline=GOLD, width=1)
        # Fender stripe
        d.line([(cx - 80, cy + 15), (cx - 50, cy - 5), (cx + 70, cy - 5)], fill=GOLD, width=2)
        # Grille
        d.rectangle((cx + 72, cy + 5, cx + 90, cy + 28), fill=CREAM, outline=GOLD, width=1)
        for gy in range(cy + 8, cy + 28, 5):
            d.line([(cx + 72, gy), (cx + 90, gy)], fill=DARK_GOLD, width=1)
        # Bumpers
        d.rectangle((cx - 90, cy + 28, cx - 82, cy + 35), fill=CREAM, outline=GOLD, width=1)
        d.rectangle((cx + 82, cy + 28, cx + 90, cy + 35), fill=CREAM, outline=GOLD, width=1)
        # Wheels with spokes
        for wx in [cx - 50, cx + 45]:
            wy = cy + 32
            d.ellipse((wx - 22, wy - 14, wx + 22, wy + 14), fill=BLACK, outline=GOLD, width=3)
            d.ellipse((wx - 15, wy - 10, wx + 15, wy + 10), fill=DARK_GOLD, outline=GOLD, width=1)
            d.ellipse((wx - 6, wy - 4, wx + 6, wy + 4), fill=GOLD)
            for sa in range(0, 360, 45):
                ar = math.radians(sa)
                d.line([(int(wx + 5 * math.cos(ar)), int(wy + 4 * math.sin(ar))),
                        (int(wx + 13 * math.cos(ar)), int(wy + 9 * math.sin(ar)))],
                       fill=GOLD, width=1)
        # Exhaust ports
        for ev in [cy - 5, cy + 2, cy + 9]:
            d.rectangle((cx - 85, ev, cx - 65, ev + 4), fill=GOLD, outline=DARK_GOLD, width=1)

    # 4. SKYSCRAPER — Art Deco Ziggurat
    elif any(k in p for k in ["building", "skyscraper", "tower", "tháp", "nhà"]):
        # Ziggurat tiers — more elaborate
        tiers = [
            (8, 15, cy - 100, BLACK, GOLD),
            (14, 18, cy - 85, TEAL, GOLD),
            (22, 20, cy - 67, BLACK, GOLD),
            (32, 20, cy - 47, TEAL, GOLD),
            (44, 22, cy - 25, BLACK, GOLD),
            (58, 24, cy - 1, TEAL, GOLD),
            (74, 28, cy + 23, BLACK, GOLD),
            (88, 20, cy + 51, TEAL, GOLD),
        ]
        for hw, th, top_y, fc, oc in tiers:
            d.rectangle((cx - hw, top_y, cx + hw, top_y + th), fill=fc, outline=oc, width=2)
            if hw > 15:
                for col_x in range(cx - hw + 8, cx + hw - 6, 10):
                    d.rectangle((col_x, top_y + 3, col_x + 5, top_y + th - 3),
                                 fill=LIGHT_GOLD, outline=DARK_GOLD, width=1)
        # Antenna spire
        d.line([(cx, cy - 115), (cx, cy - 100)], fill=GOLD, width=2)
        d.polygon([(cx, cy - 120), (cx - 4, cy - 105), (cx + 4, cy - 105)], fill=GOLD)
        d.ellipse((cx - 3, cy - 123, cx + 3, cy - 117), fill=LIGHT_GOLD)
        # Entrance arch
        d.arc((cx - 18, cy + 62, cx + 18, cy + 90), start=180, end=0, fill=GOLD, width=2)
        d.line([(cx - 18, cy + 76), (cx - 18, cy + 90)], fill=GOLD, width=2)
        d.line([(cx + 18, cy + 76), (cx + 18, cy + 90)], fill=GOLD, width=2)
        d.rectangle((cx - 90, cy + 71, cx + 90, cy + 80), fill=BURGUNDY, outline=GOLD, width=2)

    # 5. ROSE / FLOWER — Geometric Art Deco Bloom
    elif any(k in p for k in ["flower", "rose", "hoa"]):
        # Stem and leaves
        d.line([(cx, cy + 68), (cx, cy + 100)], fill=TEAL, width=4)
        d.polygon([(cx, cy + 65), (cx - 25, cy + 48), (cx - 15, cy + 78)], fill=TEAL, outline=GOLD, width=1)
        d.polygon([(cx, cy + 65), (cx + 25, cy + 48), (cx + 15, cy + 78)], fill=TEAL, outline=GOLD, width=1)
        # Outer petals (8)
        for i in range(8):
            ang = math.radians(i * 45)
            pts = [
                (int(cx + 20 * math.cos(ang)), int(cy + 20 * math.sin(ang))),
                (int(cx + 55 * math.cos(ang + 0.3)), int(cy + 55 * math.sin(ang + 0.3))),
                (int(cx + 68 * math.cos(ang)), int(cy + 68 * math.sin(ang))),
                (int(cx + 55 * math.cos(ang - 0.3)), int(cy + 55 * math.sin(ang - 0.3))),
            ]
            d.polygon(pts, fill=BURGUNDY, outline=GOLD, width=2)
        # Middle petals (8)
        for i in range(8):
            ang = math.radians(i * 45 + 22.5)
            pts = [
                (int(cx + 14 * math.cos(ang)), int(cy + 14 * math.sin(ang))),
                (int(cx + 38 * math.cos(ang + 0.25)), int(cy + 38 * math.sin(ang + 0.25))),
                (int(cx + 46 * math.cos(ang)), int(cy + 46 * math.sin(ang))),
                (int(cx + 38 * math.cos(ang - 0.25)), int(cy + 38 * math.sin(ang - 0.25))),
            ]
            d.polygon(pts, fill=LIGHT_GOLD, outline=DARK_GOLD, width=1)
        # Outer ring
        d.arc((cx - 70, cy - 70, cx + 70, cy + 70), start=0, end=360, fill=GOLD, width=2)
        d.arc((cx - 56, cy - 56, cx + 56, cy + 56), start=0, end=360, fill=DARK_GOLD, width=1)
        # Center gem
        d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=GOLD, outline=BLACK, width=2)
        d.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=BURGUNDY, outline=GOLD, width=1)
        for i in range(6):
            ang = math.radians(i * 60)
            d.line([(cx, cy), (int(cx + 9 * math.cos(ang)), int(cy + 9 * math.sin(ang)))],
                   fill=DARK_GOLD, width=1)

    # 6. CLOCK — Ornate Octagonal Mantel Clock
    elif any(k in p for k in ["clock", "đồng hồ", "watch"]):
        # Outer octagon body
        oct_pts = [(int(cx + 72 * math.cos(math.radians(i * 45 - 22.5))),
                    int(cy + 72 * math.sin(math.radians(i * 45 - 22.5)))) for i in range(8)]
        d.polygon(oct_pts, fill=BLACK, outline=GOLD, width=3)
        oct2_pts = [(int(cx + 62 * math.cos(math.radians(i * 45 - 22.5))),
                     int(cy + 62 * math.sin(math.radians(i * 45 - 22.5)))) for i in range(8)]
        d.polygon(oct2_pts, fill=TEAL, outline=GOLD, width=1)
        # Clock face
        d.ellipse((cx - 54, cy - 54, cx + 54, cy + 54), fill=CREAM, outline=DARK_GOLD, width=2)
        # Hour markers
        for hr in range(12):
            ang = math.radians(hr * 30 - 90)
            mx, my = int(cx + 44 * math.cos(ang)), int(cy + 44 * math.sin(ang))
            if hr % 3 == 0:
                d.polygon([(mx, my - 6), (mx + 4, my), (mx, my + 6), (mx - 4, my)], fill=BLACK)
            else:
                d.polygon([(mx, my - 3), (mx + 2, my), (mx, my + 3), (mx - 2, my)], fill=DARK_GOLD)
        # Hands
        ha = math.radians(300 - 90)
        d.line([(cx, cy), (int(cx + 28 * math.cos(ha)), int(cy + 28 * math.sin(ha)))],
               fill=BLACK, width=4)
        ma = math.radians(60 - 90)
        d.line([(cx, cy), (int(cx + 40 * math.cos(ma)), int(cy + 40 * math.sin(ma)))],
               fill=BLACK, width=2)
        d.line([(cx, cy), (int(cx + 44 * math.cos(math.radians(90))),
                           int(cy + 44 * math.sin(math.radians(90))))], fill=BURGUNDY, width=1)
        d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=GOLD, outline=BLACK, width=1)
        d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=BLACK)
        # Base/stand
        d.polygon([(cx - 15, cy + 73), (cx + 15, cy + 73),
                   (cx + 30, cy + 92), (cx - 30, cy + 92)], fill=BLACK, outline=GOLD, width=2)
        d.rectangle((cx - 36, cy + 92, cx + 36, cy + 102), fill=TEAL, outline=GOLD, width=2)

    # 7. SWORD — Art Deco Golden Sword
    elif any(k in p for k in ["sword", "kiếm", "blade", "golden-sword"]):
        # Blade — tapered polygon
        blade = [(cx - 10, cy + 15), (cx + 10, cy + 15),
                 (cx + 5, cy - 55), (cx, cy - 100), (cx - 5, cy - 55)]
        d.polygon(blade, fill=LIGHT_GOLD, outline=GOLD, width=2)
        # Blade fuller
        d.polygon([(cx - 3, cy + 10), (cx + 3, cy + 10),
                   (cx + 1, cy - 85), (cx, cy - 98), (cx - 1, cy - 85)],
                  fill=PALE_GOLD, outline=DARK_GOLD, width=1)
        # Edge highlight
        d.line([(cx - 7, cy + 12), (cx - 2, cy - 80)], fill=CREAM, width=1)
        # Runes on blade
        for ry in [cy - 10, cy - 30, cy - 50]:
            d.polygon([(cx, ry), (cx - 6, ry + 8), (cx + 6, ry + 8)], fill=GOLD, outline=DARK_GOLD, width=1)
        # Crossguard with wing extensions
        d.polygon([(cx - 50, cy + 18), (cx - 42, cy + 10), (cx - 20, cy + 25),
                   (cx - 20, cy + 32), (cx - 42, cy + 25)], fill=GOLD, outline=DARK_GOLD, width=2)
        d.polygon([(cx + 50, cy + 18), (cx + 42, cy + 10), (cx + 20, cy + 25),
                   (cx + 20, cy + 32), (cx + 42, cy + 25)], fill=GOLD, outline=DARK_GOLD, width=2)
        d.rectangle((cx - 20, cy + 12, cx + 20, cy + 32), fill=GOLD, outline=DARK_GOLD, width=2)
        d.ellipse((cx - 8, cy + 17, cx + 8, cy + 27), fill=TEAL, outline=GOLD, width=1)
        # Grip
        for i in range(5):
            y = cy + 32 + i * 10
            col = GOLD if i % 2 == 0 else DARK_GOLD
            d.rectangle((cx - 7, y, cx + 7, y + 9), fill=col, outline=DARK_GOLD, width=1)
        # Pommel
        d.ellipse((cx - 16, cy + 82, cx + 16, cy + 100), fill=GOLD, outline=DARK_GOLD, width=2)
        d.ellipse((cx - 9, cy + 86, cx + 9, cy + 96), fill=BURGUNDY, outline=GOLD, width=1)
        # Base
        d.rectangle((cx - 40, cy + 98, cx + 40, cy + 108), fill=BLACK, outline=GOLD, width=2)

    # 8. DEFAULT — Art Deco 8-pointed Star Emblem
    else:
        # 8-pointed star
        for ang_deg in range(0, 360, 45):
            ang = math.radians(ang_deg)
            d.polygon([
                (int(cx + 8 * math.cos(ang + math.pi / 2)), int(cy + 8 * math.sin(ang + math.pi / 2))),
                (int(cx + 80 * math.cos(ang)), int(cy + 80 * math.sin(ang))),
                (int(cx + 8 * math.cos(ang - math.pi / 2)), int(cy + 8 * math.sin(ang - math.pi / 2))),
            ], fill=LIGHT_GOLD, outline=GOLD, width=1)
        # Concentric diamond layers
        for size, col in [(70, BLACK), (55, TEAL), (40, BLACK), (28, BURGUNDY), (16, GOLD)]:
            d.polygon([(cx, cy - size), (cx + size // 2, cy),
                       (cx, cy + size), (cx - size // 2, cy)], fill=col, outline=GOLD, width=2)
        d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=GOLD, outline=BLACK, width=2)
        d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=BLACK)

    # ── Hậu kỳ Pillow (tham khảo Worker 1.1) ──────────────────────────────
    img = ImageOps.autocontrast(img, cutoff=0.2)          # Tăng dải tương phản
    img = ImageEnhance.Color(img).enhance(1.15)            # Màu sắc rực rỡ hơn
    img = ImageEnhance.Contrast(img).enhance(1.07)         # Tương phản sắc nét
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))  # Nét hơn
    # ───────────────────────────────────────────────────────────────────────

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    return data, "png", 256, 256


def sync_to_vm4(local_path: str, storage_key: str):
    """rsync ảnh từ VM2 sang VM4 /var/lib/bt03/images/ để image-service serve được."""
    if not STORAGE_SSH_TARGET:
        return
    remote_path = f"{STORAGE_SSH_TARGET}:{STORAGE_REMOTE_DIR}/{storage_key}"
    try:
        result = subprocess.run(
            ["rsync", "-az", "--mkpath",
             "-e", "ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10",
             local_path, remote_path],
            check=False, timeout=30, capture_output=True
        )
        if result.returncode == 0:
            print(f"  [sync✓] rsync → VM4: {storage_key}")
        else:
            err = result.stderr.decode(errors="ignore").strip()
            print(f"  [sync✗] rsync failed ({err})")
    except FileNotFoundError:
        # rsync không có → fallback scp
        ssh_opts = ["-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        remote_subdir = "/".join(storage_key.split("/")[:-1])
        subprocess.run(
            ["ssh"] + ssh_opts + [STORAGE_SSH_TARGET, f"mkdir -p {STORAGE_REMOTE_DIR}/{remote_subdir}"],
            check=False, timeout=15, capture_output=True
        )
        result = subprocess.run(
            ["scp"] + ssh_opts + [local_path, f"{STORAGE_SSH_TARGET}:{STORAGE_REMOTE_DIR}/{storage_key}"],
            check=False, timeout=30, capture_output=True
        )
        if result.returncode == 0:
            print(f"  [sync✓] scp → VM4: {storage_key}")
        else:
            err = result.stderr.decode(errors="ignore").strip()
            print(f"  [sync✗] scp failed ({err})")
    except Exception as e:
        print(f"  [sync✗] Exception: {e}")


def save_and_store_image(slug: str, query: str, job_id: str = None):
    """Sinh ảnh, sync sang VM4 TRƯỚC, rồi mới ghi vào PostgreSQL."""
    if not job_id:
        job_id = str(uuid.uuid4())
    t0 = time.time()
    img_bytes, fmt, w, h = make_art_deco_image(slug, query)
    sha = hashlib.sha256(img_bytes).hexdigest()
    storage_key = f"{slug}/{AI_CODE}/{uuid.uuid4().hex}.png"

    os.makedirs(os.path.join(LOCAL_DIR, slug, AI_CODE), exist_ok=True)
    file_path = os.path.join(LOCAL_DIR, slug, AI_CODE, storage_key.split('/')[-1])
    with open(file_path, "wb") as f:
        f.write(img_bytes)

    # Sync sang VM4 TRƯỚC khi ghi DB (theo yêu cầu nhóm trưởng)
    sync_to_vm4(file_path, storage_key)

    image_id = str(uuid.uuid4())
    if db:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO images (image_id, image_name, slug, prompt, style_id, worker_id,
                   storage_key, sha256, width, height, format, file_size)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (slug, worker_id) DO UPDATE SET
                       image_name=EXCLUDED.image_name,
                       prompt=EXCLUDED.prompt,
                       storage_key=EXCLUDED.storage_key,
                       sha256=EXCLUDED.sha256,
                       width=EXCLUDED.width,
                       height=EXCLUDED.height,
                       format=EXCLUDED.format,
                       file_size=EXCLUDED.file_size""",
                (image_id, f"{slug} {AI_CODE}.png", slug, query, "deco-v1", WORKER_ID,
                 storage_key, sha, w, h, fmt, len(img_bytes)),
            )
            cur.execute("SELECT image_id FROM images WHERE slug=%s AND worker_id=%s", (slug, WORKER_ID))
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
        ("golden-sword", "golden sword geometric art deco symmetrical"),
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
