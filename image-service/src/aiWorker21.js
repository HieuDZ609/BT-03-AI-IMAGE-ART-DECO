const Redis = require('ioredis');
const config = require('./config');
const storageService = require('./storageService');
const db = require('./database');
const { generateArtDecoSvg } = require('./artDecoVectorEngine');

// Danh sach chu de bach khoa da dang - 50 chu de (phuc vu che do tu sinh / fallback)
const ENCYCLOPEDIA_TOPICS = [
  'black dog', 'red cat', 'pink pig', 'grey elephant', 'brown horse',
  'white rabbit', 'orange fox', 'black bear', 'golden eagle', 'blue whale',
  'wooden table', 'antique chair', 'classic book', 'pocket watch', 'solar system',
  'red apple', 'yellow sunflower', 'green tree', 'blue car', 'red hat',
  'sailboat', 'airplane', 'cozy house', 'roman colosseum', 'saturn rings',
  'dna double helix', 'atom electron', 'green sea turtle', 'giant redwood tree', 'sunflower blossom',
  'black swan', 'red rose', 'blue butterfly', 'golden fish', 'silver wolf',
  'marble column', 'crystal vase', 'bronze lamp', 'ivory tower', 'copper kettle',
  'hot air balloon', 'vintage camera', 'grand piano', 'telescope', 'lighthouse',
  'dragon fly', 'peacock feather', 'coral reef', 'mountain peak', 'desert cactus',
];

/**
 * Chuan hoa du lieu entry nhan tu Redis Stream
 */
function parseStreamFields(fields) {
  const obj = {};
  if (Array.isArray(fields)) {
    for (let i = 0; i < fields.length; i += 2) {
      obj[fields[i]] = fields[i + 1];
    }
  } else if (typeof fields === 'object' && fields !== null) {
    Object.assign(obj, fields);
  }

  // Truong hop Gateway/Autopilot truyen payload la JSON string
  if (obj.payload && typeof obj.payload === 'string') {
    try {
      const parsed = JSON.parse(obj.payload);
      return { ...obj, ...parsed };
    } catch (e) {
      // payload khong phai json thi giu nguyen
    }
  }
  return obj;
}

class AiWorker21 {
  constructor() {
    this.aiId = config.AI_ID; // "2.1"
    this.isRunning = false;
    this.timer = null;
    this.generatedCount = 0;
    this.lastGeneratedPrompt = null;
    this.lastGeneratedTime = null;
    this._generatedTopics = new Set();

    // Redis State theo Hop dong VM4 (100.70.241.87)
    this.redis = null;
    this.redisConnected = false;
    this.heartbeatTimer = null;
    this.isConsuming = false;
    this.lastHeartbeatTime = null;
    this.redisJobsProcessed = 0;
    this.redisLastError = null;
  }

  /**
   * Sinh anh Art Deco bang Vector Engine chuyen nghiep
   */
  async synthesizeArtDecoImage(prompt) {
    return generateArtDecoSvg(prompt);
  }

  /**
   * Sinh anh theo yeu cau truc tiep (Dashboard / REST API)
   */
  async generateOnDemand(prompt) {
    const startTime = Date.now();
    console.log('[AI 2.1] Bat dau sinh anh on-demand: "' + prompt + '"');

    const buffer = await this.synthesizeArtDecoImage(prompt);
    const storeResult = await storageService.storeImage({
      buffer,
      prompt,
      aiCode: this.aiId,
      styleId: 'deco-v1',
    });

    const durationMs = Date.now() - startTime;
    this.generatedCount++;
    this.lastGeneratedPrompt = prompt;
    this.lastGeneratedTime = new Date().toISOString();
    this._generatedTopics.add(storageService.createSlug(prompt));

    console.log('[AI 2.1] Hoan tat "' + prompt + '" trong ' + durationMs + 'ms: ' + storeResult.image.image_name);

    return {
      success: true,
      duration_ms: durationMs,
      ai_code: this.aiId,
      image: storeResult.image,
      is_duplicate: storeResult.status === 'duplicate',
    };
  }

  /**
   * Khoi tao ket noi Redis va dang ky Consumer Group theo hop dong nhom B4
   */
  initRedis() {
    if (!config.REDIS_URL) {
      console.log('[AI 2.1 Redis] Khong co REDIS_URL, bo qua che do Redis Stream.');
      return;
    }

    try {
      console.log(`[AI 2.1 Redis] Dang ket noi toi Redis: ${config.REDIS_HOST}:${config.REDIS_PORT}...`);

      this.redis = new Redis(config.REDIS_URL, {
        retryStrategy(times) {
          const delay = Math.min(times * 2000, 10000);
          return delay; // Thu ket noi lai moi 2-10 giay
        },
        maxRetriesPerRequest: null,
        enableReadyCheck: true,
        lazyConnect: false,
      });

      this.redis.on('connect', () => {
        console.log(`[AI 2.1 Redis] Ket noi thanh cong toi VM4 (${config.REDIS_HOST})!`);
        this.redisConnected = true;
        this.redisLastError = null;
        this.setupConsumerGroup();
        this.startHeartbeat();
        this.startConsumerLoop();
      });

      this.redis.on('error', (err) => {
        this.redisConnected = false;
        this.redisLastError = err.message;
        // Chi log canh bao ngan gon, tranh tran log khi chua bat Tailscale
        if (err.code === 'ECONNREFUSED' || err.code === 'ENETUNREACH' || err.code === 'ETIMEDOUT') {
          // Log dot xuat
          if (Math.random() < 0.1) {
            console.warn(`[AI 2.1 Redis] Chua ket noi duoc Redis VM4 (${config.REDIS_HOST}): ${err.code}. Se tu dong thu lai.`);
          }
        } else {
          console.warn('[AI 2.1 Redis] Canh bao Redis:', err.message);
        }
      });

      this.redis.on('close', () => {
        this.redisConnected = false;
      });
    } catch (err) {
      console.error('[AI 2.1 Redis] Loi khoi tao client Redis:', err.message);
    }
  }

  /**
   * Tao Consumer Group 'workers' tren stream 'jobs:generate' (idempotent)
   */
  async setupConsumerGroup() {
    if (!this.redis || !this.redisConnected) return;
    try {
      await this.redis.xgroup(
        'CREATE',
        config.REDIS_STREAM_JOBS,
        config.REDIS_GROUP,
        '0',
        'MKSTREAM'
      );
      console.log(`[AI 2.1 Redis] Da tao Consumer Group "${config.REDIS_GROUP}" tren stream "${config.REDIS_STREAM_JOBS}".`);
    } catch (err) {
      if (err.message && err.message.includes('BUSYGROUP')) {
        // Nhom da ton tai, hop le theo quy tac hop dong
        console.log(`[AI 2.1 Redis] Consumer Group "${config.REDIS_GROUP}" da ton tai san. San sang tiep nhan job.`);
      } else {
        console.warn('[AI 2.1 Redis] XGROUP CREATE warning:', err.message);
      }
    }
  }

  /**
   * Phat Heartbeat moi 30s voi TTL 90s: key worker:heartbeat:2.1 = "1"
   */
  startHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);

    // Bắn 1 nhát ngay lập tức
    this.sendHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      this.sendHeartbeat();
    }, config.REDIS_HEARTBEAT_SEC * 1000);
  }

  async sendHeartbeat() {
    if (!this.redis || !this.redisConnected) return;
    try {
      const key = `worker:heartbeat:${this.aiId}`;
      await this.redis.set(key, '1', 'EX', config.REDIS_HEARTBEAT_TTL);
      this.lastHeartbeatTime = new Date().toISOString();
    } catch (err) {
      // Ignored
    }
  }

  /**
   * Vong lap lang nghe Stream jobs:generate bang XREADGROUP
   */
  async startConsumerLoop() {
    if (this.isConsuming) return;
    this.isConsuming = true;

    console.log(`[AI 2.1 Redis] Bat dau lang nghe stream "${config.REDIS_STREAM_JOBS}" voi Consumer ID="${config.REDIS_CONSUMER}"...`);

    while (this.isRunning && this.redisConnected) {
      try {
        // XREADGROUP GROUP workers 2.1 BLOCK 5000 COUNT 1 STREAMS jobs:generate >
        const resp = await this.redis.xreadgroup(
          'GROUP',
          config.REDIS_GROUP,
          config.REDIS_CONSUMER,
          'BLOCK',
          5000,
          'COUNT',
          1,
          'STREAMS',
          config.REDIS_STREAM_JOBS,
          '>'
        );

        if (!resp || resp.length === 0) {
          // Timeout block 5000ms khong co job -> gui lai heartbeat va tiep tuc
          await this.sendHeartbeat();
          continue;
        }

        // resp co cau truc: [ [ 'jobs:generate', [ [ entryId, [k1, v1, ...] ] ] ] ]
        const streamData = resp[0];
        const entries = streamData[1];

        for (const [entryId, rawFields] of entries) {
          await this.processRedisJob(entryId, rawFields);
        }
      } catch (err) {
        if (!this.isRunning || !this.redisConnected) break;
        console.warn('[AI 2.1 Redis] Loi trong consumer loop:', err.message);
        // Nghi 2 giay roi thu tiep
        await new Promise(r => setTimeout(r, 2000));
      }
    }

    this.isConsuming = false;
  }

  /**
   * Xu ly 1 job tu Redis Stream theo dung hop dong nhom B4
   */
  async processRedisJob(entryId, rawFields) {
    const jobData = parseStreamFields(rawFields);
    const jobId = jobData.job_id || ('job-' + Date.now());
    const query = jobData.query || jobData.slug || 'art deco masterpiece';
    const source = jobData.source || 'SEARCH';
    const styleId = jobData.style_id || 'deco-v1';

    console.log(`[AI 2.1 Redis] >>> NHAN JOB [${jobId}] tu ${source}: "${query}" (Entry: ${entryId})`);
    const startTime = Date.now();

    try {
      // 1. Sinh anh Art Deco
      const buffer = await this.synthesizeArtDecoImage(query);

      // 2. Luu vao Storage va Database SQLite
      const storeResult = await storageService.storeImage({
        buffer,
        prompt: query,
        aiCode: this.aiId,
        styleId: styleId,
      });

      const durationMs = Date.now() - startTime;
      const imageRecord = storeResult.image;

      // 3. Chuan bi ket qua theo dung schema hop dong
      const resultEvent = {
        job_id: jobId,
        status: 'DONE',
        image_id: imageRecord.id,
        image_name: imageRecord.image_name,
        ai_code: this.aiId,
        duration_ms: durationMs,
      };

      const resultJson = JSON.stringify(resultEvent);

      // 4. Ban vao Stream job:events cho Gateway
      await this.redis.xadd(config.REDIS_STREAM_EVENTS, '*', 'payload', resultJson);

      // 5. Ghi khoa phu job:{job_id}:result voi TTL 1 gio (3600s)
      await this.redis.set(`job:${jobId}:result`, resultJson, 'EX', config.REDIS_RESULT_TTL);

      // 6. XACK de bao hoan tat
      await this.redis.xack(config.REDIS_STREAM_JOBS, config.REDIS_GROUP, entryId);

      this.redisJobsProcessed++;
      this.generatedCount++;
      this.lastGeneratedPrompt = query;
      this.lastGeneratedTime = new Date().toISOString();

      // Ghi log he thong
      db.logActivity('AI_GENERATE_REDIS', `Hoan thanh Job ${jobId} ("${query}") trong ${durationMs}ms qua Redis Stream`, imageRecord.id);

      console.log(`[AI 2.1 Redis] <<< HOAN TAT JOB [${jobId}] trong ${durationMs}ms -> Da XACK va ban job:events!`);
    } catch (err) {
      console.error(`[AI 2.1 Redis] !!! LOI xu ly job ${jobId}:`, err.message);
      // QUY TAC HOP DONG:
      // "Loi tam thoi (mang, OOM) => KHONG ack de XAUTOCLAIM giao lai sau 120s"
    }
  }

  /**
   * Khoi chay toan bo AI Worker (ca Background Local va Redis Stream)
   */
  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    console.log('[AI 2.1] Khoi chay AI Worker 2.1.');

    // 1. Khoi tao Redis Stream theo hop dong nhom B4
    this.initRedis();

    // 2. Chay background cycle cuc bo (tu sinh 50 topic bach khoa neu chua du)
    setTimeout(() => this.runBackgroundCycle(), 5000);
    this.timer = setInterval(() => this.runBackgroundCycle(), config.AI_AUTO_GENERATE_INTERVAL_SEC * 1000);
  }

  async runBackgroundCycle() {
    if (!this.isRunning) return;

    try {
      // Tim chu de CHUA duoc sinh va chua duoc xu ly
      const notGeneratedYet = ENCYCLOPEDIA_TOPICS.find(topic => {
        const slug = storageService.createSlug(topic);
        if (this._generatedTopics.has(slug)) return false;
        const existing = db.findImageBySlugAndAi(slug, this.aiId);
        if (existing) {
          this._generatedTopics.add(slug);
          return false;
        }
        return true;
      });

      if (notGeneratedYet) {
        console.log('[AI 2.1 BG] Sinh anh ngam cho chu de: "' + notGeneratedYet + '"');
        this._generatedTopics.add(storageService.createSlug(notGeneratedYet));
        await this.generateOnDemand(notGeneratedYet);
      } else {
        // Tat ca chu de da sinh xong - dung timer background, chi cho nhan job tu Redis
        if (this.timer) {
          clearInterval(this.timer);
          this.timer = null;
          console.log(`[AI 2.1 BG] Da sinh du ${ENCYCLOPEDIA_TOPICS.length} chu de bach khoa. Chuyen sang che do truc Redis Stream.`);
        }
      }
    } catch (err) {
      console.error('[AI 2.1 BG] Loi chu ky ngam:', err.message);
    }
  }

  stop() {
    this.isRunning = false;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.redis) {
      try {
        this.redis.disconnect();
      } catch (e) {}
      this.redis = null;
    }
    this.redisConnected = false;
    this.isConsuming = false;
    console.log('[AI 2.1] Da tam dung hoan toan.');
  }

  getStatus() {
    return {
      ai_code: this.aiId,
      member: config.MEMBER_NAME,
      student_id: config.STUDENT_ID,
      role: config.MEMBER_ROLE,
      style_id: 'deco-v1',
      is_running: this.isRunning,
      interval_sec: config.AI_AUTO_GENERATE_INTERVAL_SEC,
      total_generated_session: this.generatedCount,
      last_prompt: this.lastGeneratedPrompt,
      last_time: this.lastGeneratedTime,
      total_topics: ENCYCLOPEDIA_TOPICS.length,
      model_name: 'Art Deco Vector Synthesis Engine (100% Offline Local)',
      redis: {
        host: config.REDIS_HOST,
        port: config.REDIS_PORT,
        connected: this.redisConnected,
        stream_in: config.REDIS_STREAM_JOBS,
        stream_out: config.REDIS_STREAM_EVENTS,
        consumer_group: config.REDIS_GROUP,
        consumer_name: config.REDIS_CONSUMER,
        last_heartbeat: this.lastHeartbeatTime,
        jobs_processed: this.redisJobsProcessed,
        last_error: this.redisLastError,
      },
    };
  }
}

const aiWorker21 = new AiWorker21();
module.exports = aiWorker21;
