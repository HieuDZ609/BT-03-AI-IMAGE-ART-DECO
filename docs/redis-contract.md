# Hợp đồng kết nối Redis — dùng chung cho Gateway, Autopilot và 5 AI Worker

> Tài liệu này là phần **bắt buộc thống nhất trước khi code**. Mọi module nói chuyện với nhau
> qua Redis theo đúng mô tả dưới đây; không ai tự đặt thêm tên stream/khoá mới.

## 1. Thông số kết nối

| Thông số | Giá trị |
|---|---|
| Dịch vụ | Redis 7 (image `redis:7-alpine`) |
| Máy chủ | **VM4 — core node** (nhóm trưởng vận hành) |
| Địa chỉ | **`100.111.232.74`** (IP Tailscale của VM4) |
| Cổng | `6379` |
| Mật khẩu | biến môi trường `REDIS_PASSWORD` (nhóm trưởng cấp, **không commit**) |
| Database index | `0` |
| Chế độ bảo vệ | `requirepass` bật, chỉ bind trên loopback + Tailscale, **không publish ra Internet** |

Chuỗi kết nối:

```
# Khi phát triển trên chính VM4 (hoặc cùng máy, docker compose local)
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/0

# Worker trên VM1–VM3, VM5 trỏ về VM4 qua Tailscale
REDIS_URL=redis://:${REDIS_PASSWORD}@100.111.232.74:6379/0
```

## 1.1. Mạng Tailscale

Toàn bộ 5 máy ảo và máy host nằm trong cùng một tailnet, nên **không cần quan tâm dải IP của VMware
NAT**. Mỗi máy cài Tailscale và dùng IP `100.x.y.z` cố định của mình; VM4 là `100.111.232.74`.

Cấu hình Redis trên VM4 (`redis.conf` hoặc `command:` trong compose):

```
bind 127.0.0.1 100.111.232.74
protected-mode yes
requirepass ${REDIS_PASSWORD}
appendonly yes
```

Kiểm tra từ máy khác trong tailnet:

```bash
redis-cli -h 100.111.232.74 -p 6379 -a "$REDIS_PASSWORD" ping     # → PONG
```


## 2. Stream và consumer group

| Tên | Loại | Ai ghi | Ai đọc |
|---|---|---|---|
| `jobs:generate` | Stream | Gateway (khi search miss), Autopilot | 5 AI Worker |
| `job:events` | Stream | Worker (khi xong/lỗi) | Gateway (phát SSE) |

Consumer group: **`workers`** — tạo một lần, idempotent:

```python
try:
    r.xgroup_create("jobs:generate", "workers", id="0", mkstream=True)
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" not in str(e):
        raise
```

Tên consumer = `ai_code` của worker (`1.1`, `2.1`, …, `5.1`). Nhờ vậy khi một worker chết,
`XAUTOCLAIM` biết job nào đang treo ở consumer nào.

## 3. Định dạng message

### 3.1. Job (Gateway/Autopilot → Worker)

```json
{
  "job_id": "b7f1c2d3-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
  "query": "black dog",
  "slug": "black-dog",
  "source": "SEARCH",
  "style_id": "deco-v1",
  "requested_at": "2026-11-04T10:12:00Z"
}
```

- `source`: `SEARCH` (người dùng tìm không thấy) hoặc `AUTOPILOT` (hệ thống tự sinh).
- `slug` đã được chuẩn hoá ở Gateway, worker **không** chuẩn hoá lại.

### 3.2. Sự kiện kết quả (Worker → Gateway)

```json
{
  "job_id": "b7f1c2d3-...",
  "status": "DONE",
  "image_id": "8f14e45f-...",
  "image_name": "black dog 4.1.png",
  "ai_code": "4.1",
  "duration_ms": 21450
}
```

`status` chỉ nhận: `DONE` hoặc `FAILED` (kèm `"error": "..."`).

## 4. Khoá phụ

| Khoá | Kiểu | Ghi bởi | TTL | Ý nghĩa |
|---|---|---|---|---|
| `worker:heartbeat:{ai_code}` | String | Worker, mỗi 30 s | 90 s | Hết TTL ⇒ hệ thống coi worker OFFLINE |
| `job:{job_id}:result` | String (JSON) | Worker | 1 giờ | Cho polling dự phòng khi SSE lỗi |
| `lock:slug:{slug}` | String (SET NX) | Gateway | 120 s | Hai người tìm cùng lúc chỉ sinh một ảnh |

## 5. Quy trình worker (chuẩn)

```python
while True:
    resp = r.xreadgroup("workers", AI_CODE, {"jobs:generate": ">"},
                        count=1, block=5000)
    if not resp:
        r.set(f"worker:heartbeat:{AI_CODE}", "1", ex=90)
        continue
    _, entries = resp[0]
    for entry_id, data in entries:
        try:
            image = generate(data["query"])          # sinh ảnh + hậu kỳ Art Deco
            save_and_index(image, data["job_id"])    # MinIO + PostgreSQL
            r.xadd("job:events", {"payload": json.dumps(result)})
            r.set(f"job:{data['job_id']}:result", json.dumps(result), ex=3600)
            r.xack("jobs:generate", "workers", entry_id)
        except Exception as e:
            # KHÔNG ack: để XAUTOCLAIM giao lại sau 120 s
            log.error("job %s failed: %s", data.get("job_id"), e)
```

Quy tắc:

1. **Chỉ `XACK` sau khi** ảnh đã nằm trong MinIO **và** metadata đã vào PostgreSQL.
2. Lỗi tạm thời (mạng, OOM) ⇒ không ack, để job được giao lại.
3. Sau 3 lần thất bại ⇒ Gateway đánh dấu `DEAD`, phát cảnh báo Telegram/Discord.
4. Heartbeat ghi mỗi 30 giây, kể cả khi đang bận sinh ảnh (dùng thread riêng).

## 6. Kiểm tra nhanh

```bash
# Từ VM1 — kiểm tra kết nối
redis-cli -h 100.111.232.74 -p 6379 -a "$REDIS_PASSWORD" ping    # → PONG

# Xem hàng đợi và consumer
redis-cli -h 100.111.232.74 -p 6379 -a "$REDIS_PASSWORD" xlen jobs:generate
redis-cli -h 100.111.232.74 -p 6379 -a "$REDIS_PASSWORD" xinfo groups jobs:generate
redis-cli -h 100.111.232.74 -p 6379 -a "$REDIS_PASSWORD" keys 'worker:heartbeat:*'
```

## 7. Độ bền hàng đợi (đã bật trên VM4)

Redis trên VM4 chạy **không bật AOF** (`appendonly no`) và vẫn bật snapshot RDB. Lý do:
nguồn sự thật của job là bảng `generation_jobs` trong PostgreSQL; AOF từng bị hỏng khi VM
mất điện đột ngột và làm Redis không khởi động lại được. Tắt AOF giúp Redis luôn boot sạch,
đổi lại worker phải tự đối soát:

- Mỗi 60 giây worker gọi `XAUTOCLAIM` để nhận lại job nằm quá 120 giây trong PEL
  (trường hợp worker crash giữa chừng).
- Mỗi 60 giây worker quét `generation_jobs` có `status='QUEUED'` và tạo quá 90 giây
  nhưng chưa từng vào stream (Redis chết đúng lúc `XADD`) rồi đẩy lại vào `jobs:generate`.
- Job được xử lý trùng sẽ được bỏ qua nhờ kiểm tra `images (slug, worker_id)` trước khi sinh.

Ngoài ra VM4 đặt `vm.overcommit_memory=1` và cho `redis-server` tự restart vô hạn
(`StartLimitIntervalSec=0`) sau `tailscaled`, tránh lỗi bind IP Tailscale lúc mới boot.
