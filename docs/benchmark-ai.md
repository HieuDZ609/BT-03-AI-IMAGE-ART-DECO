# Benchmark mô hình AI cục bộ — B4.1 / worker 4.1

> Đo trên VM4 (Ubuntu 26.04, 8 vCPU i5-1135G7, không GPU) bằng `stable-diffusion.cpp`.
> Mục tiêu của đề: chạy CPU, không gọi API, ảnh 128–256 px, 15–45 giây/ảnh.

## 1. Mô hình chọn cho worker 4.1

| Hạng mục | Giá trị |
|---|---|
| Model | `samoudi/sd-turbo-gguf` — `sd_turbo_q8_0.gguf` |
| Kiến trúc | SD-Turbo (distilled), lượng tử q8_0 |
| Runtime | `stable-diffusion.cpp` bản Linux x86_64 (CPU) |
| Kích thước file | 2,1 GB |
| Kích thước ảnh | 256 × 256 |
| Số bước | 4 (euler, CFG 1.0, 8 thread) |
| RAM đỉnh | ~2,5 GB |
| Thời gian/ảnh | ~16–19 giây |
| Hậu kỳ | blur nhẹ 0.6 → palette 6 màu → viền vàng 3 px → title plate |

SD-Turbo q8_0 cho chủ thể **rõ ràng, dễ nhận diện** (heo ra heo, xe ra xe) và ổn định
hơn hẳn tiny-sd q4_K. Đây vẫn là model local, không gọi API ngoài.

### Vì sao không dùng tiny-sd q4_K / sd-turbo q4_0
- `tiny-sd q4_K`: nhanh nhưng ảnh trừu tượng, khó nhận ra chủ thể.
- `sd-turbo q4_0`: nhiều seed cho ảnh nhiễu/scanline, không ổn định.
- `sd-turbo q8_0`: ổn định, nhận diện tốt, vẫn trong SLA 15–45 s ở 256 px.

## 2. Kết quả đo thực tế

| Model | Size | Steps | Sampler | Thời gian | RAM đỉnh | Ghi chú |
|---|---|---|---|---|---|---|
| tiny-sd q4_K | 512×512 | 20 | euler_a | 234 s | 1.94 GB | quá chậm |
| tiny-sd q4_K | 320×320 → 256 | 8 | euler_a | 36.8 s | 1.42 GB | nhanh, chủ thể mờ |
| sd-turbo q4_0 | 256×256 | 8 | euler | 23 s | 2.2 GB | nhiều seed bị nhiễu |
| sd-turbo q8_0 | 512×512 | 4 | euler | 69 s | 2.6 GB | vượt 45 s |
| **sd-turbo q8_0** | **256×256** | **4** | **euler** | **16–19 s** | **2.5 GB** | **chọn cho worker 4.1** |

Số đo end-to-end qua worker thật (search miss `pig eating grass`): job DONE sau
~17 giây, ảnh 262 × 262 (256 + viền 3 px).

## 3. Hậu kỳ Art Deco (bắt buộc, theo báo cáo)

1. Làm mượt nhẹ (Gaussian 0.6) để khử scanline/nhiễu của model nhỏ.
2. Ép bảng màu cố định 6 màu: `#1A1A1A`, `#C9A227`, `#F4EAD5`, `#1E6E6B`, `#8A6D1F`, `#E8D5A3`.
3. Viền vàng kim 3 px.
4. Title plate tên concept ở đáy ảnh (Python/Pillow) — giúp nhận diện ảnh với tên.

Nhờ bước hậu kỳ này, dù model khác nhau thì ảnh của 5 worker vẫn cùng một tông Art Deco —
đúng ghi chú trong báo cáo: **style đến từ prompt + palette + viền, không cần LoRA**.

## 4. Cách chạy thử

```bash
/opt/bt03/venv/bin/python /opt/bt03/worker/ai_engine.py "pig eating grass" /tmp/out.png
```

Env của worker 4.1:

```env
AI_BACKEND=sd
AI_MODEL_NAME=sd-turbo-q8_0
SD_CPP_BIN=/opt/bt03/ai/bin/sd-cli
SD_MODEL=/opt/bt03/ai/models/sd-turbo-q8_0.gguf
AI_SIZE=256
AI_DELIVER=256
AI_STEPS=4
AI_CFG=1.0
AI_TITLE_PLATE=1
```
