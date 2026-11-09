import os, io, mimetypes
from pathlib import Path
import psycopg
from PIL import Image
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://bt03:B4Deco_Pg_2026!@127.0.0.1:5432/bt03')
STORAGE_DIR = Path(os.getenv('STORAGE_DIR', '/var/lib/bt03/images'))
THUMB_DIR = Path(os.getenv('THUMB_DIR', '/var/lib/bt03/thumbs'))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
THUMB_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='image-service')
CACHE_OK = {'Cache-Control': 'public, max-age=31536000, immutable'}


@app.get('/health')
def health():
    try:
        with psycopg.connect(DATABASE_URL) as c:
            c.execute('SELECT 1')
        return {'status': 'ok'}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get('/images')
def list_images(limit: int = Query(30, le=200), offset: int = 0, slug: str | None = None):
    with psycopg.connect(DATABASE_URL) as c:
        if slug:
            rows = c.execute(
                "SELECT image_id, image_name, slug, style_id, storage_key, sha256, width, height, format, file_size, created_at FROM images WHERE slug=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (slug, limit, offset)).fetchall()
        else:
            rows = c.execute(
                "SELECT image_id, image_name, slug, style_id, storage_key, sha256, width, height, format, file_size, created_at FROM images ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset)).fetchall()
    keys = ['image_id','image_name','slug','style_id','storage_key','sha256','width','height','format','file_size','created_at']
    return [dict(zip(keys, r)) for r in rows]


@app.get('/images/{image_id}')
def get_image(image_id: str):
    with psycopg.connect(DATABASE_URL) as c:
        row = c.execute(
            "SELECT image_id, image_name, slug, prompt, style_id, storage_key, sha256, width, height, format, file_size, created_at FROM images WHERE image_id=%s",
            (image_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'not found')
    keys = ['image_id','image_name','slug','prompt','style_id','storage_key','sha256','width','height','format','file_size','created_at']
    return dict(zip(keys, row))


def _thumb_path(storage_key: str, width: int) -> Path:
    return THUMB_DIR / str(width) / (storage_key + '.webp')


@app.get('/thumbs/{storage_key:path}')
def serve_thumb(storage_key: str, w: int = Query(320, ge=64, le=1024)):
    src = STORAGE_DIR / storage_key
    if not src.is_file():
        raise HTTPException(404, 'file not found')
    dst = _thumb_path(storage_key, w)
    if not dst.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert('RGB')
            if im.width > w:
                ratio = w / float(im.width)
                size = (w, max(1, int(im.height * ratio)))
                im = im.resize(size, Image.LANCZOS)
            im.save(dst, format='WEBP', quality=88, method=4)
    return FileResponse(dst, media_type='image/webp', headers=CACHE_OK)


@app.get('/files/{storage_key:path}')
def serve_file(storage_key: str):
    path = STORAGE_DIR / storage_key
    if not path.is_file():
        raise HTTPException(404, 'file not found')
    st = path.stat()
    mt = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
    headers = dict(CACHE_OK)
    headers['ETag'] = '"%d-%d"' % (st.st_mtime_ns, st.st_size)
    return FileResponse(path, media_type=mt, headers=headers)


@app.get('/metrics')
def metrics():
    with psycopg.connect(DATABASE_URL) as c:
        n = c.execute('SELECT COUNT(*) FROM images').fetchone()[0]
    body = "# HELP images_total Total images\n# TYPE images_total gauge\nimages_total %d\n" % n
    return Response(content=body, media_type='text/plain')
