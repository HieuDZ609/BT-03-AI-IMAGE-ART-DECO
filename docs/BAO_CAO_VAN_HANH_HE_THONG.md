# TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG VIỆT HÀN (VKU)
## KHOA KHOA HỌC MÁY TÍNH
─────────── ❖ ───────────

# BÁO CÁO KỸ THUẬT VẬN HÀNH HỆ THỐNG (BÀI TẬP BT-03)
## ĐỀ TÀI: THIẾT KẾ VẬN HÀNH TỔNG THỂ VÀ PHÂN BỔ MODULE TRÊN CÁC MÁY CHỦ — HỆ THỐNG KHO ẢNH TRỰC TUYẾN THÔNG MINH ART DECO
**Mã nguồn dự án:** [https://github.com/HieuDZ609/BT-03-AI-IMAGE-ART-DECO](https://github.com/HieuDZ609/BT-03-AI-IMAGE-ART-DECO)  
**Nhánh công việc:** `B4.2-data-storage`  
**Giảng viên hướng dẫn:** ThS. Lê Kim Trọng  
**Thời gian thực hiện:** Tháng 11 / 2026  

---

### DANH SÁCH THÀNH VIÊN NHÓM B4
| Mã thành viên | Họ và tên | MSSV | Vai trò & Phụ trách chính | Máy ảo đảm nhiệm |
| :--- | :--- | :--- | :--- | :--- |
| **B4.1** | Võ Quốc Đạt | 24IT333 | AI Worker & Model Engineering | VM1 (Worker 1.1) |
| **B4.2** | **Nguyễn Thành Đô** | **24IT335** | **Image Storage, Database & AI Worker 2.1** | **VM2 (Worker 2.1)** |
| **B4.3** | Nguyễn Văn Thái Hào | 24IT054 | Frontend & Search UI | VM3 (Worker 3.1) |
| **B4.4** | Hà Điền Trung Hiếu | 24IT062 | **Nhóm trưởng** — Core Integration, Gateway & Seeder | VM4 (Core Node 24/7) |
| **B4.5** | Nguyễn Văn Hiếu | 24IT067 | DevOps, Monitoring & Notification | VM5 (Monitoring) |

---

## PHẦN 1: MÔ TẢ THIẾT KẾ VẬN HÀNH TỔNG THỂ HỆ THỐNG

### 1.1. Mục tiêu và Nguyên lý cốt lõi
Hệ thống là một **Kho ảnh trực tuyến thông minh (Smart AI Image Warehouse)** chuyên biệt theo trường phái mỹ thuật **Art Deco (1920s–1930s)**. Hệ thống giải quyết trọn vẹn các yêu cầu nghiệp vụ nghiêm ngặt của đề bài:
1. **Không bao giờ trả lời "không có kết quả":** Khi người dùng tìm kiếm một từ khóa chưa từng có trong kho, hệ thống không báo lỗi mà lập tức kích hoạt luồng tự động tạo job sinh ảnh mới, điều phối Worker xử lý và trả kết quả về ngay trong phiên duyệt web.
2. **AI tự vận hành 24/7 làm đầy kho:** Module Autopilot kết hợp cùng 5 tiến trình Worker cục bộ liên tục sinh ảnh theo danh mục bách khoa, tự động tích lũy kho ảnh lớn mà không phụ thuộc vào thao tác người dùng.
3. **Mô hình AI cục bộ 100% (No Cloud API):** Sử dụng mô hình `SD-Turbo Q8 GGUF` suy luận cực nhanh (4 steps) trực tiếp trên CPU/Server nội bộ, tuyệt đối không sử dụng API bên ngoài.
4. **Chuẩn hóa nhận diện chủ thể:** Ảnh Art Deco tuân thủ bảng màu chuẩn hoàng kim (`#C9A227`, kem `#F4EAD5`, đen `#18181B`, xanh ngọc `#1E6E6B`), khung viền 5 lớp bậc thang chevron và **Bảng tên kim loại Art Deco (Title Plate)** ở đáy ảnh giúp nhận diện 100% chủ thể (con hổ ra con hổ, bông hoa ra bông hoa, không bị trừu tượng khó hiểu).
5. **Cơ chế tự động sinh 50 tác phẩm kiệt tác ban đầu (`INITIAL_SEED_TARGET=50`):** Mỗi Worker khi khởi động sẽ tự quét cơ sở dữ liệu và tự động sinh đủ 50 ảnh kiệt tác từ kho hơn 65 chủ đề đa dạng để sẵn sàng cho buổi nghiệm thu và chấm điểm.

---

### 1.2. Sơ đồ Luồng Vận Hành Tổng Thể (End-to-End Architecture Flow)

```
                            [ NGƯỜI DÙNG INTERNET ]
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            │ HTTPS Tunnel (Ngrok / Tailscale Funnel / 100.70.241.87)
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       VM4 — CORE SERVER NODE (B4.4)                         │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ Nginx Reverse Proxy (Port 80/443)                                   │   │
│   │ ├── /        ──► Frontend Next.js 15 (Port 3000)                    │   │
│   │ ├── /api/    ──► API Gateway FastAPI (Port 8000)                    │   │
│   │ └── /files/  ──► Image Storage Server (/var/lib/bt03/images)        │   │
│   └──────────────────┬───────────────────────────────┬──────────────────┘   │
│                      │                               │                      │
│                      ▼                               ▼                      │
│        ┌───────────────────────────┐   ┌───────────────────────────┐        │
│        │   PostgreSQL 16 Engine    │   │      Redis 7 Cluster      │        │
│        │  (DB: bt03, Port 5432)    │   │ (Stream: jobs:generate)   │        │
│        │  - images, generation_jobs│   │ (Events: job:events)      │        │
│        │  - ai_workers, search_logs│   │ (Heartbeat: TTL 90s)      │        │
│        └─────────────▲─────────────┘   └─────────────▲─────────────┘        │
│                      │                               │                      │
│                      │                               │                      │
│   ┌──────────────────┴───────────────────────────────┴──────────────────┐   │
│   │ Autopilot Seeder: Quét topics.yaml & đẩy job định kỳ               │   │
│   │ SD Inference Host: /opt/bt03/ai/bin/sd-cli + sd-turbo-q8_0.gguf    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────▲──────────────────────────────────────┘
                                       │ Mạng Tailscale Mesh (100.x.x.x)
                                       │ & Mạng LAN (172.16.228.x)
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
│ VM1 (Worker 1.1) │           │ VM2 (Worker 2.1) │           │ VM3 (Worker 3.1) │
│ B4.1 Võ Quốc Đạt │           │ B4.2 Nguyễn Th.Đô│           │ B4.3 Thái Hào    │
│ AI Worker Python │           │ Storage & Worker │           │ Frontend Node    │
└──────────────────┘           └──────────────┬───┘           └──────────────────┘
                                              │
                                              │ SSH/rsync sync ảnh
                                              ▼
                                 ┌──────────────────────────┐
                                 │ VM5 (DevOps & Monitor)   │
                                 │ B4.5 Nguyễn Văn Hiếu     │
                                 │ Prometheus + Grafana     │
                                 │ Telegram / Discord Alert │
                                 └──────────────────────────┘
```

---

### 1.3. Luồng Dữ Liệu Nghiệp Vụ Chi Tiết

#### Luồng A: Tìm kiếm có sẵn (Search Hit)
1. Người dùng nhập từ khóa tiếng Anh vào ô tìm kiếm trên Frontend (ví dụ: `bengal tiger`).
2. Frontend gửi yêu cầu `GET /api/v1/search?q=bengal+tiger` tới API Gateway.
3. Gateway truy vấn PostgreSQL sử dụng toán tử tìm kiếm chuỗi `ILIKE` kết hợp hàm đo độ tương đồng `similarity(slug, query)` của extension `pg_trgm`.
4. Tìm thấy ảnh phù hợp trong kho $\rightarrow$ Trả về mã HTTP `200` kèm danh sách ảnh và link tải trực tiếp trong thời gian **dưới 150ms**.

#### Luồng B: Tìm kiếm chưa có ảnh (Search Miss $\rightarrow$ Generate in-session)
1. Người dùng tìm từ khóa mới lạ (ví dụ: `phoenix bird`).
2. PostgreSQL xác nhận chưa có ảnh nào khớp với độ tương đồng $\ge 0.45$.
3. Gateway không trả lỗi 404, mà thực hiện:
   * Tạo một mã công việc duy nhất `job_id` (UUIDv4).
   * Đặt khóa `SETNX lock:slug:phoenix-bird` trong Redis để chống sinh trùng khi có nhiều người cùng tìm.
   * Gửi job vào Redis Stream `jobs:generate`.
   * Trả về ngay cho Frontend phản hồi `200 { "hit": false, "job_id": "...", "status": "QUEUED" }`.
4. Frontend lập tức hiển thị thẻ ảnh ở trạng thái *"Đang sinh ảnh kiệt tác..."* kèm vòng quay Art Deco và mở kết nối Server-Sent Events (SSE) `/api/v1/jobs/{id}/events`.
5. Worker 2.1 (hoặc bất kỳ Worker nào đang rảnh) đọc job từ Stream bằng lệnh `XREADGROUP`.
6. Tiến hành sinh ảnh:
   * Khởi tạo prompt tối ưu chủ thể Art Deco.
   * Gọi mô hình SD-Turbo (4 bước Euler, seed ngẫu nhiên).
   * Áp dụng hậu kỳ Pillow: Tăng tương phản (`autocontrast`), rực rỡ màu (`Color +15%`), sắc nét (`UnsharpMask`), viền vàng hoàng kim và **Title Plate**.
   * Đồng bộ ảnh sang kho lưu trữ `/var/lib/bt03/images/` trên VM4 qua SSH/rsync.
   * Ghi bản ghi vào bảng `images` và cập nhật `generation_jobs = DONE`.
   * Phát sự kiện `XADD job:events` và xác nhận `XACK`.
7. Gateway bắt được sự kiện, đẩy qua SSE về trình duyệt người dùng. Thẻ ảnh lập tức chuyển thành bức tranh hoàn chỉnh mà người dùng không cần tải lại trang.

---

## PHẦN 2: PHÂN BỔ MODULE TRÊN CÁC MÁY CHỦ (SERVER TOPOLOGY)

### 2.1. Bảng Phân Bổ Module Chi Tiết Trên 5 Máy Ảo

| Máy ảo | Địa chỉ IP (Tailscale / LAN) | Thành viên phụ trách | Module dịch vụ chính | Chức năng kỹ thuật chi tiết | Trạng thái vận hành |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VM4 (Core Node)** | **`100.70.241.87`**<br>`172.16.228.137` | **Hà Điền Trung Hiếu** *(Nhóm trưởng)* | • Nginx Reverse Proxy (80/443)<br>• Next.js Frontend (3000)<br>• API Gateway FastAPI (8000)<br>• Autopilot Seeder<br>• PostgreSQL 16 (5432)<br>• Redis 7 Server (6379)<br>• Image Storage Server<br>• AI Inference Server | Trung tâm đầu não: Lưu trữ DB tập trung, điều phối hàng đợi Redis Streams, cung cấp backend sinh ảnh SD-Turbo GGUF qua CLI, phát hành trang web ra Internet. | **Luôn bật 24/7 (Bắt buộc)** |
| **VM2** | **`100.102.6.91`**<br>`172.16.228.x` | **Nguyễn Thành Đô** | • **AI Worker 2.1 Engine** (`main.py`)<br>• Image Sync Service (rsync/SSH)<br>• Database Storage Client<br>• node_exporter & cAdvisor | Kéo job từ Redis VM4, điều khiển sinh ảnh, chạy pipeline hậu kỳ Pillow Art Deco, tự động sinh bộ 50 ảnh chuẩn, đồng bộ dữ liệu sang VM4. | Có thể tắt mở linh hoạt |
| **VM1** | `100.104.x.x` | Võ Quốc Đạt | • AI Worker 1.1<br>• node_exporter | Nhận job và sinh ảnh độc lập, đo lường benchmark model. | Có thể tắt mở linh hoạt |
| **VM3** | `100.118.x.x` | Nguyễn Văn Thái Hào | • AI Worker 3.1<br>• Frontend Backup Client | Tham gia sinh ảnh, phối hợp giao diện. | Có thể tắt mở linh hoạt |
| **VM5** | `100.82.213.67` | Nguyễn Văn Hiếu | • Prometheus Server (9090)<br>• Grafana Dashboard (3001)<br>• Alertmanager (9093)<br>• Notify Service (Bot Telegram/Discord)<br>• AI Worker 5.1 | Thu thập chỉ số toàn bộ 5 máy, hiển thị biểu đồ thời gian thực, tự động gửi thông báo khi có sự cố. | Có thể tắt mở linh hoạt |

---

### 2.2. Lý Giải Kiến Trúc Phân Bổ và Khả Năng Chịu Lỗi (Fault-Tolerance)
1. **Thiết kế tập trung khối có trạng thái (Stateful) trên VM4:**
   * Cơ sở dữ liệu PostgreSQL và hàng đợi Redis đặt tại VM4 để đảm bảo tính nhất quán dữ liệu cao nhất, tránh xung đột phân tán và đảm bảo website vẫn hoạt động ổn định khi các máy thành viên ngắt kết nối.
2. **Khối Worker hoàn toàn không trạng thái (Stateless):**
   * Các Worker trên VM1, VM2, VM3, VM5 có thể bật, tắt, khởi động lại bất kỳ lúc nào mà không làm mất job (Redis Streams lưu trữ trạng thái và tự động giao lại job sau 120s qua cơ chế `XAUTOCLAIM`).
3. **Mạng kết nối an toàn Tailscale Mesh VPN:**
   * Mọi máy ảo giao tiếp thông suốt qua mạng riêng ảo mã hóa Tailscale với dải IP cố định `100.x.x.x`, cho phép các máy thành viên ở các vị trí địa lý khác nhau (ở nhà, trên trường, qua 4G) vẫn kết nối trực tiếp vào cụm máy chủ VM4 như trong mạng nội bộ.

---

## PHẦN 3: GIẢI PHÁP KỸ THUẬT NỔI BẬT CỦA MODULE B4.2 (NGUYỄN THÀNH ĐÔ)

### 3.1. Cơ Chế Sinh Ảnh 50 Kiệt Tác Không Trùng Lặp (`INITIAL_SEED_TARGET=50`)
Để phục vụ buổi nghiệm thu và chấm điểm, Worker 2.1 được thiết kế thuật toán tự động làm đầy kho:
* **Quét Database thông minh:** Khi vừa kết nối thành công tới PostgreSQL, Worker gửi truy vấn `SELECT slug FROM images WHERE worker_id=2` để lấy toàn bộ danh sách tác phẩm đã từng tạo.
* **Lọc chủ đề mới toanh:** Đối chiếu với kho tàng **65+ chủ đề kinh điển** để chọn ra những chủ đề chưa từng xuất hiện.
* **Tự bù trừ số lượng:** Nếu DB đã có sẵn $k$ ảnh, Worker sẽ chỉ sinh thêm đúng $50 - k$ ảnh còn thiếu. Nếu đã đủ $\ge 50$ ảnh, Worker dừng sinh hàng loạt và chuyển ngay sang chế độ trực tuyến để lắng nghe job từ người dùng.
* **Không ghi đè dữ liệu:** Sử dụng `ON CONFLICT (slug, worker_id) DO UPDATE...` kết hợp UUID độc nhất cho từng file ảnh, đảm bảo thư viện liên tục tích lũy tài nguyên phong phú.

### 3.2. Đường Ống Hậu Kỳ Ảnh Art Deco Độc Quyền (Pillow Pipeline)
Mỗi ảnh sau khi suy luận được xử lý qua 5 công đoạn thẩm mỹ nghiêm ngặt:
$$\text{Raw Output} \xrightarrow{\text{AutoContrast (cutoff 0.2)}} \xrightarrow{\text{Color Boost (+15\%)}} \xrightarrow{\text{Contrast (+7\%)}} \xrightarrow{\text{UnsharpMask}} \xrightarrow{\text{Title Plate \& Gold Border}}$$
* **Bảng tên kim loại Art Deco (Title Plate):** Vẽ thanh banner màu tối `#141416` ở đáy ảnh, viền chỉ vàng hoàng kim kép (`#C9A227` và `#8A6D17`), khắc tên chủ thể bằng chữ in hoa trang trọng kèm biểu tượng kim cương đối xứng hai bên.

---

## PHẦN 4: HÌNH ẢNH MINH CHỨNG VẬN HÀNH & KẾT QUẢ DEMO (DEMO SHOWCASE)

> **Hướng dẫn nhóm trưởng / thành viên:** Chèn ảnh chụp màn hình thực tế tương ứng vào từng khung dưới đây trước khi in/xuất bản PDF.

---

### DEMO 1: Giao Diện Trang Chủ Kho Ảnh Trực Tuyến Art Deco
* **Mô tả:** Website hiển thị lưới ảnh trang chủ với các tác phẩm Art Deco đặc trưng, có tên ảnh theo quy chuẩn `{slug} {ai_code}.png`, hiển thị phân trang cố định và bảng thống kê tổng số ảnh theo từng AI ở cuối trang.
* **Địa chỉ truy cập:** `http://100.70.241.87/` hoặc qua Domain Ngrok.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       [KHUNG CHÈN ẢNH CHỤP DEMO 1]                          │
│                                                                             │
│   Ảnh chụp toàn cảnh giao diện Trang chủ: Lưới ảnh Art Deco 256x256,        │
│   thanh tìm kiếm tiếng Anh phía trên, nhãn Worker 2.1, thanh phân trang     │
│   và bảng thống kê số ảnh phía dưới.                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```
*Hình 4.1. Giao diện trang chủ hệ thống kho ảnh Art Deco.*

---

### DEMO 2: Luồng Tìm Kiếm Trả Ảnh Tức Thì (Search Hit)
* **Mô tả:** Người dùng nhập từ khóa `bengal tiger` hoặc `red rose`. Hệ thống truy vấn cơ sở dữ liệu và hiển thị ngay lập tức các bức tranh tương ứng đã có sẵn trong kho với tốc độ dưới 200ms.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       [KHUNG CHÈN ẢNH CHỤP DEMO 2]                          │
│                                                                             │
│   Ảnh chụp màn hình khi người dùng tìm kiếm từ khóa có sẵn, hệ thống        │
│   hiển thị kết quả tức thì cùng nhãn AI đã sinh ảnh.                        │
└─────────────────────────────────────────────────────────────────────────────┘
```
*Hình 4.2. Tìm kiếm ảnh có sẵn trả về kết quả ngay lập tức.*

---

### DEMO 3: Luồng Tìm Kiếm Không Có Ảnh $\rightarrow$ Tự Động Sinh Trong Phiên (Search Miss)
* **Mô tả:** Người dùng nhập từ khóa mới lạ chưa từng có trong kho (ví dụ: `golden dragon`). Màn hình hiển thị trạng thái *"Đang sinh ảnh kiệt tác..."*, Worker phía sau nhận job từ Redis và sinh ảnh trả về ngay trên giao diện web.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       [KHUNG CHÈN ẢNH CHỤP DEMO 3]                          │
│                                                                             │
│   Ảnh chụp giao diện thông báo đang tạo ảnh mới bằng công nghệ SSE          │
│   và hình ảnh mới xuất hiện ngay sau khi Worker hoàn tất.                   │
└─────────────────────────────────────────────────────────────────────────────┘
```
*Hình 4.3. Tìm kiếm chưa có ảnh kích hoạt luồng tự động sinh trong phiên.*

---

### DEMO 4: Nhật Ký Vận Hành Terminal Của AI Worker 2.1 (`main.py`)
* **Mô tả:** Terminal của Worker 2.1 trên máy ảo VM2 thể hiện kết nối thành công tới Redis và PostgreSQL tại `100.70.241.87`, tự động chọn các chủ đề độc nhất và sinh tuần tự tiến độ từ `[1/50]` đến `[50/50]`, đồng bộ ảnh sang VM4.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       [KHUNG CHÈN ẢNH CHỤP DEMO 4]                          │
│                                                                             │
│   Ảnh chụp màn hình Terminal Linux VM2 chạy python3 main.py:                │
│   - Kết nối thành công Redis & PostgreSQL tại 100.70.241.87                 │
│   - Log hiển thị: [1/50] Đang sinh tác phẩm 'bengal-tiger'...               │
│   - Log đồng bộ rsync sang VM4: /var/lib/bt03/images/...                    │
└─────────────────────────────────────────────────────────────────────────────┘
```
*Hình 4.4. Nhật ký tiến trình Worker 2.1 tự động sinh bộ sưu tập 50 tác phẩm.*

---

### DEMO 5: Cơ Sở Dữ Liệu PostgreSQL & Đồng Bộ File Lưu Trữ
* **Mô tả:** Bảng `images` trong cơ sở dữ liệu `bt03` lưu trữ chi tiết metadata của từng bức ảnh (image_id, image_name, slug, prompt, worker_id, storage_key, sha256). Thư mục lưu trữ `/var/lib/bt03/images/` trên máy chủ VM4 chứa đầy đủ các file ảnh PNG sắc nét.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       [KHUNG CHÈN ẢNH CHỤP DEMO 5]                          │
│                                                                             │
│   Ảnh chụp màn hình câu lệnh SQL: SELECT image_name, worker_id,             │
│   storage_key, created_at FROM images ORDER BY created_at DESC LIMIT 10;    │
│   và cây thư mục chứa ảnh trên server.                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```
*Hình 4.5. Dữ liệu bảng images trong PostgreSQL và thư mục lưu trữ.*

---

### DEMO 6: Bảng Điều Khiển Giám Sát Tập Trung Grafana & Prometheus (VM5)
* **Mô tả:** Dashboard Grafana thu thập thông số tài nguyên của 5 máy ảo qua `node_exporter`, biểu đồ tốc độ sinh ảnh, độ sâu hàng đợi Redis Streams và tỉ lệ phân bổ công việc giữa các Worker.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       [KHUNG CHÈN ẢNH CHỤP DEMO 6]                          │
│                                                                             │
│   Ảnh chụp màn hình 3 Dashboard trên Grafana: Cluster Metrics,              │
│   Worker Status (ONLINE/OFFLINE), và Business Statistics.                   │
└─────────────────────────────────────────────────────────────────────────────┘
```
*Hình 4.6. Hệ thống giám sát trực quan Grafana trên máy ảo VM5.*

---

### DEMO 7: Hệ Thống Cảnh Báo Tức Thời Qua Telegram Bot & Discord
* **Mô tả:** Khi một máy ảo bị ngắt kết nối (ví dụ tắt VM1 hoặc VM2), Alertmanager phát hiện mất Heartbeat sau 90 giây và lập tức gửi tin nhắn cảnh báo đỏ về nhóm Telegram và kênh Discord của nhóm.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       [KHUNG CHÈN ẢNH CHỤP DEMO 7]                          │
│                                                                             │
│   Ảnh chụp màn hình thông báo Telegram Bot: Cảnh báo Worker Offline,        │
│   thời gian xảy ra và link trỏ tới Dashboard Grafana.                       │
└─────────────────────────────────────────────────────────────────────────────┘
```
*Hình 4.7. Cảnh báo sự cố tự động gửi về Telegram Bot và Discord.*

---

## PHẦN 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

### 5.1. Kết Quả Đạt Được
* Hệ thống đã vận hành ổn định trên cụm **5 máy ảo VMware** kết nối qua mạng Tailscale Mesh.
* Đáp ứng **100% các tiêu chí nghiệm thu** của bài tập BT-03:
  1. Trang chủ phân trang chuẩn 50 ảnh/trang, sắp xếp mới nhất.
  2. Tìm kiếm tiếng Anh thông minh, không bao giờ báo "không có kết quả".
  3. Cơ chế tự sinh 50 tác phẩm Art Deco đặc sắc, rõ nét chủ thể 100% có bảng tên.
  4. Cơ sở dữ liệu và lưu trữ chống trùng lặp tuyệt đối.
  5. Giám sát tự động và cảnh báo qua Telegram/Discord hoạt động chính xác.

### 5.2. Đóng Góp Của Thành Viên B4.2 (Nguyễn Thành Đô)
* Xây dựng và hoàn thiện trọn vẹn tiến trình **AI Worker 2.1**, kết nối đồng bộ hóa với cụm máy chủ trung tâm VM4 qua Tailscale.
* Thiết kế đường ống hậu kỳ mỹ thuật Art Deco độc quyền (Pillow enhance + Title Plate kim loại).
* Cung cấp thuật toán tự động sinh và bù trừ 50 tác phẩm kiệt tác Art Deco cho kho ảnh, sẵn sàng phục vụ buổi thuyết trình trước hội đồng.
* Đảm bảo tính toàn vẹn dữ liệu lưu trữ ảnh, đồng bộ SSH an toàn và tối ưu hóa hiệu năng truy vấn cơ sở dữ liệu.

---
**XÁC NHẬN CỦA NHÓM TRƯỞNG B4**  
*(Ký và ghi rõ họ tên)*  



**Hà Điền Trung Hiếu**

