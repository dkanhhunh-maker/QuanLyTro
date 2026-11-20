"""Đọc và kiểm tra file sơ đồ .ailink.json (bản đặc tả mục 6).

{
  "phien_ban": 1,
  "ten": "Short YouTube",
  "nodes": [{"id": "viet", "loai": "kich_ban_short", "cai_dat": {...}, "vi_tri": [x, y]}],
  "day":   [{"tu": "kiem_tra", "cong": "khong_dat", "den": "viet", "lap_toi_da": 3}]
}
Dây có 'lap_toi_da' là dây quay ngược (vòng lặp có giới hạn). Mọi vòng khác bị từ chối.
"""
import json, os, re
from .nodes import REGISTRY

PHIEN_BAN = 1
TU_DANH_RIENG = {"input", "prev", "ngay", "gio", "kenh", "phan_tu", "chi_so", "phan_hoi", "lan_lap", "cai_dat"}


class LoiSoDo(Exception):
    def __init__(self, loi):
        self.loi = loi if isinstance(loi, list) else [loi]
        super().__init__("Sơ đồ lỗi:\n- " + "\n- ".join(self.loi))


class Day:
    __slots__ = ("tu", "den", "cong", "lap_toi_da", "ao", "stt")

    def __init__(self, tu, den, cong=None, lap_toi_da=None, ao=False, stt=-1):
        self.tu, self.den, self.cong, self.lap_toi_da, self.ao, self.stt = tu, den, cong, lap_toi_da, ao, stt

    @property
    def khoa(self):
        return f"{self.tu}:{self.cong or ''}>{self.den}"


def doc_file(path):
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except ValueError as e:
            raise LoiSoDo(f"File {os.path.basename(path)} không phải JSON hợp lệ: {e}")
    return SoDo(data, nguon=path)


class SoDo:
    def __init__(self, data, nguon="", la_con=False):
        self.data, self.nguon, self.la_con = data, nguon, la_con
        self.ten = data.get("ten", os.path.basename(nguon))
        loi = []
        if int(data.get("phien_ban", 1)) > PHIEN_BAN:
            loi.append(f"File phiên bản {data.get('phien_ban')} mới hơn app (hỗ trợ {PHIEN_BAN}), cần cập nhật AiLink")
        self.nodes = {}
        for n in data.get("nodes", []):
            nid = n.get("id", "")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nid or ""):
                loi.append(f"id node '{nid}' không hợp lệ (chỉ chữ không dấu, số, gạch dưới)")
                continue
            if nid in TU_DANH_RIENG:
                loi.append(f"id '{nid}' trùng tên biến dành riêng")
            if nid in self.nodes:
                loi.append(f"Trùng id node: {nid}")
            loai = n.get("loai")
            if loai not in REGISTRY or (loai.startswith("_") and not la_con):
                loi.append(f"Node '{nid}': loại '{loai}' không có")
            else:
                for e in REGISTRY[loai].kiem_tra(n.get("cai_dat", {})):
                    loi.append(f"Node '{nid}': {e}")
            n.setdefault("cai_dat", {})
            self.nodes[nid] = n
        if not self.nodes:
            loi.append("Sơ đồ không có node nào")
        self.day = []
        for i, d in enumerate(data.get("day", [])):
            tu, den, cong, lap = d.get("tu"), d.get("den"), d.get("cong"), d.get("lap_toi_da")
            if tu not in self.nodes or den not in self.nodes:
                loi.append(f"Dây {tu} → {den}: node không tồn tại")
                continue
            ports = self.cong_ra(tu)
            if ports and cong not in ports:
                loi.append(f"Dây {tu} → {den}: node '{tu}' có cổng {ports}, phải ghi 'cong'")
            if not ports and cong:
                loi.append(f"Dây {tu} → {den}: node '{tu}' chỉ có 1 cổng, bỏ 'cong'")
            if lap is not None and (not isinstance(lap, int) or not 1 <= lap <= 20):
                loi.append(f"Dây {tu} → {den}: lap_toi_da phải là số 1–20")
            self.day.append(Day(tu, den, cong, lap, stt=i))
        if loi:
            raise LoiSoDo(loi)

        self.tien = [d for d in self.day if d.lap_toi_da is None]
        self.lui = [d for d in self.day if d.lap_toi_da is not None]
        self.ra_tien = {n: [] for n in self.nodes}
        self.vao_tien = {n: [] for n in self.nodes}
        for d in self.tien:
            self.ra_tien[d.tu].append(d)
            self.vao_tien[d.den].append(d)
        self.thu_tu = self._topo(self.nodes, self.tien)
        self.to_tien = self._to_tien_tat_ca(self.thu_tu, self.vao_tien)
        for d in self.lui:
            if d.den != d.tu and d.den not in self.to_tien[d.tu]:
                loi.append(f"Dây quay ngược {d.tu} → {d.den}: '{d.den}' phải đứng trước '{d.tu}'")
        self._than_lap(loi)
        if not la_con:
            for nid, n in self.nodes.items():
                if n["loai"] == "dang_bai" and not any(self.nodes[a]["loai"] == "cho_duyet" for a in self.to_tien[nid]):
                    loi.append(f"Node Đăng bài '{nid}' phải đứng sau một node Chờ anh duyệt")
        if loi:
            raise LoiSoDo(loi)
        self._lich()

    def cong_ra(self, nid):
        n = self.nodes[nid]
        return REGISTRY[n["loai"]].cong_ra(n.get("cai_dat", {}))

    @staticmethod
    def _topo(nodes, day):
        bac = {n: 0 for n in nodes}
        ra = {n: [] for n in nodes}
        for d in day:
            bac[d.den] += 1
            ra[d.tu].append(d.den)
        hang = [n for n in nodes if bac[n] == 0]
        kq = []
        while hang:
            n = hang.pop(0)
            kq.append(n)
            for m in ra[n]:
                bac[m] -= 1
                if bac[m] == 0:
                    hang.append(m)
        if len(kq) != len(nodes):
            vong = [n for n in nodes if bac[n] > 0]
            raise LoiSoDo(f"Có vòng lặp không giới hạn qua các node {vong}: dây quay ngược phải ghi 'lap_toi_da'")
        return kq

    @staticmethod
    def _to_tien_tat_ca(thu_tu, vao):
        tt = {}
        for n in thu_tu:
            s = set()
            for d in vao[n]:
                s.add(d.tu)
                s |= tt[d.tu]
            tt[n] = s
        return tt

    def con_chau(self, nid, trong=None):
        """Các node phía sau nid theo dây tiến (trong lịch chạy của phạm vi này)."""
        ra = self.lich_ra if trong is None else trong
        thay, hang = set(), [nid]
        while hang:
            n = hang.pop()
            for d in ra.get(n, []):
                if d.den not in thay:
                    thay.add(d.den)
                    hang.append(d.den)
        return thay

    def _than_lap(self, loi):
        """Đoạn lặp của mỗi node Cho mỗi: nằm sau nó và trước node Gộp kết thúc."""
        self.than = {}
        for fid, n in self.nodes.items():
            if n["loai"] != "cho_moi":
                continue
            end = n["cai_dat"].get("ket_thuc")
            if end not in self.nodes or self.nodes[end]["loai"] != "gop":
                loi.append(f"Cho mỗi '{fid}': ket_thuc phải là id một node Gộp")
                continue
            if fid not in self.to_tien[end]:
                loi.append(f"Cho mỗi '{fid}': node Gộp '{end}' phải nằm phía sau")
                continue
            body = {x for x in self.nodes if fid in self.to_tien[x] and x in self.to_tien[end]}
            for x in body:
                for d in self.ra_tien[x]:
                    if d.den not in body and d.den != end:
                        loi.append(f"Node '{x}' trong đoạn lặp của '{fid}' nối ra ngoài tới '{d.den}' (chỉ được nối vào '{end}')")
                for d in self.vao_tien[x]:
                    if d.tu not in body and d.tu != fid:
                        loi.append(f"Node '{x}' trong đoạn lặp của '{fid}' nhận dây từ ngoài '{d.tu}' (dùng biến {{{{{d.tu}}}}} thay dây)")
            for d in self.ra_tien[fid]:
                if d.den not in body and d.den != end:
                    loi.append(f"Cho mỗi '{fid}' chỉ được nối vào đoạn lặp, không nối tới '{d.den}'")
            for d in self.lui:
                if (d.tu in body) != (d.den in body):
                    loi.append(f"Dây quay ngược {d.tu} → {d.den} cắt ngang đoạn lặp của '{fid}'")
            self.than[fid] = (body, end)
        # chỉ đoạn lặp ngoài cùng do phạm vi này lo; đoạn lồng bên trong do sơ đồ con lo
        self.so_huu = {}
        for fid, (body, end) in self.than.items():
            if any(fid in b for g, (b, _) in self.than.items() if g != fid):
                continue
            for x in body:
                self.so_huu[x] = fid

    def _lich(self):
        """Đồ thị dùng để chạy ở phạm vi này: bỏ node trong đoạn lặp, thêm dây ảo Cho mỗi → Gộp."""
        self.lich_nodes = [n for n in self.thu_tu if n not in self.so_huu]
        self.lich_vao = {n: [] for n in self.lich_nodes}
        self.lich_ra = {n: [] for n in self.lich_nodes}
        for d in self.tien:
            if d.tu in self.so_huu or d.den in self.so_huu:
                continue
            self.lich_vao[d.den].append(d)
            self.lich_ra[d.tu].append(d)
        for fid, (body, end) in self.than.items():
            if fid in self.so_huu:
                continue
            if not any(d.tu == fid for d in self.lich_vao[end]):
                d = Day(fid, end, ao=True)
                self.lich_vao[end].append(d)
                self.lich_ra[fid].append(d)
        self.lich_lui = {n: [] for n in self.lich_nodes}
        for d in self.lui:
            if d.tu not in self.so_huu:
                self.lich_lui[d.tu].append(d)
        self.lich_to_tien = self._to_tien_tat_ca(self.lich_nodes, self.lich_vao)

    def so_do_doan_lap(self, fid):
        """Sơ đồ con cho 1 lượt của Cho mỗi: node fid thành node phần tử."""
        body, end = self.than[fid]
        nodes = [{"id": fid, "loai": "_phan_tu", "cai_dat": {}}] + [self.nodes[x] for x in self.thu_tu if x in body]
        day, ket_thuc = [], []
        for d in self.day:
            if d.tu in body | {fid} and d.den in body:
                day.append({"tu": d.tu, "den": d.den, "cong": d.cong, "lap_toi_da": d.lap_toi_da})
            elif d.den == end and d.tu in body:
                ket_thuc.append((d.tu, d.cong))
        con = SoDo({"phien_ban": PHIEN_BAN, "ten": f"{self.ten} / {fid}", "nodes": nodes, "day": day},
                   nguon=self.nguon, la_con=True)
        con.ket_thuc = ket_thuc
        return con
