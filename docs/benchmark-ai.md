# Benchmark mô hình AI cục bộ — B4.1 / worker 4.1

> Đo trên VM4 (Ubuntu 26.04, 8 vCPU i5-1135G7, không GPU) bằng `stable-diffusion.cpp`.
> Mục tiêu của đề: chạy CPU, không gọi API, ảnh 128–256 px, 15–45 giây/ảnh.

## 1. Mô hình chọn cho worker 4.1

| Hạng mục | Giá trị |
|---|---|
| Model | `turingevo/tiny-sd-gguf` — `segmind_tiny-sd-q4_K.gguf` |
| Kiến trúc | SD 1.5 thu nhỏ (~0.5B UNet), lượng tử q4_K |
| Runtime | `stable-diffusion.cpp` bản Linux x86_64 (CPU) |
| Kích thước file | 739 MB |
| Kích thước render nội bộ | 320 × 320 (hạ về 256 × 256 khi giao) |
| Số bước | 8 (euler_a, CFG 7.0, diffusion-fa, 8 thread) |
| RAM đỉnh | ~1.4 GB |
| Thời gian/ảnh | ~25–37 giây |

Ảnh được render ở 320 px rồi resize Lanczos về 256 px: chủ thể rõ hơn so với render
thẳng 256 px, trong khi thời gian vẫn nằm trong khoảng 15–45 giây/ảnh của đề.

Đây là lựa chọn **nhẹ nhất** trong các ứng viên, phù hợp VM 3.3 GB RAM. Model khác với
các worker dùng `sd-turbo`/diffusers nên đảm bảo "mỗi người một AI".

## 2. Kết quả đo thực tế

| Model | Size | Steps | Sampler | Thời gian | RAM đỉnh | Ghi chú |
|---|---|---|---|---|---|---|
| tiny-sd q4_K | 512×512 | 20 | euler_a | 234 s | 1.94 GB | quá chậm |
| sd-turbo q8 | 512×512 | 1 | euler_a | 72.4 s | 2.62 GB | loại: quá RAM, ảnh trống |
| tiny-sd q4_K | 384×384 | 12 | euler_a | 72.8 s | 1.72 GB | đẹp nhưng vượt 45 s |
| tiny-sd q4_K | 256×256 | 8 | euler_a | 24.5 s | 1.18 GB | nhanh, chủ thể mờ |
| **tiny-sd q4_K** | **320×320 → 256** | **8** | **euler_a** | **36.8 s** | **1.42 GB** | **chọn cho worker 4.1** |

Số đo end-to-end qua worker thật (search miss `zeppelin airship`): job DONE sau
35,7 giây, ảnh 262 × 262 (256 + viền 3 px), 15,7 KB.

## 3. Hậu kỳ Art Deco (bắt buộc, theo báo cáo)

1. Ép bảng màu cố định 6 màu: `#1A1A1A`, `#C9A227`, `#F4EAD5`, `#1E6E6B`, `#8A6D1F`, `#E8D5A3`.
2. Viền vàng kim 3 px.
3. Giữ chủ thể ở giữa, nền đơn giản (prompt + negative mạnh).

Nhờ bước hậu kỳ này, dù model khác nhau thì ảnh của 5 worker vẫn cùng một tông Art Deco —
đúng ghi chú trong báo cáo: **style đến từ prompt + palette + viền, không cần LoRA**.

## 4. Cách chạy thử

```bash
/opt/bt03/venv/bin/python /opt/bt03/worker/ai_engine.py "black dog" /tmp/out.png
```

Env của worker 4.1:

```env
AI_BACKEND=sd
AI_MODEL_NAME=tiny-sd-q4_K
SD_CPP_BIN=/opt/bt03/ai/bin/sd-cli
SD_MODEL=/opt/bt03/ai/models/tiny-sd-q4_K.gguf
AI_SIZE=320
AI_DELIVER=256
AI_STEPS=8
AI_CFG=7.0
```
