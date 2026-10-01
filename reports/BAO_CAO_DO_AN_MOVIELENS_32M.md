# BÁO CÁO ĐỒ ÁN MÔN HỌC: NHẬP MÔN BIG DATA (ĐỀ TÀI 15)

---

## PHẦN 1. TRANG BÌA

- **TRƯỜNG:** ĐẠI HỌC CÔNG THƯƠNG TP. HỒ CHÍ MINH (HUIT)
- **KHOA:** CÔNG NGHỆ THÔNG TIN
- **MÔN HỌC:** NHẬP MÔN BIG DATA
- **ĐỀ TÀI SỐ 15:** XÂY DỰNG HỆ THỐNG GỢI Ý PHIM SỬ DỤNG APACHE SPARK VÀ THUẬT TOÁN ALS TRÊN BỘ DỮ LIỆU MOVIELENS 32M
- **GIẢNG VIÊN HƯỚNG DẪN:** `[Điền tên Giảng viên]`
- **NHÓM THỰC HIỆN:** Nhóm `[Điền số nhóm]`
  1. Sinh viên 1: `[Họ và tên SV A]` — MSSV: `[Điền MSSV]` — Lớp: `[Điền lớp]`
  2. Sinh viên 2: `[Họ và tên SV B]` — MSSV: `[Điền MSSV]` — Lớp: `[Điền lớp]`
- **THỜI GIAN THỰC HIỆN:** Tháng 09/2026

---

## PHẦN 2. LỊCH LÀM VIỆC NHÓM

| Tuần | Nội dung công việc | Trạng thái | Đầu ra đạt được |
| --- | --- | --- | --- |
| **Tuần 1** | Xác định bài toán, chuẩn bị môi trường Python/Spark, tải bộ dữ liệu MovieLens 32M và kiểm tra toàn vẹn dữ liệu | Đã hoàn thành | Script `scripts/00_check_data.py`, xác nhận đủ 4 tệp CSV (`32,000,204` ratings, `87,585` movies) khớp MD5 |
| **Tuần 2** | Xây dựng quy trình ETL chuyển đổi CSV sang định dạng cột Parquet, kiểm tra schema và tối ưu dung lượng | Đã hoàn thành | Script `scripts/01_convert_to_parquet.py`, thư mục `data/processed/parquet/` giảm 74.96% dung lượng `ratings` |
| **Tuần 3** | Khảo sát dữ liệu (EDA), trực quan hóa phân bố và chia tập `train`/`valid`/`test` theo thời gian trong từng user | Đã hoàn thành | Script `02_eda_local.py`, `03_prepare_splits_local.py`, biểu đồ trong `reports/figures/`, split sample & full |
| **Tuần 4** | Xây dựng mô hình cơ sở (Global Mean, Item Mean, Popularity) và huấn luyện ALS đầu tiên trên tập phát triển | Đã hoàn thành | Script `scripts/04_train_als_spark.py`, kết quả `models/als_dev/metrics.json` & `baseline_metrics.json` |
| **Tuần 5** | Tinh chỉnh siêu tham số (Hyperparameter Tuning) trên tập phát triển và mở rộng chạy grid 5–20 vòng lặp trên toàn bộ 32M | Đã hoàn thành | Script `scripts/05_tune_evaluate_spark.py`, bảng `als_tuning.csv`, chọn `rank=16, regParam=0.08, maxIter=20` |
| **Tuần 6** | Đánh giá tập Test độc lập, chẩn đoán độ đo Top-K, tổng hợp catalog 87,585 phim và xây dựng ứng dụng web CINE32 (React + FastAPI) | Đã hoàn thành | `models/als_full_iter_20260922_120859/`, `scripts/06–09`, `web_api.py`, `frontend/` |
| **Tuần 7** | Thực nghiệm hiệu năng Big Data (CSV vs Parquet, Spark multi-threading), hoàn thiện bản thảo báo cáo Word và Slide | Đã hoàn thành | Script `scripts/10_benchmark_bigdata.py`, `reports/tables/bigdata_benchmarks.md`, Báo cáo & Slide |
| **Tuần 8** | Rà soát 7 sản phẩm, kiểm tra trên máy thứ hai và diễn tập bảo vệ | Chưa xác nhận hoàn tất | Có bản thảo Markdown; còn xuất Word/PPT, điền thông tin nhóm, kiểm tra chéo và diễn tập |

---

## PHẦN 3. CÔNG VIỆC CỦA TỪNG THÀNH VIÊN

Bảng dưới đây là mẫu phân công; cần thay tên/MSSV, xác nhận công việc và tỷ lệ đóng góp thực tế trước khi nộp.

| Thành viên | Công việc cụ thể | Tệp mã nguồn / Bằng chứng thực nghiệm | Mức độ đóng góp |
| --- | --- | --- | --- |
| **Sinh viên A** | - Thiết lập môi trường PySpark, viết quy trình kiểm tra dữ liệu & ETL CSV sang Parquet.<br/>- Thực hiện thống kê EDA, xuất biểu đồ phân bố và đo hiệu năng Big Data (CSV vs Parquet, Spark `local[1..4]`).<br/>- Tổng hợp catalog 87,585 phim (`weighted_score`), tích hợp TMDB API & xây dựng giao diện web **CINE32** (React/TypeScript + FastAPI).<br/>- Viết các mục Giới thiệu, Dữ liệu, Kiến trúc, EDA, Hiệu năng và Giao diện trong báo cáo. | - `scripts/00_check_data.py`, `scripts/01_convert_to_parquet.py`<br/>- `scripts/02_eda_local.py`, `scripts/10_benchmark_bigdata.py`<br/>- `scripts/07_build_movie_catalog.py`, `scripts/08_enrich_catalog_imdb.py`<br/>- `web_api.py`, `frontend/`, `src/recommender/`<br/>- `reports/figures/*.png`, `reports/tables/bigdata_benchmarks.md` | 50% |
| **Sinh viên B** | - Thiết kế quy trình chia dữ liệu `train`/`valid`/`test` theo thứ tự thời gian trong từng user (chống data leakage).<br/>- Xây dựng các mô hình Baseline (Global Mean, Item Mean, Popularity) và huấn luyện/tuning Spark MLlib ALS trên tập phát triển & tập full 32M.<br/>- Chẩn đoán độ đo xếp hạng Top-K (`Precision@10`, `Recall@10`, `NDCG@10`), phân tích bias của ALS Explicit và xuất dữ liệu demo.<br/>- Viết các mục Cơ sở lý thuyết, Chia dữ liệu, Mô hình ALS, Đánh giá thực nghiệm và Kết luận. | - `scripts/03_prepare_splits_local.py`<br/>- `scripts/04_train_als_spark.py`, `scripts/05_tune_evaluate_spark.py`<br/>- `scripts/06_export_demo.py`, `scripts/09_diagnose_topk_and_baseline.py`<br/>- `models/als_full_iter_20260922_120859/metrics.json`<br/>- `reports/tables/topk_comparison.csv`, `README.md` | 50% |

---

## PHẦN 4. MỤC LỤC

1. Trang bìa
2. Lịch làm việc nhóm
3. Công việc của từng thành viên
4. Mục lục
5. Giới thiệu đề tài
6. Cơ sở lý thuyết
7. Xây dựng ứng dụng và xử lý trực quan hóa dữ liệu
8. Kết luận và định hướng phát triển
9. Tài liệu tham khảo
10. Phụ lục

---

## PHẦN 5. GIỚI THIỆU ĐỀ TÀI

### 5.1. Bối cảnh và lý do chọn đề tài
Trong kỷ nguyên số, các nền tảng phát trực tuyến và cơ sở dữ liệu điện ảnh sở hữu hàng chục nghìn bộ phim, gây ra tình trạng quá tải thông tin (information overload) cho người xem. Hệ thống gợi ý (Recommender System) đóng vai trò cốt lõi giúp lọc và cá nhân hóa danh mục phim phù hợp với sở thích của từng người dùng. Tuy nhiên, khi quy mô dữ liệu lên tới hàng chục triệu lượt tương tác (như bộ dữ liệu **MovieLens 32M** với hơn 32 triệu lượt chấm điểm), các phương pháp xử lý ma trận truyền thống trên một luồng bộ nhớ đơn lẻ trở nên bất khả thi do bùng nổ bộ nhớ và thời gian tính toán. Việc ứng dụng công nghệ xử lý dữ liệu lớn **Apache Spark** kết hợp định dạng lưu trữ cột **Apache Parquet** và thuật toán phân rã ma trận **ALS (Alternating Least Squares)** là giải pháp thiết thực để giải quyết bài toán này.

### 5.2. Mục tiêu và phạm vi đề tài
- **Mục tiêu:**
  1. Xây dựng đường ống xử lý dữ liệu lớn (ETL, làm sạch, chuyển đổi sang Parquet, chia tập theo thời gian) cho toàn bộ 32,000,204 lượt đánh giá của MovieLens 32M bằng PySpark.
  2. Huấn luyện, tinh chỉnh siêu tham số và đánh giá mô hình lọc cộng tác **Spark MLlib ALS** so với các phương pháp cơ sở (Global Mean, Item Mean, Popularity, Weighted Score) trên cả bài toán dự đoán điểm số (RMSE, MAE) và bài toán xếp hạng Top-K (`Precision@10`, `Recall@10`, `NDCG@10`).
  3. Xây dựng ứng dụng web thực tế **CINE32** (React/TypeScript + FastAPI) kết hợp dữ liệu cộng đồng MovieLens 32M và hình ảnh poster từ TMDB, giúp cả người dùng mới (cold-start) khám phá phim theo thể loại yêu thích một cách tức thời.
- **Đầu vào:** Lịch sử đánh giá `(userId, movieId, rating, timestamp)`, danh mục phim `(movieId, title, genres)` và bảng ánh xạ định danh ngoài `(movieId, imdbId, tmdbId)`.
- **Đầu ra:**
  - Mô hình nhân tố ẩn người dùng và phim (`user_factors.parquet`, `item_factors.parquet`) cùng danh sách Top-10 phim gợi ý cho từng người dùng đã loại trừ lịch sử đã xem.
  - Ứng dụng web CINE32 tra cứu, lọc đa thể loại và xếp hạng toàn bộ 87,585 bộ phim theo điểm trọng số Bayes ($m=100$).

---

## PHẦN 6. CƠ SỞ LÝ THUYẾT

### 6.1. Đặc trưng 5V của Big Data trên bộ dữ liệu MovieLens 32M
- **Volume (Khối lượng):** Bộ dữ liệu chứa **32,000,204** lượt đánh giá, **2,000,072** lượt gắn nhãn (tags), **200,948** người dùng và **87,585** bộ phim. Nếu biểu diễn dưới dạng ma trận dày đặc (dense matrix) `200,948 × 87,585` kiểu số thực 4 byte (`float32`), ma trận sẽ chiếm khoảng $1.76 \times 10^{10} \times 4 \approx 70.4\text{ GB}$ RAM — vượt quá bộ nhớ của máy tính cá nhân.
- **Variety (Đa dạng):** Kết hợp dữ liệu số định lượng (`rating`), thời gian (`timestamp` UTC), văn bản đa ngôn ngữ (`title`, `tag`), danh sách thể loại phân tách bằng ký tự `|` (`genres`) và định danh liên kết ngoài (`imdbId`, `tmdbId`).
- **Velocity (Tốc độ):** Trong thực nghiệm đồ án, dữ liệu được xử lý theo lô (batch processing) cho giai đoạn huấn luyện Spark và phục vụ truy vấn độ trễ thấp (< 50 ms) ở tầng ứng dụng web thông qua catalog đã tổng hợp trước.
- **Veracity (Độ tin cậy):** Dữ liệu đánh giá tự nguyện có độ thưa rất cao (**Sparsity = 99.818%**) và chịu ảnh hưởng mạnh của thiên lệch phổ biến (popularity bias) cũng như nhiễu từ các phim chỉ có 1–2 lượt chấm điểm tuyệt đối.
- **Value (Giá trị):** Khai phá mẫu sở thích tiềm ẩn từ 32 triệu tương tác để đưa ra gợi ý phim chính xác và hỗ trợ khám phá danh mục điện ảnh.

### 6.2. Lưu trữ cột Apache Parquet và xử lý phân tán với Apache Spark
- **Định dạng Apache Parquet:** Khác với CSV lưu trữ theo dòng (row-oriented) tốn dung lượng văn bản và buộc phải quét toàn bộ các cột trên đĩa, Parquet lưu trữ theo cột (columnar storage), nén dữ liệu cùng kiểu hiệu quả (dictionary encoding, run-length encoding, Snappy) và cho phép Spark thực hiện **Column Projection** (chỉ đọc đúng cột `userId, movieId, rating` khi huấn luyện ALS) cũng như **Predicate Pushdown**.
- **Apache Spark DataFrame & Catalyst Optimizer:** Spark chia dữ liệu thành các phân vùng (partitions) xử lý song song trên các luồng CPU. Các phép biến đổi (Transformations như `select`, `filter`, `join`, `repartition`) được thực thi lười (lazy evaluation) và chỉ kích hoạt tính toán vật lý khi gặp hành động (Actions như `count`, `collect`, `write`).

### 6.3. Lọc cộng tác phân rã ma trận và thuật toán ALS (Alternating Least Squares)
- Trong mô hình nhân tố ẩn (Latent Factor Model), ma trận đánh giá thưa $R \in \mathbb{R}^{|U| \times |I|}$ được xấp xỉ bởi tích của hai ma trận hạng thấp ($k \ll \min(|U|, |I|)$): ma trận người dùng $U \in \mathbb{R}^{|U| \times k}$ và ma trận phim $V \in \mathbb{R}^{|I| \times k}$ sao cho điểm dự đoán của người dùng $u$ cho phim $i$ là:
  $$\hat{r}_{u,i} = \mathbf{u}_u^T \mathbf{v}_i$$
- Hàm mục tiêu của **Explicit ALS** có điều chuẩn $L_2$ (weighted-$\lambda$-regularization trong Spark MLlib) chỉ tính tổng sai số trên tập các cặp $(u, i) \in \Omega$ **đã được quan sát** (không điền các ô trống bằng 0):
  $$\min_{U, V} \sum_{(u,i) \in \Omega} \left(r_{u,i} - \mathbf{u}_u^T \mathbf{v}_i\right)^2 + \lambda \left( \sum_u n_{u} \|\mathbf{u}_u\|_2^2 + \sum_i n_{i} \|\mathbf{v}_i\|_2^2 \right)$$
  trong đó $\lambda$ là hệ số điều chuẩn (`regParam`), $n_u$ và $n_i$ là số lượng đánh giá của người dùng $u$ và phim $i$.
- Vì cả $\mathbf{u}_u$ và $\mathbf{v}_i$ đều chưa biết, hàm mục tiêu không lồi; nhưng khi cố định $V$ để giải $U$ (và ngược lại cố định $U$ để giải $V$), bài toán trở thành bình phương tối tiểu tuyến tính lồi và giải song song độc lập cho từng người dùng / từng bộ phim qua `maxIter` vòng lặp luân phiên.

### 6.4. Vấn đề Cold-Start và Xếp hạng Điểm Trọng số Bayes (Weighted Rating)
- Khi một người dùng mới truy cập hệ thống và chưa có lịch sử đánh giá, mô hình ALS chưa có vector nhân tố $\mathbf{u}_u$ (`coldStartStrategy='drop'`). Để giải quyết bài toán người dùng mới và tránh việc các bộ phim chỉ có 1 lượt chấm 5.0 sao đứng đầu bảng xếp hạng, hệ thống sử dụng công thức điểm trọng số Bayes (tương tự IMDb Top 250):
  $$\text{weighted\_score} = \frac{v \cdot R + m \cdot C}{v + m}$$
  Trong đó:
  - $R$: Điểm trung bình cộng của bộ phim.
  - $v$: Số lượt đánh giá của bộ phim (`rating_count`).
  - $C$: Điểm trung bình toàn cục trên toàn bộ tập huấn luyện ($C = 3.546251$).
  - $m$: Ngưỡng điều chỉnh độ tin cậy ($m = 100$).

### 6.5. Các độ đo đánh giá (Evaluation Metrics)
1. **Độ đo sai số dự đoán điểm số:**
   $$\text{RMSE} = \sqrt{\frac{1}{|\mathcal{T}|} \sum_{(u,i) \in \mathcal{T}} (r_{u,i} - \hat{r}_{u,i})^2}, \qquad \text{MAE} = \frac{1}{|\mathcal{T}|} \sum_{(u,i) \in \mathcal{T}} |r_{u,i} - \hat{r}_{u,i}|$$
2. **Độ đo chất lượng danh sách gợi ý Top-K** (với tập phim liên quan của người dùng $u$ trong tập test là $Rel_u = \{i \in \mathcal{T}_u \mid r_{u,i} \ge 4.0\}$ và danh sách $K=10$ phim gợi ý $Rec_u@K$ đã loại bỏ lịch sử):
   $$\text{Precision@K}(u) = \frac{|Rec_u@K \cap Rel_u|}{K}, \qquad \text{Recall@K}(u) = \frac{|Rec_u@K \cap Rel_u|}{|Rel_u|}$$
   $$\text{DCG@K}(u) = \sum_{r=1}^{K} \frac{\mathbb{I}(rec_{u,r} \in Rel_u)}{\log_2(r + 1)}, \qquad \text{NDCG@K}(u) = \frac{\text{DCG@K}(u)}{\text{IDCG@K}(u)}$$

---

## PHẦN 7. XÂY DỰNG ỨNG DỤNG VÀ XỬ LÝ TRỰC QUAN HÓA DỮ LIỆU

### 7.1. Nguồn dữ liệu và kiểm tra chất lượng ban đầu (ETL & Data Quality)
Bộ dữ liệu **MovieLens 32M** được tải từ GroupLens và kiểm tra bằng script `scripts/00_check_data.py`. Toàn bộ 4 tệp CSV gốc đều khớp hoàn toàn số dòng và mã băm MD5 công bố:

| Tệp dữ liệu | Số dòng bản ghi | Các cột dữ liệu | Dung lượng CSV (MB) | Dung lượng Parquet (MB) | Mức tiết kiệm |
| --- | ---: | --- | ---: | ---: | ---: |
| `ratings.csv` | 32,000,204 | `userId, movieId, rating, timestamp` | 836.45 | 209.44 | **74.96%** |
| `movies.csv` | 87,585 | `movieId, title, genres` | 4.05 | 2.35 | **41.98%** |
| `tags.csv` | 2,000,072 | `userId, movieId, tag, timestamp` | 69.00 | 19.97 | **71.06%** |
| `links.csv` | 87,585 | `movieId, imdbId, tmdbId` | 1.86 | 1.90 | -2.15% |

- **Kết quả kiểm tra làm sạch:** Không có bản ghi thiếu `userId`, `movieId` hay `rating`; toàn bộ 32,000,204 lượt đánh giá đều nằm trong miền hợp lệ $[0.5, 5.0]$ với bước nhảy $0.5$.
- Trong số `87,585` bộ phim trong `movies.csv`, có `84,432` phim có ít nhất 1 lượt đánh giá trên toàn bộ lịch sử (và `77,409` phim xuất hiện trong tập `train + validation`).

### 7.2. Kiến trúc hệ thống và cấu hình môi trường thực nghiệm
Hệ thống được thiết kế tách biệt thành hai tầng rõ ràng để đảm bảo hiệu năng:
1. **Tầng xử lý dữ liệu lớn & Huấn luyện ngoại tuyến (Offline Batch Pipeline với PySpark):** Chuyển đổi Parquet, chia tập theo thời gian, huấn luyện/tuning mô hình ALS, đánh giá Test và tổng hợp trước `movie_catalog.parquet`.
2. **Tầng phục vụ trực tuyến (FastAPI + React/TypeScript):** Đọc catalog để lọc thể loại/tìm kiếm; đọc vector ALS và chỉ mục lịch sử để gợi ý cá nhân. Poster/mô tả TMDB tải bất đồng bộ qua cache SQLite. Không chạy Spark hoặc train lại cho từng yêu cầu web.

**HDFS đã bổ sung ngày 01/10/2026:** Hadoop 3.3.4 một NameNode và một DataNode trên Windows, Spark `local[4]`. Script `13_verify_hdfs_spark.py` đọc MovieLens CSV trên HDFS, làm sạch và ghi/đọc lại **32.000.204** dòng ratings Parquet, tạo checkpoint, đọc vector ALS từ HDFS và ghi Top 10 cho User 1. Bằng chứng tại `reports/tables/hdfs_spark_verification.json`; hướng dẫn tại `HUONG_DAN_HDFS_VA_DEMO_ALS.md`. Đây là HDFS giả phân tán một máy. Train/tuning và benchmark trước đây chạy với dữ liệu local; không coi đó là kết quả train hay benchmark trên HDFS.

- **Cấu hình phần cứng & phần mềm thực nghiệm:**
  - Hệ điều hành: Windows 10/11 64-bit, RAM hệ thống 32 GB.
  - Ngôn ngữ & Engine: Python 3.13.7, Java 1.8.0_461 (64-bit Server VM), Apache Spark / PySpark 3.5.7, PyArrow, Pandas, FastAPI, React 18 + TypeScript + Vite.
  - Cấu hình Spark cho tập toàn bộ 32M: `master = local[4]`, `spark.driver.memory = 16g`, `spark.driver.memoryOverhead = 2g`, `spark.sql.shuffle.partitions = 128`, `numUserBlocks = 50`, `numItemBlocks = 50`, `-Xss16m`.

### 7.3. Khảo sát và trực quan hóa dữ liệu (EDA)
Script `scripts/02_eda_local.py` thực hiện thống kê toàn bộ 32,000,204 lượt đánh giá từ ngày `1995-01-09` đến `2023-10-13` và xuất 3 biểu đồ chính trong `reports/figures/`:

1. **Phân bố điểm đánh giá (`reports/figures/rating_distribution.png`):**

| Điểm đánh giá (Sao) | Số lượt đánh giá | Tỷ lệ (%) |
| ---: | ---: | ---: |
| 0.5 | 525,132 | 1.64% |
| 1.0 | 946,675 | 2.96% |
| 1.5 | 531,063 | 1.66% |
| 2.0 | 2,028,622 | 6.34% |
| 2.5 | 1,685,386 | 5.27% |
| 3.0 | 6,054,990 | 18.92% |
| 3.5 | 4,290,105 | 13.41% |
| **4.0** | **8,367,654** | **26.15%** |
| 4.5 | 2,974,000 | 9.29% |
| 5.0 | 4,596,577 | 14.36% |

- **Nhận xét:** Phân bố lệch trái rõ rệt (điểm trung bình toàn cục khoảng `3.55` sao). Mức `4.0` sao chiếm tỷ lệ cao nhất (`26.15%`), tiếp theo là `3.0` sao (`18.92%`) và `5.0` sao (`14.36%`). Người dùng có xu hướng chấm điểm số nguyên (`3.0, 4.0, 5.0`) nhiều hơn điểm lẻ `.5`, và thường ưu tiên xem cũng như chấm điểm các bộ phim họ kỳ vọng sẽ thích. Do đó, việc chọn ngưỡng liên quan `relevance_threshold = 4.0` (chiếm khoảng 49.8% tổng số lượt đánh giá) là hợp lý để định nghĩa sở thích tích cực khi đo Top-K.

2. **Phân bố thể loại phim (`reports/figures/top_genres.png`):**
- Hai thể loại dẫn đầu về số lượng đầu phim trong catalog 87,585 phim là **Drama** (`34,175` phim) và **Comedy** (`23,124` phim), tiếp theo là **Thriller** (`11,823`), **Romance** (`10,369`), **Action** (`9,668`) và **Documentary** (`9,363`).
- Có `7,080` bộ phim mang nhãn `(no genres listed)` và `195` phim gắn nhãn định dạng trình chiếu `IMAX`. Phát hiện này dẫn đến quyết định thiết kế trong ứng dụng CINE32: chuẩn hóa 18 thể loại chính sang tiếng Việt và loại `(no genres listed)` cùng `IMAX` khỏi bộ lọc sở thích thể loại.

3. **Biến thiên số lượt đánh giá theo năm (`reports/figures/ratings_by_year.png`):**
- Dữ liệu kéo dài 29 năm (1995–2023), phản ánh sự thay đổi lớn về danh mục phim và hành vi người dùng theo thời gian. Do đó, nếu chia tập huấn luyện/kiểm tra ngẫu nhiên sẽ gây rò rỉ thông tin tương lai (data leakage).

### 7.4. Chiến lược chia dữ liệu và chống rò rỉ thông tin (Temporal Split)
Script `scripts/03_prepare_splits_local.py` sắp xếp lịch sử đánh giá của **từng người dùng** theo thứ tự thời gian tăng dần `(timestamp ASC, movieId ASC)` và chia theo tỷ lệ xấp xỉ **80% Train – 10% Validation – 10% Test** bên trong mỗi người dùng:

| Tập dữ liệu | Tập phát triển 10% Users (`data/interim/`) | Tập toàn bộ 100% Users (`data/full_interim/`) | Vai trò trong quy trình |
| --- | ---: | ---: | --- |
| Số lượng người dùng | 20,094 | 200,948 | Tất cả người dùng đều có mặt ở cả 3 tập |
| **Train** | 2,519,826 | 25,520,897 | Huấn luyện các cấu hình ALS và tính thống kê Baseline |
| **Validation** | 314,807 | 3,188,339 | Đánh giá và lựa chọn siêu tham số tối ưu |
| **Test** | 325,041 | 3,290,968 | Đánh giá độc lập một lần cuối; không tham gia huấn luyện |
| **Train + Validation** | 2,834,633 | 28,709,236 | Huấn luyện lại mô hình cuối sau khi đã khóa siêu tham số |

- **Thống kê Cold-Start:** Vì chia theo từng người dùng có tối thiểu 20 lượt đánh giá trong MovieLens, tỷ lệ cold-start người dùng bằng `0%`. Tuy nhiên, các bộ phim mới ra mắt ở giai đoạn cuối của người dùng có thể chỉ xuất hiện trong Validation hoặc Test mà chưa từng xuất hiện trong Train, dẫn đến độ phủ dự đoán (rating coverage) đạt **98.85%** trên tập phát triển và **99.77% / 99.73%** trên tập toàn bộ 32M.

### 7.5. Thực nghiệm Baseline và Tinh chỉnh siêu tham số ALS (Hyperparameter Tuning)

#### 1. So sánh với Baseline trên tập phát triển (`data/interim/`, 20,094 users)
Trước khi mở rộng ra toàn bộ 32 triệu dòng, nhóm đánh giá các phương pháp cơ sở và thử nghiệm lưới tham số trên tập phát triển (`scripts/04_train_als_spark.py` & `scripts/05_tune_evaluate_spark.py`):

| Mô hình / Cấu hình | Số dòng chấm | RMSE Validation | MAE Validation | Coverage (%) |
| --- | ---: | ---: | ---: | ---: |
| **Baseline Global Mean** ($\mu = 3.5625$) | 314,807 | 1.051351 | 0.825242 | 100.00% |
| **Baseline Item Mean** (Trung bình theo từng phim) | 314,807 | 0.968203 | 0.745043 | 100.00% |
| ALS (`rank=8, regParam=0.08, maxIter=4`) | 311,174 | 0.847219 | 0.654703 | 98.85% |
| **ALS (`rank=16, regParam=0.08, maxIter=5`)** | **311,174** | **0.837409** | **0.647536** | **98.85%** |
| ALS (`rank=24, regParam=0.12, maxIter=5`) | 311,174 | 0.856976 | 0.670669 | 98.85% |

- **Phân tích:** ALS giảm mạnh RMSE từ `1.051351` (Global Mean) và `0.968203` (Item Mean) xuống `0.837409` (giảm hơn **13.5%** sai số so với trung bình từng phim). Cấu hình `rank=16, regParam=0.08` đạt hiệu quả tốt nhất nên được khóa để thử nghiệm sâu số vòng lặp trên toàn bộ 32M.

#### 2. Tinh chỉnh số vòng lặp (`maxIter = 5, 10, 15, 20`) trên toàn bộ 32M (`data/full_interim/`)
Chạy lưới 4 cấu hình trên `25,520,897` dòng Train và chấm trên `3,188,339` dòng Validation (`reports/tables/full_iter_20260922_120859/als_tuning.csv`):

| `rank` | `regParam` | `maxIter` | Số dòng dự đoán được | RMSE Validation | MAE Validation | Coverage (%) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 0.08 | 5 | 3,181,118 | 0.833791 | 0.651167 | 99.7735% |
| 16 | 0.08 | 10 | 3,181,118 | 0.810538 | 0.624590 | 99.7735% |
| 16 | 0.08 | 15 | 3,181,118 | 0.803717 | 0.615847 | 99.7735% |
| **16** | **0.08** | **20 (Được chọn)** | **3,181,118** | **0.800952** | **0.612026** | **99.7735%** |

- **Kết quả đánh giá cuối trên tập Test độc lập (`3,290,968` dòng):**
  Sau khi chọn `maxIter=20`, mô hình cuối được huấn luyện lại trên `28,709,236` dòng (`Train + Validation`) và chấm trên tập Test:
  - **Test RMSE:** `0.812898`
  - **Test MAE:** `0.621380`
  - **Test Rating Coverage:** `99.7284%` (`3,282,031 / 3,290,968` dòng; chỉ `0.27%` dòng rơi vào các bộ phim hoàn toàn mới chưa từng có mặt trong `Train + Validation`).
  - **Tổng thời gian thực thi toàn bộ quy trình grid 4 mô hình + fit cuối + chấm Top-K:** `2,387.3` giây (khoảng `39` phút `47` giây).

### 7.6. Chẩn đoán chất lượng xếp hạng Top-K và đối chiếu Baseline
Khi chấm trực tiếp danh sách Top-10 từ mô hình ALS Explicit trên toàn bộ catalog `77,409` phim, các độ đo xếp hạng thu được rất thấp (`Precision@10 = 1.57e-6`, `Recall@10 = 5.60e-6`, `NDCG@10 = 2.21e-6`). Nhóm đã xây dựng script chẩn đoán chuyên sâu `scripts/09_diagnose_topk_and_baseline.py` và thu được bằng chứng thực nghiệm rõ ràng:

1. **Kiểm tra tính đúng đắn của thuật toán lọc lịch sử:**
   - Đối chiếu 5,000 dòng gợi ý của 500 user demo với lịch sử `Train + Validation`: số cặp trùng lặp bằng **`0`** (`seen_history_overlap_count = 0`), và cả 500/500 user đều nhận đủ 10 phim gợi ý. Như vậy kết quả thấp không phải do lỗi mã nguồn hay rò rỉ ID.
2. **Nguyên nhân cốt lõi (Outlier Bias của Explicit ALS trên phim ít lượt chấm):**
   - Trong 5,000 lượt gợi ý Top-10 của ALS Explicit toàn catalog, **94.98%** phim được đề xuất có số lượt đánh giá $\le 5$ lượt (trung vị đúng **1.0 lượt đánh giá**!), và **76.06%** có điểm dự đoán vượt quá thang 5 sao (trung vị `5.37`, cực đại `8.55`).
   - Ví dụ điển hình: Phim `One Breath Around The World (2019)` (`movieId=265364`) và `The Good Fight (1984)` (`movieId=205453`) chỉ có **duy nhất 1 lượt chấm 5.0 sao** trong tập huấn luyện nhưng được ALS đề xuất cho tới `370/500` và `315/500` người dùng với điểm dự đoán trung bình `5.44` và `5.40`. Do những bộ phim cực hiếm này hầu như không ai xem trong tập Test, xác suất trùng khớp trong Top-10 gần bằng 0.
3. **Giải pháp khắc phục và Bảng so sánh công bằng trên 10,000 User Test (`reports/tables/topk_comparison.csv`):**
   Khi áp dụng bộ lọc ngưỡng độ tin cậy tối thiểu (`rating_count >= 100` hoặc `rating_count >= 500`) cho tập ứng viên ALS và so sánh trên cùng tập 10,000 user test đủ điều kiện:

| Phương pháp xếp hạng Top-10 | Số phim ứng viên | Precision@10 | Recall@10 | NDCG@10 | Nhận xét thực nghiệm |
| --- | ---: | ---: | ---: | ---: | --- |
| **ALS Explicit (Toàn bộ catalog)** | 77,409 | 0.000020 | 0.000007 | 0.000013 | Bị nhiễu bởi 94.98% phim có $\le 5$ lượt chấm |
| **Baseline Weighted Score ($m=100$, CINE32)** | 77,409 | 0.012310 | 0.020328 | 0.015091 | Khử hoàn toàn nhiễu phim ít lượt chấm cho user mới |
| **ALS Explicit + Lọc ngưỡng (`rating_count >= 100`)** | 11,330 | **0.014670** | **0.026738** | **0.022586** | **Tăng 733 lần** so với ALS thô; **vượt qua** cả Weighted Score toàn cục nhờ cá nhân hóa |
| **ALS Explicit + Lọc ngưỡng (`rating_count >= 500`)** | 5,760 | **0.021640** | **0.036183** | **0.030951** | **Tăng 1,082 lần** so với ALS thô; cân bằng tốt giữa độ phổ biến và sở thích cá nhân |
| **Baseline Popularity (Theo `rating_count` giảm dần)** | 77,409 | 0.031720 | 0.053728 | 0.050040 | Cao nhất về độ trúng thô do người dùng MovieLens tập trung xem các phim bom tấn phổ biến |

- **Kết luận học thuật quan trọng:** RMSE thấp trên các đánh giá đã biết không tự động đảm bảo danh sách xếp hạng Top-K tốt nếu không kiểm soát độ tin cậy của ứng viên (`support threshold`). Khi kết hợp vector nhân tố ALS với ngưỡng `rating_count >= 100`, mô hình cá nhân hóa vượt qua bảng xếp hạng điểm trọng số tĩnh (`0.014670` so với `0.012310` ở Precision@10 và `0.022586` so với `0.015091` ở NDCG@10).

### 7.7. Thực nghiệm khả năng xử lý dữ liệu lớn (Big Data Performance Benchmarks)
Script `scripts/10_benchmark_bigdata.py` thực hiện hai thí nghiệm đo lường trực tiếp trên máy thực nghiệm (`reports/tables/bigdata_benchmarks.md`):

#### 1. So sánh hiệu năng đọc và tổng hợp 32,000,204 dòng: CSV gốc vs Parquet (`local[4]`, 3 lần chạy)
- Truy vấn kiểm tra: Đọc toàn bộ 32 triệu dòng và thực hiện `groupBy("movieId").agg(count("*"), avg("rating"))`.
- **CSV gốc (`836.45 MB`):** Thời gian 3 lần chạy `[27.535s, 19.690s, 19.384s]` $\rightarrow$ **Trung vị: `19.690` giây**.
- **Parquet (`209.44 MB`):** Thời gian 3 lần chạy `[3.040s, 1.642s, 1.567s]` $\rightarrow$ **Trung vị: `1.642` giây**.
- **Kết luận:** Định dạng cột Parquet giúp **tiết kiệm 74.96% dung lượng đĩa** và **tăng tốc truy vấn tổng hợp gấp 11.99 lần** so với CSV nhờ chỉ đọc đúng 2 cột `movieId, rating` và giải nén nhị phân trực tiếp.

#### 2. Thực nghiệm mở rộng số luồng xử lý song song Spark (`local[1]` vs `local[2]` vs `local[4]`)
Đo trên tập phát triển (`2,519,826` dòng Train + `314,807` dòng Validation) với ALS `rank=16, regParam=0.08, maxIter=5`:

| Cấu hình Spark | Số luồng CPU | Nạp & Cache (giây) | Fit ALS & Đánh giá (giây) | Tổng thời gian (giây) | RMSE Validation | Mức tăng tốc (Speedup) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `local[1]` | 1 | 4.002 | 40.121 | 44.123 | 0.836664 | **1.00x** |
| `local[2]` | 2 | 2.744 | 20.388 | 23.132 | 0.836664 | **1.91x** |
| `local[4]` | 4 | 2.227 | 15.636 | 17.863 | 0.836664 | **2.47x** |

- **Nhận xét:** Khi tăng từ 1 luồng lên 2 luồng, tốc độ huấn luyện tăng gần tuyến tính (**1.91 lần**). Khi tăng lên 4 luồng, tổng thời gian giảm từ `44.123s` xuống `17.863s` (**nhanh gấp 2.47 lần**), trong khi kết quả RMSE giữ nguyên tuyệt đối (`0.836664`). Mức tăng tốc ở 4 luồng thấp hơn 4.0x lý tưởng do chi phí trộn dữ liệu (shuffle overhead) giữa các phân vùng ở mỗi vòng lặp ALS.

### 7.8. Xây dựng ứng dụng web CINE32 (React/TypeScript + FastAPI + TMDB)
Để phục vụ người dùng cuối và giải quyết triệt để bài toán người dùng mới (cold-start) cũng như hạn chế của ALS thô đối với phim ít lượt chấm, nhóm đã xây dựng ứng dụng web **CINE32**:
- **Chuẩn bị Catalog (`scripts/07_build_movie_catalog.py` & `08_enrich_catalog_imdb.py`):** Dùng Spark tổng hợp `28,709,236` lượt đánh giá (`Train + Validation`), tính `avg_rating`, `rating_count`, và `weighted_score` với $C = 3.546251, m = 100$ cho toàn bộ `87,585` bộ phim, đồng thời nối `tmdbId` và `imdbId` từ `links.parquet`.
- **Backend API (`web_api.py` & `src/recommender/`):**
  - Chuẩn hóa 18 thể loại sang tiếng Việt (`genre_recommender.py`). Khi người dùng chọn nhiều thể loại, hệ thống ưu tiên số lượng thể loại khớp (`matched_count` giảm dần), sau đó xếp theo `weighted_score` giảm dần, `rating_count` giảm dần và `movieId` tăng dần.
  - Phim chưa có lượt đánh giá vẫn được giữ trong danh sách phân trang (hiển thị nhãn `"Chưa có đánh giá"`, không biến thành điểm `0/5`).
  - Tích hợp `tmdb_client.py` và `poster_loader.py` tải nền poster/backdrop và tóm tắt nội dung từ TMDB (tự động fallback sang tra cứu theo `imdbId` khi `tmdbId` cũ không còn hợp lệ) và lưu cache SQLite tại `artifacts/cache/tmdb_cache.db`.
- **Giao diện người dùng (`frontend/src/App.tsx`):** Phong cách tối – vàng lấy cảm hứng từ IMDb, chip thể loại tự cập nhật, tìm tên phim, phân trang 24 phim/trang và modal chi tiết. Mục **Gợi ý ALS** (`frontend/src/PersonalRecommendations.tsx`) nhận User ID, hiển thị tối đa 10 phim từ vector cá nhân, điểm ALS, điểm cộng đồng, poster và lịch sử. ID mới dùng Weighted Score với thông báo rõ. `app.py` là bản Streamlit khám phá theo thể loại cũ, không phải demo ALS.

**Giao thức serving:** dùng vector full model của 200.948 user và 77.409 phim; ứng viên có ít nhất 100 lượt chấm trong train + validation (11.330 phim). Serving loại toàn bộ lịch sử 32M, gồm cả test, để không giới thiệu phim đã chấm. Giao thức đánh giá offline vẫn chỉ loại lịch sử của tập fit rồi chấm trên test; giữ nguyên các độ đo đã công bố. Điểm dự đoán là tích vô hướng và có thể ngoài 0,5–5; không nhầm với điểm trung bình cộng đồng.

---

## PHẦN 8. KẾT LUẬN VÀ ĐỊNH HƯỚNG PHÁT TRIỂN

### 8.1. Kết luận những kết quả đạt được
1. **Xử lý trọn vẹn quy mô MovieLens 32M:** Đã xây dựng thành công pipeline PySpark hoàn chỉnh từ kiểm tra dữ liệu gốc, chuyển đổi Parquet (tiết kiệm **74.96%** dung lượng và tăng tốc truy vấn **11.99 lần**), đến chia tập theo thời gian cho toàn bộ **32,000,204** lượt đánh giá của **200,948** người dùng.
2. **Huấn luyện và đánh giá bài bản mô hình ALS:** Đã huấn luyện và tinh chỉnh ALS trên toàn bộ dữ liệu với cấu hình tối ưu `rank=16, regParam=0.08, maxIter=20`, đạt **Validation RMSE = 0.800952** và **Test RMSE = 0.812898** (vượt xa Global Mean `1.051` và Item Mean `0.968`), độ phủ dự đoán đạt **99.73%**.
3. **Phân tích sâu và khắc phục hạn chế xếp hạng Top-K:** Đã chứng minh bằng số liệu hiện tượng ALS Explicit ưu tiên các phim cực ít lượt đánh giá (`94.98%` ứng viên có $\le 5$ lượt chấm), và chỉ ra rằng việc lọc ứng viên theo ngưỡng độ tin cậy (`rating_count >= 100` hoặc `500`) giúp tăng `Precision@10` lên gấp **733 – 1,082 lần**, vượt qua cả bảng xếp hạng điểm trọng số tĩnh.
4. **Hoàn thiện sản phẩm ứng dụng CINE32:** Xây dựng giao diện web hiện đại bằng React/TypeScript + FastAPI phục vụ duyệt toàn bộ 87,585 bộ phim theo thể loại và tìm kiếm tức thời kèm poster TMDB.

### 8.2. Hạn chế của hệ thống hiện tại
- Mô hình ALS hiện chạy theo lô (batch) trên dữ liệu tĩnh; khi người dùng mới chấm điểm trên ứng dụng, hệ thống chưa cập nhật vector nhân tố $\mathbf{u}_u$ theo thời gian thực.
- ALS Explicit tối ưu sai số bình phương trên các lượt chấm đã quan sát nên nhạy cảm với các bộ phim có ít lượt đánh giá nếu không kết hợp lọc ngưỡng hỗ trợ (`support filtering`).

### 8.3. Định hướng phát triển
- **Mô hình Hybrid (Kết hợp ALS + Content/Genre + Support Weighting):** Kết hợp điểm tích vô hướng $\mathbf{u}_u^T \mathbf{v}_i$ của ALS với độ khớp thể loại và hệ số co rút Bayes $\frac{v}{v+m}$ ngay trong bước xếp hạng ứng viên.
- **Cập nhật vector người dùng tức thời (Fold-in Inference):** Cho phép người dùng mới chọn hoặc chấm điểm 5–10 bộ phim trên giao diện CINE32, sau đó giải nhanh phương trình bình phương tối tiểu với ma trận $V$ cố định để sinh vector cá nhân hóa $\mathbf{u}_{\text{new}}$ ngay trong phiên làm việc.
- **Triển khai cụm phân tán nhiều máy:** Đưa pipeline Parquet và Spark lên cụm HDFS/YARN hoặc Kubernetes nhiều node vật lý để giảm thời gian huấn luyện grid full xuống dưới 5 phút.

---

## PHẦN 9. TÀI LIỆU THAM KHẢO

1. Khoa Công nghệ Thông tin – Trường Đại học Công Thương TP.HCM (HUIT), *Hướng dẫn đồ án môn học Nhập môn Big Data*, 2026.
2. GroupLens Research, *MovieLens 32M Dataset*, https://grouplens.org/datasets/movielens/32m/ (Truy cập ngày 15/09/2026).
3. F. Maxwell Harper and Joseph A. Konstan, *The MovieLens Datasets: History and Context*, ACM Transactions on Interactive Intelligent Systems (TiiS), Vol. 5, No. 4, Article 19, 2015. https://doi.org/10.1145/2827872
4. Yunhong Zhou, Dennis Wilkinson, Robert Schreiber, and Rong Pan, *Large-Scale Parallel Collaborative Filtering for the Netflix Prize*, Proceedings of AAIM 2008, LNCS 5034, pp. 337–348, 2008.
5. Apache Spark Documentation, *Collaborative Filtering – Spark 3.5.7 MLlib Guide*, https://spark.apache.org/docs/3.5.7/ml-collaborative-filtering.html (Truy cập ngày 22/09/2026).
6. The Movie Database (TMDB), *TMDB API v3 Reference & Image Basics*, https://developer.themoviedb.org/docs/image-basics (Truy cập ngày 23/09/2026).

---

## PHẦN 10. PHỤ LỤC

### 10.1. Danh mục các kịch bản chương trình (`scripts/`)
| Kịch bản | Chức năng chính | Đầu ra |
| --- | --- | --- |
| `scripts/00_check_data.py` | Kiểm tra sự tồn tại, header, số dòng và MD5 của bộ dữ liệu gốc | Xác nhận 4 file CSV hợp lệ |
| `scripts/01_convert_to_parquet.py` | ETL chuyển đổi CSV sang Parquet với schema chặt chẽ | `data/processed/parquet/*.parquet` |
| `scripts/02_eda_local.py` | Thống kê phân bố rating, thể loại, năm và vẽ biểu đồ EDA | `reports/tables/eda_*.csv`, `reports/figures/*.png` |
| `scripts/03_prepare_splits_local.py` | Chia dữ liệu `train/valid/test` theo thứ tự thời gian từng user | `data/interim/` và `data/full_interim/` |
| `scripts/04_train_als_spark.py` | Huấn luyện ALS và tính các mô hình cơ sở trên tập phát triển | `models/als_dev/` |
| `scripts/05_tune_evaluate_spark.py` | Grid search ALS, fit lại `train+valid`, chấm Test và xuất gợi ý | `models/als_full_iter_20260922_120859/` |
| `scripts/06_export_demo.py` | Đóng gói dữ liệu gợi ý nhỏ gọn cho ứng dụng demo | `artifacts/demo/` |
| `scripts/07_build_movie_catalog.py` | Dùng Spark tổng hợp 28.7M ratings thành catalog 87,585 phim | `artifacts/catalog/movie_catalog.parquet` |
| `scripts/08_enrich_catalog_imdb.py` | Bổ sung `imdbId` vào catalog phục vụ tra cứu dự phòng TMDB | Cập nhật `movie_catalog.parquet` |
| `scripts/09_diagnose_topk_and_baseline.py` | Chẩn đoán Top-K ALS và so sánh với Popularity / Weighted Score | `reports/tables/topk_comparison.csv` |
| `scripts/10_benchmark_bigdata.py` | Đo hiệu năng CSV vs Parquet và Spark `local[1..4]` | `reports/tables/bigdata_benchmarks.md` |
| `scripts/11_hdfs_local.py` | Cài, khởi động, kiểm tra và dừng HDFS một máy | `.hadoop/` (không đưa lên Git) |
| `scripts/12_prepare_als_serving.py` | Đóng gói vector và lịch sử cho gợi ý cá nhân | `artifacts/als_serving/` (không đưa lên Git) |
| `scripts/13_verify_hdfs_spark.py` | ETL 32M và inference ALS trên HDFS | `reports/tables/hdfs_spark_verification.json` |

### 10.2. Lệnh khởi chạy nhanh toàn bộ hệ thống Demo

Chuẩn bị HDFS trong terminal riêng bằng `py scripts/11_hdfs_local.py start --foreground`. Xem [hướng dẫn HDFS và demo ALS](../HUONG_DAN_HDFS_VA_DEMO_ALS.md) để tạo artifact, kiểm tra HDFS và chạy Spark trước buổi bảo vệ.
```powershell
# 1. Chạy kiểm tra tự động (Unit Tests)
py -m unittest discover -s tests -p "test_*.py" -v

# 2. Khởi chạy ứng dụng web CINE32 (FastAPI + React build)
py -m uvicorn web_api:app --host 127.0.0.1 --port 8502
# Mở trình duyệt tại: http://127.0.0.1:8502/
```
