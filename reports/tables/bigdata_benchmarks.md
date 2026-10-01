# Kết quả Thực nghiệm Hiệu năng Big Data (MovieLens 32M)

## 1. So sánh dung lượng lưu trữ CSV và Parquet

| Bảng dữ liệu | CSV gốc (MB) | Parquet sau ETL (MB) | Tiết kiệm dung lượng (%) |
| --- | ---: | ---: | ---: |
| `ratings` | 836.45 | 209.44 | 74.96% |
| `movies` | 4.05 | 2.35 | 41.98% |
| `tags` | 69.00 | 19.97 | 71.06% |
| `links` | 1.86 | 1.90 | -2.15% |

## 2. So sánh thời gian truy vấn tổng hợp 32 triệu dòng (CSV vs Parquet)

- Truy vấn: `Read 32M ratings + groupBy(movieId).agg(count, avg)` trên `local[4]` (3 lần chạy).
- Thời gian đọc & tổng hợp CSV: các lần chạy `[27.535, 19.69, 19.384]` giây -> **Trung vị: 19.690 giây**.
- Thời gian đọc & tổng hợp Parquet: các lần chạy `[3.04, 1.642, 1.567]` giây -> **Trung vị: 1.642 giây**.
- **Tốc độ tăng tốc (Speedup) của Parquet so với CSV:** **11.99 lần** (nhờ đọc cột chọn lọc `movieId, rating` và nén cột nhị phân).

## 3. Thực nghiệm tăng số luồng xử lý Spark (`local[1]` vs `local[2]` vs `local[4]`)

Đo trên tập phát triển (`2,519,826` dòng train + `314,807` dòng validation) với cấu hình ALS `rank=16, regParam=0.08, maxIter=5`:

| Cấu hình Spark | Số luồng | Nạp & Cache (giây) | Huấn luyện ALS & Đánh giá (giây) | Tổng thời gian (giây) | RMSE Validation | Tăng tốc (Speedup) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `local[1]` | 1 | 4.002 | 40.121 | 44.123 | 0.836664 | 1.00x |
| `local[2]` | 2 | 2.744 | 20.388 | 23.132 | 0.836664 | 1.91x |
| `local[4]` | 4 | 2.227 | 15.636 | 17.863 | 0.836664 | 2.47x |
