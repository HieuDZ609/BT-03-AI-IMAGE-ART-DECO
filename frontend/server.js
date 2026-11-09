const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
// IP Gateway VM4 (qua Tailscale hoặc local Nginx)
const GATEWAY_URL = process.env.GATEWAY_URL || 'http://100.111.232.74:8000';

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Proxy lấy ảnh static hoặc direct presigned redirect
app.get('/api/v1/images/:id/file', async (req, res) => {
  try {
    const response = await axios.get(`${GATEWAY_URL}/api/v1/images/${req.params.id}/file`, {
      maxRedirects: 0,
      validateStatus: (status) => status >= 200 && status < 400
    });
    if (response.status === 302 || response.status === 301) {
      return res.redirect(response.headers.location);
    }
    res.status(response.status).send(response.data);
  } catch (err) {
    res.status(404).send('Image file not found');
  }
});

// Proxy lấy trạng thái job & SSE stream
app.get('/api/v1/jobs/:id', async (req, res) => {
  try {
    const response = await axios.get(`${GATEWAY_URL}/api/v1/jobs/${req.params.id}`);
    res.json(response.data);
  } catch (err) {
    res.status(500).json({ error: 'Gateway unavailable' });
  }
});

app.get('/api/v1/jobs/:id/events', (req, res) => {
  // Proxy SSE stream từ API Gateway
  res.redirect(`${GATEWAY_URL}/api/v1/jobs/${req.params.id}/events`);
});

// Route chính Trang chủ / Tìm kiếm
app.get('/', async (req, res) => {
  const page = parseInt(req.query.page, 10) || 1;
  const query = (req.query.q || '').trim();
  const worker = (req.query.worker || '').trim();

  try {
    // 1. Gọi API Search / List trên API Gateway
    const searchUrl = query 
      ? `${GATEWAY_URL}/api/v1/search?q=${encodeURIComponent(query)}&page=${page}${worker ? '&worker=' + encodeURIComponent(worker) : ''}`
      : `${GATEWAY_URL}/api/v1/images?page=${page}&size=50${worker ? '&worker=' + encodeURIComponent(worker) : ''}`;

    const apiRes = await axios.get(searchUrl);
    const data = apiRes.data;

    // 2. Lấy thống kê AI Worker ở cuối trang
    let stats = [];
    try {
      const statsRes = await axios.get(`${GATEWAY_URL}/api/v1/statistics`);
      stats = statsRes.data;
    } catch (e) {
      console.warn("Chưa lấy được statistics từ gateway");
    }

    // 3. Nếu Search Miss -> Render giao diện sinh ảnh SSE
    if (query && data.hit === false) {
      return res.render('generating', {
        searchKeyword: query,
        jobId: data.job_id
      });
    }

    // 4. Render danh sách ảnh
    res.render('index', {
      images: data.items || [],
      currentPage: data.page || page,
      totalPages: data.totalPages || Math.max(1, Math.ceil((data.total || 0) / 50)),
      search: query,
      selectedWorker: worker || '',
      stats: stats
    });
  } catch (err) {
    console.error("Lỗi kết nối Gateway:", err.message);
    res.render('index', {
      images: [],
      currentPage: 1,
      totalPages: 1,
      search: query,
      stats: []
    });
  }
});

app.listen(PORT, () => {
  console.log(`[B4.3 Frontend] Running on http://localhost:${PORT}`);
});