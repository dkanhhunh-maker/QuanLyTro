"""Nhóm Điều khiển (tím): bắt đầu, hẹn giờ, điều kiện, vòng lặp, cho mỗi, gộp, chọn kênh, khối con."""
from .base import NodeType, KetQua, LoiNode, dang_ky, chu, lay_json


@dang_ky
class BatDau(NodeType):
    loai, ten, nhom, giai_doan = "bat_dau", "Bắt đầu tay", "dieu_khien", 1
    cache = False
    mo_ta = "Anh bấm chạy và nhập đầu vào (chủ đề, link, ý tưởng)."
    vi_du = "Đầu mọi sơ đồ chạy tay. Kết quả là {{input}}."
    cai_dat_mau = {"goi_y_nhap": "Chủ đề video"}

    def chay(self, nx):
        return KetQua(nx.bien.get("input", ""))


@dang_ky
class HenGio(NodeType):
    loai, ten, nhom, giai_doan = "hen_gio", "Hẹn giờ", "dieu_khien", 5
    cache = False
    mo_ta = "Chạy sơ đồ theo lịch: hằng ngày, ngày trong tuần, mỗi N giờ, 1 lần."
    vi_du = "Báo cáo 9h sáng mỗi ngày; lưu nhật ký 22h."
    cai_dat_mau = {"lich": {"kieu": "hang_ngay", "gio": "09:00"}, "dau_vao": "Báo cáo sáng"}

    def chay(self, nx):
        return KetQua(nx.bien.get("input") or nx.cd("dau_vao", ""))


_PHEP = {
    ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b,
    "<": lambda a, b: a < b, "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
}


def _so(x):
    try:
        return float(str(x).strip())
    except ValueError:
        return None


def so_sanh(trai, phep, phai):
    if phep in _PHEP:
        a, b = _so(trai), _so(phai)
        if a is None or b is None:
            a, b = str(trai).strip(), str(phai).strip()
            if phep not in ("==", "!="):
                raise LoiNode(f"Không so sánh '{phep}' được giữa '{trai}' và '{phai}' (không phải số)")
        return _PHEP[phep](a, b)
    if phep == "chua":
        return str(phai).lower() in str(trai).lower()
    if phep == "khong_chua":
        return str(phai).lower() not in str(trai).lower()
    if phep == "rong":
        return not str(trai).strip()
    if phep == "khong_rong":
        return bool(str(trai).strip())
    raise LoiNode(f"Phép so sánh '{phep}' không có")


@dang_ky
class DieuKien(NodeType):
    loai, ten, nhom, giai_doan = "dieu_kien", "Điều kiện", "dieu_khien", 1
    cong = ["dat", "khong_dat"]
    mo_ta = "Rẽ Đạt / Không đạt theo luật (so sánh) hoặc theo AI chấm. Đầu vào đi thẳng qua."
    vi_du = "Điểm kiểm tra >= 8 thì đi tiếp, không thì quay lại viết lại (dây quay ngược tối đa 3 lần)."
    cai_dat_mau = {"kieu": "luat", "ket_hop": "va",
                   "dieu_kien": [{"trai": "{{kiem_tra.diem}}", "phep": ">=", "phai": "8"}]}

    def kiem_tra(self, cd):
        if cd.get("kieu", "luat") == "luat" and not cd.get("dieu_kien"):
            return ["kiểu 'luat' cần danh sách 'dieu_kien'"]
        if cd.get("kieu") == "ai" and not cd.get("cau_hoi"):
            return ["kiểu 'ai' cần 'cau_hoi'"]
        return []

    def chay(self, nx):
        if nx.cd("kieu", "luat") == "ai":
            cau_hoi = nx.cd("cau_hoi")
            kq = nx.ai(f"{cau_hoi}\n\nNội dung:\n{chu(nx.prev)}\n\nTrả JSON: {{\"dat\": true/false, \"ly_do\": \"...\"}}",
                       vai="kiem_tra", json=True,
                       gia_lap=lambda p: {"dat": True, "ly_do": "Giả lập: đạt"})
            dat, ly_do = bool(kq.get("dat")), kq.get("ly_do", "")
        else:
            kqs = []
            for d in nx.cai_dat.get("dieu_kien", []):
                trai, phai = nx.render(d.get("trai", "")), nx.render(str(d.get("phai", "")))
                kqs.append((so_sanh(trai, d.get("phep", "=="), phai), f"{trai} {d.get('phep')} {phai}"))
            dat = all(k for k, _ in kqs) if nx.cd("ket_hop", "va") == "va" else any(k for k, _ in kqs)
            ly_do = "; ".join(f"{s} → {'đúng' if k else 'sai'}" for k, s in kqs)
        nx.ghi_chu(ly_do)
        return KetQua(nx.prev, "dat" if dat else "khong_dat")


@dang_ky
class VongLap(NodeType):
    loai, ten, nhom, giai_doan = "vong_lap", "Vòng lặp", "dieu_khien", 1
    cong = ["lap", "xong"]
    cache = False
    mo_ta = "Chạy đoạn phía sau cổng 'lap' N lần, gom kết quả mỗi lượt (dây quay về), xong thì ra cổng 'xong'."
    vi_du = "Tạo 3 bản thumbnail khác nhau rồi đưa cả 3 cho AI chọn."
    cai_dat_mau = {"so_lan": 3}

    def chay(self, nx):
        n = int(nx.cd("so_lan", 3))
        gom = nx.giu.setdefault("ket_qua", [])
        if nx.phan_hoi is not None:
            gom.append(nx.phan_hoi)
        if len(gom) < n:
            return KetQua({"lan": len(gom) + 1, "dau_vao": nx.prev}, "lap")
        return KetQua(list(gom), "xong")


def _danh_sach(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for k in ("danh_sach", "y_tuong", "items"):
            if isinstance(x.get(k), list):
                return x[k]
        return [x]
    s = str(x).strip()
    if s.startswith("["):
        try:
            v = lay_json("{\"a\":" + s + "}")["a"]
            if isinstance(v, list):
                return v
        except LoiNode:
            pass
    return [ln.strip(" -•\t") for ln in s.splitlines() if ln.strip(" -•\t")]


@dang_ky
class ChoMoi(NodeType):
    loai, ten, nhom, giai_doan = "cho_moi", "Cho mỗi", "dieu_khien", 1
    cache = False
    bat_buoc = ("ket_thuc",)
    mo_ta = ("Chạy đoạn sơ đồ phía sau một lần cho từng phần tử (kênh, ngôn ngữ, ý tưởng). "
             "Đoạn lặp kết thúc ở node Gộp ghi trong 'ket_thuc'. Trong đoạn lặp dùng {{phan_tu}}, {{chi_so}}.")
    vi_du = "Mỗi ngôn ngữ [vi, en, ja]: dịch → giọng đọc → dựng. Gộp lại 3 bản."
    cai_dat_mau = {"danh_sach": ["vi", "en", "ja"], "ket_thuc": "gop_ban", "song_song": 2}

    def chay(self, nx):
        ds = nx.cai_dat.get("danh_sach")
        if ds == "tat_ca_kenh":
            items = nx.danh_sach_kenh()
        elif isinstance(ds, list):
            items = [nx.render(x) if isinstance(x, str) else x for x in ds]
        elif ds:
            items = _danh_sach(nx.render_gia_tri(ds))
        else:
            items = _danh_sach(nx.prev)
        if not items:
            raise LoiNode("Danh sách rỗng, không có gì để lặp")
        return KetQua(nx.chay_doan_lap(items, int(nx.cd("song_song", 2))))


@dang_ky
class Gop(NodeType):
    loai, ten, nhom, giai_doan = "gop", "Gộp", "dieu_khien", 1
    cache = False
    mo_ta = "Chờ nhiều nhánh xong rồi gộp. che_do: cho_tat_ca | xong_truoc. kieu: danh_sach | noi_chu | doi_tuong."
    vi_du = "Gộp kịch bản + ảnh + giọng trước khi dựng; hoặc gom kết quả của Cho mỗi."
    cai_dat_mau = {"che_do": "cho_tat_ca", "kieu": "doi_tuong"}

    def chay(self, nx):
        vao = nx.dau_vao  # {id_node: kết quả}
        kieu = nx.cd("kieu", "doi_tuong")
        if len(vao) == 1 and isinstance(next(iter(vao.values())), list) and nx.tu_cho_moi:
            ds = next(iter(vao.values()))
            if kieu == "noi_chu":
                return KetQua(nx.cd("ngan_cach", "\n\n---\n\n").join(chu(x.get("ket_qua")) for x in ds))
            return KetQua(ds)
        if kieu == "danh_sach":
            return KetQua(list(vao.values()))
        if kieu == "noi_chu":
            return KetQua(nx.cd("ngan_cach", "\n\n").join(chu(v) for v in vao.values()))
        return KetQua(dict(vao))


@dang_ky
class ChonKenh(NodeType):
    loai, ten, nhom, giai_doan = "chon_kenh", "Chọn kênh đích", "dieu_khien", 2
    bat_buoc = ("kenh",)
    mo_ta = "Lấy hồ sơ kênh đưa vào biến {{kenh}} cho các node phía sau (ngách, giọng văn, thị trường...)."
    vi_du = "Trong Cho mỗi kênh: kenh = {{phan_tu}}."
    cai_dat_mau = {"kenh": "vn_chuyen_la"}

    def chay(self, nx):
        return KetQua(nx.ho_so_kenh(nx.cd("kenh")))


@dang_ky
class KhoiCon(NodeType):
    loai, ten, nhom, giai_doan = "khoi_con", "Khối con", "dieu_khien", 5
    cache = False
    bat_buoc = ("so_do",)
    mo_ta = "Gói cả 1 sơ đồ khác thành 1 node dùng lại. Đầu vào thành {{input}} của sơ đồ con."
    vi_du = "Khối 'Kiểm tra + Kiểm duyệt' dùng chung cho mọi dây chuyền."
    cai_dat_mau = {"so_do": "khoi_kiem_tra.ailink.json"}

    def chay(self, nx):
        return KetQua(nx.chay_khoi_con(nx.cd("so_do"), nx.prev))
