const express = require('express');
const multer = require('multer');
const db = require('./database');
const storageService = require('./storageService');
const aiWorker21 = require('./aiWorker21');
const config = require('./config');

const router = express.Router();
const _startTime = Date.now();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 25 * 1024 * 1024 } });

// ───────────────────────────────────────────────────────
// 0. GET /api/v1/health  →  B4.5 DevOps monitoring
//    Prometheus / Beszel / Telegram Bot heartbeat check
// ───────────────────────────────────────────────────────
router.get(['/health', '/v1/health'], (req, res) => {
  try {
    const imgInfo = db.getImages({ page: 1, size: 1 });
    const ws = aiWorker21.getStatus();
    const uptimeSec = Math.floor((Date.now() - _startTime) / 1000);
    return res.json({
      status: 'ok',
      service: 'B4.2 - Image Storage and Database',
      member: config.MEMBER_NAME,
      student_id: config.STUDENT_ID,
      ai_code: config.AI_ID,
      uptime_sec: uptimeSec,
      port: config.PORT,
      base_url: config.BASE_URL,
      total_images: imgInfo.total || 0,
      ai_worker: {
        is_running: ws.is_running,
        total_generated_session: ws.total_generated_session,
        last_prompt: ws.last_prompt,
        redis: ws.redis,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    return res.status(503).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 1. GET /api/v1/images  →  B4.3 Frontend gallery
// ───────────────────────────────────────────────────────
router.get(['/images', '/v1/images'], (req, res) => {
  try {
    const page = Math.max(1, parseInt(req.query.page) || 1);
    const size = Math.max(1, parseInt(req.query.size || req.query.limit) || 50);
    const result = db.getImages({ page, size });
    return res.json({ status: 'success', ...result, data: result.items });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 2. GET /api/v1/search  →  B4.4 Gateway + B4.3 Frontend
//    MISS: tu dong sinh anh ngay, KHONG BAO GIO tra rong
// ───────────────────────────────────────────────────────
router.get(['/search', '/v1/search', '/images/search', '/v1/images/search'], async (req, res) => {
  try {
    const query = (req.query.q || req.query.query || '').trim();
    const page = Math.max(1, parseInt(req.query.page) || 1);
    const size = Math.max(1, parseInt(req.query.size || req.query.limit) || 50);
    const autoGenerate = req.query.auto_generate !== 'false';

    if (!query) {
      return res.status(400).json({ hit: false, message: 'Thieu tham so ?q=<ten tieng Anh>' });
    }

    const searchResult = db.searchImages({ query, page, size });
    if (searchResult.hit) {
      return res.json({
        hit: true,
        page: searchResult.page, size: searchResult.size, total: searchResult.total,
        items: searchResult.items.map(img => ({
          image_id: img.image_id, image_name: img.image_name, slug: img.slug,
          ai_code: img.ai_code, url: img.file_url, created_at: img.created_at,
          width: img.width, height: img.height, file_size: img.file_size, sha256: img.sha256,
        })),
      });
    }

    const slug = storageService.createSlug(query);
    const job = db.createJob({ query, slug, source: 'SEARCH' });

    if (autoGenerate) {
      console.log('[Search MISS] Sinh anh cho: "' + query + '"');
      const t0 = Date.now();
      const genResult = await aiWorker21.generateOnDemand(query);
      db.updateJobStatus(job.job_id, { status: 'DONE', workerId: 'W2', durationMs: Date.now() - t0, imageId: genResult.image.image_id });
      const updated = db.searchImages({ query, page, size });
      return res.json({
        hit: true, auto_generated: true, job_id: job.job_id,
        page: 1, size: updated.size, total: updated.total,
        items: updated.items.map(img => ({
          image_id: img.image_id, image_name: img.image_name, slug: img.slug,
          ai_code: img.ai_code, url: img.file_url, created_at: img.created_at,
        })),
      });
    }
    return res.json({ hit: false, job_id: job.job_id, status: 'QUEUED', message: 'Dang sinh anh...' });
  } catch (err) {
    return res.status(500).json({ hit: false, error: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 3. GET /api/v1/statistics  →  B4.3 Footer + B4.4 Gateway
//    Tra du thong tin de B4.4 tong hop voi cac VM khac
// ───────────────────────────────────────────────────────
router.get(['/statistics', '/v1/statistics', '/images/stats', '/v1/images/stats'], (req, res) => {
  try {
    const list = db.getStatistics();
    const totalImages = list.reduce((s, i) => s + i.total, 0);
    const byAi = {};
    list.forEach(i => { byAi[i.ai_code] = i.total; });
    const ws = aiWorker21.getStatus();
    const enriched = list.map(item => ({
      ai_code: item.ai_code,
      member: item.member || config.MEMBER_NAME,
      student_id: config.STUDENT_ID,
      model: 'Art Deco Local Procedural Generator (100% Offline)',
      total: item.total,
      online: item.ai_code === config.AI_ID ? ws.is_running : false,
      last_heartbeat: new Date().toISOString(),
      base_url: config.BASE_URL,
    }));
    return res.json({ status: 'success', total_images: totalImages, by_ai: byAi, items: enriched, workers_detail: enriched });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 4. GET /api/v1/workers  →  B4.4 + B4.5
// ───────────────────────────────────────────────────────
router.get(['/workers', '/v1/workers'], (req, res) => {
  try {
    return res.json({ status: 'success', local_worker_21: aiWorker21.getStatus(), workers: db.getStatistics() });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 5. GET /api/v1/images/:id
// ───────────────────────────────────────────────────────
router.get(['/images/:id', '/v1/images/:id'], (req, res) => {
  try {
    const img = db.getImageById(req.params.id);
    if (!img) return res.status(404).json({ status: 'error', message: 'Khong tim thay anh.' });
    return res.json({ status: 'success', data: img });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 6. GET /api/v1/images/:id/file
// ───────────────────────────────────────────────────────
router.get(['/images/:id/file', '/v1/images/:id/file'], (req, res) => {
  try {
    const img = db.getImageById(req.params.id);
    if (!img) return res.status(404).json({ status: 'error', message: 'Khong tim thay file.' });
    return res.redirect(img.file_url);
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 7. POST /api/v1/generate  →  B4.4 Gateway trigger
// ───────────────────────────────────────────────────────
router.post(['/generate', '/v1/generate', '/ai/generate', '/v1/ai/generate'], async (req, res) => {
  try {
    const query = (req.body.query || req.body.prompt || '').trim();
    if (!query) return res.status(400).json({ status: 'error', message: 'Thieu query/prompt.' });
    const slug = storageService.createSlug(query);
    const job = db.createJob({ query, slug, source: 'API' });
    const result = await aiWorker21.generateOnDemand(query);
    db.updateJobStatus(job.job_id, { status: 'DONE', workerId: 'W2', durationMs: result.duration_ms, imageId: result.image.image_id });
    return res.json({ status: 'success', job_id: job.job_id, ...result });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 8. GET /api/v1/jobs/:id
// ───────────────────────────────────────────────────────
router.get(['/jobs/:id', '/v1/jobs/:id'], (req, res) => {
  try {
    const job = db.getJobById(req.params.id);
    if (!job) return res.status(404).json({ status: 'error', message: 'Khong tim thay job.' });
    return res.json({ status: 'success', data: job });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 9. POST /api/v1/images  →  B4.1 AI Workers nop anh
// ───────────────────────────────────────────────────────
router.post(['/images', '/v1/images'], upload.single('image'), async (req, res) => {
  try {
    let buffer = null;
    let prompt = req.body.prompt || '';
    let aiCode = req.body.ai_code || req.body.ai_id || config.AI_ID;
    let customFilename = req.body.filename || req.body.image_name || null;

    if (req.file) {
      buffer = req.file.buffer;
      if (!customFilename) customFilename = req.file.originalname;
    } else if (req.body.base64) {
      buffer = Buffer.from(req.body.base64.replace(/^data:image\/\w+;base64,/, ''), 'base64');
    }
    if (!buffer) {
      return res.status(400).json({ status: 'error', message: 'Can cung cap file anh (form-data "image") hoac base64.' });
    }
    if (!prompt) prompt = (customFilename || 'unnamed').replace(/.[^/.]+$/, '').replace(/[d._-]+/g, ' ').trim();

    const result = await storageService.storeImage({ buffer, prompt, aiCode, customFilename });
    if (result.status === 'duplicate') return res.status(409).json({ status: 'duplicate', message: result.message, image: result.image });
    return res.status(201).json({ status: 'success', message: result.message, image: result.image });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 10. DELETE /api/v1/images/:id
// ───────────────────────────────────────────────────────
router.delete(['/images/:id', '/v1/images/:id'], (req, res) => {
  try {
    const deleted = storageService.removeImage(req.params.id);
    if (!deleted) return res.status(404).json({ status: 'error', message: 'Khong tim thay anh.' });
    return res.json({ status: 'success', message: 'Da xoa: ' + deleted.image_name, deleted });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

// ───────────────────────────────────────────────────────
// 11. POST /api/v1/ai/toggle
// ───────────────────────────────────────────────────────
router.post(['/ai/toggle', '/v1/ai/toggle'], (req, res) => {
  try {
    if (aiWorker21.isRunning) aiWorker21.stop(); else aiWorker21.start();
    return res.json({ status: 'success', data: aiWorker21.getStatus() });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err.message });
  }
});

module.exports = router;
