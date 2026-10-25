# Trang phân tích Big Data trên CINE32

## Mở và trình chiếu

Chọn **Big Data** trên menu hoặc mở `/#analytics`. Trang có bốn mục:

1. **Dữ liệu MovieLens:** phân bố rating, số phim từng thể loại, rating theo năm và độ thưa ma trận user–phim.
2. **Hiệu năng Spark:** dung lượng CSV–Parquet theo từng bảng, trung vị thời gian truy vấn 32M rating và số liệu local[1/2/4].
3. **Kết quả ALS:** RMSE validation 5/10/15/20 vòng, kết quả test, train/validation/test và so sánh Precision/Recall/NDCG@10.
4. **Quy trình Big Data:** sơ đồ CSV → Parquet → Spark ALS → artifact → FastAPI/React, nhánh kiểm chứng HDFS và phân biệt ALS với hồ sơ Đã xem.

Chọn thanh/điểm biểu đồ để xem giá trị; nút **Xem bảng số liệu** hỗ trợ đối chiếu. Có thể dùng Tab và phím mũi tên để điều hướng các mục. **Tải số liệu JSON** xuất cùng dữ liệu tổng hợp mà trang sử dụng.

## Nguồn và giới hạn

Endpoint `GET /api/analytics` trả snapshot từ `assets/bigdata_analytics.json` khoảng 10 KB. Chỉ đọc tệp tổng hợp, không nạp model hoặc quét 32 triệu rating, phù hợp dịch vụ demo 512 MB. Trang ghi riêng ngày train, benchmark và kiểm chứng HDFS, đồng thời dẫn link tới các bảng gốc trong `reports/tables/`.

- Đây là kết quả offline, chưa phải số liệu user đang truy cập hoặc log xem trực tiếp.
- Phân bố dùng **32.000.204 rating nguồn**; fit model cuối dùng **28.709.236** dòng train + validation, giữ test riêng.
- Tổng thể loại có thể lớn hơn số phim vì một phim có nhiều nhãn. Năm 2023 chỉ có dữ liệu đến 13/10.
- Hiệu năng CSV–Parquet và Spark là đo local; một DataNode chưa chứng minh chịu lỗi nhiều máy. Model chưa train lại trên HDFS trong lần kiểm chứng này.
- RMSE và coverage có ý nghĩa khác nhau; metric ALS không phải chất lượng của gợi ý từ hồ sơ Đã xem.
- Popularity đang cao hơn ALS trong bảng Top K. Các tập ứng viên khác nhau và bộ lọc được điều chỉnh sau phân tích test, nên cần holdout mới và tập ứng viên chung trước khi kết luận.

## Tạo lại số liệu sau thí nghiệm mới

```powershell
py scripts/16_export_bigdata_analytics.py
py -m unittest discover -s tests -v
cd frontend
npm test
npm run build
```

Script xuất dùng thư viện chuẩn Python, đọc các CSV/JSON thực nghiệm, đối soát tổng phân bố và kích thước tập fit/test. Chạy script sau khi cập nhật bộ kết quả đầy đủ; không sửa tay số liệu hiển thị trong React. Tệp public không chứa rating cá nhân, tên hồ sơ, token hoặc đường dẫn tuyệt đối trên máy.

Docker sao chép snapshot từ mã nguồn và build frontend mới. Không cần huấn luyện lại hoặc sửa gói model v1.0.0 chỉ để thêm trang phân tích. Nguồn biểu đồ ở `frontend/src/BigDataAnalytics.tsx`, kiểu ở `frontend/src/types.ts`, API ở `web_api.py`.
