# BT-03 — AI Image Warehouse (Art Deco)

Hệ thống **kho ảnh trực tuyến thông minh**: website phát hành công khai trên Internet, phía sau là
nhiều tiến trình **AI cục bộ (không dùng API AI)** tự động sinh ảnh liên tục để làm đầy kho.
Người dùng tra cứu ảnh theo tên tiếng Anh; nếu kho chưa có, hệ thống **tự sinh ảnh mới, lưu lại và
trả về ngay trong phiên tìm kiếm** — không bao giờ trả lời "không có kết quả".

> Bài tập môn học — Nhóm B4, Trường Đại học Công nghệ Thông tin và Truyền thông Việt Hàn (VKU).

---

## 1. Kiến trúc tổng thể

```
                    Internet
                       │  HTTPS (Cloudflare Tunnel / Ngrok static domain)
                       ▼
        ┌──────────────────────────────┐
        │  VM4 — CORE NODE (24/7)      │
        │  Nginx · Frontend · Gateway  │
        │  Autopilot · Redis           │
        │  PostgreSQL · MinIO          │
        │  image-service · Worker 4.1  │
        └──────────┬───────────────────┘
                   │  mạng nội bộ VMware
     ┌─────────────┼─────────────┬──────────────┐
     ▼             ▼             ▼              ▼
   VM1           VM2           VM3            VM5
 Worker 1.1    Worker 2.1    Worker 3.1    Worker 5.1
 (B4.1)        (B4.2)        (B4.3)        + Prometheus
                                            + Grafana
                                            + Alertmanager
                                            + notify-service
```

| Module | Công nghệ | Máy |
|---|---|---|
| Reverse proxy | Nginx | VM4 |
| Frontend | Next.js 15 + Tailwind | VM4 |
| API Gateway | FastAPI + Uvicorn (REST + SSE) | VM4 |
| Autopilot (Seeder) | Python scheduler + `topics.yaml` | VM4 |
| AI Worker ×5 | Python + diffusers / stable-diffusion.cpp | VM1–VM5 |
| image-service | FastAPI + SQLAlchemy + MinIO SDK | VM4 |
| Database | PostgreSQL 16 (`pg_trgm`) | VM4 |
| Object storage | MinIO (S3 API) | VM4 |
| Queue | Redis 7 Streams (consumer group) | VM4 |
| Monitoring | Prometheus + Grafana + Alertmanager | VM5 |
| Notification | Telegram Bot + Discord Webhook | VM5 |

## 2. Điểm thiết kế đáng chú ý

- **Kho luôn tự đầy**: module Autopilot liên tục đẩy job từ ~600 chủ đề bách khoa vào Redis,
  5 worker pull theo ai rảnh — AI chạy 24/7, không phụ thuộc người dùng.
- **Không bao giờ "không có kết quả"**: search miss → tạo job → SSE/polling → trả ảnh vừa sinh.
  Timeout vẫn giữ trạng thái "đang sinh ảnh"; chỉ khi hệ thống hỏng mới trả `503 SYSTEM_DEGRADED`
  kèm cảnh báo Telegram/Discord.
- **Không mất job**: Redis Streams + `XAUTOCLAIM`, worker chết giữa chừng thì job được giao lại.
- **Phong cách đồng nhất**: `packages/shared/style.yaml` dùng chung cho cả 5 worker + hậu kỳ ép
  bảng màu Art Deco → 5 model khác nhau vẫn cho ra một bộ ảnh cùng tông.
- **Module độc lập**: mỗi máy một `docker-compose.yml`, giao tiếp chỉ qua HTTP/JSON và Redis.
  Tắt máy thành viên chỉ giảm công suất, website vẫn chạy.

## 3. Quy tắc đặt tên ảnh

```
image_name  = "{slug} {member_id}.{worker_index}.{ext}"
              black dog 4.1.png     red hat 2.1.jpg

storage_key = "{slug}/{ai_code}/{uuid}.{ext}"     # không bao giờ ghi đè
unique      = (slug, ai_code)  và  (sha256)
```

`4.1` = AI thứ 1 của thành viên B4.4. Nếu thành viên chạy worker thứ hai thì mã là `4.2`.

## 4. Cấu trúc kho mã

```
BT-03-AI-IMAGE-ART-DECO/
├── packages/shared/       # style.yaml, schemas, naming, metrics dùng chung
├── api-gateway/           # FastAPI: search, job, SSE, rate limit, /metrics
├── autopilot/             # topics.yaml + scheduler sinh job 24/7
├── image-service/         # API dữ liệu ảnh + MinIO + PostgreSQL
├── ai-workers/
│   ├── worker-common/     # sinh ảnh, hậu kỳ Art Deco, upload, ack
│   └── worker-1..5/
├── frontend/              # Next.js 15
├── monitoring/            # Prometheus, Grafana, Alertmanager, exporters
├── notification/          # Telegram bot, Discord webhook
├── deployment/vm1..vm5/   # docker-compose + .env.example từng máy
├── scripts/               # bootstrap, seed, backup, restore
└── docs/                  # thiết kế, API spec, báo cáo
```

## 5. Thành viên nhóm B4

| Mã | Họ tên | MSSV | Module |
|---|---|---|---|
| B4.1 | Võ Quốc Đạt | 24IT333 | AI Worker & Model Engineering |
| B4.2 | Nguyễn Thành Đô | 24IT335 | Image Storage & Database |
| B4.3 | Nguyễn Văn Thái Hào | 24IT054 | Frontend & Search UI |
| B4.4 | Hà Điền Trung Hiếu | 24IT062 | Nhóm trưởng — Core & Integration |
| B4.5 | Nguyễn Văn Hiếu | 24IT067 | DevOps, Monitoring & Notification |

## 6. Tài liệu

- `docs/report/` — báo cáo thiết kế và phân chia công việc
- `docs/assets/` — sơ đồ kiến trúc, ERD, lưu đồ xử lý

## 7. Nhánh làm việc

Mỗi thành viên làm trên nhánh riêng, mở pull request vào `main`; `main` chỉ nhận code đã chạy được.
Tên nhánh dùng dấu gạch nối vì git không cho phép khoảng trắng trong tên nhánh.

| Nhánh | Thành viên | Module |
|---|---|---|
| `B4.1-ai-worker` | Võ Quốc Đạt | AI Worker & Model Engineering |
| `B4.2-data-storage` | Nguyễn Thành Đô | Image Storage & Database |
| `B4.3-frontend` | Nguyễn Văn Thái Hào | Frontend & Search UI |
| `B4.4-core-gateway` | Hà Điền Trung Hiếu | Core & Integration (Gateway, Autopilot) |
| `B4.5-devops-monitoring` | Nguyễn Văn Hiếu | DevOps, Monitoring & Notification |

```bash
git checkout B4.1-ai-worker      # chuyển sang nhánh của mình
git push -u origin B4.1-ai-worker
```

## 8. Giấy phép

Dự án học tập, sử dụng các thành phần mã nguồn mở: PostgreSQL, MinIO, Redis, Next.js, FastAPI,
Prometheus, Grafana, và các mô hình sinh ảnh mở (SD-Turbo, Tiny-SD, Stable Diffusion).
