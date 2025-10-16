# Attendance App (ArcFace + InsightFace + ONNXRuntime, CPU) 🧑‍🎓📸

Ứng dụng điểm danh bằng nhận diện khuôn mặt trên **CPU**, độ chính xác cao nhờ **ArcFace** (InsightFace) + **cosine + centroid**.
Giao diện **Tkinter**, log **CSV**, kiến trúc module rõ ràng.

## Tính năng
- Đăng ký khuôn mặt (chụp từ webcam) → lưu ảnh gốc + embedding (512d) và **centroid** cho mỗi người.
- Điểm danh realtime: detect → embed → so khớp cosine với **centroid** từng người.
- Trạng thái `IN/OUT` tự động (toggle) + cooldown tránh spam.
- Xuất báo cáo CSV theo ngày trong `app/reports/`.
- Test tổng thể trước khi chạy (`test_system.py`).

## Cài đặt
> Yêu cầu: Python 3.9–3.11, webcam, Windows/Linux/macOS.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

pip install -r requirements.txt
```

> Lần đầu chạy, InsightFace sẽ tự **download** model về `~/.insightface`.

## Chạy
- Kiểm thử:
```bash
python test_system.py
```
- Ứng dụng GUI:
```bash
python app.py
```

## Cấu hình
Xem `config.py` để chỉnh:
- `SIM_THRESHOLD`: ngưỡng cosine để chấp nhận nhận diện (mặc định 0.35–0.45 thường ổn, đã đặt 0.38).
- `MIN_FACE_SIZE`: bỏ qua mặt quá nhỏ.
- `ATTEND_COOLDOWN_SEC`: thời gian tối thiểu giữa 2 lần điểm danh cùng người.

## Cấu trúc
```
attendance_arcface_app/
├─ app.py                 # Tkinter UI
├─ config.py              # Tham số hệ thống
├─ face_engine.py         # Detector + embedder (InsightFace)
├─ registry.py            # Đăng ký người dùng, quản lý embeddings + centroid
├─ attendance.py          # Ghi log IN/OUT, báo cáo CSV
├─ utils.py               # Tiện ích chung
├─ test_system.py         # Kiểm thử hệ thống
├─ requirements.txt
└─ app/
   ├─ data/
   │  ├─ faces/           # Ảnh gốc theo user
   │  └─ embeddings/      # .npz (vectors, centroid) mỗi user
   ├─ reports/            # CSV báo cáo
   └─ tmp/                # Ảnh tạm, debug
```

## Ghi chú
- Mô hình InsightFace mặc định (zoo: `buffalo_l`) gồm RetinaFace + ArcFace (512d).
- Nếu máy yếu, có thể bật `det_size=(320,320)` trong `config.py` để nhẹ hơn.
- Nếu môi trường bị chặn internet, bạn cần **tải model thủ công** theo hướng dẫn InsightFace và đặt trong `~/.insightface`.

Chúc bạn triển khai trơn tru! ✨
