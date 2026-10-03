# Đưa CINE32 lên Internet và dùng chung poster TMDB

Mục tiêu: mọi người mở một URL để dùng giao diện CINE32 hoặc gọi API của ứng dụng. Máy chủ của chủ dự án gọi TMDB bằng token riêng; trình duyệt người dùng chỉ nhận thông tin phim và URL ảnh, không nhận token.

**Trạng thái ngày 03/10/2026:** đã triển khai trên Render Free, vùng Singapore, 512 MB RAM, một Uvicorn worker. Dịch vụ đã báo Live và đã được kiểm tra từ client bên ngoài qua HTTPS:

- Website: [https://cine32-movie-recommender.onrender.com/](https://cine32-movie-recommender.onrender.com/).
- Tài liệu API: [Swagger UI](https://cine32-movie-recommender.onrender.com/docs).
- Schema: [OpenAPI](https://cine32-movie-recommender.onrender.com/openapi.json).
- Trạng thái: [Health](https://cine32-movie-recommender.onrender.com/api/health).

**Đã kiểm tra:** 15 kiểm tra tự động trên máy phát triển đạt. [Docker Linux giới hạn 512 MB RAM](https://github.com/Sang6215/movielens-32m-movie-recommender/actions/runs/37121573665) chạy thành công với bốn yêu cầu ALS đồng thời ngay lúc chưa có cache. Kiểm tra trên dịch vụ thật xác nhận catalog 87.585 phim, lọc thể loại, Top 10 User 1 đúng artifact đã kiểm chứng, fallback User 999999, poster và mô tả TMDB thật, cùng các đường dẫn giao diện/tài liệu/health. Token chỉ nằm trong cấu hình riêng của Render; không truyền vào GitHub Actions hoặc Docker image.

## 1. GitHub và hosting có vai trò gì?

- GitHub lưu mã nguồn, hướng dẫn và gói demo đã huấn luyện trên [Releases v1.0.0](https://github.com/Sang6215/movielens-32m-movie-recommender/releases/tag/v1.0.0).
- Hosting chạy FastAPI, phục vụ giao diện React và giữ token TMDB trong môi trường của máy chủ.
- Người truy cập website đã triển khai không cần đăng ký TMDB hoặc nhập token.
- Người clone repository để tự chạy backend cần cấu hình token của mình nếu muốn có poster mới. Token của chủ dự án không được tự chuyển sang máy họ.

GitHub Pages chỉ phục vụ trang tĩnh HTML/CSS/JavaScript, không chạy FastAPI hoặc Spark/Hadoop. Vì vậy, đưa repository lên GitHub chưa tạo ra API đang chạy trên Internet. Xem [tài liệu GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

GitHub Actions Secrets dành cho các workflow được cấp quyền sử dụng secret. Nó không cấp token cho người clone repository và không thay thế biến môi trường của hosting. Xem [tài liệu GitHub Actions Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

Luồng phục vụ:

```text
Người dùng -> HTTPS CINE32 -> FastAPI -> TMDB
                             |
                             +-> Catalog + vector ALS + cache metadata

TMDB_READ_ACCESS_TOKEN chỉ nằm trong môi trường FastAPI.
Trình duyệt nhận URL poster và tải ảnh từ máy chủ ảnh TMDB.
```

API hiện phục vụ catalog, lọc phim, poster và gợi ý từ mô hình đã train. Các thao tác train ALS, chạy Spark hoặc quản trị HDFS chưa có giao diện/API quản trị trong bản triển khai này.

## 2. Cấu trúc Docker

Dockerfile dùng Python 3.12 slim, cài `requirements-web.txt`, tải gói demo v1.0.0 và kiểm tra SHA-256 trong bước build. Catalog, vector ALS và frontend đã build được lấy từ gói phát hành. Không cần chạy train, cài Spark/Hadoop/Java hoặc build Node.js để khởi động image này.

Ứng dụng chạy một Uvicorn worker trên `0.0.0.0:8502`. Đường dẫn cache trong container là `/app/artifacts/cache`. Gói demo nén khoảng 106 MB; kích thước image và RAM khi chạy sẽ lớn hơn kích thước ZIP.

Không đưa token vào Dockerfile, Docker build arguments, frontend, image hoặc repository. FastAPI đọc `TMDB_READ_ACCESS_TOKEN` khi ứng dụng chạy. Render cũng lưu ý không tham chiếu build arguments chứa secret trong Dockerfile. Xem [Docker trên Render](https://render.com/docs/docker).

## 3. Thử Docker trên máy trước

Yêu cầu Docker đang hoạt động với Linux containers. Chạy từ thư mục gốc của repository, dùng phiên bản mã nguồn có Dockerfile này, không checkout tag v1.0.0 cũ:

```powershell
docker build -t cine32-web:local .
```

Image được build bằng artifact của v1.0.0 nhưng dùng mã nguồn backend tại checkout hiện tại. Token không cần có trong bước build.

Nhập token cục bộ qua lời nhắc ẩn ký tự; câu lệnh lưu trong lịch sử không chứa giá trị token:

```powershell
$cine32TokenSecure = Read-Host 'Nhập TMDB API Read Access Token' -AsSecureString
$env:TMDB_READ_ACCESS_TOKEN = [System.Net.NetworkCredential]::new('', $cine32TokenSecure).Password

docker run -d --name cine32-web -p 127.0.0.1:8502:8502 --env TMDB_READ_ACCESS_TOKEN --mount type=volume,source=cine32-tmdb-cache,target=/app/artifacts/cache cine32-web:local

Remove-Item Env:TMDB_READ_ACCESS_TOKEN
```

Lệnh trên chỉ mở cổng trên máy hiện tại. Volume giữ cache qua những lần tạo lại container trên cùng máy. Nếu máy đã có ứng dụng dùng cổng 8502, đổi phần ánh xạ thành `127.0.0.1:8503:8502` và mở cổng 8503.

Mở:

- Website: `http://127.0.0.1:8502/`.
- Health check: `http://127.0.0.1:8502/api/health`.
- Tài liệu API: `http://127.0.0.1:8502/docs`.
- Schema OpenAPI: `http://127.0.0.1:8502/openapi.json`.

Kiểm tra bằng PowerShell:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8502/api/health'
Invoke-RestMethod 'http://127.0.0.1:8502/api/meta'
Invoke-RestMethod 'http://127.0.0.1:8502/api/als/recommendations?user_id=1'
docker stats --no-stream cine32-web
```

Health check trả HTTP 200 khi có catalog Parquet, manifest catalog, NPZ ALS, manifest ALS và `frontend/dist/index.html`; thiếu file trả HTTP 503. Nó kiểm tra sự hiện diện của file, không kiểm tra nội dung toàn bộ artifact hoặc kết nối TMDB. `tmdbConfigured=true` trong `/api/meta` chỉ cho biết đã cấu hình token.

Trong giao diện, mở một trang phim và chờ poster tải nền. Phim có dữ liệu ảnh hợp lệ sẽ hiện ảnh; phim không có ảnh có thể tiếp tục dùng ảnh thay thế. Điểm cộng đồng lấy từ MovieLens, điểm dự đoán ALS là giá trị riêng, không phải rating TMDB.

Dừng khi thử xong:

```powershell
docker stop cine32-web
```

## 4. Triển khai thủ công trên Render

Các bước sau được đối chiếu với tài liệu Render ngày 03/10/2026. Dịch vụ hiện tại dùng gói Free theo lựa chọn của chủ dự án; không chọn gói compute trả phí.

### 4.1. Tạo Web Service từ repository

1. Đăng nhập [Render Dashboard](https://dashboard.render.com/).
2. Chọn **New → Web Service**.
3. Kết nối GitHub của chủ repository và chọn `Sang6215/movielens-32m-movie-recommender`.
4. Chọn branch `main`, đã có các file triển khai.
5. Chọn **Language/Runtime: Docker**; Dockerfile Path là `./Dockerfile`, build context là thư mục gốc.
6. Để Docker Command mặc định để chạy `CMD` trong Dockerfile.
7. Tự chọn region và tài nguyên phù hợp sau khi xem phép đo RAM tại mục 6.

Render có thể build image trực tiếp từ Dockerfile trong repository. Xem [hướng dẫn Docker](https://render.com/docs/docker) và [tạo Web Service](https://render.com/docs/web-services).

### 4.2. Đặt biến môi trường và health check

Trong phần Environment/Advanced của dịch vụ:

| Tên | Giá trị cần đặt |
|---|---|
| `TMDB_READ_ACCESS_TOKEN` | Token thật của chủ dự án; nhập trực tiếp vào dashboard, không ghi vào GitHub |
| `PORT` | `8502` |
| `CINE32_CORS_ORIGINS` | Chỉ cần nếu một frontend ở origin khác gọi API; xem mục 5 |

Đặt **Health Check Path** là `/api/health`.

Render yêu cầu dịch vụ lắng nghe trên `0.0.0.0`. Cổng mặc định của Render là 10000, có thể đổi qua `PORT`; cấu hình `PORT=8502` khớp với image này. Render cấp URL cho Web Service và xử lý HTTPS ở phía nền tảng. Xem [cấu hình cổng và HTTPS](https://render.com/docs/web-services#port-binding).

Biến môi trường được quản lý trong tab **Environment**. Sau khi thay token của dịch vụ đã chạy, chọn **Save and deploy** hoặc **Save, rebuild, and deploy** để tiến trình mới nhận giá trị; **Save only** chưa áp dụng ngay. Xem [Environment Variables and Secrets](https://render.com/docs/configure-environment-variables).

### 4.3. Deploy và kiểm tra URL thật

1. Bấm **Create Web Service/Deploy** trên dashboard.
2. Theo dõi bước tải artifact, kiểm tra checksum, cài dependencies và khởi động Uvicorn trong Deploys/Logs.
3. Khi dịch vụ hoạt động, sao chép URL HTTPS do Render cấp. Chỉ sau bước này mới có URL website/API để chia sẻ.
4. Mở `/`, `/api/health`, `/docs` và thử chọn thể loại, User 1, User 999999.
5. Kiểm tra poster thật trên một phim có ảnh; không coi `tmdbConfigured=true` là bằng chứng token còn hợp lệ.

Nếu health check thất bại, xem lỗi thiếu artifact, checksum, cổng hoặc thiếu RAM trong log. Không đưa giá trị token vào log hoặc ảnh chụp khi trao đổi lỗi.

### 4.4. Cache và gói miễn phí

Cache SQLite ở `/app/artifacts/cache` có thể tạo lại từ TMDB. Nếu hosting có ổ lưu trữ bền vững, mount đúng thư mục này để giữ cache; không mount đè toàn bộ `/app/artifacts`, vì thư mục cha còn chứa catalog và vector ALS trong image.

Render Free tạm dừng sau 15 phút không có request; lần truy cập tiếp theo có thể cần khoảng một phút khởi động. Dữ liệu mới ghi vào filesystem bị mất khi restart, redeploy hoặc tạm dừng; Free không hỗ trợ persistent disk. Với CINE32, điều này khiến cache metadata phải tải lại, còn artifact nằm sẵn trong image. Dịch vụ miễn phí cũng có giới hạn giờ chạy, băng thông và build; xem [giới hạn Render Free](https://render.com/docs/free) trước khi chọn. Bản demo đã chạy và được kiểm tra trong giới hạn 512 MB, chưa chứng minh phục vụ tải lớn ổn định.

Dịch vụ hiện bỏ qua thay đổi `*.md`, `reports/**`, `tests/**` và `.github/**` khi tự deploy. Sửa tài liệu sẽ không build lại image. Đổi mã runtime hoặc Dockerfile vẫn tự kích hoạt triển khai từ `main`.

## 5. Dùng API từ một website khác

Cách đơn giản nhất là để FastAPI phục vụ frontend đã build cùng một URL. Giao diện hiện gọi các đường dẫn tương đối `/api/...`, nên không cần tách frontend và backend.

Nếu frontend chạy ở tên miền khác:

1. Đổi địa chỉ gọi API của frontend sang URL HTTPS backend đã triển khai. Giao diện hiện tại chưa tự biết URL hosting mới.
2. Đặt `CINE32_CORS_ORIGINS` trên backend thành danh sách origin được cho phép, ngăn cách bằng dấu phẩy. Origin gồm giao thức, tên miền và cổng nếu có; không thêm đường dẫn trang hoặc `*`. Các origin này được bổ sung vào hai origin phát triển mặc định `http://127.0.0.1:5173` và `http://localhost:5173`.

Ví dụ cấu hình, các tên miền dưới đây chỉ là mẫu:

```text
CINE32_CORS_ORIGINS=https://frontend.example.org,http://localhost:5173
```

CORS điều khiển việc trình duyệt đọc phản hồi từ origin khác; nó không phải đăng nhập, API key hoặc giới hạn số request. Ứng dụng hiện phục vụ API đọc công khai, chưa có cơ chế hạn mức theo tài khoản. Người dùng website hoặc client gọi backend đã host không cần token TMDB riêng; backend dùng token của chủ dịch vụ.

URL `posterUrl` có thể là URL HTTPS của TMDB hoặc đường dẫn tương đối `/media/poster-placeholder.svg`. Client bên ngoài cần nối đường dẫn tương đối với base URL của backend. Khi `posterPending=true`, có thể gọi lại `/api/posters` với các `movie_ids` đang hiển thị, tối đa 40 phim mỗi lần, để lấy kết quả tải nền.

## 6. Tài nguyên và phạm vi triển khai

Chạy một worker vì mỗi worker nạp riêng catalog, vector ALS và chỉ mục lịch sử. Hai phép đo tiến trình Python mới trên Windows trong workspace, lần lượt gọi từng request và không gọi TMDB thật:

| Thời điểm | BLAS mặc định | Giới hạn BLAS một thread như Dockerfile |
|---|---:|---:|
| Sau khi gọi catalog | 189,58 MiB | 174,91 MiB |
| Sau khi gọi ALS | 459,49 MiB | 444,90 MiB |
| Mức cao nhất ghi nhận | 462,96 MiB | 448,37 MiB |

Kiểm tra Docker Linux riêng với giới hạn cứng 512 MB, không swap, đã chạy được catalog, ALS và fallback. [Lượt kiểm tra đầu tiên](https://github.com/Sang6215/movielens-32m-movie-recommender/actions/runs/37121423195) ghi nhận khoảng 434,3 MiB sử dụng sau các request; cgroup memory peak 462.917.632 byte (khoảng 441,47 MiB), `OOMKilled=false`. Lượt kiểm tra mới nhất bổ sung bốn request ALS đồng thời ngay khi mô hình chưa được nạp; backend dùng khóa lúc nạp catalog và model để tránh tạo nhiều bản trong RAM.

**Gói 512 MB phù hợp với bản demo đã kiểm tra; nên dùng từ 1 GB RAM nếu mở rộng tải, cân nhắc 2 GB cho nhiều request đồng thời.** Các phép đo trên Windows và kiểm tra ngắn trong Docker không thay thế kiểm thử tải dài trên hosting. Chủ dự án đã chọn thử gói Free; không tự nâng cấp lên gói trả phí.

Kích thước ZIP không thể dùng làm mức RAM tối thiểu. Kiểm tra lại RAM sau khi gọi cả catalog, ALS và poster trên máy chủ thật, rồi đánh giá thêm tải đồng thời.

Docker image này triển khai **ứng dụng phục vụ gợi ý đã huấn luyện**. Nó không triển khai cụm HDFS, không tự train lại ALS và không thêm bảng điều khiển quản trị Big Data. User ID là mã ẩn danh MovieLens phục vụ demo; ứng dụng chưa có tài khoản mới hoặc ghi thêm rating.

Nếu dùng hosting Docker khác Render, cần các cấu hình tương đương: build từ Dockerfile, HTTPS phía reverse proxy/nền tảng, kết nối tới cổng container 8502, runtime secret TMDB, health check `/api/health`, đủ RAM và thư mục cache có quyền ghi.

## 7. Vận hành dịch vụ đã triển khai

- Chia sẻ URL website hoặc `/docs`; người dùng không cần token TMDB.
- Trước buổi bảo vệ, mở website sớm để dịch vụ Free khởi động và poster nạp vào cache.
- Theo dõi Logs, Metrics và hạn mức Free trên dashboard của Render. Chỉ đổi gói trả phí khi chủ dự án chọn ngân sách phù hợp.
- Nếu thay token TMDB, cập nhật biến `TMDB_READ_ACCESS_TOKEN` trong Environment rồi deploy lại. Không ghi token vào mã nguồn.
- Các thay đổi chỉ gồm tài liệu đã được lọc khỏi auto-deploy. Nếu thay frontend, cần build và phát hành artifact mới, cập nhật URL/checksum trong installer trước khi deploy; Docker hiện dùng frontend từ gói v1.0.0.

Word, PowerPoint, file mẫu, cache, token và file tạm vẫn lưu ngoài GitHub. Điều kiện sử dụng dữ liệu và nguồn MovieLens: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
