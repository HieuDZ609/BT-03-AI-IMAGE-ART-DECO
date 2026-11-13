"""AI engine cho worker 4.1 — tiny-sd q4_K chạy cục bộ qua stable-diffusion.cpp.

Không gọi API AI. Sinh ảnh 256x256 trên CPU, sau đó hậu kỳ Art Deco:
ép bảng màu 6 màu + viền vàng 3px (đúng thiết kế trong báo cáo).
"""
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SD_BIN = os.getenv('SD_CPP_BIN', '/opt/bt03/ai/bin/sd-cli')
SD_MODEL = os.getenv('SD_MODEL', '/opt/bt03/ai/models/sd-turbo-q8_0.gguf')
AI_SIZE = int(os.getenv('AI_SIZE', '256'))          # độ phân giải render (256×256)
AI_DELIVER = int(os.getenv('AI_DELIVER', '256'))    # kích thước ảnh giao cho kho
AI_STEPS = int(os.getenv('AI_STEPS', '6'))          # 6 bước: cân bằng nhận diện & thời gian
AI_CFG = os.getenv('AI_CFG', '1.0')                 # SD-Turbo: CFG thấp
AI_THREADS = os.getenv('AI_THREADS', '8')
AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', '180'))
MODEL_NAME = os.getenv('AI_MODEL_NAME', 'sd-turbo-q8_0')
AI_TITLE_PLATE = os.getenv('AI_TITLE_PLATE', '1') == '1'
FONT = os.getenv('AI_FONT', '/opt/bt03/ai/fonts/DejaVuSerif-Bold.ttf')

POSITIVE = (
    "{concept}, centered, clearly visible, simple clean background, "
    "art deco poster, gold and black, flat illustration, clean shapes, high contrast"
)
NEGATIVE = (
    "blurry, low quality, distorted, messy, complex background, extra objects, "
    "multiple subjects, text, letters, watermark, signature, bad proportions, "
    "noisy details, oversaturated"
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
    # Làm mượt nhẹ để khử nhiễu/scanline của model nhỏ trước khi ép palette.
    im = im.filter(ImageFilter.GaussianBlur(0.6))
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


def _title_plate(im: Image.Image, text: str, band: int = 30) -> Image.Image:
    """Gắn tên chủ thể vào đáy ảnh như bảng tên Art Deco — giúp nhận diện ảnh với tên."""
    w, h = im.size
    out = im.copy()
    d = ImageDraw.Draw(out)
    d.rectangle((0, h - band, w, h), fill=PALETTE[0])
    d.line((0, h - band, w, h - band), fill=PALETTE[1], width=1)
    label = ' '.join(text.replace('-', ' ').replace('_', ' ').split()).upper()
    if len(label) > 22:
        label = label[:21] + '…'
    size = 15
    while size > 7:
        try:
            font = ImageFont.truetype(FONT, size)
        except OSError:
            font = ImageFont.load_default()
            size = 0
        tw = d.textlength(label, font=font)
        if tw <= w - 18 or size <= 8:
            break
        size -= 1
    d.text(((w - tw) / 2, h - band + (band - size) / 2 - 1), label, font=font, fill=PALETTE[5])
    # hai viên kim cương nhỏ hai bên
    for cx in (10, w - 11):
        cy = h - band // 2
        d.polygon([(cx, cy - 3), (cx + 3, cy), (cx, cy + 3), (cx - 3, cy)], fill=PALETTE[1])
    return out


def generate_image(query: str) -> tuple[bytes, str, int, int]:
    """Sinh ảnh Art Deco thật bằng SD-Turbo local (CPU)."""
    prompt = POSITIVE.format(concept=query)
    with tempfile.TemporaryDirectory(prefix='bt03-ai-') as td:
        out = Path(td) / 'out.png'
        cmd = [
            SD_BIN, '-m', SD_MODEL,
            '-W', str(AI_SIZE), '-H', str(AI_SIZE),
            '--cfg-scale', AI_CFG, '--steps', str(AI_STEPS),
            '--sampling-method', 'euler',
            '-t', AI_THREADS, '-s', '-1', '-o', str(out),
            '-p', prompt, '-n', NEGATIVE,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=AI_TIMEOUT)
        if proc.returncode != 0 or not out.is_file():
            raise RuntimeError('sd-cli failed: ' + (proc.stderr or proc.stdout)[-800:])
        with Image.open(out) as im:
            im = im.convert('RGB')
            if im.size != (AI_DELIVER, AI_DELIVER):
                im = im.resize((AI_DELIVER, AI_DELIVER), Image.LANCZOS)
            if AI_TITLE_PLATE:
                im = _frame(_title_plate(_quantize(im), query, band=30))
            else:
                im = _frame(_quantize(im), width=2)
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
