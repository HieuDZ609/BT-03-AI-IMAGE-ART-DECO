const express = require('express');
const cors = require('cors');
const path = require('path');
const config = require('./config');
const db = require('./database');
const routes = require('./routes');
const aiWorker21 = require('./aiWorker21');

const app = express();

// Middleware
app.use(cors({ origin: '*' }));
app.use(express.json({ limit: '25mb' }));
app.use(express.urlencoded({ extended: true, limit: '25mb' }));

// 1. Phục vụ file tĩnh ảnh trong kho: /static/<filename>
app.use('/static', express.static(config.STORAGE_DIR));

// 2. Giao diện Web Dashboard Quản trị & Giám sát kho ảnh: /
app.use(express.static(path.join(__dirname, '..', 'public')));

// 3. Đăng ký REST API routes
app.use('/api', routes);

// Khởi động server
async function startServer() {
  // Khởi tạo Database SQLite
  db.initDatabase();

  // Khởi động server HTTP
  const server = app.listen(config.PORT, async () => {
    console.log(`==================================================================`);
    console.log(`🏛️ B4.2 - IMAGE STORAGE & DATABASE SERVICE (THÀNH VIÊN 2)`);
    console.log(`👤 Phụ trách: ${config.MEMBER_NAME}`);
    console.log(`🤖 AI Local Worker: Mã ${config.AI_ID} (100% Offline Generator)`);
    console.log(`🌐 Server đang chạy tại: http://localhost:${config.PORT}`);
    console.log(`🖼️ Thư mục ảnh phục vụ: http://localhost:${config.PORT}/static/`);
    console.log(`📊 Dashboard Quản trị: http://localhost:${config.PORT}/`);
    console.log(`📋 API Docs & Endpoints: http://localhost:${config.PORT}/api/images`);
    console.log(`==================================================================`);

    // Gieo ảnh mẫu ban đầu nếu kho còn trống để sẵn sàng demo ngay
    try {
      const imgInfo = db.getImages({ page: 1, size: 1 });
      if (imgInfo.total === 0) {
        console.log('🌱 Kho ảnh đang trống. Đang khởi tạo bộ ảnh Art Deco ban đầu...');
        const initialTopics = [
          'black dog',
          'solar system',
          'red rose',
          'golden eagle',
          'saturn rings',
          'blue whale',
          'dna double helix',
          'sunflower blossom',
          'atom electron structure',
          'green sea turtle',
          'giant redwood tree',
          'roman colosseum'
        ];

        for (const topic of initialTopics) {
          await aiWorker21.generateOnDemand(topic);
        }
        console.log(`✅ Đã khởi tạo thành công ${initialTopics.length} ảnh bách khoa toàn thư ban đầu!`);
      }
    } catch (e) {
      console.warn('Lỗi khi tạo ảnh ban đầu:', e.message);
    }

    // Tự động khởi chạy tiến trình AI 2.1 chạy ngầm sinh ảnh liên tục
    aiWorker21.start();
  });

  return server;
}

if (require.main === module) {
  startServer().catch(err => {
    console.error('Không thể khởi động server:', err);
  });
}

module.exports = { app, startServer };
