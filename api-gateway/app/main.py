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
    with psycopg.connect(DATABASE_URL) as c:
        rows = c.execute(
            "SELECT image_id, image_name, slug, style_id, storage_key, sha256, width, height, format, file_size, created_at FROM images WHERE slug=%s OR slug %% %s ORDER BY created_at DESC LIMIT %s",
            (slug, slug, limit)).fetchall()
        keys = ['image_id','image_name','slug','style_id','storage_key','sha256','width','height','format','file_size','created_at']
        images = [dict(zip(keys, row)) for row in rows]
        if images:
            c.execute("INSERT INTO search_logs (query, hit, job_id) VALUES (%s, true, NULL)", (q,))
            return {'hit': True, 'images': images, 'job_id': None, 'status': 'DONE'}
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

@app.get('/metrics')
def metrics():
    with psycopg.connect(DATABASE_URL) as c:
        n = c.execute('SELECT COUNT(*) FROM images').fetchone()[0]
        j = c.execute('SELECT COUNT(*) FROM generation_jobs').fetchone()[0]
    body = "# HELP images_total Total images\n# TYPE images_total gauge\nimages_total %d\n# HELP jobs_total Total jobs\n# TYPE jobs_total gauge\njobs_total %d\n" % (n, j)
    return body
