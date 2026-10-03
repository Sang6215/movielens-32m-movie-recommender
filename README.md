# MovieLens 32M Movie Recommender

Project cho đề tài 15: hệ thống gợi ý phim dùng MovieLens 32M.

Hướng dẫn chạy và so sánh 5–20 vòng ALS: [Hướng dẫn train MovieLens 32M](HUONG_DAN_TRAIN_ALS_MOVIELENS_32M.md).

HDFS và demo gợi ý cá nhân theo User ID: [Hướng dẫn HDFS + ALS](HUONG_DAN_HDFS_VA_DEMO_ALS.md).

## Chạy demo bằng model đã train

[Bản phát hành v1.0.0](https://github.com/Sang6215/movielens-32m-movie-recommender/releases/tag/v1.0.0) có gói `cine32-demo-v1.0.0.zip` chứa catalog, vector ALS đã train, chỉ mục lịch sử và giao diện đã build. Chạy web bằng gói này không cần train lại, tải CSV gốc, cài Spark/HDFS hay build bằng Node.js. Cần Python 3.11+ và các thư viện web.

Các bước tải, giải nén và kiểm tra checksum: [Hướng dẫn chạy demo](HUONG_DAN_CHAY_DEMO.md). Muốn tái tạo thí nghiệm train hoặc HDFS, dùng các hướng dẫn bên dưới.

## Đưa website/API lên Internet

[Hướng dẫn triển khai Docker và Render](HUONG_DAN_DEPLOY_WEB.md) mô tả cách chạy web với model đã train và đặt token TMDB riêng trên máy chủ để mọi người truy cập có poster. GitHub lưu mã nguồn và artifact; cần hosting chạy FastAPI để có URL website/API công khai. Hiện chưa xác nhận dịch vụ hosting hoạt động. Token không được đưa vào GitHub hoặc frontend; người clone để tự chạy backend cần token riêng.

## Tài liệu báo cáo

- [Báo cáo dạng Markdown](reports/BAO_CAO_BIG_DATA_THEO_MAU.md).
- [Phân tích nghiệp vụ, Use Case và ERD](reports/PHAN_TICH_NGHIEP_VU_USECASE_ERD.md).
- [Nguồn sơ đồ có thể chỉnh sửa bằng draw.io](reports/diagrams/CINE32_USECASE_ERD.drawio).

Báo cáo Word và PowerPoint lưu trên máy của nhóm, không đưa lên GitHub theo yêu cầu. Các tài liệu Markdown cũ vẫn giữ để tham khảo quá trình thực hiện; bản cập nhật là các liên kết trên.

## Trạng thái hiện tại

- Bộ dữ liệu MovieLens 32M cần được tải riêng vào `ml-32m/`; GitHub chỉ lưu mã nguồn và hướng dẫn, không chứa bộ dữ liệu gần 1 GB.
- Đã hoàn thành pipeline đến **tuần 6**: ETL, EDA, chia dữ liệu, ALS, tuning, đánh giá test và xuất dữ liệu demo.
- Spark chạy `local[4]`; HDFS một NameNode/một DataNode được quản lý bằng `scripts/11_hdfs_local.py`. Đây là môi trường một máy, không phải cụm nhiều máy.
- Trong workspace hiện tại, grid full chọn `rank=16`, `regParam=0.08`, `maxIter=20` theo RMSE validation `0.800952`; model fit trên 28.709.236 rating train + validation, giữ 3.290.968 rating test ngoài bước học. Các model và dữ liệu xử lý không được commit lên GitHub; có thể tạo lại bằng scripts và hướng dẫn train.
- Demo ALS trực tuyến dùng vector của 200.948 user, loại phim đã đánh giá và lọc ứng viên có ít nhất 100 lượt chấm. Artifact 500 user cũ phục vụ thí nghiệm trước đây; chẩn đoán Top-K lưu trong `reports/tables/`.
- Ứng dụng xem phim chính dùng **React/TypeScript + FastAPI**, giao diện tối và vàng lấy cảm hứng từ trang danh mục phim IMDb, với tên riêng CINE32. Ứng dụng đọc toàn bộ catalog MovieLens, lọc thể loại và tìm tên phim; bản `app.py` Streamlit được giữ làm bản thử nghiệm cũ.

## Cấu trúc

```text
.
├── ml-32m/                         # Dataset gốc MovieLens 32M
├── data/
│   ├── interim/                    # Sample và train/valid/test split
│   └── processed/parquet/          # Dữ liệu Parquet sau ETL
├── reports/
│   ├── figures/                    # Biểu đồ EDA
│   └── tables/                     # Bảng thống kê và kết quả mô hình
├── models/                         # Factor model và metrics ALS
│   ├── als_dev/                    # Kết quả thử nghiệm trên sample
│   ├── als_full/                   # Model full baseline trước khi tuning
│   └── als_full_iter_20260922_120859/  # Grid full, maxIter=20 được chọn
├── artifacts/
│   ├── demo/                       # Dữ liệu nhỏ cho mô hình ALS
│   ├── catalog/                    # Catalog phim tổng hợp cho giao diện thể loại
│   └── cache/                      # Cache metadata poster TMDB
├── scripts/
│   ├── 00_check_data.py            # Kiểm tra headers, số dòng, checksum
│   ├── 01_convert_to_parquet.py    # ETL CSV -> Parquet
│   ├── 02_eda_local.py             # EDA local bằng pandas/pyarrow
│   ├── 03_prepare_splits_local.py  # Sample users và chia train/valid/test
│   ├── 04_train_als_spark.py       # ALS + baseline + validation + gợi ý
│   ├── 05_tune_evaluate_spark.py   # Tuning, test metrics và Top-K metrics
│   ├── 06_export_demo.py           # Chuẩn bị artifact cho bản thử nghiệm ALS
│   ├── 07_build_movie_catalog.py   # Tổng hợp rating, links, movies thành catalog gợi ý
│   └── 08_enrich_catalog_imdb.py   # Bổ sung IMDb ID cho catalog đã tạo trước đó
├── web_api.py                      # FastAPI: catalog, lọc phim, poster, phục vụ frontend
├── frontend/                       # React + TypeScript; npm run build tạo dist/
├── requirements-web.txt            # Python dependencies để chạy ứng dụng web
├── app.py                          # Bản Streamlit cũ, giữ để đối chiếu
└── src/recommender/                # Module nghiệp vụ, thuật toán gợi ý & TMDB API
```

Các thư mục dataset, Parquet, model, cache TMDB, log, `node_modules` và bản build `frontend/dist/` được loại khỏi lịch sử Git. Gói demo trên GitHub Releases cung cấp riêng các artifact phục vụ web và frontend đã build. Nếu không dùng gói này, tải/tạo lại dữ liệu theo các bước bên dưới rồi build giao diện. Điều kiện sử dụng dữ liệu: [Thông báo nguồn MovieLens](THIRD_PARTY_NOTICES.md). File mẫu môn khác, Word, PowerPoint và file tạm không phát hành cùng mã nguồn.

## Cài môi trường Spark local

```powershell
py -m pip install -r requirements.txt
```

Trên Windows, Spark có thể cần `winutils.exe` và `hadoop.dll` để ghi file local. Các binary này không được phân phối trong repository; có thể đặt chúng cục bộ trong `.hadoop/bin/`. Nếu chuyển sang WSL/Linux, dùng Spark theo môi trường Linux.

## Chạy tuần 1-3

Kiểm tra dataset:

```powershell
py scripts\00_check_data.py --data-dir ml-32m
```

Chuyển CSV sang Parquet:

```powershell
py scripts\01_convert_to_parquet.py --data-dir ml-32m --output-dir data\processed\parquet
```

Tạo thống kê và biểu đồ EDA:

```powershell
py scripts\02_eda_local.py --parquet-dir data\processed\parquet --report-dir reports
```

Tạo sample dev và chia train/valid/test theo thời gian:

```powershell
py scripts\03_prepare_splits_local.py --parquet-dir data\processed\parquet --output-dir data\interim --user-mod 10
```

`--user-mod 10` lấy các user có `userId % 10 == 0`, đủ nhỏ để thử mô hình nhanh.

## Chạy tuần 4

Train ALS trên tập phát triển, tính baseline và lưu factor model:

```powershell
py scripts\04_train_als_spark.py `
  --ratings-train data\interim\train.parquet `
  --ratings-valid data\interim\valid.parquet `
  --movies data\processed\parquet\movies.parquet `
  --output-dir models\als_dev `
  --rank 16 --reg-param 0.08 --max-iter 5
```

Kết quả nằm trong `models/als_dev/metrics.json`, `baseline_metrics.json`, `model/factors/` và `recommendations/`.

## Chạy tuần 5-6

Thử ba cấu hình ALS, chọn theo RMSE validation, fit lại trên train+validation, chấm test và tính Precision@10/Recall@10/NDCG@10:

```powershell
py scripts\05_tune_evaluate_spark.py `
  --ratings-train data\interim\train.parquet `
  --ratings-valid data\interim\valid.parquet `
  --ratings-test data\interim\test.parquet `
  --movies data\processed\parquet\movies.parquet `
  --output-dir models\als_final `
  --report-dir reports\tables
```

Xuất file nhỏ cho bản thử nghiệm ALS:

```powershell
py scripts\06_export_demo.py
```

Các kết quả sample nằm trong `reports/tables/als_tuning.csv`, `reports/tables/test_metrics.json` và `models/als_final/metrics.json`. Kết quả final full nằm trong `reports/tables/full/als_tuning.csv`, `models/als_full/metrics.json` và `artifacts/demo/manifest.json`.

## Chạy model final trên toàn bộ 32M

Split full đã được tạo sẵn trong `data/full_interim/`. Dùng tham số đã chọn từ tuning sample và tăng số block để tránh một task giữ quá nhiều rating:

```powershell
py scripts\05_tune_evaluate_spark.py `
  --ratings-train data\full_interim\train.parquet `
  --ratings-valid data\full_interim\valid.parquet `
  --ratings-test data\full_interim\test.parquet `
  --movies data\processed\parquet\movies.parquet `
  --output-dir models\als_full `
  --report-dir reports\tables\full `
  --grid 16:0.08:5 `
  --shuffle-partitions 128 `
  --num-user-blocks 50 --num-item-blocks 50 `
  --driver-memory 16g --memory-overhead 2g
```

Sau đó cập nhật dữ liệu demo:

```powershell
py scripts\06_export_demo.py --model-dir models\als_full --output-dir artifacts\demo
```

## Ứng dụng gợi ý phim theo thể loại yêu thích (MovieLens 32M + TMDB)

Ứng dụng web CINE32 cho phép người dùng mới khám phá phim theo thể loại, tìm tên phim, xem điểm cộng đồng từ MovieLens và lấy ảnh poster/tóm tắt từ TMDB. Giao diện React có thanh tìm kiếm, phim nổi bật, dãy poster và hộp chi tiết theo phong cách trang phim IMDb; đây là nhận diện riêng của đề tài.

Chọn một hoặc nhiều **chip thể loại**: danh sách tự cập nhật ngay, không cần bấm nút. Ứng dụng liệt kê **tất cả phim có ít nhất một thể loại đã chọn**, kể cả phim chưa có đánh giá; phim khớp nhiều thể loại được ưu tiên. Mặc định **Tất cả phim** cho phép duyệt toàn catalog. Kết quả chia 24 phim mỗi trang; ô **Trang** cho phép tới bất kỳ trang nào. Poster chỉ tải cho trang đang xem. Phim chưa có điểm MovieLens hiển thị **Chưa có đánh giá**.

### 1. Chuẩn bị catalog phim

Sử dụng Spark để tổng hợp hơn 28,7 triệu lượt đánh giá (train + validation), tính điểm điều chỉnh $m=100$, trích xuất năm và giữ cả `tmdbId` lẫn `imdbId` từ MovieLens:

```powershell
py scripts\07_build_movie_catalog.py
```

Nếu đã tạo catalog bằng phiên bản cũ, bổ sung IMDb ID mà không cần tổng hợp lại ratings:

```powershell
py scripts\08_enrich_catalog_imdb.py
```

Kết quả được lưu tại:
- `artifacts/catalog/movie_catalog.parquet` (catalog phim)
- `artifacts/catalog/manifest.json` (thông tin kiểm toán tập dữ liệu)

### 2. Cấu hình TMDB API (tùy chọn)

Để hiển thị ảnh poster thật và mô tả nội dung từ The Movie Database:
1. Đăng ký tài khoản miễn phí tại [TMDB](https://www.themoviedb.org/).
2. Lấy **API Read Access Token (v4)** tại mục Settings -> API.
3. Đặt biến môi trường `TMDB_READ_ACCESS_TOKEN`, hoặc tạo file `.streamlit/secrets.toml` từ file mẫu (vẫn được FastAPI đọc):
   ```powershell
   Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
   ```
4. Điền token của bạn vào `TMDB_READ_ACCESS_TOKEN`.

*Lưu ý: Nếu không cấu hình token, ứng dụng vẫn hoạt động bình thường và sử dụng ảnh placeholder vector.*

Khi TMDB không còn nhận `tmdbId` ở mục phim, ứng dụng dùng chính `imdbId` của MovieLens để tìm bản ghi phim hoặc chương trình truyền hình tương ứng. Poster tải nền; tên, thể loại và điểm MovieLens hiện trước. Trạng thái “Đã xác minh kết nối” chỉ xuất hiện sau một phản hồi API thật; khi chỉ dùng dữ liệu cache, trạng thái là “chưa xác minh kết nối hiện tại”.

### 3. Khởi chạy ứng dụng React + FastAPI

Cần Python 3.11+ và Node.js/npm. Chạy các lệnh sau từ thư mục gốc của dự án:

```powershell
py -m pip install -r requirements-web.txt
py scripts/12_prepare_als_serving.py
Set-Location frontend
npm install
npm run build
Set-Location ..
py -m uvicorn web_api:app --host 127.0.0.1 --port 8502
```

Truy cập `http://127.0.0.1:8502/`. Lần đầu cần Node.js và npm để build giao diện; các lần sau chỉ cần chạy lệnh Uvicorn nếu không sửa frontend. API có tài liệu tại `http://127.0.0.1:8502/docs`.

Để chỉnh giao diện và xem cập nhật tức thời: mở FastAPI trên cổng 8000, rồi chạy `npm run dev` trong `frontend/`; Vite sẽ mở cổng 5173 và chuyển tiếp `/api` sang backend. Nếu cần xem lại bản Streamlit cũ, chạy `py -m streamlit run app.py` ở cổng riêng.
