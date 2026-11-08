import os, time, uuid, random, json
import redis
import psycopg

REDIS_URL = os.getenv('REDIS_URL', 'redis://:B4Deco_Redis_2026!@127.0.0.1:6379/0')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://bt03:B4Deco_Pg_2026!@127.0.0.1:5432/bt03')
STREAM = 'jobs:generate'
r = redis.from_url(REDIS_URL, decode_responses=True)

TOPICS = [
    # Animals
    'golden lion', 'golden peacock', 'eagle', 'butterfly', 'cat', 'wolf',
    # Nature
    'celestial sun', 'moon', 'mountain', 'ocean', 'flower', 'tree',
    # Architecture
    'skyscraper', 'luxury hotel', 'palace', 'lighthouse', 'tower',
    # Objects
    'vintage clock', 'vintage radio', 'diamond', 'perfume', 'camera',
    # Mythology
    'phoenix', 'dragon', 'medusa', 'egyptian pharaoh',
    # Space
    'saturn', 'galaxy', 'shooting star', 'solar system',
    # Vehicles
    'vintage car', 'steam train', 'airplane', 'yacht',
    # Abstract
    'golden geometry', 'symmetrical shapes', 'sunburst',
    # Fashion
    'vintage woman', 'art deco jewelry', 'luxury hat',
    # Fantasy
    'crystal castle', 'golden sword', 'magic portal',
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
