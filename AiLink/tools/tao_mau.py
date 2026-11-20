"""Sinh các sơ đồ mẫu trong mau/. Chạy từ thư mục AiLink: python tools/tao_mau.py"""
import json, os
def N(_i, _l, x, y, **cd): return {"id": _i, "loai": _l, "cai_dat": cd, "vi_tri": [x, y]}
def D(tu, den, cong=None, lap=None):
    d = {"tu": tu, "den": den}
    if cong: d["cong"] = cong
    if lap: d["lap_toi_da"] = lap
    return d
def W(fn, ten, mo_ta, nodes, day):
    os.makedirs("mau", exist_ok=True)
    data = {"phien_ban": 1, "ten": ten, "mo_ta": mo_ta, "nodes": nodes, "day": day}
    with open(f"mau/{fn}.ailink.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

W("short_youtube", "Short YouTube: ý tưởng → bài đăng",
  "Viết kịch bản Short, AI chấm (không đạt thì viết lại tối đa 3 lần), làm tiêu đề + ảnh + giọng + thumbnail song song, kiểm duyệt, chờ anh duyệt rồi mới đăng.",
  [N("bat_dau", "bat_dau", 40, 200, goi_y_nhap="Chủ đề Short"),
   N("viet", "kich_ban_short", 240, 200, do_dai_giay=45, ai="tu_chon"),
   N("kiem_tra", "kiem_tra_chat_luong", 440, 200, nguong=8),
   N("tieu_de", "tieu_de_mo_ta", 660, 60),
   N("anh", "tao_anh", 660, 170, khung="9:16"),
   N("giong", "giong_doc", 660, 280),
   N("thumb", "thumbnail", 880, 60, khung="9:16", chu_tren_anh="{{tieu_de.tieu_de}}"),
   N("gom", "gop", 1080, 200, che_do="cho_tat_ca", kieu="doi_tuong"),
   N("kiem_duyet", "kiem_duyet", 1280, 200, nen_tang=["youtube", "facebook", "tiktok"]),
   N("duyet", "cho_duyet", 1480, 200),
   N("dang", "dang_bai", 1680, 200, nen_tang=["youtube"])],
  [D("bat_dau", "viet"), D("viet", "kiem_tra"),
   D("kiem_tra", "viet", "khong_dat", 3),
   D("kiem_tra", "tieu_de", "dat"), D("kiem_tra", "anh", "dat"), D("kiem_tra", "giong", "dat"), D("kiem_tra", "gom", "dat"),
   D("tieu_de", "thumb"), D("tieu_de", "gom"), D("anh", "gom"), D("giong", "gom"), D("thumb", "gom"),
   D("gom", "kiem_duyet"),
   D("kiem_duyet", "duyet", "dat"), D("kiem_duyet", "duyet", "can_xem"), D("kiem_duyet", "viet", "chan", 2),
   D("duyet", "dang", "duyet"), D("duyet", "viet", "sua", 3)])

W("bao_cao_sang_9h", "Báo cáo 9h sáng",
  "Đọc view mọi kênh + nghiên cứu ngách + tin AI/YouTube → AI báo cáo gửi Telegram, lưu file .md, cập nhật dashboard Kênh Mới.",
  [N("hen_gio", "hen_gio", 40, 200, lich={"kieu": "hang_ngay", "gio": "09:00"}, dau_vao="Báo cáo sáng"),
   N("view", "doc_view", 260, 60, kenh="tat_ca", khoang="24h"),
   N("ngach", "nghien_cuu_ngach", 260, 200, so_y_tuong=5),
   N("tin_ai", "hoi_ai", 260, 340, vai="nghien_cuu",
     lenh="Tóm tắt 5 tin AI và YouTube đáng chú ý trong 24h qua (ngày {{ngay}}), mỗi tin 1 dòng kèm nguồn. Tin nào không chắc thì ghi 'chưa chắc'."),
   N("gom", "gop", 480, 200, che_do="cho_tat_ca", kieu="doi_tuong"),
   N("bao_cao", "bao_cao_ai", 680, 200, loai="sang_9h", dinh_dang="telegram", do_dai="vua", luu_file=True),
   N("gui", "nhan_tin", 900, 200, qua=["telegram"], noi_dung="{{bao_cao.van_ban}}"),
   N("dashboard", "cap_nhat_dashboard", 480, 40, ten="kenh_moi")],
  [D("hen_gio", "view"), D("hen_gio", "ngach"), D("hen_gio", "tin_ai"),
   D("view", "gom"), D("ngach", "gom"), D("tin_ai", "gom"), D("view", "dashboard"),
   D("gom", "bao_cao"), D("bao_cao", "gui")])

W("kiem_duyet_noi_dung", "Kiểm duyệt nội dung có sẵn",
  "Dán kịch bản/tiêu đề có sẵn → kiểm duyệt 2 lớp (luật + AI) → đạt thì báo xanh; cần xem / chặn thì AI viết bản sửa và báo anh.",
  [N("bat_dau", "bat_dau", 40, 160, goi_y_nhap="Dán kịch bản + tiêu đề"),
   N("kiem_duyet", "kiem_duyet", 260, 160, nen_tang=["youtube", "facebook"], tu_cam=[]),
   N("bao_dat", "nhan_tin", 500, 40, qua=["telegram"], noi_dung="✅ Nội dung đạt kiểm duyệt."),
   N("sua", "hoi_ai", 500, 220, vai="kiem_duyet",
     lenh="Viết lại nội dung sau cho hết vi phạm, giữ ý chính.\nVi phạm: {{kiem_duyet.vi_pham}}\nNội dung gốc:\n{{input}}"),
   N("bao_sua", "nhan_tin", 720, 220, qua=["telegram"],
     noi_dung="⚠️ Kiểm duyệt: {{kiem_duyet.ket_luan}}\n{{kiem_duyet.van_ban}}\n\nBản sửa đề xuất:\n{{sua}}")],
  [D("bat_dau", "kiem_duyet"), D("kiem_duyet", "bao_dat", "dat"),
   D("kiem_duyet", "sua", "can_xem"), D("kiem_duyet", "sua", "chan"), D("sua", "bao_sua")])

W("khoi_kiem_tra", "Khối: Kiểm tra chất lượng + Kiểm duyệt",
  "Khối con dùng lại: chấm chất lượng rồi kiểm duyệt; ra kết quả kiểm duyệt.",
  [N("vao", "bat_dau", 40, 120), N("chat_luong", "kiem_tra_chat_luong", 240, 120, nguong=7),
   N("kiem_duyet", "kiem_duyet", 460, 120)],
  [D("vao", "chat_luong"), D("chat_luong", "kiem_duyet", "dat"), D("chat_luong", "kiem_duyet", "khong_dat")])

W("nhan_ban_ngon_ngu", "1 nội dung → 3 ngôn ngữ",
  "Viết gốc tiếng Việt, rồi Cho mỗi ngôn ngữ: dịch + bản địa hoá → giọng đọc → kiểm duyệt; gộp 3 bản, anh duyệt 1 lần rồi đăng.",
  [N("bat_dau", "bat_dau", 40, 200), N("goc", "kich_ban_short", 220, 200),
   N("moi_ngon_ngu", "cho_moi", 400, 200, danh_sach=["vi", "en", "ja"], ket_thuc="gop_ban", song_song=3),
   N("dich", "dich", 580, 200, den="{{phan_tu}}"), N("giong", "giong_doc", 760, 200),
   N("kiem_duyet", "kiem_duyet", 940, 200),
   N("gop_ban", "gop", 1120, 200, kieu="danh_sach"), N("duyet", "cho_duyet", 1300, 200), N("dang", "dang_bai", 1480, 200)],
  [D("bat_dau", "goc"), D("goc", "moi_ngon_ngu"), D("moi_ngon_ngu", "dich"), D("dich", "giong"), D("giong", "kiem_duyet"),
   D("kiem_duyet", "gop_ban", "dat"), D("kiem_duyet", "gop_ban", "can_xem"),
   D("gop_ban", "duyet"), D("duyet", "dang", "duyet")])

W("hang_loat_moi_kenh", "Mọi kênh × 1 Short (duyệt từng kênh)",
  "Cho mỗi kênh: chọn hồ sơ → nghiên cứu ngách → viết → khối kiểm tra → chờ anh duyệt riêng từng kênh → đăng; cuối cùng AI báo cáo lần chạy.",
  [N("bat_dau", "bat_dau", 40, 200, goi_y_nhap="Chủ đề chung (để trống = theo ngách)"),
   N("moi_kenh", "cho_moi", 200, 200, danh_sach="tat_ca_kenh", ket_thuc="tong_hop", song_song=3),
   N("chon", "chon_kenh", 360, 200, kenh="{{phan_tu}}"),
   N("ngach", "nghien_cuu_ngach", 520, 200, so_y_tuong=3),
   N("viet", "kich_ban_short", 680, 200),
   N("kiem", "khoi_con", 840, 200, so_do="khoi_kiem_tra.ailink.json"),
   N("duyet", "cho_duyet", 1000, 200), N("dang", "dang_bai", 1160, 200),
   N("tong_hop", "gop", 1320, 200, kieu="danh_sach"),
   N("bao_cao", "bao_cao_ai", 1480, 200, loai="lan_chay", dinh_dang="telegram", do_dai="ngan")],
  [D("bat_dau", "moi_kenh"), D("moi_kenh", "chon"), D("chon", "ngach"), D("ngach", "viet"), D("viet", "kiem"),
   D("kiem", "duyet"), D("duyet", "dang", "duyet"), D("duyet", "viet", "sua", 3), D("dang", "tong_hop"),
   D("tong_hop", "bao_cao")])

W("phien_dich_video", "Phiên dịch video nước ngoài → bản tiếng Việt",
  "Tải video (bắt buộc ghi loại nguồn) → tách lời → dịch → phụ đề .srt + lồng tiếng → kiểm duyệt → chờ duyệt. Nguồn 'chưa rõ' thì không cho đăng.",
  [N("bat_dau", "bat_dau", 40, 200, goi_y_nhap="Link video"),
   N("tai", "tai_video_nguon", 220, 200, link="{{input}}", loai_nguon="co_giay_phep", ghi_nguon="Tác giả, link gốc"),
   N("tach_loi", "tach_loi", 400, 140), N("tach_giong", "tach_giong", 400, 280),
   N("dich", "dich", 580, 140, den="vi"), N("phu_de", "chen_phu_de", 760, 60),
   N("long_tieng", "long_tieng", 760, 220), N("gom", "gop", 940, 160),
   N("kiem_duyet", "kiem_duyet", 1100, 160), N("duyet", "cho_duyet", 1260, 160), N("dang", "dang_bai", 1420, 160)],
  [D("bat_dau", "tai"), D("tai", "tach_loi"), D("tai", "tach_giong"), D("tach_loi", "dich"), D("tach_loi", "phu_de"),
   D("dich", "long_tieng"), D("tach_giong", "long_tieng"), D("phu_de", "gom"), D("long_tieng", "gom"),
   D("gom", "kiem_duyet"), D("kiem_duyet", "duyet", "dat"), D("kiem_duyet", "duyet", "can_xem"), D("duyet", "dang", "duyet")])

W("tra_loi_binh_luan", "Soạn trả lời bình luận",
  "Dán bình luận (mỗi dòng 1 cái) → AI soạn trả lời theo giọng kênh → kiểm duyệt → chờ anh duyệt.",
  [N("bat_dau", "bat_dau", 40, 160, goi_y_nhap="Mỗi dòng 1 bình luận"), N("soan", "tra_loi_binh_luan", 240, 160),
   N("kiem_duyet", "kiem_duyet", 440, 160, nen_tang=["youtube"]), N("duyet", "cho_duyet", 640, 160)],
  [D("bat_dau", "soan"), D("soan", "kiem_duyet"), D("kiem_duyet", "duyet", "dat"), D("kiem_duyet", "duyet", "can_xem")])

W("phan_loai_y_tuong", "Phân loại ý tưởng → Short hay Dài",
  "AI phân loại ý tưởng; mỗi nhãn đi dây chuyền riêng; Gộp lấy nhánh xong trước; AI báo cáo tóm tắt.",
  [N("bat_dau", "bat_dau", 40, 200), N("loai", "phan_loai", 220, 200, nhan=["short", "dai"], cau_hoi="Ý tưởng này hợp Short hay video dài?"),
   N("short", "kich_ban_short", 440, 100), N("dai", "kich_ban_dai", 440, 300),
   N("gom", "gop", 640, 200, che_do="xong_truoc", kieu="noi_chu"),
   N("bao_cao", "bao_cao_ai", 820, 200, loai="tuy_chinh",
     muc=["Ý tưởng được xếp loại gì, vì sao", "Kịch bản tóm tắt", "Bước tiếp theo"], dinh_dang="markdown", do_dai="ngan")],
  [D("bat_dau", "loai"), D("loai", "short", "short"), D("loai", "dai", "dai"), D("loai", "short", "khac"),
   D("short", "gom"), D("dai", "gom"), D("gom", "bao_cao")])
print("xong")
