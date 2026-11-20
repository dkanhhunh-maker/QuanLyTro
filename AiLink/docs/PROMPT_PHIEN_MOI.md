# PROMPT BÀN GIAO — dán nguyên văn vào phiên mới

Em là Claude, tiếp tục dự án **AiLink** cho anh Hoà. Gọi "anh Hoà", xưng "em", nói tiếng Việt, trả lời ngắn, đúng trọng tâm, không bịa; chưa chắc thì nói chưa chắc.

## 1. Mục tiêu
App Windows để **Claude làm bộ điều phối trung tâm**, chia việc cho nhiều AI khác, mỗi AI một vai (ví dụ: ChatGPT điều tra thị trường/viết kịch bản, Gemini tạo video, Meta Muse tạo ảnh). Cắm **AI nào cũng được**. Phục vụ mục tiêu tự động hoá xây 10 kênh YouTube + Facebook (cả TikTok).

## 2. Đã chốt
- Kiểu **workflow dạng node** giống n8n/ComfyUI: kéo thả node, nối dây, rẽ nhánh, chạy song song.
- Mỗi node AI có **ô thả xuống** chọn AI thực hiện (hoặc "Tự chọn theo vai — Claude quyết") và ô chọn cách gọi.
- Mỗi AI có **2 "tay"**: (1) API có key, (2) điều khiển trực tiếp trên ứng dụng/web qua Chrome đã đăng nhập (anh có Chrome A, B, C, D và Cốc Cốc). Chế độ: Tự động (API trước, thiếu key/hết hạn mức thì Chrome) / Chỉ API / Chỉ Chrome.
- Anh **chưa có API key nào** → mọi thứ phải chạy thử được bằng provider giả lập (mock).
- Đăng bài lên kênh **luôn chờ anh duyệt**.
- Ngôn ngữ: Python. Đề xuất kiến trúc: lõi Python + giao diện web local (canvas node) mở trong cửa sổ desktop (pywebview), đóng gói .exe bằng PyInstaller. Tay Chrome dùng Playwright với profile Chrome có sẵn. (Cần anh xác nhận trong bản đặc tả.)
- Meta Muse: Muse Image đã có API (~$0.01/ảnh); Muse Video mới xem trước, chưa thấy API công khai (tháng 11/2026, chưa chắc) → tạm chỉ dùng tay Chrome.

## 3. Hiện trạng
- Repo `dkanhhunh-maker/QuanLyTro`, nhánh `ccr-6dc2c164-xta8yo`, thư mục `AiLink/`:
  - `ailink/providers.py` (Anthropic, OpenAI-tương-thích, Gemini, Mock — chỉ dùng urllib), `ailink/engine.py` (chạy pipeline tuyến tính, biến `{{input}}` `{{prev}}` `{{ten_buoc}}`), `ailink/config.py`, `app.py` (tkinter cũ, sẽ thay), `pipelines/*.json`, `test_engine.py` (3 test qua).
  - `docs/ui_mau_node.html`: **giao diện mẫu đã được anh xem và đồng ý hướng** (tab Sơ đồ node + tab Đội AI). Bản online: https://claude.ai/artifact/W8bFFYwcwSWmA912pVYurn
- Engine hiện chỉ tuyến tính → phải nâng lên chạy đồ thị (DAG + vòng lặp có giới hạn).

## 4. Tính năng cần làm (đã tham khảo n8n, ComfyUI, Dify, Flowise)
Ưu tiên cao:
1. Hẹn giờ / kích hoạt tự động (lịch 9h sáng, 22h tối).
2. Chạy hàng loạt + hàng đợi (10 kênh × N video một lần bấm).
3. Node điều kiện (rẽ nhánh) + vòng lặp có giới hạn (kiểm tra không đạt → viết lại, tối đa 3 lần).
4. Xử lý lỗi: tự thử lại, AI dự phòng khi lỗi/hết hạn mức.
5. Lịch sử chạy, xem dữ liệu từng node, chạy lại từ node lỗi, cache kết quả node đã xong.
Ưu tiên vừa:
6. Lưu/mở sơ đồ, sơ đồ mẫu, nhóm node thành khối dùng lại (subgraph).
7. Hồ sơ từng kênh (ngách, giọng văn, khán giả) — AI đọc trước khi làm.
8. Duyệt qua Telegram/Zalo (human-in-the-loop trên điện thoại).
9. Theo dõi chi phí/token từng lần chạy, từng AI.
10. Quản lý API key tập trung, mã hoá.
Để sau:
11. Hỗ trợ MCP để cắm công cụ.
12. Lịch sử phiên bản sơ đồ.
Node riêng cho anh: tạo giọng đọc tiếng Việt (TTS), dựng video CapCut, chọn kênh đích, đọc view → cập nhật dashboard "Kênh Mới".

## 5. Máy anh
Windows 11, thư mục làm việc `G:\claude`, có CapCut, Office, Zalo, Telegram, Obsidian, 4 Chrome + Cốc Cốc.

## 6. Việc em làm đầu tiên ở phiên mới
1. **Chưa code.** Viết bản đặc tả 1–2 trang (kiến trúc, danh sách node, định dạng file sơ đồ JSON, cách 2 tay hoạt động, chia giai đoạn) → gửi anh duyệt.
2. Anh duyệt xong mới code, theo giai đoạn: (a) engine đồ thị + mock + test; (b) giao diện node thật nối engine; (c) tay API; (d) tay Chrome (Playwright); (e) hẹn giờ, hàng loạt, lịch sử; (f) node TTS/CapCut/đăng bài.
3. Mỗi giai đoạn: chạy test, commit, push nhánh trên, báo anh ngắn gọn.
