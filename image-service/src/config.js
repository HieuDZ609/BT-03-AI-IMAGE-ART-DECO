const path = require('path');
const fs = require('fs');

const ROOT_DIR = path.resolve(__dirname, '..');

// Tu dong load .env neu co
const envPath = path.join(ROOT_DIR, '.env');
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx !== -1) {
      const key = trimmed.slice(0, eqIdx).trim();
      const val = trimmed.slice(eqIdx + 1).trim();
      if (!process.env[key]) {
        process.env[key] = val;
      }
    }
  }
}

// IP của VM2 trong mạng VMware NAT / Tailscale
const HOST_IP = process.env.HOST_IP || '192.168.100.12';
const PORT = parseInt(process.env.PORT) || 8002;

// Redis cấu hình chuẩn theo Hợp đồng nhóm B4 (Core node VM4 - 100.111.232.74:6379)
const REDIS_HOST = process.env.REDIS_HOST || '100.111.232.74';
const REDIS_PORT = parseInt(process.env.REDIS_PORT) || 6379;
const REDIS_PASSWORD = process.env.REDIS_PASSWORD || 'B4Deco_Redis_2026!';
const REDIS_URL = process.env.REDIS_URL || `redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0`;

module.exports = {
  PORT,
  HOST_IP,
  BASE_URL: process.env.BASE_URL || ('http://' + HOST_IP + ':' + PORT),

  AI_ID: '2.1',
  MEMBER_NAME: 'Nguyen Thanh Do',
  MEMBER_ROLE: 'B4.2 - Image Storage and Database',
  STUDENT_ID: '24IT002',

  STORAGE_DIR: path.join(ROOT_DIR, 'storage', 'images'),
  DB_PATH: path.join(ROOT_DIR, 'data', 'storage.sqlite'),
  PAGE_SIZE_DEFAULT: 50,

  AI_AUTO_GENERATE_INTERVAL_SEC: 15,
  AI_MIN_DIMENSION: 256,

  // Redis Stream & Heartbeat Settings (Tuân thủ hợp đồng nhóm B4)
  REDIS_URL,
  REDIS_HOST,
  REDIS_PORT,
  REDIS_PASSWORD,
  REDIS_STREAM_JOBS: 'jobs:generate',
  REDIS_STREAM_EVENTS: 'job:events',
  REDIS_GROUP: 'workers',
  REDIS_CONSUMER: '2.1',
  REDIS_HEARTBEAT_SEC: 30,
  REDIS_HEARTBEAT_TTL: 90,
  REDIS_RESULT_TTL: 3600,
};
