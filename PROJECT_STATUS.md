# Project Status

Ngày cập nhật: 2026-10-01

Repository công khai chỉ chứa mã nguồn, tài liệu và các bảng báo cáo tổng hợp. Dataset gốc, Parquet, model factor, cache và log trong các đường dẫn bên dưới là artifact cục bộ; chúng được tạo lại theo hướng dẫn trong [README.md](README.md) và không nằm trên GitHub.

## Đã hoàn thành

### Tuần 1: Khởi động và kiểm tra dữ liệu

- Dataset MovieLens 32M đã được tải và đối soát checksum trong workspace hiện tại (`scripts/00_check_data.py`).
- Đã kiểm tra đủ 4 file chính: `ratings.csv`, `movies.csv`, `tags.csv`, `links.csv`.
- Đã kiểm tra số dòng và checksum MD5, tất cả đều khớp với bộ dữ liệu gốc.

| File | Số dòng dữ liệu | Dung lượng CSV |
| --- | ---: | ---: |
| `ratings.csv` | 32,000,204 | 836.45 MB |
| `movies.csv` | 87,585 | 4.05 MB |
| `tags.csv` | 2,000,072 | 69.00 MB |
| `links.csv` | 87,585 | 1.86 MB |

### Tuần 2: ETL và lưu dữ liệu xử lý

- Đã chuyển toàn bộ CSV sang Parquet trong `data/processed/parquet/` bằng `scripts/01_convert_to_parquet.py`.
- Đã đo hiệu năng lưu trữ và truy vấn tổng hợp 32 triệu dòng (`scripts/10_benchmark_bigdata.py`): Parquet tiết kiệm **74.96%** dung lượng `ratings` và tăng tốc truy vấn tổng hợp **11.99 lần** so với CSV (`1.642s` so với `19.690s`).

| File | Kích thước Parquet | Tiết kiệm so với CSV |
| --- | ---: | ---: |
| `ratings.parquet` | 209.44 MB | 74.96% |
| `movies.parquet` | 2.35 MB | 41.98% |
| `tags.parquet` | 19.97 MB | 71.06% |
| `links.parquet` | 1.90 MB | -2.15% |

### Tuần 3: EDA và chuẩn bị tập train/validation/test

- Đã tạo thống kê EDA trong `reports/tables/` và biểu đồ trong `reports/figures/` (`scripts/02_eda_local.py`).
- Đã tạo sample phát triển (`userId % 10 == 0`) gồm 20,094 users và 3,159,674 ratings, cùng tập full (`userId % 1 == 0`) gồm 200,948 users và 32,000,204 ratings (`scripts/03_prepare_splits_local.py`).
- Đã chia theo thứ tự thời gian trong từng user (chống rò rỉ dữ liệu tương lai):

| Tập dữ liệu | Sample phát triển (`data/interim/`) | Toàn bộ 32M (`data/full_interim/`) |
| --- | ---: | ---: |
| Train | 2,519,826 | 25,520,897 |
| Validation | 314,807 | 3,188,339 |
| Test | 325,041 | 3,290,968 |
| **Tổng cộng** | **3,159,674** | **32,000,204** |

### Tuần 4: Baseline và ALS trên tập phát triển

- Đã cài PySpark 3.5.7 và chạy Spark `local[4]` trên Windows (`scripts/04_train_als_spark.py`).
- Đã so sánh Global Mean (`RMSE = 1.051351`, `MAE = 0.825242`) và Item Mean (`RMSE = 0.968203`, `MAE = 0.745043`) với ALS (`RMSE = 0.837409`, `MAE = 0.647536`, `coverage = 98.85%`).
- Đã đo thực nghiệm khả năng tăng tốc theo số luồng Spark (`local[1]` -> `local[2]` -> `local[4]` đạt speedup **2.47x**).

### Tuần 5: Tuning tham số và chạy tập toàn bộ 32M

- Đã thử 3 cấu hình rank/regParam trên tập sample (`reports/tables/als_tuning.csv`), chọn `rank=16, regParam=0.08`.
- Đã chạy grid so sánh số vòng lặp `maxIter = 5, 10, 15, 20` trên **toàn bộ MovieLens 32M** (`reports/tables/full_iter_20260922_120859/als_tuning.csv`):

| `rank` | `regParam` | `maxIter` | RMSE Validation | MAE Validation | Coverage |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 0.08 | 5 | 0.833791 | 0.651167 | 99.77% |
| 16 | 0.08 | 10 | 0.810538 | 0.624590 | 99.77% |
| 16 | 0.08 | 15 | 0.803717 | 0.615847 | 99.77% |
| **16** | **0.08** | **20 (chọn)** | **0.800952** | **0.612026** | **99.77%** |

### Tuần 6: Đánh giá Test, Chẩn đoán Top-K và Ứng dụng Web CINE32

- Đã fit lại model cuối (`rank=16, regParam=0.08, maxIter=20`) trên `28,709,236` dòng (`train + validation`) tại `models/als_full_iter_20260922_120859/`.
- **Kết quả dự đoán rating trên tập Test (3,290,968 dòng):** `RMSE = 0.812898`, `MAE = 0.621380`, `Coverage = 99.73%`.
- **Chẩn đoán Top-K và đối chiếu Baseline (`scripts/09_diagnose_topk_and_baseline.py`):**
  - Đã xác minh nguyên nhân ALS explicit toàn catalog có `Precision@10 ≈ 1.57e-6`: `94.98%` phim được ALS đề xuất trên toàn bộ catalog có `<= 5` lượt đánh giá (trung vị `1.0` lượt chấm 5 sao) với điểm dự đoán trung vị `5.37 > 5.0`.
  - Trong phép đối chiếu trên 10.000 user, ALS toàn catalog đạt `Precision@10 = 0.000020`. Lọc `rating_count >= 100` (11,330 phim) đạt `0.014670` (733,5 lần trong cùng phép đo, so với Weighted Score `0.012310`); ngưỡng `>= 500` đạt `0.021640`, `Recall@10 = 0.036183`, `NDCG@10 = 0.030951`. Không lấy hệ số cải thiện này so trực tiếp với độ đo toàn bộ test `1.57e-6` vì khác tập user.
- **Ứng dụng web CINE32 (`web_api.py` + `frontend/`):** Giao diện React/TypeScript + FastAPI duyệt toàn bộ 87,585 phim theo thể loại tiếng Việt, xếp hạng theo `weighted_score` ($m=100$), tìm kiếm tức thời và tải poster/mô tả từ TMDB qua cache SQLite.

### Bổ sung yêu cầu bắt buộc: HDFS và demo ALS (01/10/2026)

- HDFS 3.3.4 một NameNode/một DataNode đã chạy trên Windows; Spark `local[4]` đọc 4 CSV từ HDFS, làm sạch ratings, ghi/đọc lại đủ **32.000.204** dòng Parquet, tạo checkpoint và ghi Top 10 ALS trên HDFS. Bằng chứng: `reports/tables/hdfs_spark_verification.json`.
- CINE32 có mục **Gợi ý ALS**, dùng vector của **200.948 user**, tập ứng viên **11.330 phim** có ít nhất 100 lượt chấm trong train + validation. Loại toàn bộ phim user đã chấm trong dataset, hiển thị điểm ALS riêng với điểm cộng đồng, xem lịch sử, xử lý user mới bằng Weighted Score.
- Dùng lại model đã train; không thay đổi độ đo test đã công bố. Train và benchmark trước đây dùng filesystem local, thí nghiệm HDFS bổ sung dùng cùng vector model để chạy inference từ HDFS.
- Frontend build thành công; 11 bài kiểm tra đạt. Đã kiểm tra đổi User ID, fallback, modal và bố cục mobile/desktop. Hướng dẫn: [HDFS và demo ALS](HUONG_DAN_HDFS_VA_DEMO_ALS.md).

### Tuần 7 & Tuần 8: Hồ sơ báo cáo, Slide thuyết trình và Kịch bản Demo

- Đã hoàn thành bản thảo Báo cáo đồ án đầy đủ 10 phần theo chuẩn HUIT tại [reports/BAO_CAO_DO_AN_MOVIELENS_32M.md](reports/BAO_CAO_DO_AN_MOVIELENS_32M.md).
- Đã hoàn thành nội dung 11 Slide thuyết trình, kịch bản Demo 5–7 phút, bộ câu hỏi bảo vệ đồ án và bảng phân công/checklist nộp bài tại [reports/SLIDE_VA_KICH_BAN_DEMO.md](reports/SLIDE_VA_KICH_BAN_DEMO.md).
- Các artifact kiểm tra tạm, runtime và log được loại khỏi GitHub theo `.gitignore`.

## Trạng thái hiện tại

Hai yêu cầu kỹ thuật **HDFS + demo ALS theo User ID** đã có triển khai và bằng chứng chạy thật. Báo cáo/slide hiện là bản thảo Markdown; chưa xác nhận hoàn tất Word/PPT, thông tin thành viên, chạy lại trên máy thứ hai và diễn tập bảo vệ. Không đánh dấu toàn bộ tuần 8 hoàn thành trước khi có các sản phẩm này.
