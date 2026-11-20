"""Đăng ký mọi loại node. Thêm file mới thì import ở đây."""
from .base import REGISTRY, NHOM, KetQua, LoiNode, ChoDuyet, NodeType, dang_ky, chu, chu_phan_hoi, lay_json
from . import dieu_khien, van_ban, phan_tich, media, duyet, tien_ich  # noqa: F401


@dang_ky
class _PhanTu(NodeType):
    """Node nội bộ: đầu đoạn lặp của Cho mỗi, trả phần tử hiện tại."""
    loai, ten, nhom = "_phan_tu", "Phần tử", "dieu_khien"
    cache = False

    def chay(self, nx):
        return KetQua(nx.bien.get("phan_tu"))


def danh_sach_node():
    return [n.mo_ta_day_du() for k, n in REGISTRY.items() if not k.startswith("_")]
