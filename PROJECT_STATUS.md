# Project Status

Ngày cập nhật: 2026-09-23

Repository công khai chỉ chứa mã nguồn, tài liệu và một số báo cáo nhỏ. Dataset, Parquet, model, cache và log trong các đường dẫn bên dưới là artifact cục bộ; chúng được tạo lại theo hướng dẫn và không nằm trên GitHub.

## Đã hoàn thành

### Tuần 1: Khởi động và kiểm tra dữ liệu

- Dataset MovieLens 32M đã được tải và đối soát checksum trong workspace hiện tại; mỗi người dùng cần tự tải vào `ml-32m/`.
- Đã kiểm tra đủ 4 file chính: `ratings.csv`, `movies.csv`, `tags.csv`, `links.csv`.
- Đã kiểm tra số dòng và checksum MD5, tất cả đều khớp với bộ dữ liệu gốc.

| File | Số dòng dữ liệu |
| --- | ---: |
| `ratings.csv` | 32,000,204 |
| `movies.csv` | 87,585 |
| `tags.csv` | 2,000,072 |
| `links.csv` | 87,585 |

### Tuần 2: ETL và lưu dữ liệu xử lý

- Đã chuyển toàn bộ CSV sang Parquet trong `data/processed/parquet/`.
- Đã chuẩn bị script chạy lại ETL: `scripts/01_convert_to_parquet.py`.

| File | Kích thước |
| --- | ---: |
| `ratings.parquet` | 219.6 MB |
| `movies.parquet` | 2.5 MB |
| `tags.parquet` | 20.9 MB |
| `links.parquet` | 2.0 MB |

### Tuần 3: EDA và chuẩn bị tập train/validation/test

- Đã tạo thống kê EDA trong `reports/tables/` và biểu đồ trong `reports/figures/`.
- Đã tạo sample phát triển từ 20,094 users, gồm 3,159,674 ratings.
- Đã chia sample theo thời gian trong từng user:

| Tập | Số dòng |
| --- | ---: |
| Train | 2,519,826 |
| Validation | 314,807 |
| Test | 325,041 |

Các file chính: `reports/tables/eda_summary.md`, `reports/figures/`, `data/interim/train.parquet`, `data/interim/valid.parquet`, `data/interim/test.parquet`.

### Tuần 4: Baseline và ALS

- Đã cài PySpark 3.5.7 và chạy Spark `local[4]` trên Windows.
- Đã so sánh global-mean và item-mean với ALS.
- Validation ALS (`rank=16`, `regParam=0.08`, `maxIter=5`): RMSE `0.837409`, MAE `0.647536`, coverage `98.85%`.
- Đã xuất factor model và Top-10 cho 100 user trong `models/als_dev/`.

### Tuần 5: Tuning và chạy tập phát triển

- Đã thử 3 cấu hình trong `reports/tables/als_tuning.csv`.
- Cấu hình chọn theo RMSE validation: `rank=16`, `regParam=0.08`, `maxIter=5`.
- Đã fit lại trên train + validation (2,834,633 dòng).

- Đã tạo split full từ toàn bộ 32,000,204 rating: train 25,520,897; validation 3,188,339; test 3,290,968.

### Tuần 6: Đánh giá test và demo

- Đã train model final trên toàn bộ MovieLens 32M trong workspace tại `models/als_full/`.
- Full validation RMSE: `0.833791`; MAE: `0.651167`; coverage: `99.77%`.
- Full test RMSE: `0.847450`; MAE: `0.662661`; rating coverage: `99.73%`.
- Đã tính Precision@10, Recall@10 và NDCG@10 theo giao thức đánh giá Top-K trong `models/als_full/metrics.json`.
- Đã xuất 5.000 dòng gợi ý cho 500 user trong workspace tại `artifacts/demo/`.
- Ứng dụng chính hiện dùng React/TypeScript + FastAPI: lọc toàn bộ phim theo thể loại, tìm kiếm, phân trang, poster TMDB và điểm MovieLens. `app.py` là giao diện Streamlit cũ.

## Đang ở tuần nào?

Đã hoàn thành đến **tuần 6**. Sản phẩm gồm pipeline Spark ALS, kết quả đánh giá và ứng dụng web React/FastAPI. Hai tuần còn lại dành cho viết báo cáo, slide, kiểm tra trên máy thành viên còn lại và diễn tập demo.

## Lưu ý khi viết báo cáo

Tuning được thực hiện trên sample để tiết kiệm thời gian; model final đã fit trên toàn bộ 32M với cấu hình đã khóa. Khi viết báo cáo, ghi rõ số block ALS (`50 x 50`), Spark `local[4]`, heap driver `16g` và thời gian chạy khoảng 10 phút trên máy này.
