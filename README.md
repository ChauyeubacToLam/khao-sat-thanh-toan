# Khảo sát sự hài lòng với thanh toán tự phục vụ

Bảng hỏi trực tuyến cho nghiên cứu về sự hài lòng của khách hàng với các giải pháp
thanh toán tự phục vụ tại cửa hàng bán lẻ Việt Nam.

## Nội dung

38 item thang đo Likert 5 mức, thuộc 10 khái niệm:

| Mã | Khái niệm | Nguồn thang đo |
|---|---|---|
| EFF | Tính hiệu quả | SSTQUAL, Lin & Hsieh (2011) |
| REL | Độ tin cậy hệ thống | Dabholkar (1996) |
| SEC | An toàn và bảo mật | SSTQUAL, Lin & Hsieh (2011) |
| STF | Hỗ trợ của nhân viên | e-SELFQUAL, Ding, Hu & Sheng (2011) |
| PCT | Cảm nhận quyền kiểm soát | Collier & Sherrell (2010) |
| PRK | Rủi ro sai sót thanh toán | Featherman & Pavlou (2003) |
| TAX | Lo ngại công nghệ | Meuter và cộng sự (2003) |
| SAT | Hài lòng | Bhattacherjee (2001) |
| CI | Ý định tiếp tục dùng | Bhattacherjee (2001) |
| WOM | Truyền miệng tích cực | Zeithaml và cộng sự (1996) |

Các thang gốc đều dùng 7 mức và đã được chuyển về 5 mức. Cần khai báo điều này trong
phần Phương pháp nghiên cứu.

## Cơ chế chống trả lời qua loa

Hai lớp. Lớp một nhắc ngay lúc người dùng đang điền, giọng nhẹ, không chặn ai, mục tiêu
là cứu phiếu tại chỗ thay vì loại sau khi gửi. Lớp hai chấm điểm khi nhận phiếu.

Các dấu hiệu được phát hiện:

- Câu bẫy trực tiếp: `AC1` phải chọn mức 2, `AC2` mức 4, `BOG` là câu vô lý
- Cặp đồng nghĩa `SYN1` và `SYN2` phải trả lời gần nhau
- Cặp trái nghĩa `ANT1` và `ANT2` phải trả lời ngược nhau
- Chọn cùng một mức cho nhiều câu liền nhau
- Phương sai quá thấp (điền một cột) hoặc quá cao (bấm ngẫu nhiên)
- Kiểu zigzag và chuỗi lặp theo chu kỳ
- Đáp án tán loạn trong cùng một khái niệm
- Thời gian tổng, thời gian mỗi câu, thời gian từng trang
- Số lần rời khỏi tab

Ngưỡng tham khảo Meade & Craig (2012) và Curran (2016). Mỗi phiếu được xếp loại
`PASS`, `REVIEW` hoặc `FAIL` kèm lý do cụ thể.

Thứ tự item trong mỗi khối được trộn ngẫu nhiên cho từng người trả lời.

## Cấu trúc

```
index.html          giao diện, tĩnh
survey.js           toàn bộ nội dung bảng hỏi
quality.py          logic chấm điểm, dùng chung cho cả hai môi trường
api/submit.py       hàm serverless trên Vercel, ghi vào Google Sheets
server.py           server chạy trên máy để phát triển và thử
make_docx.py        xuất bảng hỏi ra file Word, đọc thẳng từ survey.js
```

## Chạy trên máy

```bash
python server.py
```

Bảng hỏi ở http://localhost:8000, bảng theo dõi chất lượng ở `/admin`, xuất CSV ở
`/export.csv`. Dữ liệu ghi vào `responses.jsonl` ngay trong thư mục.

## Triển khai trên Vercel

Cần hai biến môi trường:

| Tên | Nội dung |
|---|---|
| `SHEET_ID` | mã Google Sheet, lấy trong đường dẫn của Sheet |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | toàn bộ nội dung file khoá JSON của service account |

Nhớ chia sẻ Sheet cho địa chỉ `client_email` trong file khoá với quyền Người chỉnh sửa,
và đổi tên tab thành `responses`.

Trên Vercel không có `/admin` và `/export.csv`. Google Sheet đã làm sẵn hai việc đó, và
quyền truy cập do Google quản lý nên an toàn hơn.

## Sửa nội dung bảng hỏi

Sửa trong `survey.js`. Bản web cập nhật ngay, bản Word chạy lại `python make_docx.py`
là khớp theo. Nếu thêm hoặc bớt item, nhớ cập nhật `BLOCKS` trong `api/submit.py` cho
đúng số cột của Sheet.
