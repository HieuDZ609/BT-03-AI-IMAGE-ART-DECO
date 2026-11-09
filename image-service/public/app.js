let currentPage = 1;
let currentQuery = '';
const PAGE_LIMIT = 50;

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

function initApp() {
  loadStats();
  loadImages(1);
  setupEvents();
  setupUploadDropzone();

  setInterval(() => {
    loadStats();
    if (!currentQuery) {
      loadImages(currentPage, false);
    }
  }, 10000);
}

function setupEvents() {
  // 1. Nút bật/tắt AI 2.1
  const btnToggleAi = document.getElementById('btn-toggle-ai');
  btnToggleAi.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/v1/ai/toggle', { method: 'POST' });
      const data = await res.json();
      updateAiWorkerStatus(data.data);
    } catch (err) {
      alert('Lỗi chuyển trạng thái AI: ' + err.message);
    }
  });

  // 2. Nút sinh ảnh On-Demand Art Deco
  const btnGenOnDemand = document.getElementById('btn-generate-ondemand');
  const inputPrompt = document.getElementById('input-ondemand-prompt');

  const triggerGenerate = async (prompt) => {
    if (!prompt.trim()) {
      alert('Vui lòng nhập từ khóa tiếng Anh!');
      return;
    }

    btnGenOnDemand.disabled = true;
    btnGenOnDemand.innerText = '⏳ Đang sinh ảnh Art Deco...';

    try {
      const res = await fetch('/api/v1/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: prompt.trim() })
      });
      const data = await res.json();
      if (data.status === 'success') {
        inputPrompt.value = '';
        loadStats();
        loadImages(1);
      } else {
        alert('Lỗi: ' + (data.message || 'Không thể sinh ảnh.'));
      }
    } catch (e) {
      alert('Lỗi kết nối: ' + e.message);
    } finally {
      btnGenOnDemand.disabled = false;
      btnGenOnDemand.innerText = '⚡ Sinh Ảnh Art Deco Ngay (AI 2.1)';
    }
  };

  btnGenOnDemand.addEventListener('click', () => triggerGenerate(inputPrompt.value));
  inputPrompt.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') triggerGenerate(inputPrompt.value);
  });

  // 3. Quick tags
  document.querySelectorAll('.tag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = btn.getAttribute('data-prompt');
      inputPrompt.value = p;
      triggerGenerate(p);
    });
  });

  // 4. Tìm kiếm trong Gallery
  const btnSearch = document.getElementById('btn-search-gallery');
  const btnReset = document.getElementById('btn-reset-gallery');
  const searchInput = document.getElementById('gallery-search-input');

  const doSearch = () => {
    currentQuery = searchInput.value.trim();
    currentPage = 1;
    loadImages(1);
  };

  btnSearch.addEventListener('click', doSearch);
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doSearch();
  });

  btnReset.addEventListener('click', () => {
    searchInput.value = '';
    currentQuery = '';
    currentPage = 1;
    loadImages(1);
  });

  // 5. Phân trang
  document.getElementById('btn-prev-page').addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      loadImages(currentPage);
    }
  });

  document.getElementById('btn-next-page').addEventListener('click', () => {
    currentPage++;
    loadImages(currentPage);
  });

  // 6. Nút làm mới thống kê
  document.getElementById('btn-refresh-stats').addEventListener('click', () => {
    loadStats();
  });

  // 7. Nút Copy URL API
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const url = window.location.origin + btn.getAttribute('data-url');
      navigator.clipboard.writeText(url);
      const originalText = btn.innerText;
      btn.innerText = 'Đã Copy!';
      setTimeout(() => btn.innerText = originalText, 1500);
    });
  });

  // 8. Đóng modal
  document.getElementById('btn-close-modal').addEventListener('click', () => {
    document.getElementById('image-modal').style.display = 'none';
  });
  document.getElementById('image-modal').addEventListener('click', (e) => {
    if (e.target.id === 'image-modal') {
      document.getElementById('image-modal').style.display = 'none';
    }
  });
}

// Tải thống kê từ Backend
async function loadStats() {
  try {
    const res = await fetch('/api/v1/statistics');
    const data = await res.json();
    if (data.status !== 'success' && !Array.isArray(data)) return;

    const list = data.workers_detail || data.items || data;
    const totalImages = data.total_images !== undefined ? data.total_images : list.reduce((s, i) => s + (i.total || 0), 0);
    
    document.getElementById('stat-total-images').innerText = totalImages;

    const ai21Worker = list.find(w => w.ai_code === '2.1');
    document.getElementById('stat-ai21-images').innerText = ai21Worker ? ai21Worker.total : 0;

    // Render danh sách chi tiết các AI Workers trong cụm
    const container = document.getElementById('ai-breakdown-container');
    if (list && list.length > 0) {
      container.innerHTML = list.map(w => {
        const is21 = w.ai_code === '2.1';
        return `
          <div class="ai-row ${is21 ? 'active-local' : ''}">
            <div class="ai-meta">
              <span class="ai-code-badge" style="background: ${is21 ? 'linear-gradient(135deg, #c9a227, #78350f)' : 'rgba(255,255,255,0.1)'};">
                ${w.ai_code}
              </span>
              <div class="ai-name-role">
                <span class="ai-owner">${w.member || w.member_name} ${is21 ? '(Máy bạn - VM2)' : ''}</span>
                <span class="ai-model">${w.model || w.model_name} &bull; <strong style="color: ${w.online || w.status === 'ONLINE' ? '#10b981' : '#9ca3af'}">${w.status || (w.online ? 'ONLINE' : 'STANDBY')}</strong></span>
              </div>
            </div>
            <div class="ai-count-box">
              <span class="ai-count-num">${w.total || 0}</span>
              <span class="ai-count-label">ảnh trong kho</span>
            </div>
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    console.error('Lỗi tải thống kê:', err);
  }
}

// Tải danh sách ảnh trong kho
async function loadImages(page = 1, showLoading = true) {
  const grid = document.getElementById('images-grid');
  if (showLoading) {
    grid.innerHTML = '<div class="grid-loading">Đang tải danh sách ảnh Art Deco từ kho lưu trữ...</div>';
  }

  const autoGen = document.getElementById('chk-auto-generate').checked;
  let url = `/api/v1/images?page=${page}&size=${PAGE_LIMIT}`;
  if (currentQuery) {
    url = `/api/v1/search?q=${encodeURIComponent(currentQuery)}&page=${page}&size=${PAGE_LIMIT}&auto_generate=${autoGen}`;
  }

  try {
    const res = await fetch(url);
    const data = await res.json();

    const list = data.items || data.data || [];
    currentPage = data.page || 1;
    const total = data.total || list.length || 0;
    const totalPages = data.total_pages || Math.ceil(total / PAGE_LIMIT) || 1;

    document.getElementById('pagination-info').innerText = `Trang ${currentPage} / ${totalPages} (Tổng ${total} ảnh trong kho)`;
    document.getElementById('current-page-num').innerText = currentPage;
    document.getElementById('btn-prev-page').disabled = currentPage <= 1;
    document.getElementById('btn-next-page').disabled = currentPage >= totalPages;

    if (list.length === 0) {
      grid.innerHTML = '<div class="grid-loading">Chưa có ảnh nào trong kho hoặc không tìm thấy ảnh phù hợp.</div>';
      return;
    }

    grid.innerHTML = list.map(img => {
      const filename = img.image_name || img.filename;
      const aiCode = img.ai_code || '2.1';
      const prompt = img.prompt || img.slug || '';
      const sizeKb = img.file_size ? (img.file_size / 1024).toFixed(1) : '24.5';
      const hashShort = (img.sha256 || img.file_hash || '').substring(0, 16);
      const imgId = img.image_id || img.id;
      const imgUrl = img.url || img.file_url;

      return `
        <div class="image-card" data-id="${imgId}">
          <div class="image-thumb-wrapper" onclick="viewImageDetail('${imgId}')">
            <img src="${imgUrl}" alt="${prompt}" class="image-thumb" loading="lazy" />
            <span class="image-ai-tag">AI ${aiCode}</span>
          </div>
          <div class="image-details">
            <span class="image-filename" title="${filename}">${filename}</span>
            <div class="image-sub">
              <span>${img.width || 256}x${img.height || 256} &bull; ${sizeKb} KB</span>
              <span style="color:#c9a227; font-weight:700;">Art Deco</span>
            </div>
            <div class="image-hash" title="Mã băm SHA-256 chống trùng lặp: ${img.sha256 || img.file_hash}">
              #${hashShort}...
            </div>
            <div class="image-card-actions">
              <button class="btn btn-xs btn-outline" style="flex:1" onclick="viewImageDetail('${imgId}')">🔍 Xem</button>
              <button class="btn btn-xs btn-danger" onclick="deleteImage('${imgId}')">🗑️ Xóa</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    if (data.auto_generated) {
      loadStats();
    }
  } catch (err) {
    grid.innerHTML = `<div class="grid-loading">Lỗi kết nối API: ${err.message}</div>`;
  }
}

// Xem chi tiết ảnh trong modal
window.viewImageDetail = async function(id) {
  try {
    const res = await fetch(`/api/v1/images/${id}`);
    const result = await res.json();
    const img = result.data || result;

    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
      <div style="text-align: center; margin-bottom: 1rem;">
        <img src="${img.file_url || img.url}" style="max-width: 100%; max-height: 280px; border-radius: 8px; border: 2px solid #c9a227;" />
      </div>
      <table style="width:100%; font-size: 0.85rem; border-collapse: collapse;">
        <tr><td style="color:#9ca3af; padding:4px 0;">Tên file ảnh:</td><td style="font-weight:700; color:#fff;">${img.image_name}</td></tr>
        <tr><td style="color:#9ca3af; padding:4px 0;">Slug / Prompt:</td><td style="color:#38bdf8;">${img.slug || img.prompt}</td></tr>
        <tr><td style="color:#9ca3af; padding:4px 0;">Phong cách:</td><td style="color:#c9a227; font-weight:700;">Art Deco (${img.style_id || 'deco-v1'})</td></tr>
        <tr><td style="color:#9ca3af; padding:4px 0;">Mã AI sinh ảnh:</td><td style="color:#f59e0b; font-weight:700;">AI ${img.ai_code} (Worker ${img.worker_id || 'W2'})</td></tr>
        <tr><td style="color:#9ca3af; padding:4px 0;">Kích thước:</td><td>${img.width} x ${img.height} pixel</td></tr>
        <tr><td style="color:#9ca3af; padding:4px 0;">Dung lượng:</td><td>${((img.file_size || 25000) / 1024).toFixed(2)} KB</td></tr>
        <tr><td style="color:#9ca3af; padding:4px 0;">MinIO Storage Key:</td><td style="font-family:monospace; font-size:0.75rem; word-break:break-all; color:#93c5fd;">${img.storage_key}</td></tr>
        <tr><td style="color:#9ca3af; padding:4px 0;">Mã hash SHA-256:</td><td style="font-family:monospace; font-size:0.75rem; color:#10b981; word-break:break-all;">${img.sha256}</td></tr>
        <tr><td style="color:#9ca3af; padding:4px 0;">Thời gian tạo:</td><td style="color:#cbd5e1;">${new Date(img.created_at).toLocaleString('vi-VN')}</td></tr>
      </table>
      <div style="margin-top: 1.25rem; display: flex; justify-content: flex-end; gap: 0.75rem;">
        <a href="${img.file_url || img.url}" download="${img.image_name}" class="btn btn-sm btn-primary">⬇️ Tải Ảnh Về</a>
      </div>
    `;

    document.getElementById('image-modal').style.display = 'flex';
  } catch (err) {
    alert('Không thể xem chi tiết: ' + err.message);
  }
};

window.deleteImage = async function(id) {
  if (!confirm('Bạn có chắc muốn xóa ảnh này khỏi kho?')) return;
  try {
    const res = await fetch(`/api/v1/images/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.status === 'success') {
      loadStats();
      loadImages(currentPage);
    } else {
      alert('Lỗi xóa ảnh: ' + data.message);
    }
  } catch (err) {
    alert('Lỗi kết nối: ' + err.message);
  }
};

function updateAiWorkerStatus(status) {
  const statusText = document.getElementById('ai-status-text');
  const btnToggle = document.getElementById('btn-toggle-ai');

  if (status.is_running) {
    statusText.innerText = `Đang chạy ngầm (Chu kỳ ${status.interval_sec}s)`;
    statusText.style.color = '#10b981';
    btnToggle.innerText = '⏸️ Tạm Dừng AI';
    btnToggle.className = 'btn btn-warning';
  } else {
    statusText.innerText = 'Đã tạm dừng';
    statusText.style.color = '#f43f5e';
    btnToggle.innerText = '▶️ Bật Lại AI';
    btnToggle.className = 'btn btn-primary';
  }
}

function setupUploadDropzone() {
  const dropzone = document.getElementById('upload-dropzone');
  const fileInput = document.getElementById('upload-file-input');
  const resultBox = document.getElementById('upload-result');

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = '#c9a227';
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.style.borderColor = 'rgba(255, 255, 255, 0.15)';
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'rgba(255, 255, 255, 0.15)';
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  async function handleFileUpload(file) {
    resultBox.style.display = 'block';
    resultBox.className = 'upload-result-box';
    resultBox.innerHTML = `⏳ Đang tính toán mã băm SHA-256 và lưu kho...`;

    const formData = new FormData();
    formData.append('image', file);
    formData.append('ai_code', '2.1');
    formData.append('filename', file.name);

    try {
      const res = await fetch('/api/v1/images', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (res.status === 409 || data.status === 'duplicate') {
        resultBox.className = 'upload-result-box duplicate';
        resultBox.innerHTML = `
          <strong>🛡️ PHÁT HIỆN TRÙNG LẶP HASH SHA-256!</strong><br/>
          Hệ thống từ chối lưu ảnh trùng lặp. Ảnh có nội dung hoàn toàn trùng với: <strong>${data.image.image_name}</strong>.<br/>
          <span style="font-family:monospace; font-size:0.75rem;">Mã SHA-256: ${data.image.sha256}</span>
        `;
      } else if (data.status === 'success') {
        resultBox.className = 'upload-result-box success';
        resultBox.innerHTML = `
          <strong>✅ LƯU ẢNH THÀNH CÔNG!</strong><br/>
          Đã thêm ảnh mới: <strong>${data.image.image_name}</strong><br/>
          <span style="font-family:monospace; font-size:0.75rem;">MinIO Storage Key: ${data.image.storage_key}</span>
        `;
        loadStats();
        loadImages(1);
      } else {
        resultBox.className = 'upload-result-box duplicate';
        resultBox.innerHTML = `Lỗi: ${data.message}`;
      }
    } catch (err) {
      resultBox.className = 'upload-result-box duplicate';
      resultBox.innerHTML = `Lỗi kết nối server: ${err.message}`;
    }
  }
}
