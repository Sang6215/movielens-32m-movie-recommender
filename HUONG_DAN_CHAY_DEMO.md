# Chạy CINE32 bằng model đã train

Gói demo v1.0.0 chứa vector ALS của 200.948 user, chỉ mục 32.000.204 lượt đánh giá, catalog 87.585 phim và frontend đã build. ALS phục vụ Top 10 từ 11.330 phim có ít nhất 100 lượt chấm trong train + validation. Model dùng rank=16, regParam=0,08, maxIter=20, fit trên 28.709.236 dòng train + validation.

Không cần huấn luyện lại hoặc cài Spark, Hadoop, Java và Node.js để chạy web từ gói demo. Gói không bao gồm môi trường Python, tài khoản TMDB, Word, PowerPoint hay runtime HDFS. Pipeline train và HDFS vẫn dùng hướng dẫn riêng trong README.

## 1. Tải mã nguồn

Yêu cầu Python 3.11+ và Git. Chạy PowerShell:

```powershell
git clone --branch v1.0.0 https://github.com/Sang6215/movielens-32m-movie-recommender.git
Set-Location movielens-32m-movie-recommender
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
```

Nếu đã clone, dùng bản mã nguồn tương ứng tag v1.0.0. Giữ các thay đổi riêng trước khi chuyển phiên bản.

## 2. Tải gói demo

Mở [GitHub Releases v1.0.0](https://github.com/Sang6215/movielens-32m-movie-recommender/releases/tag/v1.0.0), tải `cine32-demo-v1.0.0.zip` và `SHA256SUMS.txt` vào thư mục gốc repository.

Hoặc tải bằng PowerShell:

```powershell
Invoke-WebRequest -Uri 'https://github.com/Sang6215/movielens-32m-movie-recommender/releases/download/v1.0.0/cine32-demo-v1.0.0.zip' -OutFile 'cine32-demo-v1.0.0.zip'
Invoke-WebRequest -Uri 'https://github.com/Sang6215/movielens-32m-movie-recommender/releases/download/v1.0.0/SHA256SUMS.txt' -OutFile 'SHA256SUMS.txt'
```

Kiểm tra checksum rồi giải nén từ thư mục gốc repository:

```powershell
$demoExpectedHash = ((Get-Content -LiteralPath 'SHA256SUMS.txt' -Raw).Trim() -split '\s+')[0]
$demoActualHash = (Get-FileHash -LiteralPath 'cine32-demo-v1.0.0.zip' -Algorithm SHA256).Hash
if ($demoActualHash -ne $demoExpectedHash) { throw 'Checksum không khớp. Hãy tải lại gói demo.' }
Expand-Archive -LiteralPath 'cine32-demo-v1.0.0.zip' -DestinationPath '.'
```

Lệnh giải nén không ghi đè các artifact đang có. Với repository đã chứa catalog hoặc frontend build, giải nén vào thư mục riêng để kiểm tra trước khi thay thế.

Cấu trúc sau giải nén:

```text
artifacts/catalog/movie_catalog.parquet
artifacts/catalog/manifest.json
artifacts/als_serving/factors_and_history.npz
artifacts/als_serving/manifest.json
frontend/dist/index.html
frontend/dist/assets/...
licenses/MovieLens32M_README.txt
DEMO_PACKAGE_MANIFEST.json
DEMO_README.md
```

`DEMO_PACKAGE_MANIFEST.json` ghi SHA-256 từng file và cấu hình model. Gói giữ nguyên README cùng điều kiện sử dụng do GroupLens cung cấp. Xem [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## 3. Chạy web

```powershell
.\.venv\Scripts\python.exe -m uvicorn web_api:app --host 127.0.0.1 --port 8502
```

Mở http://127.0.0.1:8502/ . Chọn thể loại để duyệt phim hoặc mở mục Gợi ý ALS và thử User 1, User 2. User 999999 nhận danh sách dự phòng. API: http://127.0.0.1:8502/docs . Dừng bằng Ctrl+C.

Nếu cổng 8502 đang dùng, chạy với `--port 8503` rồi mở đúng cổng đó. Điểm MovieLens và điểm ALS là hai loại điểm riêng. User ID là mã ẩn danh của dataset, chưa phải tài khoản người dùng thật.

## 4. Poster và metadata

Không có token TMDB, web vẫn hiển thị tên, thể loại, rating, gợi ý ALS và ảnh thay thế. Muốn có poster thật, đặt token của bạn trước khi khởi động:

```powershell
$env:TMDB_READ_ACCESS_TOKEN = 'TOKEN_CUA_BAN'
.\.venv\Scripts\python.exe -m uvicorn web_api:app --host 127.0.0.1 --port 8502
```

Token và cache không nằm trong gói phát hành. Poster cần kết nối TMDB; gói không chứa ảnh poster tải từ dịch vụ.

## 5. Tạo lại gói phát hành

Sau khi đã có catalog và NPZ trên máy:

```powershell
Set-Location frontend
npm ci
npm run build
Set-Location ..
py scripts/14_package_demo.py
```

Script chỉ đóng gói danh sách file cho phép, từ chối file frontend ngoài HTML/JS/CSS/SVG, giữ README MovieLens, kiểm tra số lượng user/phim và tính checksum. Đầu ra nằm trong `artifacts/releases/`, không commit vào Git. Script đóng gói không huấn luyện lại model.
