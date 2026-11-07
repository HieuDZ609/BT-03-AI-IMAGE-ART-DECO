"""AI engine cho worker 4.1 — tiny-sd q4_K chạy cục bộ qua stable-diffusion.cpp.

Không gọi API AI. Sinh ảnh 256x256 trên CPU, sau đó hậu kỳ Art Deco:
ép bảng màu 6 màu + viền vàng 3px (đúng thiết kế trong báo cáo).
"""
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

SD_BIN = os.getenv('SD_CPP_BIN', '/opt/bt03/ai/bin/sd-cli')
SD_MODEL = os.getenv('SD_MODEL', '/opt/bt03/ai/models/tiny-sd-q4_K.gguf')
AI_SIZE = int(os.getenv('AI_SIZE', '320'))          # độ phân giải render nội bộ
AI_DELIVER = int(os.getenv('AI_DELIVER', '256'))    # kích thước ảnh giao cho kho
AI_STEPS = int(os.getenv('AI_STEPS', '8'))
AI_CFG = os.getenv('AI_CFG', '7.0')
AI_THREADS = os.getenv('AI_THREADS', '8')
AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', '180'))
MODEL_NAME = os.getenv('AI_MODEL_NAME', 'tiny-sd-q4_K')

POSITIVE = (
    "{concept}, art deco poster, gold and black, symmetrical composition, "
    "flat vector, high contrast, clean silhouette, geometric sunburst and fan motifs"
)
NEGATIVE = (
    "text, letters, watermark, signature, logo, blurry, low quality, deformed, "
    "photorealistic, modern, cartoon, anime, extra limbs"
)

# Bảng màu Art Deco cố định — dùng chung với style.yaml
PALETTE = [
    (26, 26, 26),      # đen
    (201, 162, 39),    # vàng kim
    (244, 234, 213),   # kem
    (30, 110, 107),    # teal
    (138, 109, 31),    # vàng đồng
    (232, 213, 163),   # vàng nhạt
]


def _quantize(im: Image.Image) -> Image.Image:
    pal = Image.new('P', (1, 1))
    flat = []
    for c in PALETTE:
        flat.extend(c)
    flat.extend([0] * (768 - len(flat)))
    pal.putpalette(flat)
    return im.convert('RGB').quantize(palette=pal, dither=Image.NONE).convert('RGB')


def _frame(im: Image.Image, width: int = 3) -> Image.Image:
    w, h = im.size
    out = Image.new('RGB', (w + width * 2, h + width * 2), PALETTE[1])
    out.paste(im, (width, width))
    return out


def generate_image(query: str) -> tuple[bytes, str, int, int]:
    """Sinh ảnh thật bằng model local. Trả (bytes, format, width, height)."""
    prompt = POSITIVE.format(concept=query)
    with tempfile.TemporaryDirectory(prefix='bt03-ai-') as td:
        out = Path(td) / 'out.png'
        cmd = [
            SD_BIN, '-m', SD_MODEL,
            '-W', str(AI_SIZE), '-H', str(AI_SIZE),
            '--cfg-scale', AI_CFG, '--steps', str(AI_STEPS),
            '--sampling-method', 'euler_a', '--diffusion-fa',
            '-t', AI_THREADS, '-o', str(out),
            '-p', prompt, '-n', NEGATIVE,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=AI_TIMEOUT)
        if proc.returncode != 0 or not out.is_file():
            raise RuntimeError('sd-cli failed: ' + (proc.stderr or proc.stdout)[-800:])
        with Image.open(out) as im:
            im = im.convert('RGB')
            if im.size != (AI_DELIVER, AI_DELIVER):
                im = im.resize((AI_DELIVER, AI_DELIVER), Image.LANCZOS)
            im = _frame(_quantize(im))
            w, h = im.size
            import io
            buf = io.BytesIO()
            im.save(buf, format='PNG', optimize=True)
            return buf.getvalue(), 'png', w, h


if __name__ == '__main__':
    import sys
    data, fmt, w, h = generate_image(sys.argv[1] if len(sys.argv) > 1 else 'black dog')
    out = sys.argv[2] if len(sys.argv) > 2 else '/tmp/ai-out.png'
    open(out, 'wb').write(data)
    print('saved', out, fmt, w, h, len(data))
