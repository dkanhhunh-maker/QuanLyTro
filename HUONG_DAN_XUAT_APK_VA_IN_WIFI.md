# HƯỚNG DẪN ĐÓNG GÓI FILE `.APK` & IN NHIỆT WIFI CỔNG 9100 THẬT TRÊN ANDROID
**Tác giả ứng dụng:** Hoà Nguyễn (`0353633755`)

---

## TẠI SAO TRÊN TRÌNH DUYỆT WEB LẠI BỊ CHẶN KẾT NỐI MÁY IN?
Khi chạy trên trình duyệt web thông thường (Chrome/Safari), trình duyệt **cấm mở kết nối Raw TCP Socket tới cổng `9100`** của máy in nhiệt nội bộ (`192.168.2.60:9100`) vì lý do bảo mật trình duyệt.

Để in thật 100% ra máy in nhiệt WiFi khổ 80mm từ điện thoại Android, bạn có **2 cách cực kỳ đơn giản** dưới đây (cả 2 cách đều đã được tích hợp sẵn vào code của bạn):

---

## CÁCH 1: ĐÓNG GÓI RA FILE `QuanLyNhaTro.apk` (BẮN THẲNG TCP SOCKET 9100 THẬT 100%)

Bộ mã nguồn trong thư mục này đã tích hợp sẵn lớp cầu nối **`AndroidPrinterBridge` trong `MainActivity.java`** sử dụng `java.net.Socket` kết nối thẳng tới `IP:9100` (VD: `192.168.2.60:9100`) và đẩy trực tiếp lệnh cắt giấy ESC/POS khổ 80mm.

### Phương án A: Xuất file `.APK` tự động trên mạng (Không cần cài phần mềm nặng máy)
1. Tạo 1 tài khoản trên [GitHub.com](https://github.com) và tạo 1 Repository mới (VD: `quan-ly-nha-tro-apk`).
2. Giải nén toàn bộ file trong gói `QuanLyNhaTro_Android_APK.zip` này và tải (Upload) lên Repository đó.
3. Bấm vào tab **Actions** trên GitHub -> Chọn workflow **Build Android APK (Quan Ly Tro Hoa Nguyen)** -> Bấm **Run workflow**.
4. Sau khoảng 2 phút, GitHub sẽ biên dịch xong và xuất ra file **`QuanLyNhaTro_HoaNguyen_0353633755_APK.zip`** chứa file `app-debug.apk`. Bạn tải về điện thoại Android, bấm cài đặt là dùng in WiFi cổng 9100 trực tiếp 1 chạm!

### Phương án B: Xuất file `.APK` bằng Android Studio trên máy tính
1. Mở phần mềm **Android Studio** -> Chọn **Open** -> Chọn thư mục giải nén `QuanLyNhaTro_Android_APK`.
2. Đợi Gradle đồng bộ xong (khoảng 1-2 phút).
3. Trên thanh menu, chọn **Build** -> **Build Bundle(s) / APK(s)** -> **Build APK(s)**.
4. File `.apk` sẽ nằm tại: `app/build/outputs/apk/debug/app-debug.apk`. Chép file này qua Zalo vào điện thoại Android và cài đặt.

---

## CÁCH 2: IN THẬT NGAY LẬP TỨC TRÊN ANDROID KHÔNG CẦN CHỜ BUILD APK (QUA CẦU NỐI RAWBT)
Nếu bạn muốn in ngay lập tức trên điện thoại Android ngay bây giờ:
1. Mở **CH Play** trên điện thoại Android, tìm và cài đặt ứng dụng miễn phí **RawBT Print Service**.
2. Mở app **RawBT** -> Chọn **Connection method: WiFi / Ethernet** -> Nhập IP máy in của bạn (VD: `192.168.2.60`) và Port `9100`.
3. Mở ứng dụng Quản Lý Trọ của bạn -> Vào tab **Cài đặt** -> Bấm **⚙️ Cài đặt** ở mục Máy in WiFi 80mm -> Tại mục **Phương thức truyền lệnh in thật**, chọn **🚀 In trực tiếp qua App RawBT** rồi bấm **Lưu**.
4. Từ lúc này, mỗi khi bạn bấm **🖨️ In thử** hoặc **🖨️ In Bill WiFi 80mm**, ứng dụng sẽ truyền thẳng mã lệnh ESC/POS khổ 80mm sang RawBT và máy in nhiệt sẽ tự động in & cắt giấy ngay lập tức!
