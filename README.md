# 🀄 Website Học Từ Vựng Tiếng Trung Khung Đen (Batch OCR Vocab Extractor)

Hệ thống web chuyên dụng tự động nhận diện và trích xuất từ vựng tiếng Trung nằm **bên trong khung màu đen** từ hàng trăm ảnh cùng lúc, tạo Pinyin có dấu thanh Unicode chuẩn và dịch nghĩa tiếng Việt tự nhiên.

Hỗ trợ truy cập đa nền tảng: **Máy tính cá nhân**, **Điện thoại cùng mạng Wi-Fi**, và **Toàn bộ người dùng trên Internet qua URL Công khai**.

---

## 🌐 Các Đường Link Truy Cập Hệ Thống

| Phạm vi truy cập | Địa chỉ URL | Đối tượng sử dụng |
| :--- | :--- | :--- |
| **Public Internet (Toàn cầu)** | **[https://pressed-including-lock-nothing.trycloudflare.com](https://pressed-including-lock-nothing.trycloudflare.com)** | **Bất kỳ ai trên thế giới** (mở trên điện thoại 4G/5G, máy tính người khác, đối tác, bạn bè mà không cần cài đặt gì thêm). |
| **Mạng Wi-Fi nội bộ** | **[http://192.168.21.103:8000](http://192.168.21.103:8000)** | Các thiết bị (điện thoại, iPad, laptop khác) đang kết nối cùng mạng Wi-Fi. |
| **Máy tính hiện tại** | **[http://localhost:8000](http://localhost:8000)** | Trình duyệt trên máy tính đang chạy phần mềm. |

---

## 🌟 Tính Năng Nổi Bật

### 1. Nhận diện chuẩn xác trong khung màu đen (Chống nhiễu 100%)
* Sử dụng Computer Vision (OpenCV) phân tích contour và nhận diện viền hình chữ nhật màu đen.
* Tự động loại bỏ hoàn toàn các văn bản bên ngoài khung: câu ví dụ, bài văn đọc hiểu, ngữ pháp, giải thích.
* Tự động thụt lề (margin) và bóc tách nét chữ để tránh viền khung gây nhiễu cho mô hình OCR.

### 2. Pinyin chuẩn Unicode (Hanyu Pinyin Zhengcifa)
* Dấu thanh chuẩn Unicode: `ā ē ī ō ū`, `á é í ó ú`, `ǎ ě ǐ ǒ ǔ`, `à è ì ò ù`, `ü: ǖ ǘ ǚ ǜ`.
* Tuyệt đối không dùng ký hiệu số (`ni3 hao3`).
* Phân tách từ ghép và cụm từ tự nhiên:
  * `你好 → nǐ hǎo`
  * `学习 → xuéxí`
  * `喜欢 → xǐhuan`
  * `环境 → huánjìng`
  * `解释 → jiěshì`
  * `买房子 → mǎi fángzi`
  * `旅游 → lǚyóu`

### 3. Nghĩa tiếng Việt tự nhiên & chuẩn xác
* Tích hợp từ điển HSK 1–6 và từ vựng đời sống offline tốc độ tức thì.
* Tự động dịch và lưu bộ nhớ đệm (cache) cho các từ/cụm từ mới.
* Hỗ trợ người dùng tự điều chỉnh nghĩa và lưu vĩnh viễn.

### 4. Tối ưu cho xử lý hàng trăm ảnh cùng lúc
* **Hàng đợi song song không nghẽn DOM:** Hỗ trợ lựa chọn 2, 4, 6, hoặc 8 luồng song song (tận dụng 8 nhân CPU của máy).
* **Tiến trình thực tế:** Hiển thị phần trăm %, số lượng ảnh đã hoàn thành (`20 / 100`), bộ đếm thời gian thực và ước tính thời gian còn lại.
* **Xử lý độc lập:** Nếu 1 ảnh lỗi hoặc không tìm thấy khung, hệ thống không làm gián đoạn các ảnh còn lại; có nút thử lại (retry) riêng cho từng ảnh.
* **Chế độ nạp nối tiếp (Append Mode):** Cho phép kéo-thả thêm hàng chục ảnh mới mà không làm mất danh sách từ vựng đã xử lý trước đó.

### 5. Chống trùng lặp (Deduplication)
* Nếu cùng một từ xuất hiện trên nhiều ảnh khác nhau (ví dụ: `学习` xuất hiện 10 lần), danh sách cuối cùng mặc định **chỉ giữ lại 1 lần**.

### 6. Kiểm tra chất lượng & Sửa trực tiếp (Human in the loop)
* Cảnh báo `⚠️ Cần kiểm tra` đối với các từ có độ tin cậy thấp hoặc nghi ngờ lỗi OCR.
* Xem ảnh cắt khung đen gốc để đối chiếu bằng mắt.
* **Tự động cập nhật:** Khi sửa chữ Hán trong bảng, hệ thống lập tức tính toán lại Pinyin và Nghĩa tiếng Việt trong thời gian thực!
* Tích hợp nút phát âm giọng đọc tiếng Trung chuẩn (TTS).

### 7. Xuất kết quả linh hoạt (VOCABULARY LIST)
* Định dạng chuẩn từng dòng: `Pinyin — Nghĩa tiếng Việt`.
* Tùy chọn chuyển đổi định dạng: `Pinyin — Nghĩa` hoặc `Hán tự — Pinyin — Nghĩa`.
* Thanh tìm kiếm nhanh từ vựng (`Quick Search`).
* Nút **Copy all** (Sao chép toàn bộ vào clipboard).
* Tải về file **.txt** (chuẩn UTF-8 BOM, không lỗi font Notepad).
* Tải về file **.csv** (nhập ngay vào Anki, Quizlet, Excel).

---

## 🚀 Cách Khởi Động Ứng Dụng

### Cách 1: Click chạy file `run.bat`
Nhấp đúp vào file:
```
C:\Users\user\.gemini\antigravity\scratch\chinese-vocab-web\run.bat
```
File này sẽ tự động khởi động server trên `0.0.0.0:8000`, kích hoạt đường truyền Cloudflare Tunnel và mở trình duyệt.

### Cách 2: Chạy từ Terminal / PowerShell
```powershell
cd C:\Users\user\.gemini\antigravity\scratch\chinese-vocab-web
& "C:\Users\user\.gemini\antigravity\scratch\chinese_vocab_env\Scripts\python.exe" server_launcher.py
```
