"""Nhóm Chữ (xanh ngọc): hỏi AI, nghiên cứu, kịch bản, kiểm tra chất lượng, tiêu đề, dịch, tách lời."""
from .base import NodeType, KetQua, LoiNode, dang_ky, chu, chu_phan_hoi


class NodeAI(NodeType):
    """Node gửi lệnh cho 1 AI. Cài đặt chung: ai, che_do, du_phong, lenh, he_thong."""
    vai = "kich_ban"
    lenh_mac_dinh = "{{prev}}"
    he_thong_mac_dinh = ""

    def mau_gia_lap(self, nx):
        return None

    def chay(self, nx):
        lenh = nx.render(nx.cai_dat.get("lenh", self.lenh_mac_dinh))
        he = nx.render(nx.cai_dat.get("he_thong", self.he_thong_mac_dinh))
        if nx.phan_hoi is not None:
            lenh += ("\n\n[Lần sửa thứ {}] Bản trước chưa đạt. Nhận xét cần sửa:\n{}".format(
                nx.lan_lap, chu_phan_hoi(nx.phan_hoi)))
        return KetQua(nx.ai(lenh, he, vai=nx.cd("vai", self.vai), gia_lap=self.mau_gia_lap(nx)))


@dang_ky
class HoiAI(NodeAI):
    loai, ten, nhom, giai_doan = "hoi_ai", "Hỏi AI", "chu", 1
    mo_ta = "Node AI chung: viết lệnh, chọn AI (hoặc Tự chọn theo vai), chọn chế độ gọi, AI dự phòng."
    vi_du = "Bất cứ việc chữ nào chưa có node riêng: viết caption, đặt câu hỏi, đổi giọng văn."
    cai_dat_mau = {"lenh": "Viết 5 ý tưởng video về {{input}} cho kênh {{kenh.ten}}", "ai": "tu_chon",
                   "vai": "y_tuong", "che_do": "tu_dong", "du_phong": ["gemini", "claude"]}


@dang_ky
class NghienCuuNgach(NodeAI):
    loai, ten, nhom, giai_doan = "nghien_cuu_ngach", "Nghiên cứu ngách", "chu", 3
    vai = "nghien_cuu"
    mo_ta = "Chủ đề đang lên, đối thủ, từ khoá theo thị trường của kênh."
    vi_du = "9h sáng: tìm 10 chủ đề đang lên ở thị trường JP cho ngách chuyện bí ẩn."
    cai_dat_mau = {"so_y_tuong": 10}
    lenh_mac_dinh = ("Thị trường {{kenh.thi_truong}}, ngách {{kenh.ngach}}, ngày {{ngay}}. "
                     "Liệt kê {{cai_dat.so_y_tuong}} chủ đề đang lên, 3 kênh đối thủ mạnh, 10 từ khoá. "
                     "Chủ đề gợi ý thêm: {{input}}")

    def mau_gia_lap(self, nx):
        k = nx.bien.get("kenh") or {}
        return lambda p: ("Chủ đề đang lên (giả lập) — thị trường {} / {}:\n".format(
            k.get("thi_truong", "?"), k.get("ngach", "?")) + "\n".join(
            f"{i}. Chủ đề mẫu {i} về {nx.bien.get('input') or k.get('ngach', 'ngách')}" for i in range(1, 6)))


@dang_ky
class KichBanShort(NodeAI):
    loai, ten, nhom, giai_doan = "kich_ban_short", "Viết kịch bản Short", "chu", 3
    mo_ta = "Câu móc 3 giây, 30–90 giây, 1 ý chính, kết kêu gọi, có phụ đề."
    vi_du = "Ý tưởng → kịch bản 45 giây cho Shorts/Reels/TikTok."
    cai_dat_mau = {"do_dai_giay": 45}
    he_thong_mac_dinh = "Bạn là biên kịch video ngắn. Viết bằng {{kenh.ngon_ngu}}, giọng {{kenh.giong_van}}."
    lenh_mac_dinh = ("Viết kịch bản Short {{cai_dat.do_dai_giay}} giây cho chủ đề: {{prev}}\n"
                     "Gồm: CÂU MÓC (3 giây đầu), NỘI DUNG (đổi cảnh 2–3 giây), KÊU GỌI. Kèm gợi ý hình từng cảnh.")

    def mau_gia_lap(self, nx):
        return lambda p: (f"CÂU MÓC: Bạn có biết điều này về {chu(nx.prev)[:60]}?\n"
                          "NỘI DUNG: Cảnh 1… Cảnh 2… Cảnh 3…\nKÊU GỌI: Theo dõi kênh để xem phần 2!"
                          + (f"\n(Bản sửa lần {nx.lan_lap})" if nx.lan_lap else ""))


@dang_ky
class KichBanDai(NodeAI):
    loai, ten, nhom, giai_doan = "kich_ban_dai", "Viết kịch bản Dài", "chu", 3
    mo_ta = "Dàn ý theo chương, 8–20 phút, mở bài giữ người xem 30 giây đầu."
    vi_du = "Chủ đề → kịch bản 12 phút có chương và mốc thời gian."
    cai_dat_mau = {"so_phut": 12}
    he_thong_mac_dinh = "Bạn là biên kịch YouTube. Viết bằng {{kenh.ngon_ngu}}, giọng {{kenh.giong_van}}."
    lenh_mac_dinh = ("Viết kịch bản video {{cai_dat.so_phut}} phút cho chủ đề: {{prev}}\n"
                     "Mở bài giữ người xem 30 giây đầu, chia chương có mốc thời gian, kết kêu gọi.")

    def mau_gia_lap(self, nx):
        return lambda p: (f"MỞ BÀI (0:00): {chu(nx.prev)[:60]}…\nCHƯƠNG 1 (0:30)…\nCHƯƠNG 2 (4:00)…\n"
                          "CHƯƠNG 3 (8:00)…\nKẾT (11:30): Đăng ký kênh.")


@dang_ky
class KiemTraChatLuong(NodeAI):
    loai, ten, nhom, giai_doan = "kiem_tra_chat_luong", "Kiểm tra chất lượng", "chu", 3
    vai = "kiem_tra"
    cong = ["dat", "khong_dat"]
    mo_ta = ("AI chấm theo tiêu chí, trả {diem, dat, ly_do, goi_y_sua}. Cổng 'khong_dat' thường nối "
             "dây quay ngược về node viết, kèm gợi ý sửa.")
    vi_du = "Chấm kịch bản: câu móc mạnh không, đúng ngách không, đọc tự nhiên với người bản xứ không."
    cai_dat_mau = {"nguong": 8, "tieu_chi": ["Câu móc 3 giây đầu đủ mạnh", "Đúng ngách và giọng kênh",
                                              "Đọc tự nhiên với người bản xứ", "Không nội dung cấm"]}

    def chay(self, nx):
        nguong = float(nx.cd("nguong", 8))
        tc = nx.cai_dat.get("tieu_chi") or self.cai_dat_mau["tieu_chi"]
        lenh = ("Chấm nội dung sau thang 0–10 theo các tiêu chí:\n- " + "\n- ".join(nx.render(t) for t in tc) +
                f"\n\nNội dung:\n{chu(nx.prev)}\n\nTrả JSON: "
                '{"diem": số, "ly_do": "...", "goi_y_sua": "..."}')
        # Giả lập: lần đầu 6 điểm (để thấy vòng lặp viết lại chạy), từ lần sửa thứ nhất 8.5 điểm
        lan = nx.lan_lap
        kq = nx.ai(lenh, vai="kiem_tra", json=True, gia_lap=lambda p: {
            "diem": 8.5 if lan else 6, "ly_do": "Giả lập chấm điểm",
            "goi_y_sua": "" if lan else "Câu móc chưa đủ mạnh, thêm con số cụ thể."})
        diem = float(kq.get("diem", 0))
        kq["dat"] = diem >= nguong
        kq["noi_dung"] = chu(nx.prev)
        kq["van_ban"] = f"Điểm {diem}/10 — {kq.get('ly_do', '')}. Gợi ý sửa: {kq.get('goi_y_sua') or 'không'}"
        nx.ghi_chu(f"{diem}/10 (ngưỡng {nguong}): {kq.get('ly_do', '')}")
        return KetQua(kq, "dat" if kq["dat"] else "khong_dat")


@dang_ky
class TieuDeMoTa(NodeAI):
    loai, ten, nhom, giai_doan = "tieu_de_mo_ta", "Tiêu đề, mô tả, hashtag", "chu", 3
    mo_ta = "Theo ngôn ngữ và thị trường đích; trả {tieu_de, mo_ta, hashtag, gio_dang}."
    vi_du = "Kịch bản → 1 tiêu đề ≤ 60 ký tự, mô tả có mốc thời gian, 10 hashtag, giờ đăng theo múi giờ nước đó."

    def chay(self, nx):
        lenh = nx.render(nx.cai_dat.get("lenh", (
            "Thị trường {{kenh.thi_truong}}, ngôn ngữ {{kenh.ngon_ngu}}, múi giờ {{kenh.mui_gio}}. "
            "Từ nội dung sau, viết tiêu đề ≤ 60 ký tự, mô tả, 10 hashtag, giờ đăng tốt nhất.\n{{prev}}\n"
            'Trả JSON: {"tieu_de": "...", "mo_ta": "...", "hashtag": ["#..."], "gio_dang": "HH:MM"}')))
        return KetQua(nx.ai(lenh, vai="kich_ban", json=True, gia_lap=lambda p: {
            "tieu_de": "Tiêu đề giả lập: " + chu(nx.bien.get("input"))[:40],
            "mo_ta": "Mô tả giả lập.", "hashtag": ["#shorts", "#ailink"], "gio_dang": "19:00"}))


@dang_ky
class Dich(NodeAI):
    loai, ten, nhom, giai_doan = "dich", "Dịch / bản địa hoá", "chu", 7
    vai = "dich"
    mo_ta = "Dịch có chỉnh văn hoá, giữ độ dài câu để khớp giọng đọc và mốc thời gian."
    vi_du = "Kịch bản tiếng Việt → tiếng Nhật cho kênh JP (trong Cho mỗi ngôn ngữ: den = {{phan_tu}})."
    cai_dat_mau = {"den": "ja"}
    lenh_mac_dinh = ("Dịch và bản địa hoá sang ngôn ngữ '{{cai_dat.den}}', giữ độ dài từng câu gần bằng bản gốc, "
                     "đổi ví dụ cho hợp văn hoá:\n{{prev}}")

    def mau_gia_lap(self, nx):
        return lambda p: f"[{nx.cd('den', '?')}] " + chu(nx.prev)[:300]


@dang_ky
class TachLoi(NodeAI):
    loai, ten, nhom, giai_doan = "tach_loi", "Tách lời video", "chu", 7
    vai = "doc_video"
    gia_lap = True
    mo_ta = "Nghe video, ra lời + mốc thời gian, tự nhận ngôn ngữ gốc."
    vi_du = "Video nước ngoài → lời gốc có mốc thời gian để dịch và lồng tiếng."

    def chay(self, nx):
        src = chu(nx.prev)[:80]
        return KetQua({"ngon_ngu_goc": "en", "doan": [
            {"bat_dau": 0.0, "ket_thuc": 3.2, "loi": f"(giả lập) Lời đầu của {src}"},
            {"bat_dau": 3.2, "ket_thuc": 7.5, "loi": "(giả lập) Câu thứ hai"}]})
