"""Nhóm Duyệt (vàng): kiểm duyệt nội dung, chờ anh duyệt, đăng bài."""
import re
from .base import NodeType, KetQua, LoiNode, ChoDuyet, dang_ky, chu

# Cụm từ rủi ro mặc định (spam, hứa hẹn quá mức, y tế). Anh thêm trong hồ sơ kênh (dieu_cam) hoặc cài đặt node.
TU_RUI_RO = ["sub4sub", "sub chéo", "cam kết 100%", "chữa khỏi hoàn toàn", "kiếm tiền nhanh",
             "làm giàu nhanh", "100% sự thật", "bấm vào link này", "free robux"]

GIOI_HAN = {"youtube": {"tieu_de": 100, "mo_ta": 5000}}  # giới hạn ký tự chính thức của YouTube

DANH_MUC_AI = [
    "Bạo lực, nguy hiểm, thử thách gây hại",
    "Thù ghét, quấy rối, xúc phạm nhóm người",
    "Nội dung người lớn, khiêu dâm",
    "Thông tin sai lệch (y tế, bầu cử, thảm hoạ)",
    "Bản quyền: nhạc, hình, đoạn phim của người khác",
    "Tiêu đề / thumbnail gây hiểu lầm (clickbait quá mức)",
    "Nội dung dùng lại, lặp lại, AI hàng loạt ít giá trị (rủi ro không bật kiếm tiền)",
    "Nội dung nhắm trẻ em (cần đánh dấu 'dành cho trẻ em')",
    "Điều cấm riêng của kênh",
]
MUC = {"thap": 1, "vua": 2, "cao": 3}


def _tim_chu(x, khoa):
    if isinstance(x, dict):
        if khoa in x and isinstance(x[khoa], str):
            return x[khoa]
        for v in x.values():
            r = _tim_chu(v, khoa)
            if r:
                return r
    return ""


@dang_ky
class KiemDuyet(NodeType):
    loai, ten, nhom, giai_doan = "kiem_duyet", "Kiểm duyệt nội dung", "duyet", 1
    cong = ["dat", "can_xem", "chan"]
    mo_ta = ("Kiểm tra trước khi gửi anh duyệt, 2 lớp. Lớp luật (không cần AI): từ cấm của kênh, cụm từ "
             "spam, nguồn video 'chưa rõ', tiêu đề quá 100 ký tự, mô tả quá 5.000 ký tự, số điện thoại/link lạ, "
             "tiêu đề viết hoa toàn bộ. Lớp AI: chấm rủi ro theo chính sách YouTube/Facebook/TikTok "
             "(bạo lực, thù ghét, người lớn, tin sai, bản quyền, clickbait, nội dung dùng lại, trẻ em). "
             "Ra 3 cổng: dat / can_xem / chan, kèm danh sách vi phạm và gợi ý sửa.")
    vi_du = ("Kịch bản + tiêu đề → Kiểm duyệt: dat → Chờ duyệt; can_xem → Chờ duyệt kèm cảnh báo; "
             "chan → quay lại viết lại (tối đa 2 lần) hoặc Nhắn tin báo anh.")
    cai_dat_mau = {"nen_tang": ["youtube", "facebook", "tiktok"], "tu_cam": [], "dung_ai": True,
                   "nguong_rui_ro": {"can_xem": 30, "chan": 70}}

    def chay(self, nx):
        vi_pham = []

        def them(loai, muc, trich, goi_y):
            vi_pham.append({"loai": loai, "muc_do": muc, "trich_doan": trich[:120], "goi_y": goi_y, "lop": "luat"})

        toan_bo = "\n".join(chu(v) for v in nx.dau_vao.values()) or chu(nx.prev)
        thap = toan_bo.lower()
        kenh = nx.bien.get("kenh") or {}
        cam = kenh.get("dieu_cam", [])
        cam = [c.strip() for c in (cam.split(",") if isinstance(cam, str) else cam) if c.strip()]
        for tu in cam + list(nx.cai_dat.get("tu_cam", [])):
            if tu.lower() in thap:
                them("Điều cấm của kênh", "cao", tu, f"Bỏ nội dung '{tu}' (hồ sơ kênh cấm)")
        for tu in TU_RUI_RO:
            if tu in thap:
                them("Spam / hứa hẹn quá mức", "vua", tu, f"Bỏ cụm '{tu}'")
        if nx.co_nguon_chua_ro():
            them("Bản quyền", "cao", "nguồn video: chưa rõ", "Chọn nguồn có quyền dùng, hoặc chỉ xuất file, không đăng")
        tieu_de = _tim_chu(nx.prev, "tieu_de") or "".join(_tim_chu(v, "tieu_de") for v in nx.dau_vao.values())
        mo_ta = _tim_chu(nx.prev, "mo_ta") or "".join(_tim_chu(v, "mo_ta") for v in nx.dau_vao.values())
        if "youtube" in nx.cai_dat.get("nen_tang", ["youtube"]):
            if len(tieu_de) > GIOI_HAN["youtube"]["tieu_de"]:
                them("Tiêu đề quá dài", "vua", tieu_de, "YouTube tối đa 100 ký tự")
            if len(mo_ta) > GIOI_HAN["youtube"]["mo_ta"]:
                them("Mô tả quá dài", "vua", mo_ta[:60], "YouTube tối đa 5.000 ký tự")
        if tieu_de and len(tieu_de) > 12 and tieu_de.upper() == tieu_de and any(c.isalpha() for c in tieu_de):
            them("Tiêu đề viết hoa toàn bộ", "thap", tieu_de, "Viết hoa vừa phải, tránh bị coi là clickbait")
        for sdt in re.findall(r"(?:\+?84|0)\d{9,10}", toan_bo):
            them("Thông tin cá nhân", "vua", sdt, "Bỏ số điện thoại khỏi nội dung")
        for url in re.findall(r"https?://\S+", toan_bo):
            if not re.search(r"(youtube\.com|youtu\.be|facebook\.com|tiktok\.com)", url):
                them("Link lạ", "thap", url, "Kiểm tra link trước khi đăng")

        diem_ai, nhan_xet = 0, ""
        if nx.cd("dung_ai", True):
            lenh = ("Bạn là người kiểm duyệt nội dung trước khi đăng lên " + ", ".join(nx.cai_dat.get("nen_tang", ["youtube"]))
                    + ". Chấm rủi ro 0–100 theo các mục:\n- " + "\n- ".join(DANH_MUC_AI)
                    + f"\nĐiều cấm của kênh: {', '.join(cam) or 'không có'}.\n\nNỘI DUNG:\n{toan_bo[:8000]}\n\n"
                    'Trả JSON: {"diem_rui_ro": số, "vi_pham": [{"loai": "...", "muc_do": "thap|vua|cao", '
                    '"trich_doan": "...", "goi_y": "..."}], "nhan_xet": "..."}')
            kq = nx.ai(lenh, vai="kiem_duyet", json=True,
                       gia_lap=lambda p: {"diem_rui_ro": 10, "vi_pham": [], "nhan_xet": "Giả lập: không thấy rủi ro"})
            diem_ai = float(kq.get("diem_rui_ro", 0))
            nhan_xet = kq.get("nhan_xet", "")
            for v in kq.get("vi_pham", []):
                v["lop"] = "ai"
                vi_pham.append(v)

        nguong = {"can_xem": 30, "chan": 70}
        nguong.update(nx.cai_dat.get("nguong_rui_ro") or {})
        nang = max([MUC.get(v.get("muc_do"), 1) for v in vi_pham] or [0])
        if nang >= 3 or diem_ai >= nguong["chan"]:
            ket_luan = "chan"
        elif nang >= 2 or diem_ai >= nguong["can_xem"]:
            ket_luan = "can_xem"
        else:
            ket_luan = "dat"
        nx.ghi_chu(f"{ket_luan}: {len(vi_pham)} vi phạm, rủi ro AI {diem_ai}")
        goi_y = "; ".join(v.get("goi_y", "") for v in vi_pham if v.get("goi_y"))
        return KetQua({"ket_luan": ket_luan, "diem_rui_ro": diem_ai, "vi_pham": vi_pham, "nhan_xet": nhan_xet,
                       "van_ban": f"Kiểm duyệt: {ket_luan}. Cần sửa: {goi_y or 'không'}",
                       "noi_dung": nx.prev}, ket_luan)


@dang_ky
class ChoAnhDuyet(NodeType):
    loai, ten, nhom, giai_doan = "cho_duyet", "Chờ anh duyệt", "duyet", 2
    cong = ["duyet", "sua", "bo"]
    cache = False
    mo_ta = ("Dừng nhánh, gửi bản xem trước (video, thumbnail, tiêu đề, mô tả) về tab Duyệt và Telegram. "
             "Duyệt → đi tiếp; Sửa → anh ghi yêu cầu, dây quay ngược về node cần làm lại; Bỏ → dừng. "
             "Chưa duyệt thì chờ mãi, không bao giờ tự đăng.")
    vi_du = "Trước mọi node Đăng bài. Cổng 'sua' nối ngược về Viết kịch bản (tối đa 3 lần)."
    cai_dat_mau = {"gui_qua": ["app", "telegram"], "nhac_lai_gio": 24}

    def chay(self, nx):
        qd = nx.rieng.get("quyet_dinh")
        if not qd:
            raise ChoDuyet({"dau_vao": nx.dau_vao, "kenh": (nx.bien.get("kenh") or {}).get("ten"),
                            "canh_bao": nx.canh_bao_truoc()})
        ghi_chu = nx.rieng.get("ghi_chu", "")
        if qd == "sua":
            return KetQua({"van_ban": f"Anh Hoà yêu cầu sửa: {ghi_chu}", "quyet_dinh": qd, "ghi_chu": ghi_chu}, "sua")
        return KetQua({"quyet_dinh": qd, "ghi_chu": ghi_chu, "noi_dung": nx.prev,
                       "van_ban": chu(nx.prev)}, qd)


@dang_ky
class DangBai(NodeType):
    loai, ten, nhom, giai_doan = "dang_bai", "Đăng bài", "duyet", 6
    cache = False
    gia_lap = True
    mo_ta = ("Đăng YouTube (API chính thức), Facebook, TikTok (tay Chrome) sau khi anh Duyệt. "
             "Tự chặn nếu chưa có Duyệt, Kiểm duyệt ra 'chan', hoặc nguồn video 'chưa rõ'.")
    vi_du = "Sau Chờ duyệt (cổng duyet): đăng ngay hoặc hẹn giờ theo múi giờ thị trường."
    cai_dat_mau = {"nen_tang": ["youtube"], "hen_gio": "theo_ho_so"}

    def chay(self, nx):
        if not nx.da_duyet():
            raise LoiNode("Chặn: chưa có bước Chờ duyệt nào được anh bấm Duyệt trước node này")
        if nx.co_nguon_chua_ro():
            raise LoiNode("Chặn: có video nguồn 'chưa rõ' bản quyền, chỉ được xuất file")
        if nx.kiem_duyet_chan():
            raise LoiNode("Chặn: Kiểm duyệt kết luận 'chan'")
        return KetQua({"trang_thai": "gia_lap_chua_dang", "nen_tang": nx.cai_dat.get("nen_tang", ["youtube"]),
                       "van_ban": "Giả lập: đã đủ điều kiện đăng, CHƯA đăng thật (giai đoạn 6)"})
