"""Engine chạy sơ đồ theo đồ thị (bản đặc tả mục 4).

- Node chạy khi mọi dây vào đã có dữ liệu; nhánh độc lập chạy song song (tối đa song_song).
- Điều kiện / Kiểm tra / Kiểm duyệt / Duyệt chọn cổng ra; nhánh không được chọn → Bỏ qua.
- Dây quay ngược có lap_toi_da: chạy lại đoạn từ node đích, kèm {{phan_hoi}}, {{lan_lap}}.
- Cho mỗi: chạy đoạn lặp cho từng phần tử (sơ đồ con), Gộp gom kết quả.
- Cache theo mã băm (loại + cài đặt đã thay biến + đầu vào). Lưu trạng thái sau mỗi node
  nên tắt app giữa chừng vẫn chạy tiếp được; chạy lại từ node bất kỳ.
"""
import copy, datetime, hashlib, json, os, re, threading, time, uuid
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from . import config, so_do as so_do_mod, kenh as kenh_mod
from .doi_ai import DoiAI
from .nodes import REGISTRY, KetQua, LoiNode, ChoDuyet, chu, lay_json
from .providers import AIError

TRANG_THAI = ("cho", "dang_chay", "xong", "loi", "bo_qua", "cho_duyet")
_BIEN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)\s*\}\}")


def node_moi():
    return {"trang_thai": "cho", "ra": None, "cong": None, "loi": None, "ly_do": None, "ghi_chu": None,
            "ai": None, "tay": None, "chi_phi": 0.0, "token_vao": 0, "token_ra": 0, "bat_dau": None,
            "ket_thuc": None, "giay": None, "lan_lap": 0, "so_lan_chay": 0, "tu_cache": False,
            "nhat_ky": [], "canh_bao": [], "lenh": [], "the_he": 0, "phan_hoi": None, "rieng": {}, "giu": {}}


def _lay_duong(goc, phan):
    v = goc
    for p in phan:
        if isinstance(v, str) and v.strip().startswith(("{", "[")):
            try:
                v = lay_json(v)
            except LoiNode:
                return None
        if isinstance(v, dict):
            v = v.get(p)
        elif isinstance(v, list) and p.isdigit() and int(p) < len(v):
            v = v[int(p)]
        else:
            return None
    return v


class NX:
    """Ngữ cảnh đưa cho node khi chạy."""

    def __init__(self, lan, nid, dau_vao, tu_cho_moi):
        self.lan, self.id = lan, nid
        self.spec = lan.so_do.nodes[nid]
        self.loai = REGISTRY[self.spec["loai"]]
        self.cai_dat = self.spec.get("cai_dat", {})
        self.st = lan.st["nodes"][nid]
        self.dau_vao = dau_vao
        self.tu_cho_moi = tu_cho_moi
        vals = list(dau_vao.values())
        self.prev = vals[0] if len(vals) == 1 else (dict(dau_vao) if vals else lan.bien_goc().get("input"))
        self.phan_hoi = self.st.get("phan_hoi")
        self.lan_lap = self.st.get("lan_lap", 0)
        self.rieng = self.st.setdefault("rieng", {})
        self.giu = self.st.setdefault("giu", {})
        self.bien = lan.bien_goc()
        self.bien.update(prev=self.prev, phan_hoi=self.phan_hoi, lan_lap=self.lan_lap,
                         cai_dat={**self.loai.cai_dat_mau, **self.cai_dat})
        k = lan.kenh_cho(nid)
        if k is not None:
            self.bien["kenh"] = k
        self.thieu_bien = set()

    # ---- biến ----
    def _tra(self, ten):
        phan = ten.split(".")
        goc = phan[0]
        if goc in self.bien:
            return _lay_duong(self.bien[goc], phan[1:])
        v = self.lan.ket_qua_node(goc)
        if v is not None:
            return _lay_duong(v, phan[1:])
        self.thieu_bien.add(ten)
        return None

    def render(self, s):
        if not isinstance(s, str):
            return s
        return _BIEN.sub(lambda m: chu(self._tra(m.group(1))), s)

    def render_gia_tri(self, s):
        """Như render, nhưng '{{x}}' đứng một mình thì giữ nguyên kiểu (list, dict)."""
        if isinstance(s, str):
            m = _BIEN.fullmatch(s.strip())
            if m:
                return self._tra(m.group(1))
        return self.render(s)

    def render_sau(self, x):
        if isinstance(x, str):
            return self.render(x)
        if isinstance(x, list):
            return [self.render_sau(v) for v in x]
        if isinstance(x, dict):
            return {k: self.render_sau(v) for k, v in x.items()}
        return x

    def cd(self, khoa, mac_dinh=None):
        v = self.cai_dat.get(khoa, self.loai.cai_dat_mau.get(khoa, mac_dinh))
        return self.render(v) if isinstance(v, str) else v

    # ---- AI ----
    def ai(self, lenh, he_thong="", vai="kich_ban", json=False, gia_lap=None):
        k = self.bien.get("kenh")
        if k and self.cai_dat.get("doc_ho_so", True):
            he_thong = (kenh_mod.tom_tat(k) + "\n\n" + (he_thong or "")).strip()
        kq = self.lan.goc.doi.goi(lenh, he_thong, ai=self.cai_dat.get("ai", "tu_chon"), vai=self.cai_dat.get("vai", vai),
                              che_do=self.cai_dat.get("che_do"), du_phong=self.cai_dat.get("du_phong", []),
                              model=self.cai_dat.get("model"), gia_lap=gia_lap, log=self.log)
        with self.lan.khoa:
            st = self.st
            st["ai"], st["tay"] = kq.ai, kq.tay
            st["token_vao"] += kq.token_vao
            st["token_ra"] += kq.token_ra
            st["chi_phi"] = round(st["chi_phi"] + kq.chi_phi, 6)
            st["canh_bao"].extend(kq.canh_bao)
            st["nhat_ky"].extend(kq.nhat_ky)
            st["lenh"].append({"ai": kq.ai, "tay": kq.tay, "he_thong": he_thong[:2000], "lenh": lenh[:8000]})
            if kq.la_gia_lap and self.cai_dat.get("ai") != "gia_lap":
                st["rieng"]["_du_phong_gia_lap"] = True
        self.lan.goc.cong_chi_phi(kq.chi_phi)
        if json:
            return lay_json(kq.van_ban)
        return kq.van_ban

    # ---- tiện ích ----
    def log(self, s):
        with self.lan.khoa:
            self.st["nhat_ky"].append(s)

    def ghi_chu(self, s):
        self.st["ghi_chu"] = s

    def ghi_tep(self, ten, noi_dung, noi_them=False):
        d = os.path.join(self.lan.goc.thu_muc, "tep", *self.lan.duong_dan_pham_vi())
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, ten)
        with open(p, "a" if noi_them else "w", encoding="utf-8") as f:
            f.write(noi_dung)
        return p

    def ghi_xuat(self, rel, noi_dung):
        p = os.path.join(config.thu_muc("xuat", self.lan.goc.home), rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(noi_dung)
        return p

    def duong_dan_an_toan(self, rel):
        goc = os.path.realpath(self.lan.goc.goc_file)
        p = os.path.realpath(os.path.join(goc, rel))
        if os.path.commonpath([goc, p]) != goc:
            raise LoiNode(f"Đường dẫn '{rel}' ra ngoài thư mục cho phép {goc}")
        return p

    def danh_sach_kenh(self):
        return kenh_mod.danh_sach(self.lan.goc.home)

    def ho_so_kenh(self, ma):
        k = kenh_mod.doc(ma, self.lan.goc.home)
        if k is None:
            raise LoiNode(f"Không có hồ sơ kênh '{ma}'")
        return k

    def chay_doan_lap(self, items, song_song=2):
        return self.lan.chay_doan_lap(self, items, song_song)

    def chay_khoi_con(self, ten_file, dau_vao):
        return self.lan.chay_khoi_con(self, ten_file, dau_vao)

    def _to_tien(self, loai):
        return [st for st, sp in self.lan.to_tien_xuyen_pham_vi(self.id) if sp["loai"] == loai]

    def da_duyet(self):
        return any(st["trang_thai"] == "xong" and st["cong"] == "duyet" for st in self._to_tien("cho_duyet"))

    def co_nguon_chua_ro(self):
        return any(st["trang_thai"] == "xong" and isinstance(st["ra"], dict) and st["ra"].get("loai_nguon") == "chua_ro"
                   for st in self._to_tien("tai_video_nguon"))

    def kiem_duyet_chan(self):
        return any(st["trang_thai"] == "xong" and st["cong"] == "chan" for st in self._to_tien("kiem_duyet"))

    def canh_bao_truoc(self):
        cb = []
        for st in self._to_tien("kiem_duyet"):
            if st["trang_thai"] == "xong" and st["cong"] in ("can_xem", "chan"):
                cb.append(f"Kiểm duyệt: {st['cong']} — " + "; ".join(
                    f"{v.get('loai')}: {v.get('goi_y', '')}" for v in (st["ra"] or {}).get("vi_pham", [])))
        if self.co_nguon_chua_ro():
            cb.append("Nguồn video CHƯA RÕ bản quyền: không được đăng, chỉ xuất file")
        return cb


class Goc:
    """Phần dùng chung cho cả cây lần chạy (lần chạy chính + các lần chạy con)."""

    def __init__(self, home, doi, song_song, dung_cache, tran_chi_phi, on_event, thu_muc, goc_file, luu):
        self.home, self.doi, self.song_song = home, doi, song_song
        self.dung_cache, self.tran_chi_phi, self.on_event = dung_cache, tran_chi_phi, on_event
        self.thu_muc, self.goc_file, self.luu = thu_muc, goc_file, luu
        self.khoa = threading.RLock()
        self.chi_phi = 0.0
        self.dung = False
        self.lan_chinh = None

    def cong_chi_phi(self, x):
        with self.khoa:
            self.chi_phi += x
            if self.tran_chi_phi is not None and self.chi_phi > self.tran_chi_phi:
                self.dung = True

    def phat(self, ev):
        if self.on_event:
            try:
                self.on_event(ev)
            except Exception:
                pass


class LanChay:
    def __init__(self, so_do, dau_vao="", kenh=None, home=None, doi=None, trang_thai=None, song_song=None,
                 dung_cache=True, tran_chi_phi=None, on_event=None, luu=True, _cha=None):
        self.so_do = so_do
        if _cha is not None:
            self.goc, self.cha, self.cha_node, self.st = _cha["goc"], _cha["lan"], _cha["node"], _cha["st"]
            self.pham_vi = _cha["pham_vi"]
            self.bien_ngoai = _cha["bien"]
        else:
            home = home or config.HOME
            cd = config.cai_dat(home)
            st = trang_thai or {
                "id": time.strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:4],
                "so_do": so_do.data, "nguon": so_do.nguon, "la_con": so_do.la_con, "ten": so_do.ten, "dau_vao": dau_vao,
                "kenh": kenh, "trang_thai": "moi", "bat_dau": time.strftime("%Y-%m-%d %H:%M:%S"),
                "ket_thuc": None, "ngay": datetime.date.today().isoformat(), "nodes": {}, "dem_lap": {},
                "canh_bao": [], "chi_phi": 0.0}
            thu_muc = os.path.join(config.thu_muc("lan_chay", home), st["id"])
            self.goc = Goc(home, doi or DoiAI(home=home), song_song or cd["song_song"], dung_cache,
                           tran_chi_phi, on_event, thu_muc, os.path.dirname(os.path.abspath(home)), luu)
            self.goc.chi_phi = st.get("chi_phi", 0.0)
            self.goc.lan_chinh = self
            self.cha = self.cha_node = None
            self.st = st
            self.pham_vi = []
            ks = st.get("kenh")
            self.bien_ngoai = {"kenh": kenh_mod.doc(ks, home) if isinstance(ks, str) else ks}
        self.khoa = self.goc.khoa
        for nid in so_do.nodes:
            self.st["nodes"].setdefault(nid, node_moi())
        self.st.setdefault("dem_lap", {})

    # ---------- biến & tra cứu ----------
    def bien_goc(self):
        g = self.goc.lan_chinh.st
        b = {"input": g.get("dau_vao", ""), "ngay": g.get("ngay"), "gio": time.strftime("%H:%M")}
        b.update({k: v for k, v in self.bien_ngoai.items() if v is not None and k not in ("ket_qua",)})
        return b

    def ket_qua_node(self, nid):
        if nid in self.st["nodes"] and self.st["nodes"][nid]["trang_thai"] == "xong":
            return self.st["nodes"][nid]["ra"]
        return (self.bien_ngoai.get("ket_qua") or {}).get(nid)

    def tat_ca_ket_qua(self):
        kq = dict(self.bien_ngoai.get("ket_qua") or {})
        kq.update({n: s["ra"] for n, s in self.st["nodes"].items() if s["trang_thai"] == "xong"})
        return kq

    def kenh_cho(self, nid):
        sd = self.so_do
        tt = sd.lich_to_tien.get(nid, sd.to_tien.get(nid, set()))
        for a in reversed(sd.thu_tu):
            if a in tt and sd.nodes[a]["loai"] == "chon_kenh" and self.st["nodes"][a]["trang_thai"] == "xong":
                return self.st["nodes"][a]["ra"]
        return self.bien_ngoai.get("kenh")

    def to_tien_xuyen_pham_vi(self, nid):
        kq = [(self.st["nodes"][a], self.so_do.nodes[a]) for a in self.so_do.to_tien.get(nid, ())]
        if self.cha is not None:
            kq += self.cha.to_tien_xuyen_pham_vi(self.cha_node)
        return kq

    def duong_dan_pham_vi(self):
        return list(self.pham_vi)

    # ---------- lưu & sự kiện ----------
    def _luu(self):
        g = self.goc
        if not g.luu:
            return
        with self.khoa:
            g.lan_chinh.st["chi_phi"] = round(g.chi_phi, 6)
            for _ in range(3):  # node khác có thể đang thêm khoá vào dict ngoài khoá
                try:
                    config.ghi_json(os.path.join(g.thu_muc, "trang_thai.json"), g.lan_chinh.st)
                    break
                except RuntimeError:
                    time.sleep(0.01)

    def _doi(self, nid, ly_do=None):
        st = self.st["nodes"][nid]
        self.goc.phat({"loai": "node", "lan": self.goc.lan_chinh.st["id"],
                       "duong_dan": "/".join(self.pham_vi + [nid]), "trang_thai": st["trang_thai"],
                       "cong": st["cong"], "ghi_chu": st.get("ghi_chu"), "loi": st.get("loi")})
        self._luu()

    # ---------- trạng thái dây ----------
    def _day(self, d):
        u = self.st["nodes"][d.tu]
        t = u["trang_thai"]
        if t == "xong":
            return "song" if (d.cong is None or d.cong == u["cong"]) else "chet"
        if t == "bo_qua":
            return "chan" if u.get("ly_do") == "loi_truoc" else "chet"
        if t == "loi":
            return "chan"
        return "cho"

    def _quet(self):
        san = []
        sd = self.so_do
        for v in sd.lich_nodes:
            st = self.st["nodes"][v]
            if st["trang_thai"] != "cho":
                continue
            ins = sd.lich_vao[v]
            if not ins:
                san.append(v)
                continue
            tt = [self._day(d) for d in ins]
            xong_truoc = sd.nodes[v]["loai"] == "gop" and sd.nodes[v]["cai_dat"].get("che_do") == "xong_truoc"
            if xong_truoc and "song" in tt:
                san.append(v)
            elif "cho" in tt:
                continue
            elif "chan" in tt:
                self._bo_qua(v, "loi_truoc")
            elif "song" in tt:
                san.append(v)
            else:
                self._bo_qua(v, "nhanh")
        return san

    def _bo_qua(self, v, ly_do):
        st = self.st["nodes"][v]
        st["trang_thai"], st["ly_do"] = "bo_qua", ly_do
        self._doi(v)

    def _dau_vao(self, v):
        vao = {}
        for d in self.so_do.lich_vao[v]:
            if self._day(d) == "song":
                vao[d.tu] = self.st["nodes"][d.tu]["ra"]
        return vao

    # ---------- chạy 1 node ----------
    def _khoa_cache(self, nx):
        s = json.dumps([nx.spec["loai"], nx.render_sau(nx.cai_dat), nx.dau_vao, nx.phan_hoi, nx.lan_lap,
                        (nx.bien.get("kenh") or {}).get("ma") if isinstance(nx.bien.get("kenh"), dict) else None,
                        nx.bien.get("phan_tu")], ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _thuc_thi(self, v, the_he):
        with self.khoa:
            nx = NX(self, v, self._dau_vao(v), any(d.ao for d in self.so_do.lich_vao[v] if self._day(d) == "song"))
        loai = nx.loai
        dung_cache = (self.goc.dung_cache and loai.cache and not nx.cai_dat.get("khong_cache"))
        p_cache = None
        try:
            if dung_cache:
                k = self._khoa_cache(nx)
                p_cache = os.path.join(config.thu_muc("cache", self.goc.home), k[:2], k + ".json")
                c = config.doc_json(p_cache)
                if c is not None:
                    return ("ok", KetQua(c["ra"], c.get("cong")), True)
            kq = loai.chay(nx)
            if nx.thieu_bien:
                nx.log("Biến không có giá trị: " + ", ".join(sorted(nx.thieu_bien)))
            if p_cache and not nx.rieng.get("_du_phong_gia_lap"):
                config.ghi_json(p_cache, {"ra": kq.ra, "cong": kq.cong, "luc": time.strftime("%Y-%m-%d %H:%M:%S")})
            return ("ok", kq, False)
        except ChoDuyet as cd:
            return ("duyet", cd.xem_truoc, False)
        except (LoiNode, AIError, so_do_mod.LoiSoDo) as e:
            return ("loi", str(e), False)
        except Exception as e:  # lỗi lập trình: vẫn giữ engine sống
            return ("loi", f"{type(e).__name__}: {e}", False)

    def _ket_thuc_node(self, v, the_he, kq):
        st = self.st["nodes"][v]
        if st["the_he"] != the_he:
            return  # node đã bị đặt lại bởi vòng lặp, bỏ kết quả cũ
        loai, gia_tri, tu_cache = kq
        st["ket_thuc"] = time.strftime("%Y-%m-%d %H:%M:%S")
        st["giay"] = round(time.time() - st.pop("_t0", time.time()), 3)
        if loai == "duyet":
            st["trang_thai"] = "cho_duyet"
            st["rieng"]["xem_truoc"] = gia_tri
            self._doi(v)
            return
        if loai == "loi":
            st["trang_thai"], st["loi"] = "loi", gia_tri
            self.goc.lan_chinh.st["canh_bao"].append(f"{'/'.join(self.pham_vi + [v])}: {gia_tri}")
            self._doi(v)
            return
        st["trang_thai"], st["ra"], st["cong"], st["tu_cache"] = "xong", gia_tri.ra, gia_tri.cong, tu_cache
        self._doi(v)
        for d in self.so_do.lich_lui.get(v, []):
            if d.cong is not None and d.cong != gia_tri.cong:
                continue
            dem = self.st["dem_lap"].get(d.khoa, 0)
            if dem < d.lap_toi_da:
                self.st["dem_lap"][d.khoa] = dem + 1
                vung = {d.den} | self.so_do.con_chau(d.den)
                self._dat_lai(vung, tang_lap=True)
                self.st["nodes"][d.den]["phan_hoi"] = gia_tri.ra
                self.goc.phat({"loai": "vong_lap", "lan": self.goc.lan_chinh.st["id"],
                               "tu": "/".join(self.pham_vi + [v]), "den": d.den, "lan_thu": dem + 1})
            else:
                st["giu"]["het_vong"] = True
                msg = f"{'/'.join(self.pham_vi + [v])}: hết {d.lap_toi_da} lượt vòng lặp về '{d.den}' mà vẫn '{gia_tri.cong}'"
                st["canh_bao"].append(msg)
                self.goc.lan_chinh.st["canh_bao"].append(msg)
                self._luu()

    def _dat_lai(self, vung, tang_lap=False):
        vung = set(vung)
        for n in list(vung):
            if n in self.so_do.than and n not in self.so_do.so_huu:
                vung |= self.so_do.than[n][0]
        for n in vung:
            cu = self.st["nodes"][n]
            moi = node_moi()
            moi["the_he"] = cu["the_he"] + 1
            moi["lan_lap"] = cu.get("lan_lap", 0) + (1 if tang_lap else 0)
            moi["so_lan_chay"] = cu.get("so_lan_chay", 0)
            moi["giu"] = cu.get("giu", {}) if tang_lap else {}
            self.st["nodes"][n] = moi
            self._doi(n)

    # ---------- vòng chạy chính ----------
    def chay(self):
        with self.khoa:
            for n, s in self.st["nodes"].items():
                if s["trang_thai"] == "dang_chay":
                    s["trang_thai"] = "cho"
            self.st["trang_thai"] = "dang_chay"
        self.goc.phat({"loai": "lan", "lan": self.goc.lan_chinh.st["id"], "pham_vi": "/".join(self.pham_vi),
                       "trang_thai": "dang_chay"})
        dang = {}
        with ThreadPoolExecutor(max_workers=self.goc.song_song) as pool:
            while True:
                with self.khoa:
                    san = [] if self.goc.dung else self._quet()
                    for v in san:
                        st = self.st["nodes"][v]
                        st["trang_thai"] = "dang_chay"
                        st["bat_dau"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        st["_t0"] = time.time()
                        st["so_lan_chay"] = st.get("so_lan_chay", 0) + 1
                        self._doi(v)
                        dang[pool.submit(self._thuc_thi, v, st["the_he"])] = (v, st["the_he"])
                if not dang:
                    break
                xong, _ = wait(list(dang), return_when=FIRST_COMPLETED)
                for f in xong:
                    v, th = dang.pop(f)
                    with self.khoa:
                        self._ket_thuc_node(v, th, f.result())
        with self.khoa:
            self.st["trang_thai"] = self._tong_ket()
            if self.cha is None:
                self.st["ket_thuc"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._luu()
        self.goc.phat({"loai": "lan", "lan": self.goc.lan_chinh.st["id"], "pham_vi": "/".join(self.pham_vi),
                       "trang_thai": self.st["trang_thai"]})
        return self.st["trang_thai"]

    def _tong_ket(self):
        tt = [s["trang_thai"] for n, s in self.st["nodes"].items() if n not in self.so_do.so_huu]
        if "cho_duyet" in tt:
            return "cho_duyet"
        if "loi" in tt:
            return "loi"
        if self.goc.dung and "cho" in tt:
            return "dung_chi_phi"
        if any(s.get("giu", {}).get("het_vong") for s in self.st["nodes"].values()):
            return "can_xem"
        return "xong"

    # ---------- Cho mỗi & khối con ----------
    def _lan_con(self, so_do, st, nx, pham_vi, bien):
        return LanChay(so_do, _cha={"goc": self.goc, "lan": self, "node": nx.id, "st": st,
                                    "pham_vi": self.pham_vi + pham_vi, "bien": bien})

    def chay_doan_lap(self, nx, items, song_song):
        sd_con = self.so_do.so_do_doan_lap(nx.id)
        with self.khoa:
            con = nx.rieng.setdefault("con", {})
        ket_qua_ngoai = self.tat_ca_ket_qua()
        kenh = nx.bien.get("kenh")

        def mot(i, item):
            with self.khoa:
                st = con.get(str(i))
                if st is None or st.get("phan_tu") != item:
                    st = {"phan_tu": item, "trang_thai": "moi", "nodes": {}, "dem_lap": {}}
                    con[str(i)] = st
            lan = self._lan_con(sd_con, st, nx, [nx.id, str(i)],
                                {"phan_tu": item, "chi_so": i, "kenh": kenh, "ket_qua": ket_qua_ngoai})
            if st["trang_thai"] not in ("xong", "can_xem"):
                lan.chay()
            return lan

        with ThreadPoolExecutor(max_workers=max(1, song_song)) as pool:
            lans = list(pool.map(lambda p: mot(*p), list(enumerate(items))))
        kq, cho, loi = [], [], []
        for i, lan in enumerate(lans):
            t = lan.st["trang_thai"]
            if t == "cho_duyet":
                cho.append(i)
            elif t == "loi":
                loi.append(i)
            ra = {}
            for (src, cong) in sd_con.ket_thuc:
                s = lan.st["nodes"][src]
                if s["trang_thai"] == "xong" and (cong is None or s["cong"] == cong):
                    ra[src] = s["ra"]
            kq.append({"phan_tu": items[i], "chi_so": i, "trang_thai": t,
                       "ket_qua": next(iter(ra.values())) if len(ra) == 1 else ra})
        if cho:
            raise ChoDuyet({"doan_lap": nx.id, "cho_duyet": cho, "so_phan_tu": len(items)})
        if loi and len(loi) == len(items):
            raise LoiNode(f"Mọi phần tử của '{nx.id}' đều lỗi")
        if loi:
            nx.st["canh_bao"].append(f"{len(loi)}/{len(items)} phần tử lỗi: {loi}")
        return kq

    def chay_khoi_con(self, nx, ten_file, dau_vao):
        p = ten_file
        for d in (config.thu_muc("so_do", self.goc.home), config.MAU_DIR):
            if os.path.exists(os.path.join(d, ten_file)):
                p = os.path.join(d, ten_file)
                break
        if not os.path.exists(p):
            raise LoiNode(f"Không tìm thấy sơ đồ con '{ten_file}'")
        sd = so_do_mod.doc_file(p)
        if any(n["loai"] == "khoi_con" for n in sd.nodes.values()) and len(self.pham_vi) > 6:
            raise LoiNode("Khối con lồng quá sâu")
        with self.khoa:
            st = nx.rieng.setdefault("con", {}).setdefault("0", {"trang_thai": "moi", "nodes": {}, "dem_lap": {}})
        lan = self._lan_con(sd, st, nx, [nx.id, "0"], {"kenh": nx.bien.get("kenh"), "ket_qua": {}})
        lan.bien_ngoai["input"] = chu(dau_vao)
        if st["trang_thai"] not in ("xong", "can_xem"):
            lan.chay()
        t = st["trang_thai"]
        if t == "cho_duyet":
            raise ChoDuyet({"khoi_con": nx.id})
        if t == "loi":
            raise LoiNode(f"Khối con '{ten_file}' lỗi: " + "; ".join(
                f"{n}: {s['loi']}" for n, s in st["nodes"].items() if s["trang_thai"] == "loi"))
        cuoi = [n for n in sd.lich_nodes if not sd.lich_ra[n] and st["nodes"][n]["trang_thai"] == "xong"]
        return st["nodes"][cuoi[0]]["ra"] if len(cuoi) == 1 else {n: st["nodes"][n]["ra"] for n in cuoi}

    # ---------- thao tác của anh ----------
    def duyet(self, duong_dan, quyet_dinh, ghi_chu=""):
        """duong_dan: 'duyet' hoặc 'cho_moi_kenh/2/duyet' (node trong đoạn lặp)."""
        if quyet_dinh not in ("duyet", "sua", "bo"):
            raise ValueError("quyet_dinh phải là duyet / sua / bo")
        phan = duong_dan.split("/")
        with self.khoa:
            st = self.st
            cha_list = []
            while len(phan) > 1:
                cha_list.append(st["nodes"][phan[0]])
                st = st["nodes"][phan[0]]["rieng"]["con"][phan[1]]
                phan = phan[2:]
            n = st["nodes"].get(phan[0])
            if n is None or n["trang_thai"] != "cho_duyet":
                raise ValueError(f"Node '{duong_dan}' không ở trạng thái chờ duyệt")
            n["rieng"]["quyet_dinh"], n["rieng"]["ghi_chu"] = quyet_dinh, ghi_chu
            n["trang_thai"] = "cho"
            for c in cha_list:
                c["trang_thai"] = "cho"
            self._luu()

    def chay_lai_tu(self, nid):
        """Giữ kết quả các node đã xong, chạy lại nid và mọi node phía sau."""
        if nid not in self.so_do.lich_nodes:
            raise ValueError(f"Không có node '{nid}' ở phạm vi chính")
        with self.khoa:
            vung = {nid} | self.so_do.con_chau(nid)
            for d in self.so_do.lui:
                if d.den in vung:
                    self.st["dem_lap"].pop(d.khoa, None)
            self._dat_lai(vung)
            self.goc.dung = False
        return self.chay()

    def cho_duyet_list(self):
        """Mọi node đang chờ duyệt (cả trong đoạn lặp): [(duong_dan, xem_truoc)]."""
        kq = []

        def quet(st, tien_to):
            for n, s in st["nodes"].items():
                if s["trang_thai"] != "cho_duyet":
                    continue
                if "con" in s.get("rieng", {}):
                    for i, c in s["rieng"]["con"].items():
                        quet(c, tien_to + [n, i])
                else:
                    kq.append(("/".join(tien_to + [n]), s["rieng"].get("xem_truoc")))
        quet(self.st, [])
        return kq


def mo_lan(id_lan, home=None, **kw):
    """Mở lại lần chạy đã lưu (tắt app giữa chừng, chờ duyệt...)."""
    home = home or config.HOME
    p = os.path.join(config.thu_muc("lan_chay", home), id_lan, "trang_thai.json")
    st = config.doc_json(p)
    if st is None:
        raise ValueError(f"Không có lần chạy {id_lan}")
    sd = so_do_mod.SoDo(st["so_do"], nguon=st.get("nguon", ""), la_con=st.get("la_con", False))
    return LanChay(sd, home=home, trang_thai=st, **kw)


def danh_sach_lan(home=None, toi_da=50):
    d = config.thu_muc("lan_chay", home)
    kq = []
    for ten in sorted(os.listdir(d), reverse=True)[:toi_da]:
        st = config.doc_json(os.path.join(d, ten, "trang_thai.json"))
        if st:
            kq.append({k: st.get(k) for k in ("id", "ten", "trang_thai", "bat_dau", "ket_thuc", "chi_phi", "dau_vao")})
    return kq
