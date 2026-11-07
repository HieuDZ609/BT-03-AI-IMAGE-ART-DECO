# ĐẶC TẢ TÀI LIỆU API (OPENAPI 3 · PREFIX /api/v1)
## MODULE: DATA & STORAGE (B4.2 – NGUYỄN THÀNH ĐÔ · 24IT002)
**Hệ thống:** Distributed AI Image Warehouse (Nhóm B4)  
**Địa chỉ triển khai:** Port `8002` (VM2: `192.168.100.12` / Localhost)  
**Base URL:** `http://<IP_MAY_B4.2>:8002/api/v1`  
**Phong cách ảnh:** `ART DECO` (Gold `#C9A227`, Cream `#F4EAD5`, Muted Teal `#1E6E6B`)

---

## 1. Lấy danh sách ảnh phân trang (Cho B4.3 Frontend)
- **Method:** `GET`
- **Endpoint:** `/api/v1/images`
- **Query Parameters:**
  - `page`: Số trang (Mặc định: `1`)
  - `size`: Số ảnh mỗi trang (Mặc định: `50`, đúng yêu cầu đề bài)
- **Quy tắc sắp xếp:** Luôn sắp xếp theo thời gian tạo mới nhất ở đầu (`created_at DESC`).
- **Response mẫu (200 OK):**
```json
{
  "page": 1,
  "size": 50,
  "total": 300,
  "total_pages": 6,
  "items": [
    {
      "image_id": "053bb902-aeb2-46de-b10c-c4777dad6819",
      "image_name": "black dog 2.1.png",
      "slug": "black dog",
      "prompt": "black dog",
      "style_id": "deco-v1",
      "ai_code": "2.1",
      "worker_id": "W2",
      "storage_key": "black-dog/2.1/56645ea19ae9.png",
      "sha256": "56645ea19ae99fa631d3ce4488d791624d4cbc38daf7be7997c57d9d064048fc",
      "width": 256,
      "height": 256,
      "format": "PNG",
      "file_size": 6399,
      "file_url": "/static/black%20dog%202.1.png",
      "created_at": "2026-11-04T10:12:00Z"
    }
  ]
}
```

---

## 2. Tìm kiếm ảnh theo tên tiếng Anh (Cho B4.4 Gateway & B4.3 Frontend)
- **Method:** `GET`
- **Endpoint:** `/api/v1/search?q=black+dog&page=1`
- **Quy tắc:**
  - Nếu **HIT** (Kho đã có ảnh): Trả về danh sách ảnh ngay lập tức.
  - Nếu **MISS** (Kho chưa có ảnh): Tự động sinh ảnh trong phiên hoặc trả về job sinh ảnh để client theo dõi qua polling / SSE. **Tuyệt đối không bao giờ trả "không có kết quả"**.
- **Response khi HIT (200 OK):**
```json
{
  "hit": true,
  "page": 1,
  "size": 50,
  "total": 1,
  "items": [
    {
      "image_id": "053bb902-aeb2-46de-b10c-c4777dad6819",
      "image_name": "black dog 2.1.png",
      "slug": "black dog",
      "ai_code": "2.1",
      "url": "/static/black%20dog%202.1.png",
      "created_at": "2026-11-04T10:12:00Z"
    }
  ]
}
```
- **Response khi MISS (Chưa có ảnh, đang sinh trong phiên / xếp hàng):**
```json
{
  "hit": false,
  "job_id": "b7f1e4...",
  "status": "QUEUED",
  "message": "Đang sinh ảnh mới cho chủ đề này…"
}
```

---

## 3. Thống kê số lượng ảnh theo từng AI Worker (Cho Footer Website B4.3)
- **Method:** `GET`
- **Endpoint:** `/api/v1/statistics`
- **Response mẫu (200 OK):**
```json
{
  "status": "success",
  "total_images": 320,
  "items": [
    {
      "ai_code": "1.1",
      "member": "Võ Quốc Đạt",
      "model": "Stable Diffusion 1.5 Local",
      "total": 60,
      "online": true,
      "last_heartbeat": "2026-11-04T10:15:00Z"
    },
    {
      "ai_code": "2.1",
      "member": "Nguyễn Thành Đô",
      "model": "Art Deco Local Procedural Generator",
      "total": 95,
      "online": true,
      "last_heartbeat": "2026-11-04T10:15:00Z"
    },
    {
      "ai_code": "3.1",
      "member": "Nguyễn Văn Thái Hào",
      "model": "Local Light Model",
      "total": 55,
      "online": true,
      "last_heartbeat": "2026-11-04T10:15:00Z"
    },
    {
      "ai_code": "4.1",
      "member": "Hà Điền Trung Hiếu",
      "model": "SD-Turbo Local Integration",
      "total": 65,
      "online": true,
      "last_heartbeat": "2026-11-04T10:15:00Z"
    },
    {
      "ai_code": "5.1",
      "member": "Nguyễn Văn Hiếu",
      "model": "Local Backup Worker",
      "total": 45,
      "online": true,
      "last_heartbeat": "2026-11-04T10:15:00Z"
    }
  ]
}
```

---

## 4. Thêm ảnh mới vào kho (Cho các AI Workers B4.1 -> B4.5 nộp ảnh)
- **Method:** `POST`
- **Endpoint:** `/api/v1/images`
- **Chống trùng lặp:** Kiểm tra đồng thời cặp `(slug, ai_code)` và `sha256`. Nếu phát hiện trùng lặp, trả về mã `409 Conflict`.

---

## 5. Yêu cầu sinh ảnh Art Deco thủ công
- **Method:** `POST`
- **Endpoint:** `/api/v1/generate`
- **Payload:**
```json
{
  "query": "red hat"
}
```
- **Response:** Trả về `{ "status": "success", "job_id": "...", "image": { "image_name": "red hat 2.1.png", ... } }`.
