# AiLink — Claude điều phối nhiều AI làm video cho nhiều kênh

App Windows: vẽ dây chuyền bằng sơ đồ node, bấm chạy hoặc hẹn giờ, anh Hoà chỉ việc duyệt trước khi đăng.
Bản đặc tả v1: https://claude.ai/artifact/PgKkVHyr1i4EQdcyjycBWX

## Trạng thái

| Giai đoạn | Nội dung | Trạng thái |
| --- | --- | --- |
| 1 | Engine đồ thị + AI giả lập + 40 loại node + 9 sơ đồ mẫu | **Xong**, 33 test qua |
| 2 | Giao diện node thật (pywebview), tab Sơ đồ / Kênh / Duyệt, 4 chủ đề, hiệu ứng sạc điện | Đang làm |
| 3–7 | Tay API, tay Chrome, hẹn giờ + Telegram, âm thanh + CapCut + đăng bài, đa ngôn ngữ | Chưa |

Quyết định đã duyệt: kiến trúc Python + giao diện web trong cửa sổ riêng + .exe; 3 thị trường đầu VN, US, JP;
Telegram là kênh duyệt chính, Zalo chỉ báo tin; trần chi phí mặc định 5 USD/ngày, 100 USD/tháng (sửa trong cai_dat.json).

## Chạy thử (không cần key, không tốn tiền)

    cd AiLink
    python -m ailink node                                    # xem 40 loại node + ví dụ
    python -m ailink chay mau/short_youtube.ailink.json "Bí ẩn tam giác Bermuda" --kenh vn_chuyen_la
    python -m ailink duyet <id_lan> duyet duyet              # anh bấm Duyệt (hoặc sua "yêu cầu" / bo)
    python -m ailink chay mau/bao_cao_sang_9h.ailink.json    # AI báo cáo 9h sáng
    python -m unittest discover -s tests                     # chạy test

Chưa có key thì mọi node AI tự rơi về **AI giả lập** và ghi cảnh báo. Dữ liệu nằm ở `G:\claude\AiLink`
(hoặc biến môi trường `AILINK_HOME`): `so_do\ kenh\ lan_chay\ cache\ xuat\ kich_ban_chrome\`.

## Sơ đồ mẫu (`mau/`)

| File | Làm gì |
| --- | --- |
| `short_youtube` | Kịch bản → AI chấm (viết lại tối đa 3 lần) → tiêu đề + ảnh + giọng + thumbnail song song → **kiểm duyệt** → chờ duyệt → đăng |
| `bao_cao_sang_9h` | Đọc view mọi kênh + nghiên cứu ngách + tin AI → **AI báo cáo** → Telegram + file .md + dashboard |
| `kiem_duyet_noi_dung` | Dán nội dung có sẵn → **kiểm duyệt 2 lớp** → đạt / AI viết bản sửa và báo anh |
| `khoi_kiem_tra` | Khối con dùng lại: kiểm tra chất lượng + kiểm duyệt |
| `nhan_ban_ngon_ngu` | 1 nội dung → Cho mỗi [vi, en, ja]: dịch → giọng → kiểm duyệt → gộp → duyệt → đăng |
| `hang_loat_moi_kenh` | Cho mỗi kênh: hồ sơ → ngách → viết → khối kiểm tra → **duyệt riêng từng kênh** → đăng → AI báo cáo lần chạy |
| `phien_dich_video` | Video nước ngoài (bắt buộc ghi loại nguồn) → tách lời → dịch → .srt + lồng tiếng → kiểm duyệt → duyệt |
| `tra_loi_binh_luan` | Bình luận → AI soạn trả lời theo giọng kênh → kiểm duyệt → duyệt |
| `phan_loai_y_tuong` | AI phân loại Short / Dài → mỗi nhãn 1 nhánh → gộp nhánh xong trước → AI báo cáo |

Hồ sơ kênh mẫu (`kenh_mau/`: VN, US, JP) chỉ để minh hoạ, không phải kênh thật.

## Node ví dụ: AI báo cáo và Kiểm duyệt

**AI báo cáo (`bao_cao_ai`)** — gom mọi dữ liệu nối vào rồi viết báo cáo theo mẫu `sang_9h`, `kenh`, `tuan`,
`chi_phi`, `lan_chay` hoặc tự đặt `muc`. Định dạng Telegram hoặc Markdown, lưu `.md` vào `xuat\bao_cao\`.
Lệnh gửi AI dặn rõ: chỉ dùng số liệu có trong dữ liệu, thiếu thì ghi "chưa có số liệu", không bịa.

```json
{"id": "bao_cao", "loai": "bao_cao_ai",
 "cai_dat": {"loai": "sang_9h", "dinh_dang": "telegram", "do_dai": "vua", "luu_file": true}}
```

**Kiểm duyệt (`kiem_duyet`)** — 3 cổng ra `dat` / `can_xem` / `chan`, 2 lớp:
- Lớp luật (không cần AI, không tốn tiền): điều cấm trong hồ sơ kênh, cụm từ spam / hứa hẹn quá mức,
  video nguồn "chưa rõ" bản quyền, tiêu đề > 100 ký tự, mô tả > 5.000 ký tự (giới hạn YouTube),
  số điện thoại, link lạ, tiêu đề viết hoa toàn bộ.
- Lớp AI: chấm rủi ro 0–100 theo chính sách nền tảng (bạo lực, thù ghét, người lớn, tin sai, bản quyền,
  clickbait, nội dung dùng lại / AI hàng loạt, nội dung trẻ em, điều cấm của kênh).

```json
{"id": "kiem_duyet", "loai": "kiem_duyet",
 "cai_dat": {"nen_tang": ["youtube", "facebook"], "tu_cam": ["giảm cân thần tốc"],
             "nguong_rui_ro": {"can_xem": 30, "chan": 70}}},
{"tu": "kiem_duyet", "cong": "dat",     "den": "duyet"},
{"tu": "kiem_duyet", "cong": "can_xem", "den": "duyet"},
{"tu": "kiem_duyet", "cong": "chan",    "den": "viet", "lap_toi_da": 2}
```

Node **Đăng bài** tự chặn khi: chưa có bước Chờ duyệt được anh bấm Duyệt, Kiểm duyệt ra `chan`,
hoặc có video nguồn "chưa rõ". Sơ đồ có Đăng bài mà không có Chờ duyệt phía trước thì không mở được.

## 40 loại node

| Nhóm | Node | Giai đoạn | Ví dụ |
| --- | --- | --- | --- |
| Điều khiển | `bat_dau` Bắt đầu tay | 1 | Đầu mọi sơ đồ chạy tay. Kết quả là {{input}}. |
| Điều khiển | `hen_gio` Hẹn giờ | 5 | Báo cáo 9h sáng mỗi ngày; lưu nhật ký 22h. |
| Điều khiển | `dieu_kien` Điều kiện | 1 | Điểm kiểm tra >= 8 thì đi tiếp, không thì quay lại viết lại (dây quay ngược tối đa 3 lần). |
| Điều khiển | `vong_lap` Vòng lặp | 1 | Tạo 3 bản thumbnail khác nhau rồi đưa cả 3 cho AI chọn. |
| Điều khiển | `cho_moi` Cho mỗi | 1 | Mỗi ngôn ngữ [vi, en, ja]: dịch → giọng đọc → dựng. Gộp lại 3 bản. |
| Điều khiển | `gop` Gộp | 1 | Gộp kịch bản + ảnh + giọng trước khi dựng; hoặc gom kết quả của Cho mỗi. |
| Điều khiển | `chon_kenh` Chọn kênh đích | 2 | Trong Cho mỗi kênh: kenh = {{phan_tu}}. |
| Điều khiển | `khoi_con` Khối con | 5 | Khối 'Kiểm tra + Kiểm duyệt' dùng chung cho mọi dây chuyền. |
| Chữ | `hoi_ai` Hỏi AI | 1 | Bất cứ việc chữ nào chưa có node riêng: viết caption, đặt câu hỏi, đổi giọng văn. |
| Chữ | `nghien_cuu_ngach` Nghiên cứu ngách | 3 | 9h sáng: tìm 10 chủ đề đang lên ở thị trường JP cho ngách chuyện bí ẩn. |
| Chữ | `kich_ban_short` Viết kịch bản Short | 3 | Ý tưởng → kịch bản 45 giây cho Shorts/Reels/TikTok. |
| Chữ | `kich_ban_dai` Viết kịch bản Dài | 3 | Chủ đề → kịch bản 12 phút có chương và mốc thời gian. |
| Chữ | `kiem_tra_chat_luong` Kiểm tra chất lượng | 3 | Chấm kịch bản: câu móc mạnh không, đúng ngách không, đọc tự nhiên với người bản xứ không. |
| Chữ | `tieu_de_mo_ta` Tiêu đề, mô tả, hashtag | 3 | Kịch bản → 1 tiêu đề ≤ 60 ký tự, mô tả có mốc thời gian, 10 hashtag, giờ đăng theo múi giờ nước đó. |
| Chữ | `dich` Dịch / bản địa hoá | 7 | Kịch bản tiếng Việt → tiếng Nhật cho kênh JP (trong Cho mỗi ngôn ngữ: den = {{phan_tu}}). |
| Chữ | `tach_loi` Tách lời video | 7 (giả lập) | Video nước ngoài → lời gốc có mốc thời gian để dịch và lồng tiếng. |
| AI phân tích | `bao_cao_ai` AI báo cáo | 1 | 9h sáng: Đọc view 10 kênh + Nghiên cứu ngách + Hỏi AI tin AI/YouTube → AI báo cáo (sang_9h) → Nhắn tin Telegram + lưu G:\claude\AiLink\xuat\bao_cao\. |
| AI phân tích | `tom_tat` Tóm tắt | 1 | Tóm tắt 20 tin AI trong ngày thành 5 ý cho báo cáo sáng. |
| AI phân tích | `phan_loai` Phân loại | 1 | Ý tưởng → nhãn short / dai / ca_hai → mỗi nhãn đi dây chuyền riêng. |
| AI phân tích | `phan_tich_doi_thu` Phân tích đối thủ | 3 | Mỗi thứ Hai: phân tích 3 kênh đối thủ ngách bí ẩn JP → gợi ý 5 video lấp khoảng trống. |
| AI phân tích | `tra_loi_binh_luan` Trả lời bình luận | 6 | Đọc 50 bình luận mới → soạn trả lời → Chờ duyệt → (giai đoạn 6) đăng trả lời. |
| Ảnh | `tao_anh` Tạo ảnh | 3 (giả lập) | Kịch bản 6 cảnh → 6 ảnh 9:16 cùng phong cách. |
| Ảnh | `thumbnail` Thumbnail | 3 (giả lập) | Tiêu đề → thumbnail chữ to 3–5 từ tiếng Nhật. |
| Video | `tao_video` Tạo video AI | 4 (giả lập) | Mỗi cảnh 1 đoạn 5 giây từ ảnh minh hoạ. |
| Video | `dung_capcut` Dựng CapCut | 6 (giả lập) | Gộp (ảnh + giọng + phụ đề) → video 9:16 hoàn chỉnh. |
| Video | `cat_short` Cắt Short từ video dài | 7 (giả lập) | Chế độ 'Cả hai': video dài → 3 Short. |
| Video | `chen_phu_de` Chèn phụ đề | 7 | Tách lời → Dịch → Chèn phụ đề (.srt tiếng Việt). |
| Video | `tai_video_nguon` Tải video nguồn | 7 (giả lập) | Phiên dịch video nước ngoài: link → tách lời → dịch → lồng tiếng. |
| Giọng | `giong_doc` Giọng đọc TTS | 6 (giả lập) | Kịch bản tiếng Nhật → giọng nam trầm của kênh JP. |
| Giọng | `app_am_thanh` App âm thanh ngoài | 6 (giả lập) | Nhạc nền 60 giây không lời cho Short. |
| Giọng | `long_tieng` Lồng tiếng | 7 (giả lập) | Bản dịch tiếng Việt + nhạc nền đã tách → video lồng tiếng Việt. |
| Giọng | `tach_giong` Tách giọng / nhạc | 7 (giả lập) | Trước Lồng tiếng: giữ nhạc nền, bỏ giọng gốc. |
| Duyệt | `kiem_duyet` Kiểm duyệt nội dung | 1 | Kịch bản + tiêu đề → Kiểm duyệt: dat → Chờ duyệt; can_xem → Chờ duyệt kèm cảnh báo; chan → quay lại viết lại (tối đa 2 lần) hoặc Nhắn tin báo anh. |
| Duyệt | `cho_duyet` Chờ anh duyệt | 2 | Trước mọi node Đăng bài. Cổng 'sua' nối ngược về Viết kịch bản (tối đa 3 lần). |
| Duyệt | `dang_bai` Đăng bài | 6 (giả lập) | Sau Chờ duyệt (cổng duyet): đăng ngay hoặc hẹn giờ theo múi giờ thị trường. |
| Theo dõi | `doc_view` Đọc view | 6 (giả lập) | 9h sáng: đọc view 10 kênh → AI báo cáo. |
| Theo dõi | `cap_nhat_dashboard` Cập nhật dashboard | 6 | Sau Đọc view: cập nhật bảng 10 kênh. |
| Tiện ích | `doc_ghi_file` Đọc / ghi file | 1 | Ghi kịch bản đã duyệt vào G:\claude\kich_ban\{{ngay}}.md; đọc danh sách ý tưởng từ Obsidian. |
| Tiện ích | `chay_lenh` Chạy lệnh máy | 6 (giả lập) | ffmpeg ghép ảnh + giọng thành video. |
| Tiện ích | `nhan_tin` Nhắn tin | 5 (giả lập) | Gửi báo cáo 9h; báo lỗi; báo có video chờ duyệt. |

"(giả lập)": giai đoạn này node chạy giả lập để dây chuyền chạy hết; bản thật làm ở giai đoạn ghi bên cạnh.

## File sơ đồ `.ailink.json`

```json
{"phien_ban": 1, "ten": "...",
 "nodes": [{"id": "viet", "loai": "kich_ban_short", "cai_dat": {"do_dai_giay": 45}, "vi_tri": [240, 200]}],
 "day":   [{"tu": "kiem_tra", "cong": "khong_dat", "den": "viet", "lap_toi_da": 3}]}
```

Biến trong lệnh: `{{input}}`, `{{prev}}`, `{{id_node}}`, `{{id_node.truong}}`, `{{kenh.ngach}}`, `{{ngay}}`,
`{{phan_tu}}`, `{{chi_so}}` (trong Cho mỗi), `{{phan_hoi}}`, `{{lan_lap}}` (khi bị gửi ngược về để sửa),
`{{cai_dat.x}}`.

## Mã nguồn

- `ailink/engine.py` — engine đồ thị: song song, rẽ nhánh, vòng lặp giới hạn, Cho mỗi, cache, lưu sau mỗi node, chạy tiếp, chạy lại, duyệt.
- `ailink/so_do.py` — đọc + kiểm tra file sơ đồ.
- `ailink/nodes/` — 40 loại node theo nhóm.
- `ailink/doi_ai.py` — Đội AI: chọn theo vai, thử lại, chuyển tay, AI dự phòng, rơi về giả lập.
- `ailink/providers.py` — tay API (Claude, kiểu OpenAI, Gemini) + AI giả lập. `ailink/kho_key.py` — key qua Windows Credential Manager.
- `ailink/kenh.py` — hồ sơ kênh. `tools/tao_mau.py` — sinh sơ đồ mẫu.
