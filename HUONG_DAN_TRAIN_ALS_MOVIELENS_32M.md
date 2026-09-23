# Hướng dẫn train ALS với MovieLens 32M

Tài liệu cho đề tài 15 — hệ thống gợi ý phim. Các lệnh bên dưới dùng **PowerShell tại thư mục dự án**, khớp với script hiện có ngày **22/09/2026**.

**Mục tiêu:** so sánh 5, 10, 15 và 20 vòng lặp, chọn cấu hình bằng validation, đánh giá kết quả và đưa model vào demo. Grid full đã chạy xong; model được chọn hiện dùng **20 vòng**.

## 1. Có nên train nhiều vòng không?

Có thể thử, nhưng cần đo trên validation. Nhiều vòng hơn không bảo đảm model gợi ý tốt hơn.

ALS học hai bảng vector: một cho người dùng và một cho phim. Thuật toán luân phiên cập nhật hai bảng này. Trong Spark, số vòng được điều khiển bằng **`maxIter`**; đây là tham số tương ứng khi nói đến “epoch” trong dự án này. Giá trị mặc định của Spark là 10, còn script dự án có cấu hình riêng. [Tài liệu ALS của Spark 3.5.7](https://spark.apache.org/docs/3.5.7/api/python/reference/api/pyspark.ml.recommendation.ALS.html).

Thí nghiệm đầu tiên giữ cố định các tham số khác:

| Tham số | Giá trị | Ý nghĩa |
|---|---:|---|
| `rank` | 16 | Số thành phần trong vector người dùng/phim |
| `regParam` | 0.08 | Mức điều chuẩn, giúp hạn chế model khớp quá sát dữ liệu train |
| `maxIter` | 5, 10, 15, 20 | Số vòng cần so sánh |
| `seed` | 42 | Seed được đặt trong script |
| `implicitPrefs` | `False` | Học trực tiếp từ điểm rating |
| `nonnegative` | `True` | Cấu hình hiện có trong script |

Mỗi cấu hình được **train mới từ đầu**. Chạy 10 vòng không phải tải model 5 vòng rồi train thêm 5 vòng. Script hiện chưa hỗ trợ tiếp tục từ checkpoint, dừng sớm theo validation hoặc lưu loss từng vòng.

Trên Windows hiện tại, Spark checkpoint cục bộ có thể gọi `NativeIO` và lỗi nếu `hadoop.dll` không tương thích. Script đã tăng JVM thread stack lên `16m`; lệnh full bên dưới dùng `--checkpoint-interval 0` để tránh đường native này. Khi chạy Linux/WSL và đã cấu hình Hadoop native I/O, có thể đổi thành `--checkpoint-interval 5`.

## 2. Dữ liệu và kết quả hiện tại

### 2.1. “Train full 32M” trong dự án nghĩa là gì?

Toàn bộ **32.000.204 rating của 200.948 người dùng** đã được đưa vào quy trình chia tập:

| Tập dữ liệu | Số rating | Công dụng |
|---|---:|---|
| Train | 25.520.897 | Train từng cấu hình để so sánh |
| Validation | 3.188.339 | Chọn cấu hình |
| Test | 3.290.968 | Đánh giá sau khi chọn cấu hình |
| Train + validation | 28.709.236 | Train lại model được chọn |

Vì vậy, model cuối hiện tại học từ **28.709.236 rating**, còn test được giữ ngoài bước học. Không đưa test vào train rồi dùng chính test để báo cáo khả năng dự đoán.

Các tập nằm trong `data/full_interim/`. Việc chia tập theo thứ tự thời gian **trong từng người dùng**, không theo một mốc thời gian chung cho toàn hệ thống. Khi timestamp bằng nhau, script dùng `movieId` để xác định thứ tự.

### 2.2. Mốc so sánh đã chạy

Nguồn: `models/als_full/metrics.json` và `data/full_interim/split_summary.md`.

| Chỉ số | Giá trị |
|---|---:|
| Cấu hình | `rank=16`, `regParam=0.08`, `maxIter=5` |
| RMSE validation | 0.833791 |
| RMSE test | 0.847450 |
| MAE test | 0.662661 |
| Tỷ lệ rating test dự đoán được | 99.7284% |
| Precision@10 test | 5.235630 × 10⁻⁷ |
| Recall@10 test | 1.026594 × 10⁻⁷ |
| NDCG@10 test | 3.468826 × 10⁻⁷ |
| Thời gian toàn lần chạy | 590.302 giây, khoảng 9 phút 50 giây |

**Model đã train thành công, nhưng các chỉ số Top-10 gần bằng 0 cần được kiểm tra.** Chưa có căn cứ kết luận nguyên nhân là thiếu vòng lặp. Lần full trước chỉ thử một cấu hình, nên cũng chưa chứng minh 5 vòng là lựa chọn tốt nhất.

Thời gian trên bao gồm đọc dữ liệu, train, đánh giá và xuất kết quả; không phải thời gian của riêng một lần `fit`.

### 2.3. Kết quả grid full đã triển khai

Lần chạy mới nhất: `models/als_full_iter_20260922_120859/`, báo cáo tại `reports/tables/full_iter_20260922_120859/als_tuning.csv`. Các cấu hình dùng cùng `rank=16`, `regParam=0.08`, seed 42 và cùng tập full.

| `maxIter` | RMSE validation | MAE validation | Coverage |
|---:|---:|---:|---:|
| 5 | 0.833791 | 0.651167 | 99.7735% |
| 10 | 0.810538 | 0.624590 | 99.7735% |
| 15 | 0.803717 | 0.615847 | 99.7735% |
| **20 (được chọn)** | **0.800952** | **0.612026** | **99.7735%** |

Model cuối được fit lại trên 28.709.236 dòng train + validation. Kết quả test của model 20 vòng: RMSE **0.812898**, MAE **0.621380**, coverage **99.7284%**; Precision@10 **1.570689 × 10⁻⁶**, Recall@10 **5.596707 × 10⁻⁶**, NDCG@10 **2.210047 × 10⁻⁶**. Toàn pipeline mất khoảng **2.387 giây (39 phút 47 giây)**. Demo đã được xuất lại vào `artifacts/demo/` với 5.000 dòng gợi ý cho 500 người dùng.

RMSE giảm đều khi tăng số vòng trong grid này, nhưng Top-K vẫn rất thấp. Vì vậy, kết quả hiện đủ để chọn tham số theo RMSE; chưa đủ để khẳng định chất lượng gợi ý sản phẩm tốt. Tiếp tục dùng checklist ở mục 6 để kiểm tra ID, lịch sử đã xem, số ứng viên và baseline phổ biến.

## 3. Chuẩn bị trước khi chạy

### 3.1. Kiểm tra môi trường

```powershell
Set-Location -LiteralPath '<PROJECT_ROOT>'
py --version
java -version
py -c "import pyspark, pandas, pyarrow; print('pyspark', pyspark.__version__); print('pandas', pandas.__version__); print('pyarrow', pyarrow.__version__)"
py scripts\05_tune_evaluate_spark.py --help
```

Lần full trước chạy trên máy khoảng 32 GB RAM, Python 3.13.7, Java 8u461 và PySpark 3.5.7. Đây là môi trường đã quan sát trên máy hiện tại. Spark dùng `local[4]`, tức chạy song song trên một máy.

Nếu môi trường thiếu thư viện, cài theo file của dự án:

```powershell
py -m pip install -r requirements.txt
```

### 3.2. Kiểm tra các tập full đã có

```powershell
$RequiredTrainFiles = @(
  'data/full_interim/train.parquet',
  'data/full_interim/valid.parquet',
  'data/full_interim/test.parquet',
  'data/processed/parquet/movies.parquet'
)
foreach ($TrainFile in $RequiredTrainFiles) {
  if (-not (Test-Path -LiteralPath $TrainFile)) {
    throw "Thiếu dữ liệu: $TrainFile"
  }
}
Get-Content -LiteralPath 'data/full_interim/split_summary.md'
```

Máy hiện tại đã có các tập này. **Giữ nguyên chúng khi so sánh số vòng lặp**, tránh thay đổi dữ liệu giữa các lần thử.

Chỉ khi chưa có các tập full và đã có Parquet sau ETL, mới cần tạo bằng lệnh sau. Lệnh này có thể ghi đè các file cùng tên và cần đáng kể RAM để sắp xếp dữ liệu:

```powershell
py scripts\03_prepare_splits_local.py `
  --parquet-dir data\processed\parquet `
  --output-dir data\full_interim `
  --user-mod 1
```

`--user-mod 1` lấy toàn bộ người dùng. `data/interim/` là tập sample; `data/full_interim/` mới là các tập chia từ toàn bộ 32M.

## 4. Chạy so sánh 5, 10, 15 và 20 vòng trên full data

Chạy nguyên khối dưới đây trong cùng một cửa sổ PowerShell. Mỗi lần chạy tạo thư mục riêng theo thời gian, giữ lại kết quả `models/als_full/` hiện tại.

```powershell
Set-Location -LiteralPath '<PROJECT_ROOT>'

$TrainRunId = Get-Date -Format 'yyyyMMdd_HHmmss'
$TrainModelDir = "models/als_full_iter_$TrainRunId"
$TrainReportDir = "reports/tables/full_iter_$TrainRunId"
$TrainLog = "logs/als_full_iter_$TrainRunId.log"
New-Item -ItemType Directory -Path 'logs' -Force | Out-Null

py -u scripts\05_tune_evaluate_spark.py `
  --ratings-train data\full_interim\train.parquet `
  --ratings-valid data\full_interim\valid.parquet `
  --ratings-test data\full_interim\test.parquet `
  --movies data\processed\parquet\movies.parquet `
  --output-dir $TrainModelDir `
  --report-dir $TrainReportDir `
  --grid '16:0.08:5,16:0.08:10,16:0.08:15,16:0.08:20' `
  --master 'local[4]' `
  --driver-memory 16g `
  --memory-overhead 2g `
  --spark-local-dir spark_tmp\als_full_iter `
  --shuffle-partitions 128 `
  --num-user-blocks 50 `
  --num-item-blocks 50 `
  --checkpoint-interval 0 `
  --top-k 10 `
  --candidate-k 50 `
  --relevance-threshold 4.0 `
  --demo-users 500 2>&1 | Tee-Object -FilePath $TrainLog

if ($LASTEXITCODE -ne 0) {
  throw "Train thất bại. Xem log: $TrainLog"
}
Write-Output "Model: $TrainModelDir"
Write-Output "Báo cáo: $TrainReportDir"
Write-Output "Log: $TrainLog"
```

**Cách đọc `--grid`:** mỗi bộ là `rank:regParam:maxIter`, ngăn cách bằng dấu phẩy. Script `05` không có cờ `--max-iter`; cờ đó thuộc script `04`.

Lệnh trên thực hiện:

1. Train bốn model độc lập trên tập train.
2. Tính RMSE, MAE và tỷ lệ dự đoán được trên validation cho từng model.
3. Chọn cấu hình có **RMSE validation nhỏ nhất**.
4. Train mới một model với cấu hình được chọn trên train + validation.
5. Tính các chỉ số test, lưu factor model và xuất gợi ý cho 500 người dùng phục vụ demo.

Tổng cộng có **5 lần fit**, không phải một lần train 20 vòng với bốn checkpoint. JVM của script đã dành stack `16m` cho driver và executor, đủ để chạy grid 20 vòng trên máy Windows hiện tại khi checkpoint native bị tắt. Nếu chạy Linux/WSL đã có Hadoop native I/O, có thể dùng `--checkpoint-interval 5` để cắt lineage định kỳ. Vì vậy, không lấy thời gian lần chạy cũ để suy ra chính xác thời gian lần này. Nếu cần một thử nghiệm nhỏ hơn, có thể đặt trước grid `'16:0.08:5,16:0.08:10'`.

Trong PowerShell, dấu backtick ở cuối dòng phải là ký tự cuối cùng, không có khoảng trắng phía sau. Giữ cửa sổ chạy và tránh để máy chuyển sang chế độ ngủ.

## 5. Đọc kết quả và chọn số vòng

### 5.1. Đọc bảng validation

Các biến dưới đây được tạo ở bước 4. Nếu mở PowerShell mới, gán lại `$TrainModelDir` và `$TrainReportDir` bằng đúng đường dẫn của lần chạy cần xem.

```powershell
Import-Csv -LiteralPath "$TrainReportDir/als_tuning.csv" |
  Sort-Object { [double]$_.rmse } |
  Format-Table rank, regParam, maxIter, rmse, mae, coverage -AutoSize

$TrainMetrics = Get-Content -LiteralPath "$TrainModelDir/metrics.json" -Raw |
  ConvertFrom-Json
$TrainMetrics.selected_params | Format-List
$TrainMetrics.selected_validation | Format-List
$TrainMetrics.test_rating_metrics | Format-List
$TrainMetrics.test_topk_metrics | Format-List

'Precision@10 = {0:E6}' -f [double]$TrainMetrics.test_topk_metrics.precision_at_k
'Recall@10 = {0:E6}' -f [double]$TrainMetrics.test_topk_metrics.recall_at_k
'NDCG@10 = {0:E6}' -f [double]$TrainMetrics.test_topk_metrics.ndcg_at_k
```

- **RMSE/MAE càng thấp càng tốt** đối với dự đoán điểm rating.
- **Precision/Recall/NDCG càng cao càng tốt** đối với danh sách gợi ý trong cùng quy trình đánh giá.
- `coverage` cho biết tỷ lệ rating có dự đoán hợp lệ. Script dùng `coldStartStrategy='drop'`, nên RMSE không bao gồm mọi dòng nếu có người dùng hoặc phim model chưa học được. [Giải thích cold start của Spark](https://spark.apache.org/docs/3.5.7/ml-collaborative-filtering.html).
- Nếu 15 hoặc 20 vòng làm RMSE validation tăng, script vẫn chọn mức có RMSE thấp nhất trong grid.
- Nếu các kết quả gần nhau, ghi nhận mức cải thiện thực tế. Script hiện chưa có quy tắc ưu tiên model ít vòng khi chênh lệch nhỏ.

**Giới hạn hiện tại:** script chỉ dùng RMSE validation để chọn cấu hình; chưa tính Top-K trên validation. Vì thế, chưa thể kết luận model được chọn có danh sách gợi ý tốt nhất. Không dùng các chỉ số test để chọn số vòng. Nếu đã dùng test để điều chỉnh cấu hình, cần một tập đánh giá độc lập khác để có kết quả cuối không bị ảnh hưởng bởi việc lựa chọn đó.

### 5.2. File được tạo sau một lần chạy thành công

| File | Nội dung |
|---|---|
| `$TrainReportDir/als_tuning.csv` | Kết quả validation của từng cấu hình |
| `$TrainReportDir/test_metrics.json` | Báo cáo của lần chạy, gồm các chỉ số test |
| `$TrainModelDir/metrics.json` | Cấu hình được chọn, số dòng và các chỉ số |
| `$TrainModelDir/model/metadata.json` | Tham số model |
| `$TrainModelDir/_spark_checkpoints/` | Checkpoint lineage Spark nếu chạy với `--checkpoint-interval > 0` |
| `spark_tmp\als_full_iter\` | Shuffle/temp của Spark trên ổ D trong lần chạy mẫu |
| `$TrainModelDir/model/factors/user_factors.parquet` | Vector người dùng |
| `$TrainModelDir/model/factors/item_factors.parquet` | Vector phim |
| `$TrainModelDir/recommendations/recommendations.parquet` | Gợi ý cho nhóm người dùng demo |

Model được lưu dưới dạng **hai bảng factor và metadata**, không phải định dạng native để gọi trực tiếp `ALSModel.load(...)`. Các model trung gian của grid không được lưu. `als_tuning.csv` chỉ được ghi sau khi hoàn thành cả grid; có file này chưa có nghĩa các bước train lại và đánh giá test đã xong.

## 6. Kiểm tra Top-10 gần bằng 0

Đây là việc cần làm trước khi kết luận sản phẩm gợi ý đạt yêu cầu. Các mục bên dưới là **hướng kiểm tra cần bổ sung**, không phải các chức năng đã được chạy hoặc đã có đầy đủ trong CLI.

### 6.1. Kiểm tra dữ liệu và phép tính

1. Lấy vài người dùng, đối chiếu `userId`/`movieId` giữa lịch sử, gợi ý và tập đánh giá; không nhầm ID gốc với chỉ số dòng hoặc ID nguồn khác.
2. Kiểm tra danh sách gợi ý đã loại phim người dùng đánh giá trong tập dùng để fit. Khi kiểm tra trên validation, chỉ loại lịch sử train; khi đánh giá model fit trên train + validation, loại lịch sử của cả hai tập.
3. Tính tay một vài trường hợp. Ví dụ, 2 phim trúng trong 10 gợi ý thì Precision@10 = 2/10; nếu người dùng có 3 phim liên quan trong tập đánh giá thì Recall@10 = 2/3. NDCG còn phụ thuộc vị trí các phim trúng.
4. Kiểm tra phim ít rating, phân bố số rating của phim được đề xuất và các điểm dự đoán quá cao. Đây là các giả thuyết cần kiểm chứng, chưa phải nguyên nhân đã xác định.

Trong script hiện tại, phim liên quan là phim có rating **từ 4.0**, xuất hiện trong catalog mà model đã học. Các chỉ số Top-K được lấy trung bình theo người dùng đủ điều kiện; báo cáo có thêm tỷ lệ phim liên quan nằm trong catalog.

### 6.2. Kiểm tra số lượng ứng viên

Script `05` lấy tối đa `candidate-k=50` ứng viên, loại phim đã xem rồi giữ tối đa 10 phim. Một số người dùng có thể còn dưới 10 phim; script chưa tự lấy thêm ứng viên để bù.

Cần thống kê số gợi ý thực tế mỗi người dùng. `user_coverage=1.0` chỉ có nghĩa mọi người dùng được xét có **ít nhất một** gợi ý, không có nghĩa ai cũng đủ 10. Precision trong script vẫn chia cho `k=10`.

Có thể nghiên cứu tăng `candidate-k`, nhưng phải so sánh bằng cùng quy trình trên validation và đo chi phí tính toán. Thay số ứng viên không bảo đảm giải quyết được kết quả gần 0.

### 6.3. Bổ sung đánh giá phù hợp với sản phẩm

- Thêm Precision@10, Recall@10 và NDCG@10 **trên validation** cho các cấu hình đang so sánh.
- Thêm baseline phim phổ biến, thống kê từ tập train, cùng quy tắc loại phim đã xem và cùng tập người dùng đánh giá.
- So sánh ALS với baseline trên cùng điều kiện trước khi chọn model phục vụ gợi ý.

Script `04` có baseline dự đoán rating, nhưng chưa phải baseline Top-K phim phổ biến. RMSE baseline và ALS cũng cần tính trên cùng tập dòng để so sánh công bằng. Gợi ý xuất bởi script `04` chưa loại phim đã xem như script `05`; dùng kết quả script `05` cho luồng demo bên dưới.

## 7. Xuất model được chọn vào demo

Sau khi xem kết quả, có thể xuất thử sang thư mục riêng để kiểm tra artifact:

```powershell
$TrainDemoReviewDir = "artifacts/demo_review_$TrainRunId"
py scripts\06_export_demo.py `
  --model-dir $TrainModelDir `
  --output-dir $TrainDemoReviewDir `
  --top-k 10

Get-Content -LiteralPath "$TrainDemoReviewDir/manifest.json"
```

Khi muốn giao diện dùng kết quả mới, xuất vào đường dẫn mà app đang đọc:

```powershell
py scripts\06_export_demo.py `
  --model-dir $TrainModelDir `
  --output-dir artifacts\demo `
  --top-k 10

py -m streamlit run app.py
```

Lệnh xuất vào `artifacts/demo/` sẽ thay dữ liệu demo hiện tại. Nếu app đang chạy, khởi động lại để tránh đọc cache cũ. Luôn truyền `--model-dir` rõ ràng: mặc định của script `06` là `models/als_final`, không phải model full mới.

Demo sử dụng danh sách gợi ý đã tính trước cho tối đa 500 người dùng theo lệnh ở bước 4; hiện chưa suy luận trực tiếp cho người dùng mới. Lọc thể loại trong giao diện có thể làm danh sách ngắn hơn 10 phim.

## 8. Xử lý các vấn đề thường gặp

| Vấn đề | Cách xử lý |
|---|---|
| `Java heap space` | Kiểm tra RAM còn trống và các tiến trình Spark khác. Cấu hình full từng chạy thành công dùng driver `16g`, 50 user blocks và 50 item blocks. Không tăng bộ nhớ vượt khả năng máy. |
| Nhầm `shuffle-partitions` với số block ALS | Đây là hai tham số khác nhau. Giữ cả `--shuffle-partitions 128` và hai cờ block như lệnh mẫu khi so sánh số vòng. |
| Chạy lâu, chưa có bảng tuning | Bảng CSV được ghi sau cả grid. Xem log và tiến trình; chưa có CSV không tự động có nghĩa là treo. |
| Bị ngắt hoặc gặp lỗi giữa chừng | Kiểm tra exit code và log. Lần chạy mới bắt đầu train lại; script chưa có resume hoặc lưu từng model trong grid. |
| Có bảng tuning nhưng thiếu model cuối | Kiểm tra log các bước fit trên train + validation, đánh giá test và xuất factor. Không coi lần chạy đó là hoàn thành. |
| Top-K hiện `0.0000` | Đọc JSON hoặc in dạng số khoa học ở bước 5; số rất nhỏ có thể bị làm tròn thành 0 trên giao diện. |
| Lỗi ghi model native trên Windows | Luồng hiện tại lưu factor qua pandas/PyArrow. Không thay bằng `ALSModel.save(...)` rồi giả định có thể dùng nguyên môi trường hiện tại. |
| `UnsatisfiedLinkError: NativeIO$Windows.access0` | Đang bật checkpoint native trên Windows. Dùng `--checkpoint-interval 0` như lệnh full; nếu muốn checkpoint, chạy trong Linux/WSL và cấu hình Hadoop native I/O. |
| `There is not enough space on the disk` | Kiểm tra ổ chứa thư mục temp. Dùng `--spark-local-dir` trỏ tới ổ còn nhiều chỗ trống và xóa các thư mục `blockmgr-*` cũ sau khi chắc chắn không còn Spark process. |

`16g` là cấu hình heap cho JVM, không phải giới hạn tổng RAM của cả chương trình. Python, dữ liệu trung gian và hệ điều hành vẫn cần bộ nhớ riêng.

## 9. Ghi kết quả vào báo cáo đồ án

Kết quả full đã triển khai được ghi dưới đây từ `reports/tables/full_iter_20260922_120859/als_tuning.csv`.

| `rank` | `regParam` | `maxIter` | RMSE validation | MAE validation | Coverage |
|---:|---:|---:|---|---|---|
| 16 | 0.08 | 5 | 0.833791 | 0.651167 | 99.7735% |
| 16 | 0.08 | 10 | 0.810538 | 0.624590 | 99.7735% |
| 16 | 0.08 | 15 | 0.803717 | 0.615847 | 99.7735% |
| 16 | 0.08 | **20 (chọn)** | **0.800952** | **0.612026** | **99.7735%** |

Báo cáo cần ghi rõ: cách chia dữ liệu, cấu hình máy, phiên bản thư viện, tham số cố định, tiêu chí chọn model và đường dẫn lần chạy. Chỉ báo cáo test cho model được chọn, kèm coverage và các giới hạn của cách đánh giá Top-K. `elapsed_seconds` là thời gian toàn pipeline; script chưa đo riêng thời gian fit từng cấu hình.

**Kết luận cần dựa trên kết quả:** “Model được chọn có `maxIter=...` vì đạt RMSE validation thấp nhất trong grid đã thử.” Chỉ bổ sung kết luận về chất lượng danh sách gợi ý sau khi có đánh giá Top-K đáng tin cậy và so sánh với baseline.
