"""Nhóm Ảnh (hồng), Video (cam), Giọng (xanh lá).

Giai đoạn 1 chỉ chạy giả lập: tạo file giữ chỗ (ảnh .svg, mô tả .json) trong thư mục lần chạy
để dây chuyền chạy hết. Bản thật làm ở giai đoạn ghi trong 'giai_doan'.
"""
import html, json, os
from .base import NodeType, KetQua, LoiNode, dang_ky, chu

LOAI_NGUON = ["cua_anh", "co_giay_phep", "mien_phi_ban_quyen", "chua_ro"]


def _svg(chu_ve, rong, cao):
    t = html.escape(chu_ve[:80])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{rong}" height="{cao}">'
            f'<rect width="100%" height="100%" fill="#1d2330"/><text x="50%" y="50%" fill="#f0773f" '
            f'font-family="Segoe UI" font-size="{max(14, rong // 30)}" text-anchor="middle">{t}</text></svg>')


class NodeGiaLap(NodeType):
    gia_lap = True
    duoi = ".json"

    def tao(self, nx):
        return {"mo_ta": chu(nx.prev)[:200]}

    def chay(self, nx):
        ra = self.tao(nx)
        noi_dung = ra.pop("_noi_dung", None)
        if noi_dung is None:
            noi_dung = json.dumps({"gia_lap": True, "loai": self.loai, **ra}, ensure_ascii=False, indent=2)
        ra["file"] = nx.ghi_tep(f"{nx.id}{self.duoi}", noi_dung)
        ra["gia_lap"] = True
        return KetQua(ra)


@dang_ky
class TaoAnh(NodeGiaLap):
    loai, ten, nhom, giai_doan = "tao_anh", "Tạo ảnh", "anh", 3
    duoi = ".svg"
    mo_ta = "Ảnh minh hoạ theo từng cảnh (Gemini, Muse Image, ChatGPT...)."
    vi_du = "Kịch bản 6 cảnh → 6 ảnh 9:16 cùng phong cách."
    cai_dat_mau = {"khung": "9:16", "phong_cach": "điện ảnh, ánh sáng tối", "ai": "tu_chon"}

    def tao(self, nx):
        r, c = (1080, 1920) if nx.cd("khung", "9:16") == "9:16" else (1920, 1080)
        return {"_noi_dung": _svg("Ảnh giả lập: " + chu(nx.prev), r, c), "khung": nx.cd("khung", "9:16")}


@dang_ky
class Thumbnail(NodeGiaLap):
    loai, ten, nhom, giai_doan = "thumbnail", "Thumbnail", "anh", 3
    duoi = ".svg"
    mo_ta = "Ảnh bìa 16:9 / 9:16 có chữ theo ngôn ngữ kênh."
    vi_du = "Tiêu đề → thumbnail chữ to 3–5 từ tiếng Nhật."
    cai_dat_mau = {"khung": "16:9", "chu_tren_anh": "{{tieu_de.tieu_de}}"}

    def tao(self, nx):
        t = nx.cd("chu_tren_anh", "") or chu(nx.prev)
        r, c = (1280, 720) if nx.cd("khung", "16:9") == "16:9" else (1080, 1920)
        return {"_noi_dung": _svg(t, r, c), "chu": t[:80]}


@dang_ky
class TaoVideo(NodeGiaLap):
    loai, ten, nhom, giai_doan = "tao_video", "Tạo video AI", "video", 4
    mo_ta = "Gemini, Muse… tạo đoạn video từ lời mô tả hoặc ảnh."
    vi_du = "Mỗi cảnh 1 đoạn 5 giây từ ảnh minh hoạ."
    cai_dat_mau = {"do_dai_giay": 5, "ai": "gemini"}


@dang_ky
class DungCapCut(NodeGiaLap):
    loai, ten, nhom, giai_doan = "dung_capcut", "Dựng CapCut", "video", 6
    mo_ta = "Ghép ảnh, video, giọng, nhạc, phụ đề. Dự phòng: dựng bằng FFmpeg nếu CapCut không tự động được."
    vi_du = "Gộp (ảnh + giọng + phụ đề) → video 9:16 hoàn chỉnh."
    cai_dat_mau = {"khung": "9:16", "cach": "ffmpeg"}

    def tao(self, nx):
        return {"khung": nx.cd("khung", "9:16"), "thanh_phan": list(nx.dau_vao.keys())}


@dang_ky
class CatShort(NodeGiaLap):
    loai, ten, nhom, giai_doan = "cat_short", "Cắt Short từ video dài", "video", 7
    mo_ta = "Chọn 3–5 đoạn hay từ video dài, chuyển 9:16, thêm câu móc riêng."
    vi_du = "Chế độ 'Cả hai': video dài → 3 Short."
    cai_dat_mau = {"so_doan": 3}

    def tao(self, nx):
        return {"doan": [{"bat_dau": i * 60, "ket_thuc": i * 60 + 45} for i in range(int(nx.cd("so_doan", 3)))]}


@dang_ky
class ChenPhuDe(NodeType):
    loai, ten, nhom, giai_doan = "chen_phu_de", "Chèn phụ đề", "video", 7
    mo_ta = "Xuất file .srt từ lời có mốc thời gian (làm thật); đốt phụ đề vào video ở giai đoạn 7."
    vi_du = "Tách lời → Dịch → Chèn phụ đề (.srt tiếng Việt)."
    cai_dat_mau = {"kieu": "srt"}

    def chay(self, nx):
        doan = nx.prev.get("doan") if isinstance(nx.prev, dict) else None
        if not doan:
            cau = [c for c in chu(nx.prev).replace("\n", " ").split(". ") if c.strip()]
            doan = [{"bat_dau": i * 3.0, "ket_thuc": i * 3.0 + 3, "loi": c} for i, c in enumerate(cau)]

        def t(s):
            ms = int(round(float(s) * 1000))
            return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
        srt = "\n".join(f"{i}\n{t(d['bat_dau'])} --> {t(d['ket_thuc'])}\n{d['loi']}\n" for i, d in enumerate(doan, 1))
        return KetQua({"file": nx.ghi_tep(f"{nx.id}.srt", srt), "so_dong": len(doan)})


@dang_ky
class TaiVideoNguon(NodeGiaLap):
    loai, ten, nhom, giai_doan = "tai_video_nguon", "Tải video nguồn", "video", 7
    bat_buoc = ("loai_nguon",)
    mo_ta = ("Tải từ link hoặc file, BẮT BUỘC chọn loại nguồn: cua_anh / co_giay_phep / mien_phi_ban_quyen / chua_ro. "
             "'chua_ro' thì Đăng bài bị chặn, chỉ cho xuất file.")
    vi_du = "Phiên dịch video nước ngoài: link → tách lời → dịch → lồng tiếng."
    cai_dat_mau = {"link": "{{input}}", "loai_nguon": "co_giay_phep", "ghi_nguon": "Tên tác giả, link gốc"}

    def kiem_tra(self, cd):
        loi = super().kiem_tra(cd)
        if "loai_nguon" in cd and cd["loai_nguon"] not in LOAI_NGUON:
            loi.append("loai_nguon phải là " + " / ".join(LOAI_NGUON))
        return loi

    def tao(self, nx):
        return {"link": nx.cd("link", chu(nx.prev)), "loai_nguon": nx.cai_dat["loai_nguon"],
                "ghi_nguon": nx.cd("ghi_nguon", "")}


@dang_ky
class GiongDoc(NodeGiaLap):
    loai, ten, nhom, giai_doan = "giong_doc", "Giọng đọc TTS", "giong", 6
    mo_ta = "Đọc kịch bản đa ngôn ngữ; mặc định lấy giọng của kênh theo ngôn ngữ (hồ sơ kênh)."
    vi_du = "Kịch bản tiếng Nhật → giọng nam trầm của kênh JP."
    cai_dat_mau = {"giong": "", "toc_do": 1.0}

    def tao(self, nx):
        g = nx.cd("giong", "")
        if not g:  # lấy giọng mặc định của kênh theo ngôn ngữ
            gd = (nx.bien.get("kenh") or {}).get("giong_doc") or {}
            if isinstance(gd, dict):
                ngon_ngu = nx.bien.get("phan_tu") if isinstance(nx.bien.get("phan_tu"), str) else None
                g = gd.get(ngon_ngu) or gd.get((nx.bien.get("kenh") or {}).get("ngon_ngu")) or next(iter(gd.values()), "")
            else:
                g = gd
        return {"giong": g, "so_ky_tu": len(chu(nx.prev))}


@dang_ky
class AppAmThanh(NodeGiaLap):
    loai, ten, nhom, giai_doan = "app_am_thanh", "App âm thanh ngoài", "giong", 6
    mo_ta = "Gọi ElevenLabs, FPT.AI, Vbee… qua API, qua web (Chrome) hoặc chạy phần mềm trên máy rồi chờ file kết quả."
    vi_du = "Nhạc nền 60 giây không lời cho Short."
    cai_dat_mau = {"dich_vu": "elevenlabs", "viec": "nhac_nen", "tay": "api"}


@dang_ky
class LongTieng(NodeGiaLap):
    loai, ten, nhom, giai_doan = "long_tieng", "Lồng tiếng", "giong", 7
    mo_ta = "Giọng mới khớp mốc thời gian, giữ nhạc nền."
    vi_du = "Bản dịch tiếng Việt + nhạc nền đã tách → video lồng tiếng Việt."


@dang_ky
class TachGiong(NodeGiaLap):
    loai, ten, nhom, giai_doan = "tach_giong", "Tách giọng / nhạc", "giong", 7
    mo_ta = "Tách lời nói khỏi nhạc nền."
    vi_du = "Trước Lồng tiếng: giữ nhạc nền, bỏ giọng gốc."
