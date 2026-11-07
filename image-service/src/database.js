const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { DatabaseSync } = require('node:sqlite');
const config = require('./config');

const dataDir = path.dirname(config.DB_PATH);
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const db = new DatabaseSync(config.DB_PATH);

function initDatabase() {
  db.exec(`
    -- 1. Bảng members
    CREATE TABLE IF NOT EXISTS members (
      member_id TEXT PRIMARY KEY,
      student_code TEXT,
      full_name TEXT NOT NULL,
      role TEXT NOT NULL,
      is_leader INTEGER DEFAULT 0
    );

    -- 2. Bảng ai_workers
    CREATE TABLE IF NOT EXISTS ai_workers (
      worker_id TEXT PRIMARY KEY,
      member_id TEXT NOT NULL,
      ai_code TEXT UNIQUE NOT NULL,
      model_name TEXT NOT NULL,
      model_version TEXT DEFAULT 'v1.0',
      hostname TEXT,
      status TEXT DEFAULT 'ONLINE',
      last_heartbeat TEXT,
      total_generated INTEGER DEFAULT 0,
      version TEXT DEFAULT '1.0',
      FOREIGN KEY(member_id) REFERENCES members(member_id)
    );

    -- 3. Bảng images (Chuẩn spec 2.2 của nhóm trưởng)
    CREATE TABLE IF NOT EXISTS images (
      image_id TEXT PRIMARY KEY,
      image_name TEXT NOT NULL,
      slug TEXT NOT NULL,
      prompt TEXT NOT NULL,
      style_id TEXT DEFAULT 'deco-v1',
      worker_id TEXT,
      ai_code TEXT NOT NULL,
      storage_key TEXT UNIQUE NOT NULL,
      sha256 TEXT UNIQUE NOT NULL,
      width INTEGER NOT NULL,
      height INTEGER NOT NULL,
      format TEXT NOT NULL DEFAULT 'PNG',
      file_size INTEGER NOT NULL,
      file_url TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_images_slug ON images(slug);
    CREATE INDEX IF NOT EXISTS idx_images_ai_code ON images(ai_code);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_images_slug_ai ON images(slug, ai_code);

    -- 4. Bảng generation_jobs
    CREATE TABLE IF NOT EXISTS generation_jobs (
      job_id TEXT PRIMARY KEY,
      query TEXT NOT NULL,
      slug TEXT NOT NULL,
      source TEXT DEFAULT 'SEARCH',
      status TEXT DEFAULT 'QUEUED',
      worker_id TEXT,
      attempts INTEGER DEFAULT 1,
      queued_at TEXT NOT NULL,
      started_at TEXT,
      finished_at TEXT,
      duration_ms INTEGER,
      image_id TEXT,
      error TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_jobs_status ON generation_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_slug ON generation_jobs(slug);

    -- 5. Bảng search_logs
    CREATE TABLE IF NOT EXISTS search_logs (
      log_id INTEGER PRIMARY KEY AUTOINCREMENT,
      query TEXT NOT NULL,
      hit INTEGER NOT NULL,
      job_id TEXT,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      action TEXT NOT NULL,
      details TEXT,
      created_at TEXT NOT NULL
    );
  `);

  // Khởi tạo 5 thành viên nhóm B4 theo đúng danh sách phân công
  const initMember = db.prepare(`
    INSERT OR REPLACE INTO members (member_id, student_code, full_name, role, is_leader)
    VALUES (?, ?, ?, ?, ?)
  `);
  initMember.run('B4.4', '24IT062', 'Hà Điền Trung Hiếu', 'Core Node & Integration (Nhóm trưởng)', 1);
  initMember.run('B4.1', '24IT001', 'Võ Quốc Đạt', 'AI Worker & Model Engineering', 0);
  initMember.run('B4.2', '24IT002', 'Nguyễn Thành Đô', 'Data & Storage + AI Worker 2.1', 0);
  initMember.run('B4.3', '24IT003', 'Nguyễn Văn Thái Hào', 'Frontend & UX + AI Worker 3.1', 0);
  initMember.run('B4.5', '24IT005', 'Nguyễn Văn Hiếu', 'DevOps, Monitoring & Notification + AI Worker 5.1', 0);

  // Khởi tạo 5 Worker theo phân bổ VM của nhóm
  const initWorker = db.prepare(`
    INSERT OR REPLACE INTO ai_workers (worker_id, member_id, ai_code, model_name, model_version, hostname, status, last_heartbeat, total_generated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  const now = new Date().toISOString();
  initWorker.run('W2', 'B4.2', '2.1', 'Art Deco Local Procedural Generator', 'deco-v1', 'VM2-192.168.100.12', 'ONLINE', now, 0);
  initWorker.run('W1', 'B4.1', '1.1', 'Stable Diffusion 1.5 Local', 'sd-1.5', 'VM1-192.168.100.11', 'STANDBY', now, 0);
  initWorker.run('W3', 'B4.3', '3.1', 'Local Light Model', 'tiny-sd', 'VM3-192.168.100.13', 'STANDBY', now, 0);
  initWorker.run('W4', 'B4.4', '4.1', 'SD-Turbo Local Integration', 'sd-turbo', 'VM4-192.168.100.14', 'STANDBY', now, 0);
  initWorker.run('W5', 'B4.5', '5.1', 'Local Backup Worker', 'sd-cpp', 'VM5-192.168.100.15', 'STANDBY', now, 0);

  console.log('✅ Cơ sở dữ liệu SQLite đã được đồng bộ chuẩn Plan BT-03 (PostgreSQL compatible)!');
}

// Chống trùng lặp nội dung theo SHA-256
function findImageByHash(hash) {
  const stmt = db.prepare('SELECT * FROM images WHERE sha256 = ?');
  return stmt.get(hash);
}

// Chống trùng lặp theo cặp (slug, ai_code)
function findImageBySlugAndAi(slug, aiCode) {
  const stmt = db.prepare('SELECT * FROM images WHERE slug = ? AND ai_code = ?');
  return stmt.get(slug, aiCode);
}

function findImageByFilename(filename) {
  const stmt = db.prepare('SELECT * FROM images WHERE image_name = ?');
  return stmt.get(filename);
}

// Lưu ảnh vào Database
function insertImage(record) {
  const imageId = record.image_id || crypto.randomUUID();
  const stmt = db.prepare(`
    INSERT INTO images (
      image_id, image_name, slug, prompt, style_id, worker_id, ai_code,
      storage_key, sha256, width, height, format, file_size, file_url, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  stmt.run(
    imageId,
    record.image_name,
    record.slug,
    record.prompt,
    record.style_id || 'deco-v1',
    record.worker_id || `W${record.ai_code.split('.')[0]}`,
    record.ai_code,
    record.storage_key,
    record.sha256,
    record.width,
    record.height,
    record.format || 'PNG',
    record.file_size,
    record.file_url,
    record.created_at || new Date().toISOString()
  );

  // Cập nhật total_generated và last_heartbeat
  try {
    db.prepare(`
      UPDATE ai_workers
      SET total_generated = total_generated + 1,
          last_heartbeat = ?,
          status = 'ONLINE'
      WHERE ai_code = ?
    `).run(new Date().toISOString(), record.ai_code);
  } catch (err) {}

  return { ...record, image_id: imageId };
}

// Lấy danh sách ảnh phân trang (mới nhất trước)
function getImages({ page = 1, size = 50 } = {}) {
  const offset = (page - 1) * size;
  const total = Number(db.prepare('SELECT COUNT(*) AS total FROM images').get().total);

  const stmt = db.prepare(`
    SELECT 
      image_id,
      image_name,
      slug,
      prompt,
      style_id,
      ai_code,
      worker_id,
      storage_key,
      sha256,
      width,
      height,
      format,
      file_size,
      file_url,
      created_at
    FROM images
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
  `);
  const items = stmt.all(size, offset);

  return {
    page: Number(page),
    size: Number(size),
    total,
    total_pages: Math.ceil(total / size) || 1,
    items,
  };
}

// Tìm kiếm ảnh (Tìm kiếm gần đúng / Fulltext match)
function searchImages({ query = '', page = 1, size = 50 } = {}) {
  const clean = query.trim().toLowerCase();
  const searchPattern = `%${clean}%`;
  const offset = (page - 1) * size;

  const countStmt = db.prepare(`
    SELECT COUNT(*) AS total FROM images
    WHERE LOWER(slug) LIKE ? OR LOWER(image_name) LIKE ? OR LOWER(prompt) LIKE ?
  `);
  const total = Number(countStmt.get(searchPattern, searchPattern, searchPattern).total);

  const stmt = db.prepare(`
    SELECT 
      image_id,
      image_name,
      slug,
      prompt,
      style_id,
      ai_code,
      worker_id,
      storage_key,
      sha256,
      width,
      height,
      format,
      file_size,
      file_url,
      created_at
    FROM images
    WHERE LOWER(slug) LIKE ? OR LOWER(image_name) LIKE ? OR LOWER(prompt) LIKE ?
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
  `);
  const items = stmt.all(searchPattern, searchPattern, searchPattern, size, offset);

  return {
    hit: total > 0,
    page: Number(page),
    size: Number(size),
    total,
    items,
  };
}

// Quản lý Jobs
function createJob({ query, slug, source = 'SEARCH' }) {
  const jobId = crypto.randomUUID();
  const now = new Date().toISOString();
  const stmt = db.prepare(`
    INSERT INTO generation_jobs (job_id, query, slug, source, status, queued_at)
    VALUES (?, ?, ?, ?, 'QUEUED', ?)
  `);
  stmt.run(jobId, query, slug, source, now);
  return { job_id: jobId, query, slug, status: 'QUEUED', queued_at: now };
}

function updateJobStatus(jobId, { status, workerId = null, durationMs = null, imageId = null, error = null }) {
  const now = new Date().toISOString();
  const stmt = db.prepare(`
    UPDATE generation_jobs
    SET status = ?,
        worker_id = COALESCE(?, worker_id),
        finished_at = ?,
        duration_ms = COALESCE(?, duration_ms),
        image_id = COALESCE(?, image_id),
        error = COALESCE(?, error)
    WHERE job_id = ?
  `);
  stmt.run(status, workerId, now, durationMs, imageId, error, jobId);
}

function getJobById(jobId) {
  const stmt = db.prepare('SELECT * FROM generation_jobs WHERE job_id = ?');
  return stmt.get(jobId);
}

// Lấy 1 ảnh theo ID
function getImageById(id) {
  const stmt = db.prepare(`
    SELECT * FROM images WHERE image_id = ? OR id = ?
  `);
  try {
    return stmt.get(id, id);
  } catch (e) {
    return db.prepare('SELECT * FROM images WHERE image_id = ?').get(id);
  }
}

// Xóa ảnh
function deleteImageById(id) {
  const img = getImageById(id);
  if (!img) return null;

  db.prepare('DELETE FROM images WHERE image_id = ?').run(img.image_id);
  try {
    db.prepare('UPDATE ai_workers SET total_generated = MAX(0, total_generated - 1) WHERE ai_code = ?')
      .run(img.ai_code);
  } catch (e) {}

  return img;
}

// Thống kê theo từng AI (Đúng spec OpenAPI 2.3)
function getStatistics() {
  const workers = db.prepare(`
    SELECT 
      w.ai_code,
      m.full_name AS member,
      w.model_name AS model,
      w.status,
      COALESCE(i.actual_count, 0) AS total,
      CASE WHEN w.status = 'ONLINE' THEN 1 ELSE 0 END AS online,
      w.last_heartbeat
    FROM ai_workers w
    LEFT JOIN members m ON w.member_id = m.member_id
    LEFT JOIN (
      SELECT ai_code, COUNT(*) AS actual_count 
      FROM images 
      GROUP BY ai_code
    ) i ON w.ai_code = i.ai_code
    ORDER BY w.ai_code ASC
  `).all();

  return workers.map(w => ({
    ai_code: w.ai_code,
    member: w.member,
    model: w.model,
    total: Number(w.total),
    online: Boolean(w.online),
    last_heartbeat: w.last_heartbeat,
  }));
}

function logActivity(action, details = '') {
  try {
    db.prepare('INSERT INTO activity_logs (action, details, created_at) VALUES (?, ?, ?)')
      .run(action, details, new Date().toISOString());
  } catch (e) {}
}

module.exports = {
  db,
  initDatabase,
  findImageByHash,
  findImageBySlugAndAi,
  findImageByFilename,
  insertImage,
  getImages,
  searchImages,
  createJob,
  updateJobStatus,
  getJobById,
  getImageById,
  deleteImageById,
  getStatistics,
  getStatsByAi: getStatistics,
  logActivity,
};
