# Đặc tả ứng dụng gợi ý phim theo thể loại yêu thích

- **Đề tài:** Hệ thống gợi ý phim với MovieLens 32M.
- **Ngày lập:** 22/09/2026; cập nhật: 01/10/2026.
- **Trạng thái:** Đã triển khai giao diện CINE32 bằng React/TypeScript và FastAPI (`frontend/`, `web_api.py`). `app.py` là bản Streamlit cũ.

## 1. Sản phẩm cần xây dựng

Xây dựng ứng dụng web tiếng Việt cho phép người dùng nhập hoặc chọn thể loại phim yêu thích và **tự động nhận toàn bộ danh sách phim phù hợp**. Mỗi phim được trình bày thành một thẻ có **poster, tên phim, thể loại, điểm đánh giá trung bình và số lượt đánh giá**. Không có nút “Gợi ý phim” hoặc ô chọn “Số phim”.

Người dùng mới sử dụng được ngay, không cần tài khoản hoặc User ID trong MovieLens. Bản đầu tập trung vào tìm phim theo sở thích thể loại; dữ liệu đánh giá lấy từ MovieLens 32M, hình ảnh lấy từ TMDB qua ID liên kết.

“Đánh giá” trong phiên bản này là **điểm chấm của cộng đồng**, không phải bài bình luận bằng văn bản. MovieLens không cung cấp bài nhận xét phim; tính năng đó có thể bổ sung sau.

**Bổ sung để bảo vệ đồ án:** mục riêng **Gợi ý ALS** cho phép nhập User ID MovieLens và xem Top 10 cá nhân hóa, lịch sử đã đánh giá, điểm ALS và phương án cho user mới. Luồng thể loại vẫn tự cập nhật toàn bộ phim phù hợp. Chi tiết: [HDFS và demo ALS](HUONG_DAN_HDFS_VA_DEMO_ALS.md).

## 2. Luồng sử dụng

1. Người dùng mở ứng dụng, thấy thanh tìm tên phim, phim nổi bật và danh sách poster.
2. Người dùng chọn một hoặc nhiều chip thể loại, ví dụ **Hành động**, **Hài**, **Khoa học viễn tưởng**; hoặc tìm tên phim trong thanh tìm kiếm.
3. Ngay khi lựa chọn thay đổi, ứng dụng lọc catalog, xếp hạng và hiển thị **mọi phim có ít nhất một thể loại đã chọn**, kể cả phim chưa có lượt đánh giá.
4. Danh sách được chia trang, 24 phim mỗi trang; tổng số phim và khoảng phim đang xem luôn hiển thị. Người dùng nhập số trang bất kỳ để xem hết danh sách.
5. Người dùng bấm thẻ phim để xem phần chi tiết, hoặc thay đổi thể loại để nhận kết quả mới từ trang đầu.

Các chip thể loại dùng nhãn tiếng Việt và hỗ trợ chọn nhiều giá trị. Nút **Tất cả phim** hiển thị toàn catalog. Thanh tìm kiếm lọc theo tên phim trong MovieLens và có thể kết hợp với thể loại.

Khi chọn nhiều thể loại, mặc định lấy phim khớp **ít nhất một** thể loại; phim khớp nhiều thể loại đã chọn được ưu tiên. Hiển thị quy tắc này dưới ô chọn để người dùng hiểu kết quả.

## 3. Giao diện đã triển khai

### 3.1. Trang chính

```text
┌─────────────────────────────────────────────────────────────┐
│ CINE32   Khám phá  Thể loại  Nguồn dữ liệu   [Tìm tên phim]  │
├───────────────────────────────────────┬─────────────────────┤
│ ẢNH NỀN PHIM NỔI BẬT                  │ Tiếp theo           │
│ Tên phim · ★ điểm MovieLens            │ Poster + tên phim   │
│ Mô tả ngắn       [Xem chi tiết]        │                     │
├───────────────────────────────────────┴─────────────────────┤
│ KHÁM PHÁ THEO SỞ THÍCH                                      │
│ [Tất cả phim] [Hành động] [Hài] [Khoa học viễn tưởng] ...   │
│ Số phim · Đang xem 1–24          [Trang 1 / tổng số trang]  │
│ [Poster + điểm + tên] [Poster + điểm + tên] ...             │
│ [Trang trước] [Nhập trang] [Trang sau]                      │
│ Nguồn điểm: MovieLens 32M · Poster và mô tả: TMDB           │
└─────────────────────────────────────────────────────────────┘
```

Sơ đồ chỉ minh họa bố cục. Giao diện lấy cảm hứng từ cách trình bày trang phim [IMDb](https://www.imdb.com/): nền tối, điểm nhấn vàng, ảnh lớn và dãy poster. Tên CINE32 và các nguồn điểm/ảnh được trình bày riêng, không dùng nhận diện IMDb.

Poster dọc tỷ lệ 2:3, các thẻ nhất quán và chữ dễ đọc. Màn hình rộng hiển thị tối đa 6 thẻ mỗi hàng; điện thoại hiển thị 2 thẻ, thể loại cuộn ngang. Bố cục không tràn ngang khi tiêu đề phim dài.

### 3.2. Nội dung mỗi thẻ phim

| Thành phần | Yêu cầu |
|---|---|
| Poster | Đúng phim, có ảnh thay thế nếu thiếu hoặc tải lỗi |
| Tên phim | Dùng tên trong MovieLens; có thể bổ sung tên tiếng Việt từ TMDB |
| Năm phát hành | Hiển thị ở hộp chi tiết khi xác định được; không đoán khi thiếu |
| Thể loại | Hiển thị tối đa 3 nhãn tiếng Việt ở thẻ, đầy đủ trong hộp chi tiết |
| Điểm đánh giá | Ví dụ `★ 4,2/5 · MovieLens`; phim chưa được chấm hiển thị `Chưa có đánh giá` |
| Số lượt đánh giá | Hiển thị trong hộp chi tiết |
| Thẻ phim | Bấm để mở hộp chi tiết; liên kết TMDB/IMDb nếu có ID tương ứng |

Điểm và số lượt phải lấy từ dữ liệu thật. Không tạo điểm giả, không dùng điểm ALS dự đoán làm điểm cộng đồng. Điểm MovieLens là ảnh chụp từ bộ dữ liệu đã tải, không phải điểm cập nhật trực tiếp từ người xem hiện tại.

Trang chi tiết có thể bổ sung mô tả nội dung từ TMDB. Nếu thiếu mô tả tiếng Việt, dùng bản tiếng Anh có ghi ngôn ngữ hoặc hiển thị “Chưa có mô tả”.

Các chỉ số RMSE, MAE và tham số ALS ở báo cáo nghiên cứu; trang tìm phim ưu tiên thông tin giúp người dùng chọn phim.

## 4. Dữ liệu sử dụng

### 4.1. MovieLens 32M đã có trong dự án

| Nguồn | Dữ liệu cần lấy | Mục đích |
|---|---|---|
| `ml-32m/movies.csv` hoặc `data/processed/parquet/movies.parquet` | `movieId`, `title`, `genres` | Catalog phim và bộ lọc thể loại |
| `ml-32m/links.csv` hoặc `data/processed/parquet/links.parquet` | `movieId`, `tmdbId` | Nối phim MovieLens với TMDB để lấy poster |
| `data/full_interim/train.parquet` | `movieId`, `rating` | Thống kê và xếp hạng trong giai đoạn phát triển |
| `data/full_interim/valid.parquet` | `movieId`, `rating` | Đánh giá lựa chọn; gộp với train khi tạo catalog phục vụ bản cuối |
| `data/full_interim/test.parquet` | Dữ liệu giữ lại | Đánh giá cuối; không tham gia lựa chọn quy tắc xếp hạng |

Dataset có 87.585 phim và 32.000.204 rating. Rating gốc từ 0,5 đến 5 sao. Poster không nằm trong MovieLens; `links.csv` cung cấp ID để nối nguồn ngoài. Chi tiết có trong `ml-32m/README.txt`.

Giao diện mới phải lấy ứng viên từ toàn bộ catalog phù hợp, thay vì lọc tiếp 10 phim dựng sẵn của một user trong `artifacts/demo/recommendations.parquet`.

### 4.2. Ánh xạ thể loại

Đọc các giá trị thực tế từ cột `genres`, tách bằng dấu `|`, rồi ánh xạ nhãn hiển thị. Khớp chính xác từng nhãn sau khi tách, không tìm chuỗi con.

| Nhãn trong dữ liệu | Nhãn tiếng Việt |
|---|---|
| Action | Hành động |
| Adventure | Phiêu lưu |
| Animation | Hoạt hình |
| Children | Thiếu nhi |
| Comedy | Hài |
| Crime | Tội phạm |
| Documentary | Tài liệu |
| Drama | Chính kịch |
| Fantasy | Giả tưởng |
| Film-Noir | Phim noir |
| Horror | Kinh dị |
| Musical | Nhạc kịch |
| Mystery | Bí ẩn |
| Romance | Lãng mạn |
| Sci-Fi | Khoa học viễn tưởng |
| Thriller | Giật gân |
| War | Chiến tranh |
| Western | Cao bồi |

Dữ liệu hiện tại còn có `IMAX` và `(no genres listed)`. Không đưa hai nhãn này vào lựa chọn thể loại chính: IMAX là định dạng trình chiếu; phim thiếu thể loại không thể khớp sở thích thể loại. Không mặc định coi nhãn “Thiếu nhi” là chứng nhận độ tuổi.

## 5. Cách gợi ý khi người dùng chỉ nhập thể loại

### 5.1. Phương án cho bản đầu

Dùng **lọc theo thể loại và xếp hạng theo điểm cộng đồng có điều chỉnh số lượt đánh giá**. Phương án này hoạt động với người dùng mới chưa có lịch sử chấm điểm.

Model ALS hiện có học từ lịch sử rating của người dùng MovieLens. Việc chọn “Hành động” không tạo ra vector người dùng ALS; không gán ngẫu nhiên một User ID để tạo cảm giác đã cá nhân hóa.

Quy trình xử lý:

1. Chuẩn hóa các thể loại đã chọn thành nhãn MovieLens.
2. Lọc mọi phim có ít nhất một thể loại phù hợp. Phim chưa có rating vẫn thuộc kết quả nếu thể loại khớp.
3. Đếm số thể loại khớp với lựa chọn của người dùng.
4. Xếp hạng ưu tiên số thể loại khớp, sau đó điểm có điều chỉnh, rồi số lượt đánh giá; dùng `movieId` để quyết định khi các tiêu chí bằng nhau.
5. Giữ toàn bộ danh sách đã xếp hạng, chia 24 phim mỗi trang. Chỉ tải poster cho trang đang hiển thị; đổi trang không làm thay đổi tổng số kết quả.

Không tự thêm phim sai thể loại. Trong nhóm phim có cùng số thể loại khớp, phim chưa có rating được xếp sau phim có điểm và hiển thị “Chưa có đánh giá”, không hiển thị điểm 0/5 hay `NaN`. Chọn thể loại mới đưa danh sách về trang 1.

### 5.2. Tránh phim có một lượt chấm 5 sao đứng đầu

Điểm xếp hạng đề xuất:

```text
weighted_score = (v × R + m × C) / (v + m)

R = điểm trung bình của phim
v = số rating của phim
C = trung bình tất cả rating trong tập thống kê đang dùng
m = mức điều chỉnh, đề xuất ban đầu là 100
```

`m=100` là cấu hình khởi đầu cần kiểm chứng, không phải kết quả tối ưu đã đo. Nó điều chỉnh mức tin cậy, không có nghĩa phải loại mọi phim dưới 100 lượt chấm.

Ví dụ minh họa khi `C=3,5`: phim có 1 lượt chấm 5 sao nhận điểm xếp hạng khoảng 3,515; phim có 20.000 lượt và trung bình 4,2 nhận khoảng 4,197. Cách này hạn chế một phim quá ít dữ liệu đứng đầu chỉ vì có trung bình cao.

Trên thẻ vẫn hiển thị **điểm trung bình gốc `R` và số lượt `v`**. `weighted_score` chỉ phục vụ thứ tự danh sách, không gắn nhãn là điểm chấm của cộng đồng.

### 5.3. Vai trò của ALS và đánh giá chất lượng

Không cần train lại ALS để làm tính năng chọn thể loại, poster và điểm cộng đồng. Phần ALS đã train vẫn là một thành phần nghiên cứu của đề tài. Có thể bổ sung cá nhân hóa sau khi người dùng có lịch sử đánh giá; khi đó cần thiết kế cách tạo hoặc cập nhật vector người dùng và đánh giá riêng.

Các chỉ số Top-K của model ALS hiện tại vẫn rất thấp. Không dùng RMSE của ALS để chứng minh chất lượng của luồng gợi ý theo thể loại mới.

Khi đo offline: thống kê điểm và độ phổ biến từ **train**, thử quy tắc trên **validation**, chọn quy tắc trước khi xem **test**. Sở thích giả lập của người dùng phải lấy từ lịch sử có trước tập đánh giá, không suy ra từ phim trong test. Sau khi chốt, có thể xây catalog phục vụ demo từ **train + validation** và ghi nguồn rõ ràng.

Đánh giá tính đúng của bộ lọc, độ phủ poster và trải nghiệm sử dụng riêng với các chỉ số đo khả năng dự đoán sở thích.

## 6. Lấy poster từ TMDB

### 6.1. Nối đúng bộ phim

```text
movies.movieId
    → links.movieId
    → links.tmdbId
    → TMDB movie details
    → poster_path
    → URL ảnh poster
```

Không dùng `movieId` của MovieLens làm ID TMDB. Cột `tmdbId` cần kiểu số nguyên có thể rỗng; không tạo URL có ID dạng `862.0`. Nếu ID TMDB cũ không còn hợp lệ nhưng `imdbId` có trong `links.csv`, tra cứu bản ghi TMDB theo IMDb ID chính xác. Nếu vẫn không tìm được, dùng ảnh thay thế; không đoán poster bằng tên tương tự.

TMDB có endpoint lấy chi tiết phim theo ID và hỗ trợ tham số ngôn ngữ. Yêu cầu lấy chi tiết có dạng sau, trong đó `{tmdbId}` là ID từ bảng liên kết. [TMDB Movie Details](https://developer.themoviedb.org/reference/movie-details).

```http
GET https://api.themoviedb.org/3/movie/{tmdbId}?language=vi-VN
Authorization: Bearer <TMDB_READ_ACCESS_TOKEN>
```

### 6.2. Cấu hình truy cập và URL ảnh

Người triển khai cần tài khoản TMDB và **API Read Access Token** từ phần thiết lập API. Token được backend gửi qua header `Authorization`; dùng biến môi trường hoặc `.streamlit/secrets.toml`, không đưa token vào mã giao diện hay URL ảnh. [TMDB Application Authentication](https://developer.themoviedb.org/docs/authentication-application).

Ví dụ cấu hình, chỉ dùng giá trị thay thế trong tài liệu:

```toml
# .streamlit/secrets.toml — cần tạo khi triển khai
TMDB_READ_ACCESS_TOKEN = "<TOKEN_CUA_BAN>"
```

File chứa token phải được loại khỏi Git và gói mã nguồn chia sẻ.

URL poster ghép từ địa chỉ gốc ảnh, kích thước và `poster_path`. Đọc cấu hình ảnh qua TMDB `/configuration`; chọn kích thước có hỗ trợ, ví dụ `w500`. Không tự tạo tên file ảnh. [TMDB Image Basics](https://developer.themoviedb.org/docs/image-basics).

### 6.3. Cache và xử lý lỗi

- Chỉ yêu cầu metadata cho các phim sắp hiển thị hoặc một nhóm phim phổ biến chuẩn bị trước; không gọi API cho toàn bộ 87.585 phim mỗi lần mở trang.
- Cache metadata theo `tmdbId` và ngôn ngữ; đề xuất thời hạn ban đầu 7 ngày. Lưu `poster_path`, thời điểm cập nhật và trạng thái tra cứu.
- Đề xuất timeout 5 giây mỗi request, giới hạn số request đồng thời. Hiển thị tên, thể loại và điểm ngay cả khi poster chưa tải xong.
- Với lỗi giới hạn truy cập, tuân theo thời gian chờ nếu API cung cấp và retry có giới hạn; tránh vòng lặp gọi liên tục.
- Khi thiếu token, không có mạng, ID không tồn tại hoặc ảnh lỗi: vẫn trả kết quả phim với khung “Chưa có poster”. Trạng thái thiếu cấu hình được ghi cho người vận hành.
- Thiếu poster không phải lý do loại phim phù hợp khỏi danh sách.

Ảnh thay thế giúp ứng dụng hoạt động khi có lỗi, nhưng để hoàn thành yêu cầu “có hình ảnh phim”, bản trình diễn cần token hoạt động và kiểm tra poster thật trên các phim có ảnh từ TMDB.

Trong phần **“Giới thiệu / Nguồn dữ liệu”**, ghi nguồn MovieLens và TMDB. Khi dùng TMDB, thêm logo được phê duyệt và thông báo: “This product uses the TMDB API but is not endorsed or certified by TMDB.” [Yêu cầu ghi nguồn của TMDB](https://developer.themoviedb.org/docs/faq).

## 7. Kiến trúc phù hợp với dự án hiện tại

Spark xử lý dữ liệu rating ở bước chuẩn bị. FastAPI đọc catalog đã tổng hợp, lọc/xếp hạng và gọi TMDB qua cache; React/TypeScript hiển thị giao diện CINE32. Bản Streamlit cũ nằm trong `app.py` để đối chiếu.

```text
Chuẩn bị dữ liệu:
    Các tập rating phù hợp → Spark thống kê điểm/số lượt theo movieId
    movies + links + thống kê → movie_catalog.parquet

Khi người dùng sử dụng:
    React: tìm tên/chọn thể loại → FastAPI: lọc và xếp hạng catalog → chia trang
                                                        ↓
                                              Cache metadata / TMDB
                                                        ↓
                                    React: thẻ poster, điểm, hộp chi tiết
```

Không đọc lại hoặc tổng hợp 32 triệu rating mỗi lần người dùng chọn thể loại. Cũng không khởi động Spark để phục vụ từng lượt tìm phim. Các truy vấn giao diện chỉ cần catalog theo phim đã tổng hợp.

### 7.1. Catalog cần xuất

| Trường | Nội dung |
|---|---|
| `movieId` | Khóa phim MovieLens, duy nhất trong catalog |
| `title` | Tên phim |
| `year` | Năm phát hành, có thể rỗng |
| `genres` | Danh sách nhãn thể loại đã tách |
| `avg_rating` | Trung bình rating; rỗng nếu chưa có rating trong tập thống kê |
| `rating_count` | Số rating của phim |
| `weighted_score` | Điểm dùng xếp hạng |
| `tmdbId` | ID TMDB, có thể rỗng |
| `imdbId` | ID IMDb, có thể rỗng; hỗ trợ tìm poster khi ID TMDB cũ không còn hợp lệ |

Metadata poster được cache riêng để không phải tổng hợp rating khi một URL ảnh thay đổi. Cần thêm manifest ghi tập dữ liệu dùng thống kê, số dòng, thời điểm tạo và tham số `m`.

### 7.2. File của ứng dụng

| File | Công việc |
|---|---|
| `frontend/src/App.tsx`, `frontend/src/styles.css` | Giao diện, bộ lọc thể loại, tìm tên, phân trang, thẻ poster và chi tiết |
| `web_api.py` | API đọc catalog, trả kết quả phân trang, metadata và poster |
| `app.py` | Bản Streamlit cũ để đối chiếu |
| `scripts/07_build_movie_catalog.py` | Dùng Spark tổng hợp rating, nối movies/links và xuất catalog |
| `scripts/08_enrich_catalog_imdb.py` | Bổ sung IMDb ID cho catalog cũ nếu cần |
| `src/recommender/genre_recommender.py` | Chuẩn hóa thể loại, lọc và xếp hạng mọi phim khớp |
| `src/recommender/tmdb_client.py` | Truy vấn metadata, cấu hình ảnh, timeout và xử lý lỗi |
| `src/recommender/poster_cache.py`, `src/recommender/poster_loader.py` | Cache và tải poster nền cho trang đang xem |
| `artifacts/catalog/movie_catalog.parquet` | Catalog dùng cho giao diện |
| `artifacts/catalog/manifest.json` | Nguồn thống kê và cấu hình xếp hạng |
| `assets/poster_placeholder.svg` | Hình thay thế khi không có poster |
| `.streamlit/secrets.toml.example` | Mẫu cấu hình không chứa token thật |
| `requirements-web.txt` | Thư viện Python chỉ cho ứng dụng web |
| `frontend/package.json` | Thư viện React và lệnh build |
| `README.md` | Ghi cách chuẩn bị catalog, cấu hình TMDB và mở ứng dụng |

## 8. Các bước triển khai

| Bước | Công việc chính | Kết quả cần đạt |
|---|---|---|
| 1 | Tạo catalog và manifest từ dữ liệu hiện có | Có điểm trung bình, số lượt, thể loại và ID TMDB cho từng phim |
| 2 | Viết bộ lọc và xếp hạng theo thể loại | Người dùng mới nhận danh sách đúng thể loại, không cần User ID |
| 3 | Tích hợp TMDB, cache và ảnh thay thế | Poster đúng phim, lỗi mạng không làm mất kết quả |
| 4 | Xây giao diện thẻ phim và phần chi tiết | Luồng chọn sở thích → xem phim hoạt động trên máy tính/điện thoại |
| 5 | Kiểm tra dữ liệu, lỗi và hiệu năng; cập nhật README | Có bản demo dùng được và bằng chứng kiểm tra |

Sau khi các bước trên hoàn tất, mở ứng dụng từ thư mục dự án:

Yêu cầu Python 3.11+ và Node.js/npm để build giao diện lần đầu.

```powershell
Set-Location -LiteralPath '<PROJECT_ROOT>'
py -m pip install -r requirements-web.txt
Set-Location frontend
npm install
npm run build
Set-Location ..
py -m uvicorn web_api:app --host 127.0.0.1 --port 8502
```

Mở `http://127.0.0.1:8502/`, chọn một thể loại và kiểm tra danh sách tự hiện. Ô **Trang** giúp đi tới bất kỳ phần nào của danh sách; kết quả gồm toàn bộ phim phù hợp, 24 phim mỗi trang.

## 9. Tiêu chí nghiệm thu

- Người dùng mới mở app, chọn thể loại và thấy kết quả ngay, không phải chọn User ID hoặc bấm nút tìm.
- Chọn “Kinh dị” thì mọi phim trả về đều có nhãn `Horror` trong dữ liệu.
- Khi chọn nhiều thể loại, mọi phim khớp ít nhất một thể loại; thứ tự tuân theo quy tắc đã mô tả.
- Mọi phim có thể loại khớp đều nằm trong danh sách phân trang, kể cả phim chưa có đánh giá. Mỗi phim có tên, thể loại, trạng thái điểm MovieLens, số lượt đánh giá và poster hoặc ảnh thay thế.
- Đối chiếu thủ công một số phim: điểm và số lượt phải khớp phép tổng hợp từ đúng tập dữ liệu ghi trong manifest.
- Điểm thiếu không được hiển thị thành 0/5; không lấy điểm ALS hoặc điểm TMDB thay cho điểm MovieLens.
- Kiểm tra một số poster bằng `tmdbId` và trang chi tiết để bảo đảm ảnh thuộc đúng phim.
- Không chọn thể loại thì hiển thị toàn bộ catalog. Tổng số phim, khoảng phim đang xem và trang hiện tại chính xác; đổi trang không lặp hoặc bỏ sót phim.
- Lỗi token/API, mất mạng hoặc ảnh hỏng không làm ứng dụng dừng. Sau khi cấu hình hợp lệ, các phim có poster phải hiển thị ảnh thật.
- Đổi thể loại đặt lại trang 1 và cập nhật kết quả; cache phải gắn với phiên bản catalog.
- Mục tiêu trải nghiệm: kết quả chữ và điểm hiện trong khoảng 2 giây khi catalog đã nạp trên máy demo. Đo thực tế trước khi xác nhận; thời gian tải poster lần đầu được ghi riêng.
- Bố cục dùng được trên màn hình điện thoại, không tràn ngang; nút và văn bản dễ đọc.

Phạm vi hoàn thành của tài liệu là một ứng dụng giúp người dùng khám phá phim bằng thể loại, poster và đánh giá cộng đồng. Các tính năng tài khoản, lưu lịch sử, người dùng tự chấm điểm, cá nhân hóa ALS và triển khai công khai là các bước mở rộng riêng sau bản đầu.
