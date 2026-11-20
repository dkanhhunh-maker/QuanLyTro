"""Nhóm Theo dõi và Tiện ích (xám): đọc view, dashboard, đọc/ghi file, chạy lệnh máy, nhắn tin."""
import hashlib, json, os, time
from .base import NodeType, KetQua, LoiNode, dang_ky, chu


@dang_ky
class DocView(NodeType):
    loai, ten, nhom, giai_doan = "doc_view", "Đọc view", "theo_doi", 6
    gia_lap = True
    cache = False
    mo_ta = "Lấy view, sub, giờ xem 24h / 28 ngày từng kênh (YouTube Analytics API, Facebook qua Chrome)."
    vi_du = "9h sáng: đọc view 10 kênh → AI báo cáo."
    cai_dat_mau = {"kenh": "tat_ca", "khoang": "24h"}

    def chay(self, nx):
        ds = nx.danh_sach_kenh() if nx.cd("kenh", "tat_ca") == "tat_ca" else [nx.cd("kenh")]
        rows = []
        for k in ds:
            h = int(hashlib.md5(f"{k}{nx.bien['ngay']}".encode()).hexdigest()[:6], 16)
            rows.append({"kenh": k, "view_24h": h % 5000, "sub": 100 + h % 900, "sub_moi": h % 40,
                         "gio_xem": round((h % 3000) / 10, 1), "gia_lap": True})
        return KetQua(rows)


@dang_ky
class CapNhatDashboard(NodeType):
    loai, ten, nhom, giai_doan = "cap_nhat_dashboard", "Cập nhật dashboard", "theo_doi", 6
    cache = False
    mo_ta = "Ghi số liệu vào dashboard 'Kênh Mới' (giai đoạn 1: ghi file JSON cục bộ)."
    vi_du = "Sau Đọc view: cập nhật bảng 10 kênh."
    cai_dat_mau = {"ten": "kenh_moi"}

    def chay(self, nx):
        p = nx.ghi_xuat(os.path.join("dashboard", nx.cd("ten", "kenh_moi") + ".json"),
                        json.dumps({"cap_nhat": time.strftime("%Y-%m-%d %H:%M"), "du_lieu": nx.prev},
                                   ensure_ascii=False, indent=2))
        return KetQua({"file": p})


@dang_ky
class DocGhiFile(NodeType):
    loai, ten, nhom, giai_doan = "doc_ghi_file", "Đọc / ghi file", "tien_ich", 1
    cache = False
    bat_buoc = ("kieu", "duong_dan")
    mo_ta = "Đọc hoặc ghi file chữ trong G:\\claude (không ra ngoài thư mục này)."
    vi_du = "Ghi kịch bản đã duyệt vào G:\\claude\\kich_ban\\{{ngay}}.md; đọc danh sách ý tưởng từ Obsidian."
    cai_dat_mau = {"kieu": "ghi", "duong_dan": "kich_ban/{{ngay}}.md", "noi_dung": "{{prev}}"}

    def chay(self, nx):
        p = nx.duong_dan_an_toan(nx.cd("duong_dan"))
        if nx.cd("kieu") == "doc":
            if not os.path.exists(p):
                raise LoiNode(f"Không có file {p}")
            with open(p, encoding="utf-8") as f:
                return KetQua(f.read())
        os.makedirs(os.path.dirname(p), exist_ok=True)
        nd = nx.cd("noi_dung", "") if "noi_dung" in nx.cai_dat else chu(nx.prev)
        with open(p, "a" if nx.cd("noi_them", False) else "w", encoding="utf-8") as f:
            f.write(nd)
        return KetQua({"file": p, "so_ky_tu": len(nd)})


@dang_ky
class ChayLenh(NodeType):
    loai, ten, nhom, giai_doan = "chay_lenh", "Chạy lệnh máy", "tien_ich", 6
    cache = False
    gia_lap = True
    mo_ta = "Chạy chương trình trên máy anh (FFmpeg, app âm thanh...), chờ file kết quả xuất hiện rồi đi tiếp."
    vi_du = "ffmpeg ghép ảnh + giọng thành video."
    cai_dat_mau = {"lenh": "ffmpeg -i ...", "cho_file": "xuat/*.mp4", "het_gio_giay": 600}

    def chay(self, nx):
        return KetQua({"gia_lap": True, "lenh": nx.cd("lenh", ""), "van_ban": "Giả lập: chưa chạy lệnh thật"})


@dang_ky
class NhanTin(NodeType):
    loai, ten, nhom, giai_doan = "nhan_tin", "Nhắn tin", "tien_ich", 5
    cache = False
    gia_lap = True
    mo_ta = "Gửi thông báo Telegram (kênh chính) / Zalo (chỉ báo tin). Giai đoạn 1 ghi vào hộp thư giả lập."
    vi_du = "Gửi báo cáo 9h; báo lỗi; báo có video chờ duyệt."
    cai_dat_mau = {"qua": ["telegram"], "noi_dung": "{{prev}}"}

    def chay(self, nx):
        nd = nx.cd("noi_dung", "") if "noi_dung" in nx.cai_dat else chu(nx.prev)
        qua = nx.cai_dat.get("qua", ["telegram"])
        nx.ghi_tep("hop_thu_gia_lap.txt", f"[{time.strftime('%H:%M')}] → {', '.join(qua)}\n{nd}\n\n", noi_them=True)
        return KetQua({"da_gui": qua, "gia_lap": True, "van_ban": nd})
