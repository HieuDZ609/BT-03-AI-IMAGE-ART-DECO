import os, json, uuid, time, asyncio
import redis
import psycopg
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse

REDIS_URL = os.getenv('REDIS_URL', 'redis://:B4Deco_Redis_2026!@127.0.0.1:6379/0')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://bt03:B4Deco_Pg_2026!@127.0.0.1:5432/bt03')
STREAM = 'jobs:generate'
r = redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI(title='api-gateway')

def slugify(text):
    import re
    s = text.strip().lower()
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9-]', '', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s or 'image'

@app.get('/health')
def health():
    try:
        r.ping()
        with psycopg.connect(DATABASE_URL) as c:
            c.execute('SELECT 1')
        return {'status': 'ok'}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get('/search')
def search(q: str = Query(...), limit: int = 20):
    slug = slugify(q)
    cache_key = f'cache:search:{slug}:{limit}'
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    with psycopg.connect(DATABASE_URL) as c:
        rows = c.execute(
            "SELECT image_id, image_name, slug, style_id, storage_key, sha256, width, height, format, file_size, created_at FROM images WHERE slug=%s OR slug %% %s ORDER BY created_at DESC LIMIT %s",
            (slug, slug, limit)).fetchall()
        keys = ['image_id','image_name','slug','style_id','storage_key','sha256','width','height','format','file_size','created_at']
        images = [dict(zip(keys, row)) for row in rows]
        if images:
            c.execute("INSERT INTO search_logs (query, hit, job_id) VALUES (%s, true, NULL)", (q,))
            payload = {'hit': True, 'images': images, 'job_id': None, 'status': 'DONE'}
            r.set(cache_key, json.dumps(payload, default=str), ex=30)
            return payload
        # miss -> create job
        lock_key = f'lock:slug:{slug}'
        acquired = r.set(lock_key, '1', nx=True, ex=120)
        job_id = str(uuid.uuid4())
        if acquired:
            with psycopg.connect(DATABASE_URL) as c2:
                c2.execute(
                    "INSERT INTO generation_jobs (job_id, query, slug, source, status) VALUES (%s,%s,%s,'SEARCH','QUEUED')",
                    (job_id, q, slug))
                c2.execute("INSERT INTO search_logs (query, hit, job_id) VALUES (%s, false, %s)", (q, job_id))
            r.xadd(STREAM, {
                'job_id': job_id, 'query': q, 'slug': slug, 'source': 'SEARCH',
                'style_id': 'deco-v1', 'requested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            })
        else:
            # another job exists; find latest queued job for slug
            with psycopg.connect(DATABASE_URL) as c2:
                row = c2.execute(
                    "SELECT job_id FROM generation_jobs WHERE slug=%s AND status IN ('QUEUED','CLAIMED','RUNNING') ORDER BY created_at DESC LIMIT 1",
                    (slug,)).fetchone()
                if row:
                    job_id = str(row[0])
                c2.execute("INSERT INTO search_logs (query, hit, job_id) VALUES (%s, false, %s)", (q, job_id))
        return {'hit': False, 'images': [], 'job_id': job_id, 'status': 'QUEUED'}

@app.get('/jobs/{job_id}')
def job_status(job_id: str):
    cached = r.get(f'job:{job_id}:result')
    if cached:
        return json.loads(cached)
    with psycopg.connect(DATABASE_URL) as c:
        row = c.execute("SELECT status, worker_id, duration_ms, image_id, error FROM generation_jobs WHERE job_id=%s", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'job not found')
    return {'job_id': job_id, 'status': row[0], 'worker_id': row[1], 'duration_ms': row[2], 'image_id': row[3], 'error': row[4]}

@app.get('/jobs/{job_id}/stream')
def stream(job_id: str):
    def gen():
        for _ in range(60):
            cached = r.get(f'job:{job_id}:result')
            if cached:
                data = json.loads(cached)
                yield f"data: {json.dumps(data)}\n\n"
                if data.get('status') in ('DONE', 'FAILED'):
                    return
            else:
                with psycopg.connect(DATABASE_URL) as c:
                    row = c.execute("SELECT status FROM generation_jobs WHERE job_id=%s", (job_id,)).fetchone()
                status = row[0] if row else 'UNKNOWN'
                yield f"data: {json.dumps({'job_id': job_id, 'status': status})}\n\n"
                if status in ('DONE', 'FAILED', 'DEAD'):
                    return
            time.sleep(1)
        yield f"data: {json.dumps({'job_id': job_id, 'status': 'TIMEOUT'})}\n\n"
    return StreamingResponse(gen(), media_type='text/event-stream')

@app.get('/status')
def status():
    with psycopg.connect(DATABASE_URL) as c:
        workers = c.execute(
            "SELECT ai_code, status, last_heartbeat, total_generated FROM ai_workers ORDER BY worker_id").fetchall()
        images = c.execute("SELECT COUNT(*) FROM images").fetchone()[0]
        jobs = c.execute(
            "SELECT status, COUNT(*) FROM generation_jobs GROUP BY status").fetchall()
    online = [w[0] for w in workers if r.get(f'worker:heartbeat:{w[0]}')]
    return {
        'images': images,
        'jobs': {k: v for k, v in jobs},
        'workers': [
            {'ai_code': w[0], 'status': 'ONLINE' if w[0] in online else w[1],
             'last_heartbeat': w[2], 'total_generated': w[3]} for w in workers
        ],
        'online': online,
    }


@app.get('/metrics')
def metrics():
    with psycopg.connect(DATABASE_URL) as c:
        n = c.execute('SELECT COUNT(*) FROM images').fetchone()[0]
        j = c.execute('SELECT COUNT(*) FROM generation_jobs').fetchone()[0]
    body = "# HELP images_total Total images\n# TYPE images_total gauge\nimages_total %d\n# HELP jobs_total Total jobs\n# TYPE jobs_total gauge\njobs_total %d\n" % (n, j)
    return body


# ============================================================
# Adapter /api/v1 (tương thích frontend B4.3)
# ============================================================
from fastapi.responses import RedirectResponse

@app.get('/api/v1/search')
def search_v1(q: str = Query(...), page: int = 1, size: int = 50):
    res = search(q=q, limit=size)
    if res.get('hit'):
        res['items'] = res.get('images', [])
        res['page'] = page
        res['total'] = len(res['items'])
        res['totalPages'] = 1
    else:
        res['items'] = []
        res['page'] = page
        res['total'] = 0
        res['totalPages'] = 1
    return res

@app.get('/api/v1/images')
def images_v1(page: int = 1, size: int = 50):
    offset = (page - 1) * size
    with psycopg.connect(DATABASE_URL) as c:
        rows = c.execute(
            """SELECT i.image_id, i.image_name, i.slug, i.style_id, i.storage_key, i.sha256,
                      i.width, i.height, i.format, i.file_size, i.created_at,
                      w.ai_code, w.model_name
               FROM images i LEFT JOIN ai_workers w ON w.worker_id = i.worker_id
               ORDER BY i.created_at DESC LIMIT %s OFFSET %s""",
            (size, offset)).fetchall()
        total = c.execute("SELECT COUNT(*) FROM images").fetchone()[0]
    keys = ['image_id','image_name','slug','style_id','storage_key','sha256','width','height','format','file_size','created_at','ai_code','model_name']
    items = [dict(zip(keys, row)) for row in rows]
    return {'items': items, 'images': items, 'page': page, 'size': size,
            'total': total, 'totalPages': max(1, (total + size - 1) // size)}

@app.get('/api/v1/images/{image_id}/file')
def image_file_v1(image_id: str):
    with psycopg.connect(DATABASE_URL) as c:
        row = c.execute("SELECT storage_key FROM images WHERE image_id=%s", (image_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'not found')
    return RedirectResponse(url=f'/files/{row[0]}')

@app.get('/api/v1/statistics')
def statistics_v1():
    base = status()
    out = []
    with psycopg.connect(DATABASE_URL) as c:
        rows = c.execute(
            """SELECT w.ai_code, w.status, w.last_heartbeat, w.total_generated, w.model_name,
                      m.full_name
               FROM ai_workers w LEFT JOIN members m ON m.member_id = w.member_id
               ORDER BY w.worker_id""").fetchall()
    online = base.get('online', [])
    for r_ in rows:
        out.append({
            'ai_code': r_[0],
            'status': r_[1],
            'online': r_[0] in online,
            'last_heartbeat': r_[2],
            'total_generated': r_[3],
            'total': r_[3],
            'model_name': r_[4],
            'member_name': r_[5] or 'Nhóm B4',
        })
    return out

@app.post('/api/v1/generate')
def generate_v1(body: dict = None):
    q = ''
    if isinstance(body, dict):
        q = body.get('query') or body.get('q') or body.get('prompt') or ''
    if not q:
        q = 'art deco'
    slug = slugify(q)
    job_id = str(uuid.uuid4())
    with psycopg.connect(DATABASE_URL) as c:
        c.execute("INSERT INTO generation_jobs (job_id, query, slug, source, status) VALUES (%s,%s,%s,'SEARCH','QUEUED')",
                  (job_id, q, slug))
        c.execute("INSERT INTO search_logs (query, hit, job_id) VALUES (%s, false, %s)", (q, job_id))
    r.xadd(STREAM, {
        'job_id': job_id, 'query': q, 'slug': slug, 'source': 'SEARCH',
        'style_id': 'deco-v1', 'requested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    })
    return {'job_id': job_id, 'status': 'QUEUED', 'hit': False, 'images': []}

@app.get('/api/v1/jobs/{job_id}')
def job_v1(job_id: str):
    return job_status(job_id)

@app.get('/api/v1/jobs/{job_id}/events')
def events_v1(job_id: str):
    return stream(job_id)
