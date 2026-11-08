CREATE TABLE IF NOT EXISTS members (
  member_id smallint PRIMARY KEY,
  student_code varchar UNIQUE NOT NULL,
  full_name varchar NOT NULL,
  is_leader boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS ai_workers (
  worker_id smallint PRIMARY KEY,
  member_id smallint NOT NULL REFERENCES members(member_id),
  ai_code varchar UNIQUE NOT NULL,
  model_name varchar,
  hostname varchar,
  status varchar NOT NULL DEFAULT 'OFFLINE',
  last_heartbeat timestamptz,
  total_generated bigint NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS images (
  image_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  image_name varchar NOT NULL,
  slug varchar NOT NULL,
  prompt text,
  style_id varchar NOT NULL DEFAULT 'deco-v1',
  worker_id smallint REFERENCES ai_workers(worker_id),
  storage_key varchar UNIQUE NOT NULL,
  sha256 char(64) UNIQUE NOT NULL,
  width smallint,
  height smallint,
  format varchar,
  file_size integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS generation_jobs (
  job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  query varchar NOT NULL,
  slug varchar NOT NULL,
  source varchar NOT NULL,
  status varchar NOT NULL DEFAULT 'QUEUED',
  worker_id smallint REFERENCES ai_workers(worker_id),
  attempts smallint NOT NULL DEFAULT 0,
  duration_ms integer,
  image_id uuid REFERENCES images(image_id),
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS search_logs (
  log_id bigserial PRIMARY KEY,
  query varchar NOT NULL,
  hit boolean NOT NULL,
  job_id uuid REFERENCES generation_jobs(job_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_images_slug_trgm ON images USING gin (slug gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_images_created_at ON images (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON generation_jobs (status);
CREATE INDEX IF NOT EXISTS idx_search_logs_created ON search_logs (created_at DESC);

ALTER TABLE images ADD CONSTRAINT uq_images_slug_worker UNIQUE (slug, worker_id);
