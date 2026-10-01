# NỘI DUNG SLIDE THUYẾT TRÌNH, KỊCH BẢN DEMO & CÂU HỎI BẢO VỆ ĐỒ ÁN

Tài liệu này cung cấp nội dung chi tiết cho **11 Slide thuyết trình**, **Kịch bản Demo 5–7 phút**, **Bộ câu hỏi – trả lời bảo vệ đồ án** và **Checklist 7 sản phẩm nộp bài** theo đúng Mục 16 và Mục 18 của hướng dẫn đề tài 15.

---

## PHẦN 1. NỘI DUNG CHI TIẾT 11 SLIDE THUYẾT TRÌNH

### Slide 1: Trang tiêu đề
- **Môn học:** Nhập môn Big Data – Trường Đại học Công Thương TP.HCM (HUIT)
- **Đề tài 15:** Xây dựng Hệ thống Gợi ý Phim sử dụng Apache Spark và Thuật toán ALS trên Bộ dữ liệu MovieLens 32M
- **Thành viên thực hiện:**
  - Sinh viên A (`[Họ tên - MSSV]`)
  - Sinh viên B (`[Họ tên - MSSV]`)
- **Giảng viên hướng dẫn:** `[Họ tên Giảng viên]`

---

### Slide 2: Bài toán, Mục tiêu & Đầu vào / Đầu ra
- **Bối cảnh bài toán:** Hàng chục nghìn bộ phim gây quá tải thông tin; xử lý hơn 32 triệu lượt tương tác đòi hỏi lưu trữ cột nén và tính toán phân tán/song song.
- **Đầu vào:**
  - `ratings.csv` (`32,000,204` lượt chấm điểm từ `0.5` đến `5.0` sao của `200,948` người dùng).
  - `movies.csv` (`87,585` bộ phim kèm nhãn thể loại) & `links.csv` (`imdbId, tmdbId`).
- **Đầu ra:**
  1. Mô hình nhân tố ẩn **Spark MLlib ALS** dự đoán điểm số & xuất danh sách Top-10 phim gợi ý cá nhân hóa.
  2. Ứng dụng web **CINE32** (React/TypeScript + FastAPI + TMDB) giúp khám phá toàn bộ 87,585 phim theo thể loại và điểm cộng đồng có trọng số ($m=100$).

---

### Slide 3: Bộ dữ liệu MovieLens 32M & Đặc trưng Big Data (5V)
- **Quy mô thực tế đã kiểm chứng (`00_check_data.py`):**
  - **Volume:** `32,000,204` ratings (`836.45 MB` CSV), `2,000,072` tags, `200,948` users, `87,585` movies. Ma trận đầy đủ tương đương ~`70.4 GB` RAM nếu lưu dạng dense float32.
  - **Sparsity (Độ thưa):** **99.818%** các ô `(user, movie)` chưa được quan sát.
  - **Phân bố điểm (`rating_distribution.png`):** Trung bình toàn cục `3.55` sao; mức `4.0` sao chiếm cao nhất (`26.15%`), gần 50% lượt đánh giá $\ge 4.0$ sao.
  - **Phân bố thể loại (`top_genres.png`):** Drama (`34,175` phim) và Comedy (`23,124` phim) chiếm tỷ trọng lớn nhất; có `7,080` phim chưa gán thể loại.

---

### Slide 4: Kiến trúc Hệ thống (Batch Spark Pipeline + Online Serving)
- **Tầng Batch Processing (PySpark 3.5.7):**
  - `CSV gốc (ml-32m/)` $\rightarrow$ `ETL Parquet (data/processed/parquet/)` $\rightarrow$ `Chia tập theo thời gian (data/full_interim/)` $\rightarrow$ `Huấn luyện & Tuning ALS (models/)` & `Tổng hợp Catalog (artifacts/catalog/)`.
- **HDFS một máy (bổ sung 01/10/2026):** NameNode + DataNode Hadoop 3.3.4; Spark đọc CSV, ghi/đọc lại 32.000.204 ratings Parquet, checkpoint và tính Top 10 từ vector ALS trên HDFS. Bằng chứng `reports/tables/hdfs_spark_verification.json`. Train/benchmark trước đây dùng filesystem local.
- **Tầng Online Web Application (CINE32):**
  - **Backend FastAPI (`web_api.py`):** Đọc catalog để lọc đa thể loại và Weighted Score; đọc vector ALS + lịch sử để gợi ý theo User ID; tải nền poster/mô tả qua cache SQLite.
  - **Frontend React/TypeScript (`frontend/`):** Giao diện điện ảnh CINE32 trực quan, phân trang 24 phim/trang, tìm kiếm tức thời.

---

### Slide 5: Tiền xử lý Parquet & Chia dữ liệu chống rò rỉ (Anti-Leakage Split)
- **Hiệu quả chuyển đổi CSV $\rightarrow$ Parquet (`01_convert_to_parquet.py`):**
  - `ratings`: giảm từ `836.45 MB` xuống **`209.44 MB`** (**tiết kiệm 74.96%**).
  - `tags`: giảm từ `69.00 MB` xuống **`19.97 MB`** (**tiết kiệm 71.06%**).
- **Chia dữ liệu theo thời gian trong từng người dùng (`03_prepare_splits_local.py`):**
  - Sắp xếp lịch sử của mỗi user theo `(timestamp ASC, movieId ASC)` rồi chia **80% Train – 10% Validation – 10% Test**.
  - Tập Full 32M (`200,948` users): Train = `25,520,897` dòng; Validation = `3,188,339` dòng; Test = `3,290,968` dòng.
  - Ngăn chặn hoàn toàn việc dùng đánh giá ở tương lai để huấn luyện dự đoán quá khứ.

---

### Slide 6: Phương pháp Cơ sở (Baselines) & Nguyên lý Thuật toán ALS
- **Các phương pháp cơ sở (Baselines):**
  - **Global Mean:** Dự đoán mọi đánh giá bằng trung bình toàn cục ($\mu \approx 3.56$).
  - **Item Mean:** Dự đoán bằng điểm trung bình của từng bộ phim.
  - **Weighted Score ($m=100$) & Popularity:** Xếp hạng theo $\frac{vR + mC}{v+m}$ hoặc theo số lượt đánh giá $v$.
- **Thuật toán Spark MLlib ALS (Explicit Feedback):**
  - Phân rã ma trận đánh giá thành hai ma trận nhân tố ẩn $U \in \mathbb{R}^{|U|\times k}$ và $V \in \mathbb{R}^{|I|\times k}$ ($k = 16$).
  - Chỉ tối ưu sai số trên các đánh giá đã quan sát kèm điều chuẩn $L_2$ (`regParam = 0.08`, `nonnegative = True`, `coldStartStrategy = 'drop'`).

---

### Slide 7: Thiết kế Thực nghiệm & Tinh chỉnh Siêu tham số (Tuning)
- **Bước 1 – Chọn `rank` và `regParam` trên tập phát triển (`3.16M` dòng):**
  - Global Mean RMSE = `1.051351` | Item Mean RMSE = `0.968203`.
  - ALS `rank=8, reg=0.08`: `0.847219` | **`rank=16, reg=0.08`: `0.837409`** | `rank=24, reg=0.12`: `0.856976`.
- **Bước 2 – So sánh số vòng lặp `maxIter = 5, 10, 15, 20` trên toàn bộ 32M (`25.52M` Train / `3.19M` Valid):**
  - `maxIter = 5`: Validation RMSE = `0.833791`, MAE = `0.651167`
  - `maxIter = 10`: Validation RMSE = `0.810538`, MAE = `0.624590`
  - `maxIter = 15`: Validation RMSE = `0.803717`, MAE = `0.615847`
  - **`maxIter = 20 (Chọn)`**: **Validation RMSE = `0.800952`**, **MAE = `0.612026`**, Coverage = `99.77%`.

---

### Slide 8: Kết quả Đánh giá Tập Test & Phân tích Chuyên sâu Top-K
- **Kết quả dự đoán điểm trên Tập Test độc lập (`3,290,968` dòng, model fit trên `28.71M` dòng):**
  - **Test RMSE = `0.812898`**, **Test MAE = `0.621380`**, **Coverage = `99.73%`**.
- **Phát hiện quan trọng khi chấm xếp hạng Top-10 (`09_diagnose_topk_and_baseline.py`):**
  - ALS Explicit trên toàn catalog (`77,409` phim) có `Precision@10 ≈ 0.000020` vì **94.98%** phim được đề xuất chỉ có $\le 5$ lượt chấm (trung vị **1.0 lượt chấm 5 sao**, điểm dự đoán vọt lên `5.37–8.55`).
  - **Giải pháp lọc ngưỡng độ tin cậy (`support threshold`):**
    - ALS + Lọc `rating_count >= 100` (`11,330` phim): **`Precision@10 = 0.014670` (tăng 733 lần)**, vượt qua cả Baseline Weighted Score $m=100$ (`0.012310`).
    - ALS + Lọc `rating_count >= 500` (`5,760` phim): **`Precision@10 = 0.021640` (tăng 1,082 lần)**, `Recall@10 = 0.036183`, `NDCG@10 = 0.030951`.

---

### Slide 9: Thực nghiệm Hiệu năng Xử lý Dữ liệu Lớn (`10_benchmark_bigdata.py`)
- **Thí nghiệm 1: Truy vấn tổng hợp 32,000,204 dòng – CSV gốc vs Parquet (`local[4]`, trung vị 3 lần chạy):**
  - CSV (`836.45 MB`): **`19.690` giây** vs Parquet (`209.44 MB`): **`1.642` giây** $\rightarrow$ **Tăng tốc gấp 11.99 lần**.
- **Thí nghiệm 2: Mở rộng số luồng Spark trên tập phát triển (`2.83M` dòng, ALS `rank=16, maxIter=5`):**
  - `local[1]` (1 luồng): `44.123` giây (`1.00x`)
  - `local[2]` (2 luồng): `23.132` giây (**`1.91x`**)
  - `local[4]` (4 luồng): `17.863` giây (**`2.47x`**) — RMSE giữ nguyên tuyệt đối `0.836664`.
- **Thí nghiệm 3: Quy mô Toàn bộ 32M:** Huấn luyện 4 cấu hình grid + fit cuối `28.71M` dòng + chấm Test hoàn tất trong `39` phút `47` giây với cấu hình `50 × 50` blocks, heap `16g`.

---

### Slide 10: Demo Sản phẩm Ứng dụng CINE32 (React/TypeScript + FastAPI)
- **Giải quyết bài toán Cold-Start cho người dùng mới:**
  - Duyệt toàn bộ **`87,585` bộ phim** trong MovieLens 32M theo 18 chip thể loại tiếng Việt.
  - Tự động ưu tiên phim khớp nhiều thể loại đã chọn + xếp hạng theo điểm trọng số Bayes `weighted_score` ($m=100, C=3.546$).
  - Hiển thị trung thực điểm gốc MovieLens và số lượt đánh giá; phim chưa có điểm hiển thị `"Chưa có đánh giá"`.
  - Tải poster, ảnh nền và mô tả tiếng Việt/tiếng Anh từ **TMDB API** (có cơ chế tự động tra cứu qua `imdbId` và lưu cache SQLite cục bộ).

---

### Slide 11: Kết luận, Hạn chế & Hướng phát triển
- **Kết luận:** Hoàn thành trọn vẹn quy trình Big Data từ ETL Parquet, EDA, Temporal Split, huấn luyện ALS trên toàn bộ 32 triệu dòng (`Test RMSE = 0.8129`), chẩn đoán sâu bài toán xếp hạng Top-K và xây dựng ứng dụng web CINE32 hoàn chỉnh.
- **Hạn chế:** Mô hình ALS chạy theo lô (batch), chưa cập nhật tức thời vector người dùng khi có lượt chấm điểm mới trên giao diện web.
- **Hướng phát triển:**
  1. Kết hợp điểm cá nhân hóa ALS với trọng số độ tin cậy $\frac{v}{v+m}$ (Hybrid Ranking).
  2. Bổ sung cơ chế Fold-in cập nhật nhanh vector người dùng mới ngay khi người dùng chọn 5 bộ phim yêu thích.
  3. Triển khai trên cụm Spark/HDFS đa máy vật lý.

---

## PHẦN 2. KỊCH BẢN DEMO TRỰC TIẾP (5 – 7 PHÚT)

### Bước chuẩn bị trước khi lên trình bày (2 phút trước giờ G)
Mở sẵn một cửa sổ PowerShell tại thư mục gốc `d:\Học tập\bigdata` và chạy:
```powershell
py -m uvicorn web_api:app --host 127.0.0.1 --port 8502
```
Mở sẵn trình duyệt tại `http://127.0.0.1:8502/` và `http://127.0.0.1:8502/docs`.

Chuẩn bị HDFS trong terminal riêng: `py scripts/11_hdfs_local.py start --foreground`. Kiểm tra bằng `py scripts/11_hdfs_local.py status`; mở `http://127.0.0.1:9870/`. Nếu chưa có artifact ALS, chạy `py scripts/12_prepare_als_serving.py` trước khi mở web. Chạy `py scripts/13_verify_hdfs_spark.py` trước buổi bảo vệ để tạo bằng chứng HDFS; không cần train lại model trong buổi demo.

### Luồng thuyết trình Demo (6 phút)
1. **Phút 1 – Chứng minh HDFS và quy mô dữ liệu:**
   - Mở NameNode UI, chỉ 1 DataNode hoạt động và `/movielens/raw/ratings.csv`. Mở `reports/tables/hdfs_spark_verification.json`: Spark đọc/ghi lại đủ 32.000.204 dòng Parquet, checkpoint và Top 10 ALS trên HDFS. Nêu rõ đây là HDFS một máy, Spark `local[4]`.
   - Chỉ rõ: Mô hình đã học trên **28,709,236** lượt đánh giá (`Train + Validation`), chấm trên **3,290,968** lượt đánh giá Test độc lập đạt `RMSE = 0.812898`, và Parquet giúp truy vấn 32 triệu dòng chỉ mất **1.64 giây** (nhanh gấp 12 lần CSV).
2. **Phút 2–3 – Trải nghiệm khám phá phim trên giao diện CINE32 (`http://127.0.0.1:8502/`):**
   - Giới thiệu màn hình chính CINE32: tổng cộng **87,585 bộ phim** và **28.7 triệu lượt đánh giá** được tổng hợp sẵn bằng Spark.
   - Bấm chọn chip thể loại **Hành động** $\rightarrow$ Danh sách cập nhật tức thời mà không cần bấm nút tìm kiếm.
   - Chọn kết hợp thêm **Khoa học viễn tưởng** và **Phiêu lưu** $\rightarrow$ Giải thích quy tắc: các bộ phim khớp cả 3 thể loại được xếp lên đầu, sắp xếp theo `weighted_score` ($m=100$) để những kiệt tác có hàng chục nghìn lượt chấm đứng trên các phim chỉ có 1 lượt chấm 5 sao.
3. **Phút 4 – Kiểm tra tìm kiếm, phân trang và hộp chi tiết phim (Modal):**
   - Nhập từ khóa `"Inception"` hoặc `"Toy Story"` vào ô tìm kiếm $\rightarrow$ Mở hộp chi tiết phim để xem Poster/Backdrop từ TMDB, điểm trung bình cộng đồng MovieLens, tổng số lượt đánh giá, năm phát hành, nhãn thể loại đầy đủ và liên kết trực tiếp sang IMDb/TMDB.
   - Nhập một số trang ở cuối danh sách để chứng minh cả các bộ phim chưa có lượt đánh giá vẫn được giữ đầy đủ với nhãn `"Chưa có đánh giá"` (không hiển thị điểm `0/5` sai lệch).
4. **Phút 5–6 – Demo ALS theo User ID:**
   - Chọn **Gợi ý ALS**, nhập User `1`, xem Top 10, mở lịch sử để giải thích loại phim đã chấm. Đổi User `2` để chứng minh kết quả cá nhân hóa. Chọn **Người dùng mới** để xem Weighted Score và thông báo fallback.
   - Mở chi tiết phim, phân biệt điểm ALS với điểm trung bình cộng đồng. Điểm ALS là tích vô hướng, có thể lớn hơn 5; không sửa thành điểm cộng đồng.
   - Giải thích tập ứng viên có ít nhất 100 lượt chấm, liên hệ phép so sánh 10.000 user: `Precision@10` từ `0.000020` lên `0.014670`. Serving loại cả lịch sử test đã biết; độ đo offline vẫn giữ test độc lập và quy tắc loại lịch sử tập fit.

---

## PHẦN 3. BỘ CÂU HỎI & TRẢ LỜI BẢO VỆ ĐỒ ÁN (9 CÂU HỎI TRỌNG TÂM)

1. **Tại sao nhóm chọn Apache Spark và định dạng Parquet cho quy mô MovieLens 32M?**
   - *Trả lời:* Với 32,000,204 dòng (`836.45 MB` CSV), nếu dựng ma trận đầy đủ `200,948 × 87,585` sẽ tốn hơn `70 GB` RAM. Spark kết hợp Parquet cho phép lưu trữ dạng bảng thưa chỉ `209.44 MB` (giảm 74.96% dung lượng), đọc chọn lọc đúng các cột cần thiết và thực thi song song trên nhiều luồng. Thực nghiệm của nhóm chứng minh Parquet rút ngắn thời gian gom nhóm 32 triệu dòng từ `19.69 giây` xuống `1.64 giây` (**nhanh gấp 11.99 lần**).

2. **Chạy Spark `local[4]` trên một máy khác với cụm nhiều máy (cluster) ở điểm nào?**
   - *Trả lời:* `local[4]` khởi tạo các luồng thực thi (executor threads) bên trong cùng một tiến trình JVM trên một máy vật lý, giúp tận dụng đa nhân CPU (nhóm đo được mức tăng tốc **2.47 lần** so với `local[1]`), nhưng dùng chung bộ nhớ RAM và ổ cứng cục bộ. Trong khi đó, cụm nhiều máy phân tán dữ liệu và tác vụ qua mạng nội bộ tới nhiều worker độc lập, cho phép mở rộng bộ nhớ và băng thông đọc/ghi vượt giới hạn của một máy đơn.

3. **Vì sao nhóm chọn ALS Explicit (`implicitPrefs=False`) và tuyệt đối không điền các ô chưa đánh giá bằng 0?**
   - *Trả lời:* MovieLens 32M chứa điểm đánh giá tường minh từ `0.5` đến `5.0` sao. Việc một người dùng chưa chấm điểm một bộ phim chỉ có nghĩa là họ chưa xem hoặc chưa đánh giá, chứ không phải họ ghét bộ phim đó (0 sao). Nếu điền 0 vào 99.82% ô trống, thứ nhất ma trận sẽ biến thành ma trận dày đặc 17.6 tỷ phần tử gây tràn bộ nhớ, thứ hai hàm mục tiêu sẽ bị kéo lệch hoàn toàn về 0.

4. **Cách chia dữ liệu của nhóm ngăn chặn rò rỉ thông tin tương lai (data leakage) như thế nào?**
   - *Trả lời:* Nhóm không chia ngẫu nhiên mà sắp xếp lịch sử đánh giá của từng người dùng theo thứ tự thời gian `(timestamp ASC, movieId ASC)`, lấy 80% đầu làm Train, 10% tiếp theo làm Validation và 10% mới nhất làm Test. Khi đánh giá mô hình trên Validation chỉ loại trừ lịch sử Train; khi đánh giá trên Test chỉ loại trừ lịch sử `Train + Validation`.

5. **Tham số `coldStartStrategy='drop'` trong Spark ALS có tác dụng gì và đã loại bỏ bao nhiêu dữ liệu?**
   - *Trả lời:* Khi chấm điểm trên Validation hoặc Test, nếu gặp một `movieId` mới chỉ xuất hiện ở giai đoạn cuối mà chưa từng xuất hiện trong tập huấn luyện, mô hình ALS sẽ không có vector nhân tố cho phim đó và trả về `NaN`. Đặt `coldStartStrategy='drop'` giúp bỏ qua các dòng `NaN` để tính RMSE/MAE chính xác, đồng thời nhóm báo cáo kèm độ phủ (**Coverage = 99.77%** trên Validation và **99.73%** trên Test, tức chỉ bỏ qua `0.27%` dòng).

6. **Vì sao RMSE giảm tốt (`0.8129`) nhưng `Precision@10` của ALS trên toàn bộ catalog lại gần bằng 0? Nhóm đã xử lý thế nào?**
   - *Trả lời:* Nhóm đã viết script chẩn đoán `09_diagnose_topk_and_baseline.py` và phát hiện: trong 77,409 phim của tập huấn luyện, các bộ phim cực hiếm chỉ có 1–2 lượt chấm 5.0 sao có vector nhân tố tạo ra điểm dự đoán vọt lên `5.37 – 8.55` sao, chiếm tới **94.98%** danh sách Top-10 ứng viên (trung vị số lượt chấm của phim được đề xuất là `1.0`). Khi nhóm lọc tập ứng viên chỉ giữ các phim có `rating_count >= 100` (11,330 phim) hoặc `>= 500` (5,760 phim), `Precision@10` tăng gấp **733 đến 1,082 lần** (`0.01467` và `0.02164`), vượt qua cả bảng xếp hạng điểm trọng số tĩnh ($m=100$).

7. **Tại sao ứng dụng CINE32 dùng công thức `weighted_score` ($m=100$) khi người dùng lọc theo thể loại thay vì dùng điểm trung bình cộng đơn thuần?**
   - *Trả lời:* Nếu xếp theo điểm trung bình cộng đơn thuần $R$, hàng trăm bộ phim chỉ có đúng 1 người chấm 5.0 sao sẽ luôn đứng đầu mọi thể loại. Công thức trọng số Bayes $\frac{vR + mC}{v+m}$ với $m=100, C=3.546$ kéo các phim ít lượt đánh giá về gần mức trung bình toàn cục $C$, chỉ những bộ phim vừa có điểm cao vừa có hàng nghìn lượt đánh giá xác thực mới đứng đầu danh sách.

8. **Nếu một người dùng mới vào ứng dụng CINE32 hoặc vừa chấm điểm một phim mới, hệ thống xử lý ra sao?**
   - *Trả lời:* Với người dùng mới chưa có `userId` trong tập huấn luyện, CINE32 phục vụ ngay lập tức bằng luồng lọc đa thể loại kết hợp xếp hạng `weighted_score` trên catalog đã tổng hợp sẵn. Nếu người dùng phát sinh đánh giá mới, trong kiến trúc hiện tại dữ liệu sẽ được đưa vào đợt huấn luyện lại theo lô (batch retraining) định kỳ, hoặc mở rộng bằng kỹ thuật fold-in giải phương trình bình phương tối tiểu với ma trận phim $V$ cố định.

9. **Làm sao ứng dụng đảm bảo tốc độ phản hồi nhanh (< 50ms) và không bị lỗi khi mạng hoặc TMDB gặp sự cố?**
   - *Trả lời:* Toàn bộ 28.7 triệu đánh giá đã được Spark tổng hợp trước thành tệp `movie_catalog.parquet` chỉ nặng `4.57 MB`. FastAPI nạp tệp này vào RAM và chỉ truy vấn poster TMDB cho đúng **24 bộ phim của trang đang hiển thị**, kết hợp bộ nhớ đệm SQLite (`tmdb_cache.db`) và cơ chế tự động fallback sang `imdbId` hoặc ảnh vector thay thế (`poster_placeholder.svg`) khi thiếu mạng/token.

---

## PHẦN 4. CHECKLIST 7 SẢN PHẨM NỘP BÀI (MỤC 18.2)

- [x] **1. Mã nguồn đầy đủ:** `scripts/00..13`, `src/recommender/`, `web_api.py`, `frontend/`, `app.py`, `tests/`.
- [x] **2. Dữ liệu hoặc liên kết dataset:** Liên kết tải MovieLens 32M chuẩn của GroupLens và script kiểm tra MD5 `scripts/00_check_data.py`.
- [ ] **3. Báo cáo Word:** Có bản thảo Markdown; cần xuất Word, điền thông tin nhóm và kiểm tra định dạng.
- [ ] **4. Slide thuyết trình:** Có nội dung Markdown; cần xuất PPT và diễn tập.
- [x] **5. Demo sản phẩm:** CINE32 có khám phá thể loại và ALS theo User ID; HDFS có bằng chứng Spark đọc/ghi 32M. `app.py` là bản khám phá thể loại cũ.
- [x] **6. Hướng dẫn cài đặt và chạy:** Tài liệu [README.md](../README.md) và [HUONG_DAN_TRAIN_ALS_MOVIELENS_32M.md](../HUONG_DAN_TRAIN_ALS_MOVIELENS_32M.md).
- [ ] **7. Bảng phân công và đóng góp:** Có mẫu trong báo cáo; cần điền tên/MSSV và xác nhận tỷ lệ thực tế.
