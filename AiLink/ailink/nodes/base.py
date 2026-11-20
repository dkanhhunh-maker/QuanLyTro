"""Khung chung cho mọi loại node.

Mỗi loại node khai: loai (mã), ten (tên hiện), nhom, giai_doan (giai đoạn làm thật),
cong (cổng ra; None = 1 cổng), cai_dat_mau (cài đặt ví dụ), vi_du (dùng khi nào),
cache (có lưu sẵn kết quả không), gia_lap (giai đoạn này mới chạy giả lập).
"""
import json, re

NHOM = {
    "dieu_khien": {"ten": "Điều khiển", "mau": "tim"},
    "chu": {"ten": "Chữ", "mau": "xanh_ngoc"},
    "phan_tich": {"ten": "AI phân tích", "mau": "xanh_duong"},
    "anh": {"ten": "Ảnh", "mau": "hong"},
    "video": {"ten": "Video", "mau": "cam"},
    "giong": {"ten": "Giọng", "mau": "xanh_la"},
    "duyet": {"ten": "Duyệt", "mau": "vang"},
    "theo_doi": {"ten": "Theo dõi", "mau": "xam"},
    "tien_ich": {"ten": "Tiện ích", "mau": "xam"},
}

REGISTRY = {}


class LoiNode(Exception):
    pass


class ChoDuyet(Exception):
    """Node dừng nhánh, chờ anh quyết định."""
    def __init__(self, xem_truoc):
        super().__init__("cho_duyet")
        self.xem_truoc = xem_truoc


class KetQua:
    def __init__(self, ra, cong=None):
        self.ra = ra
        self.cong = cong


class NodeType:
    loai = ""
    ten = ""
    nhom = "chu"
    giai_doan = 1
    cong = None          # list cổng ra, ví dụ ["dat", "khong_dat"]
    cache = True
    gia_lap = False
    mo_ta = ""
    vi_du = ""
    cai_dat_mau = {}
    bat_buoc = ()        # trường cài đặt bắt buộc

    def cong_ra(self, cai_dat):
        return self.cong

    def kiem_tra(self, cai_dat):
        """Trả list lỗi cấu hình (rỗng = hợp lệ)."""
        return [f"thiếu cài đặt '{k}'" for k in self.bat_buoc if k not in cai_dat]

    def chay(self, nx):
        raise NotImplementedError

    def mo_ta_day_du(self):
        return {"loai": self.loai, "ten": self.ten, "nhom": self.nhom, "nhom_ten": NHOM[self.nhom]["ten"],
                "mau": NHOM[self.nhom]["mau"], "giai_doan": self.giai_doan, "cong": self.cong,
                "gia_lap": self.gia_lap, "mo_ta": self.mo_ta, "vi_du": self.vi_du,
                "cai_dat_mau": self.cai_dat_mau}


def dang_ky(cls):
    inst = cls()
    assert inst.loai and inst.loai not in REGISTRY, inst.loai
    REGISTRY[inst.loai] = inst
    return cls


def lay_json(van_ban):
    """Lấy khối JSON đầu tiên trong câu trả lời của AI."""
    if isinstance(van_ban, (dict, list)):
        return van_ban
    s = van_ban.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        return json.loads(s)
    except ValueError:
        pass
    m = re.search(r"\{.*\}", s, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except ValueError:
            pass
    raise LoiNode("AI không trả về JSON hợp lệ: " + s[:200])


def chu(x):
    """Đổi kết quả node bất kỳ thành chữ để đưa vào lệnh."""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        for k in ("noi_dung", "van_ban"):
            if isinstance(x.get(k), str):
                return x[k]
    return json.dumps(x, ensure_ascii=False, indent=2)


def chu_phan_hoi(x):
    """Phản hồi đưa ngược về node viết lại: ưu tiên gợi ý sửa / nhận xét, không phải bản cũ."""
    if isinstance(x, dict):
        for k in ("van_ban", "goi_y_sua", "ghi_chu"):
            if isinstance(x.get(k), str) and x[k].strip():
                return x[k]
    return chu(x)
