import os, time, uuid, random, json
import redis
import psycopg

REDIS_URL = os.getenv('REDIS_URL', 'redis://:B4Deco_Redis_2026!@127.0.0.1:6379/0')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://bt03:B4Deco_Pg_2026!@127.0.0.1:5432/bt03')
STREAM = 'jobs:generate'
r = redis.from_url(REDIS_URL, decode_responses=True)

TOPICS = [
    'art deco city', 'gold geometric pattern', '1920s poster', 'luxury interior',
    'zigzag motif', 'fan pattern', 'sunburst design', 'black and gold',
    'vintage automobile', 'skyscraper', 'cocktail glass', 'jazz musician',
    'egyptian motif', 'machine age', 'streamline modern', 'chrome details',
    'marble floor', 'stained glass', 'ornate gate', 'classic clock',
]

def slugify(t):
    import re
    s = t.strip().lower()
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9-]', '', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s or 'image'

def main():
    print('autopilot started')
    while True:
        topic = random.choice(TOPICS)
        slug = slugify(topic)
        job_id = str(uuid.uuid4())
        # avoid duplicate active jobs for same slug
        with psycopg.connect(DATABASE_URL) as c:
            exists = c.execute("SELECT 1 FROM generation_jobs WHERE slug=%s AND status IN ('QUEUED','CLAIMED','RUNNING') LIMIT 1", (slug,)).fetchone()
            if exists:
                time.sleep(5)
                continue
            # đã có ảnh cho slug này thì bỏ qua (tránh trùng)
            has_img = c.execute("SELECT 1 FROM images WHERE slug=%s LIMIT 1", (slug,)).fetchone()
            if has_img:
                time.sleep(5)
                continue
            c.execute("INSERT INTO generation_jobs (job_id, query, slug, source, status) VALUES (%s,%s,%s,'AUTOPILOT','QUEUED')", (job_id, topic, slug))
        r.xadd(STREAM, {
            'job_id': job_id, 'query': topic, 'slug': slug, 'source': 'AUTOPILOT',
            'style_id': 'deco-v1', 'requested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        })
        print('seeded', topic, job_id)
        time.sleep(30)

if __name__ == '__main__':
    main()
