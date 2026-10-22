# Demo tạo user và gợi ý từ thể loại đã xem

## 1. Các chức năng đã bổ sung

- Tạo tối đa 12 hồ sơ người dùng bằng tên và chuyển giữa các hồ sơ.
- Mở chi tiết phim, bấm **Đánh dấu đã xem**; bấm lại để bỏ đánh dấu.
- Mỗi hồ sơ lưu lịch sử riêng, tối đa 1.000 phim. Một phim chỉ được tính một lần.
- Thống kê thể loại dựa trên phim thực sự được đánh dấu. Mở chi tiết hoặc lọc thể loại không tự ghi lịch sử.
- Gợi ý 12 phim chưa xem, ưu tiên thể loại xuất hiện nhiều trong lịch sử; dùng điểm cộng đồng và số lượt chấm để sắp xếp khi mức phù hợp bằng nhau.
- User chưa có lịch sử nhận danh sách cộng đồng để bắt đầu khám phá.

**Phạm vi:** đây là hồ sơ demo, không yêu cầu mật khẩu. Tên, mã hồ sơ và lịch sử được lưu bằng localStorage trên trình duyệt đang dùng; không đồng bộ sang máy hoặc trình duyệt khác. Xóa dữ liệu website sẽ mất hồ sơ. Render khởi động lại không xóa localStorage trên máy trình chiếu.

## 2. Kịch bản trình chiếu khoảng 3 phút

1. Mở CINE32, chọn **Cho bạn**, nhập tên **Minh**, bấm **Tạo hồ sơ**.
2. Tìm **The Terminator**, mở chi tiết và bấm **Đánh dấu đã xem**.
3. Làm tương tự với **Terminator 2: Judgment Day**.
4. Trở lại **Cho bạn**: Minh có 2 phim đã xem; thể loại Hành động và Khoa học viễn tưởng tăng lên. Hai phim đã đánh dấu không còn trong gợi ý.
5. Bấm **Tạo user mới**, đặt tên **Lan**. Lan bắt đầu với lịch sử trống.
6. Tìm **Home Alone**, mở chi tiết, đánh dấu đã xem. Hồ sơ Lan ghi nhận Thiếu nhi và Hài; gợi ý thay đổi theo lịch sử này.
7. Chuyển về **Minh** bằng danh sách chọn hồ sơ. Lịch sử và thể loại của Minh vẫn được giữ riêng.
8. Tải lại trang để chứng minh dữ liệu được lưu. Có thể mở lịch sử và **Bỏ đã xem** để minh họa thống kê cập nhật theo việc thay đổi lịch sử.

Một phim có thể thuộc nhiều thể loại, nên tổng số đếm thể loại có thể lớn hơn số phim đã xem. Ví dụ, một phim Hành động + Hài sẽ đóng góp một lượt cho cả hai thể loại.

## 3. Cách hệ thống tạo gợi ý

```text
Hồ sơ đang chọn
    → Các movieId đã đánh dấu Đã xem
    → Backend tra thể loại từ catalog MovieLens
    → Đếm số phim của từng thể loại
    → Tính mức phù hợp theo tần suất thể loại trong lịch sử
    → Loại phim đã xem, xếp hạng phim còn lại
    → Trả 12 gợi ý kèm poster và lý do
```

Tập ứng viên ưu tiên phim có ít nhất 100 lượt đánh giá. Mức phù hợp là trung bình tần suất các thể loại của phim trong lịch sử user. Phim nhiều thể loại không tự được cộng điểm chỉ vì có nhiều nhãn. Khi hết ứng viên đủ điều kiện, hệ thống mở rộng sang các phim chưa xem khác.

Backend lấy thể loại từ catalog, không nhận số đếm thể loại do client tự khai báo. ID trùng được khử trước khi đếm; phim không có trong catalog được bỏ qua. Không có tên hoặc mã hồ sơ gửi lên API gợi ý, chỉ có danh sách movieId.

**Phân biệt với ALS:** phần **Cho bạn** dùng lịch sử đánh dấu và thể loại để đáp ứng demo user mới. Phần **Demo ALS** vẫn dùng vector mô hình đã train trên MovieLens và chỉ nạp khi được mở. Việc đánh dấu Đã xem không huấn luyện lại ALS và không tạo vector ALS mới cho hồ sơ demo.

## 4. API và mã nguồn

`POST /api/demo/recommendations`

```json
{"movie_ids": [1240, 589]}
```

Các ID trên là ví dụ The Terminator và Terminator 2 trong MovieLens. Body nhận tối đa 1.000 ID nguyên dương; danh sách theo thứ tự đánh dấu từ cũ đến mới.

Phản hồi gồm `items`, `history` (tối đa 12 phim gần nhất), `watchedCount`, `genres` (mã, tên và số phim), `strategy`, `message` và trạng thái poster. Phim gợi ý có lý do `recommendationReason`; không gán điểm ALS cho luồng này.

- [Lưu và chuyển hồ sơ](frontend/src/demoProfilesStore.ts).
- [Giao diện hồ sơ và nút Đã xem](frontend/src/DemoProfiles.tsx).
- [Giao diện gợi ý theo lịch sử](frontend/src/DemoRecommendations.tsx).
- [Tính gợi ý từ thể loại](src/recommender/history_recommender.py).
- [API](web_api.py).

## 5. Chạy trên máy trình chiếu

Chuẩn bị catalog/model theo [hướng dẫn demo](HUONG_DAN_CHAY_DEMO.md), rồi build lại giao diện mới:

```powershell
Set-Location frontend
npm ci
npm test
npm run build
Set-Location ..
python -m uvicorn web_api:app --host 127.0.0.1 --port 8502
```

Lưu ý nguồn dữ liệu hồ sơ được phân biệt theo origin: `http://127.0.0.1:8502` và website Render có kho hồ sơ riêng. Khi bảo vệ, dùng một địa chỉ cố định và cùng một trình duyệt để giữ các hồ sơ đã chuẩn bị.

Docker đã chuyển sang build frontend từ mã nguồn trong repository. Catalog và vector ALS tiếp tục lấy từ gói v1.0.0 có kiểm tra checksum; không cần train lại model.

## 6. Kiểm tra

- Backend: `python -m unittest discover -s tests -v` — 19 bài kiểm tra đạt khi bổ sung chức năng.
- Frontend: `npm test` trong `frontend/` — 4 bài kiểm tra về tách lịch sử, lưu/tải lại, đánh dấu lặp và dữ liệu lỗi.
- `npm run build` đạt.
- Kiểm tra trình duyệt: tạo Minh/Lan, đánh dấu phim, chuyển hồ sơ và tải lại trang. Trước buổi trình chiếu cần mở lại website và kiểm tra poster/kết nối Internet.

**Đã triển khai ngày 22/10/2026:** [mở mục Cho bạn trên CINE32](https://cine32-movie-recommender.onrender.com/#personalized). Render đã báo Live cho commit `4ccd237`; [kiểm tra Docker Linux giới hạn 512 MB](https://github.com/Sang6215/movielens-32m-movie-recommender/actions/runs/39710275929) đạt, gồm cả frontend mới và API gợi ý từ lịch sử. Kiểm tra trên website thật xác nhận tạo Minh/Lan, lịch sử riêng, bỏ đánh dấu và giữ hồ sơ sau tải lại.
