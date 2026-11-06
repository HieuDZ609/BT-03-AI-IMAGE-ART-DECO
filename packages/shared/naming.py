"""Quy tắc đặt tên ảnh dùng chung (packages/shared/naming.py)."""

import re
import uuid
from pathlib import Path

_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def slugify(text: str) -> str:
    """Chuẩn hoá query thành slug: lowercase, gạch nối, bỏ ký tự đặc biệt."""
    s = text.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = _SLUG_RE.sub("", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "image"


def image_name(slug: str, ai_code: str, ext: str = "png") -> str:
    """'{slug} {ai_code}.{ext}'  ví dụ 'black dog 4.1.png'."""
    ext = ext.lstrip(".")
    return f"{slug} {ai_code}.{ext}"


def storage_key(slug: str, ai_code: str, ext: str = "png") -> str:
    """'{slug}/{ai_code}/{uuid}.{ext}' — không bao giờ ghi đè."""
    ext = ext.lstrip(".")
    return f"{slug}/{ai_code}/{uuid.uuid4().hex}.{ext}"


def parse_ai_code(ai_code: str) -> tuple[int, int]:
    """'4.1' -> (4, 1)."""
    member, idx = ai_code.split(".")
    return int(member), int(idx)


def ext_from_format(fmt: str) -> str:
    fmt = fmt.lower().strip()
    return {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp"}.get(fmt, fmt)
"