"""Test giai đoạn 1: engine đồ thị + AI giả lập + node mẫu. Chạy: python -m unittest discover tests"""
import glob, json, os, shutil, sys, tempfile, threading, time, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ailink import config, engine, so_do, providers  # noqa: E402
from ailink.doi_ai import DoiAI, DOI_MAC_DINH  # noqa: E402
from ailink.nodes import REGISTRY, NodeType, KetQua, dang_ky, danh_sach_node  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dang_ky
class _Cham(NodeType):
    """Node test: ngủ X giây rồi trả tên mình (để đo song song)."""
    loai, ten, nhom = "_test_cham", "Chậm", "tien_ich"
    cache = False

    def chay(self, nx):
        time.sleep(float(nx.cai_dat.get("giay", 0.3)))
        return KetQua(nx.id)


@dang_ky
class _Dem(NodeType):
    """Node test: đếm số lần chạy thật (để kiểm tra cache)."""
    loai, ten, nhom = "_test_dem", "Đếm", "tien_ich"
    dem = 0

    def chay(self, nx):
        type(self).dem += 1
        return KetQua(f"lan {type(self).dem}: {nx.prev}")


@dang_ky
class _Tra(NodeType):
    """Node test: trả nguyên cai_dat['ra']."""
    loai, ten, nhom = "_test_tra", "Trả", "tien_ich"

    def chay(self, nx):
        return KetQua(nx.cai_dat["ra"])


def N(i, l, **cd):
    return {"id": i, "loai": l, "cai_dat": cd}


def D(tu, den, cong=None, lap=None):
    d = {"tu": tu, "den": den}
    if cong:
        d["cong"] = cong
    if lap:
        d["lap_toi_da"] = lap
    return d


def SD(nodes, day, la_con=True):
    return so_do.SoDo({"phien_ban": 1, "ten": "test", "nodes": nodes, "day": day}, la_con=la_con)


class Co(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        os.environ["AILINK_HOME"] = self.home
        self.doi = DoiAI(home=self.home, cho_giay=[0], cham_gia_lap=0, lay_key=lambda t: "")

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def lan(self, sd, vao="chủ đề thử", **kw):
        kw.setdefault("doi", self.doi)
        return engine.LanChay(sd, vao, home=self.home, **kw)


class TestSoDo(Co):
    def test_vong_khong_gioi_han_bi_tu_choi(self):
        with self.assertRaises(so_do.LoiSoDo) as c:
            SD([N("a", "hoi_ai"), N("b", "hoi_ai")], [D("a", "b"), D("b", "a")])
        self.assertIn("lap_toi_da", str(c.exception))

    def test_node_la_va_cong_sai(self):
        with self.assertRaises(so_do.LoiSoDo) as c:
            SD([N("a", "khong_co"), N("b", "dieu_kien", dieu_kien=[{"trai": "1", "phep": "==", "phai": "1"}]),
                N("c", "hoi_ai")], [D("b", "c")])
        s = str(c.exception)
        self.assertIn("khong_co", s)
        self.assertIn("phải ghi 'cong'", s)

    def test_dang_bai_phai_sau_cho_duyet(self):
        with self.assertRaises(so_do.LoiSoDo):
            SD([N("a", "bat_dau"), N("d", "dang_bai")], [D("a", "d")], la_con=False)

    def test_tai_video_bat_buoc_loai_nguon(self):
        with self.assertRaises(so_do.LoiSoDo):
            SD([N("t", "tai_video_nguon")], [])
        with self.assertRaises(so_do.LoiSoDo):
            SD([N("t", "tai_video_nguon", loai_nguon="cua_ai_do")], [])

    def test_doan_lap_khong_duoc_noi_ra_ngoai(self):
        with self.assertRaises(so_do.LoiSoDo) as c:
            SD([N("f", "cho_moi", ket_thuc="g", danh_sach=["a"]), N("x", "hoi_ai"), N("y", "hoi_ai"), N("g", "gop")],
               [D("f", "x"), D("x", "g"), D("x", "y")])
        self.assertIn("nối ra ngoài", str(c.exception))

    def test_moi_mau_hop_le(self):
        files = glob.glob(os.path.join(GOC, "mau", "*.ailink.json"))
        self.assertGreaterEqual(len(files), 9)
        for p in files:
            so_do.doc_file(p)

    def test_danh_sach_node(self):
        ds = {n["loai"]: n for n in danh_sach_node()}
        for k in ("bao_cao_ai", "kiem_duyet", "tom_tat", "phan_loai", "phan_tich_doi_thu", "tra_loi_binh_luan"):
            self.assertIn(k, ds)
            self.assertTrue(ds[k]["vi_du"])
        json.dumps(danh_sach_node(), ensure_ascii=False)


class TestEngine(Co):
    def test_song_song(self):
        sd = SD([N("a", "bat_dau")] + [N(f"c{i}", "_test_cham", giay=0.4) for i in range(4)] + [N("g", "gop")],
                [D("a", f"c{i}") for i in range(4)] + [D(f"c{i}", "g") for i in range(4)])
        t = time.time()
        l = self.lan(sd, song_song=4)
        self.assertEqual(l.chay(), "xong")
        self.assertLess(time.time() - t, 1.2)  # 4 × 0.4s chạy song song
        self.assertEqual(sorted(l.st["nodes"]["g"]["ra"].keys()), ["c0", "c1", "c2", "c3"])

    def test_dieu_kien_re_nhanh(self):
        sd = SD([N("a", "bat_dau"),
                 N("k", "dieu_kien", dieu_kien=[{"trai": "{{input}}", "phep": "chua", "phai": "mèo"}]),
                 N("co", "hoi_ai", ai="gia_lap", lenh="có mèo"), N("khong", "hoi_ai", ai="gia_lap", lenh="không"),
                 N("sau_khong", "hoi_ai", ai="gia_lap"), N("g", "gop")],
                [D("a", "k"), D("k", "co", "dat"), D("k", "khong", "khong_dat"), D("khong", "sau_khong"),
                 D("co", "g"), D("sau_khong", "g")])
        l = self.lan(sd, "con mèo đen")
        self.assertEqual(l.chay(), "xong")
        n = l.st["nodes"]
        self.assertEqual(n["co"]["trang_thai"], "xong")
        self.assertEqual(n["khong"]["trang_thai"], "bo_qua")
        self.assertEqual(n["sau_khong"]["trang_thai"], "bo_qua")
        self.assertEqual(list(n["g"]["ra"].keys()), ["co"])

    def test_vong_lap_viet_lai_roi_dat(self):
        sd = SD([N("a", "bat_dau"), N("viet", "kich_ban_short"), N("qc", "kiem_tra_chat_luong", nguong=8),
                 N("xong", "hoi_ai", ai="gia_lap")],
                [D("a", "viet"), D("viet", "qc"), D("qc", "viet", "khong_dat", 3), D("qc", "xong", "dat")])
        l = self.lan(sd)
        self.assertEqual(l.chay(), "xong")
        self.assertEqual(l.st["nodes"]["viet"]["lan_lap"], 1)
        self.assertIn("[Lần sửa thứ 1]", l.st["nodes"]["viet"]["lenh"][-1]["lenh"])
        self.assertIn("Câu móc chưa đủ mạnh", l.st["nodes"]["viet"]["lenh"][-1]["lenh"])

    def test_vong_lap_het_luot(self):
        sd = SD([N("a", "bat_dau"), N("viet", "hoi_ai", ai="gia_lap"),
                 N("k", "dieu_kien", dieu_kien=[{"trai": "1", "phep": ">", "phai": "2"}]), N("sau", "hoi_ai")],
                [D("a", "viet"), D("viet", "k"), D("k", "viet", "khong_dat", 2), D("k", "sau", "dat")])
        l = self.lan(sd)
        self.assertEqual(l.chay(), "can_xem")
        self.assertEqual(l.st["nodes"]["viet"]["lan_lap"], 2)
        self.assertEqual(l.st["nodes"]["sau"]["trang_thai"], "bo_qua")
        self.assertTrue(any("hết 2 lượt" in c for c in l.st["canh_bao"]))

    def test_vong_lap_node_gom_ket_qua(self):
        sd = SD([N("a", "bat_dau"), N("v", "vong_lap", so_lan=3), N("tao", "_test_dem"), N("ket", "hoi_ai", ai="gia_lap")],
                [D("a", "v"), D("v", "tao", "lap"), D("tao", "v", None, 3), D("v", "ket", "xong")])
        _Dem.dem = 0
        l = self.lan(sd, dung_cache=False)
        self.assertEqual(l.chay(), "xong")
        self.assertEqual(len(l.st["nodes"]["v"]["ra"]), 3)
        self.assertEqual(_Dem.dem, 3)

    def test_cho_moi_va_gop(self):
        sd = SD([N("a", "bat_dau"), N("f", "cho_moi", danh_sach=["vi", "en", "ja"], ket_thuc="g", song_song=3),
                 N("dich", "dich", den="{{phan_tu}}"), N("g", "gop", kieu="danh_sach")],
                [D("a", "f"), D("f", "dich"), D("dich", "g")])
        l = self.lan(sd, "xin chào")
        self.assertEqual(l.chay(), "xong")
        ra = l.st["nodes"]["g"]["ra"]
        self.assertEqual([x["phan_tu"] for x in ra], ["vi", "en", "ja"])
        self.assertTrue(ra[2]["ket_qua"].startswith("[ja]"))

    def test_cho_moi_moi_kenh_va_duyet_tung_kenh(self):
        sd = so_do.doc_file(os.path.join(GOC, "mau", "hang_loat_moi_kenh.ailink.json"))
        l = self.lan(sd, "")
        self.assertEqual(l.chay(), "cho_duyet")
        cho = l.cho_duyet_list()
        self.assertEqual(len(cho), 3)  # 3 kênh mẫu
        self.assertTrue(all(p.startswith("moi_kenh/") for p, _ in cho))
        for p, _ in cho:
            l.duyet(p, "duyet")
        self.assertEqual(l.chay(), "xong")
        ra = l.st["nodes"]["tong_hop"]["ra"]
        self.assertEqual(len(ra), 3)
        self.assertTrue(all(x["ket_qua"]["trang_thai"] == "gia_lap_chua_dang" for x in ra))
        self.assertIn("BÁO CÁO", l.st["nodes"]["bao_cao"]["ra"]["van_ban"])
        # mỗi kênh đọc đúng hồ sơ của mình
        con = l.st["nodes"]["moi_kenh"]["rieng"]["con"]
        he = [con[i]["nodes"]["ngach"]["lenh"][0]["he_thong"] for i in ("0", "1", "2")]
        self.assertIn("謎ミステリー", he[0])
        self.assertIn("AI Tools Daily", he[1])

    def test_cache_va_chay_lai_tu_node(self):
        sd = SD([N("a", "bat_dau"), N("x", "_test_dem"), N("y", "_test_dem")], [D("a", "x"), D("x", "y")])
        _Dem.dem = 0
        l = self.lan(sd, "A")
        l.chay()
        self.assertEqual(_Dem.dem, 2)
        l2 = self.lan(SD([N("a", "bat_dau"), N("x", "_test_dem"), N("y", "_test_dem")], [D("a", "x"), D("x", "y")]), "A")
        l2.chay()
        self.assertEqual(_Dem.dem, 2)  # lấy từ cache, không chạy lại
        self.assertTrue(l2.st["nodes"]["y"]["tu_cache"])
        l3 = self.lan(sd, "A", dung_cache=False)
        l3.chay()
        self.assertEqual(_Dem.dem, 4)
        l3.chay_lai_tu("y")
        self.assertEqual(_Dem.dem, 5)  # chỉ y chạy lại
        self.assertEqual(l3.st["nodes"]["x"]["so_lan_chay"], 1)

    def test_tat_app_giua_chung_chay_tiep(self):
        sd = SD([N("a", "bat_dau"), N("x", "_test_dem"), N("y", "_test_dem")], [D("a", "x"), D("x", "y")])
        _Dem.dem = 0
        l = self.lan(sd, "B", dung_cache=False)
        l.chay()
        st = config.doc_json(os.path.join(l.goc.thu_muc, "trang_thai.json"))
        st["nodes"]["y"].update(trang_thai="dang_chay", ra=None)  # giả như tắt app khi y đang chạy
        st["trang_thai"] = "dang_chay"
        config.ghi_json(os.path.join(l.goc.thu_muc, "trang_thai.json"), st)
        l2 = engine.mo_lan(st["id"], home=self.home, doi=self.doi, dung_cache=False)
        self.assertEqual(l2.chay(), "xong")
        self.assertEqual(_Dem.dem, 3)  # chỉ y chạy lại
        self.assertTrue(any(x["id"] == st["id"] for x in engine.danh_sach_lan(self.home)))

    def test_loi_mot_nhanh_nhanh_khac_van_chay(self):
        sd = SD([N("a", "bat_dau"), N("hong", "chon_kenh", kenh="khong_ton_tai"), N("sau_hong", "hoi_ai"),
                 N("tot", "hoi_ai", ai="gia_lap")],
                [D("a", "hong"), D("hong", "sau_hong"), D("a", "tot")])
        l = self.lan(sd)
        self.assertEqual(l.chay(), "loi")
        n = l.st["nodes"]
        self.assertEqual(n["hong"]["trang_thai"], "loi")
        self.assertEqual(n["sau_hong"]["ly_do"], "loi_truoc")
        self.assertEqual(n["tot"]["trang_thai"], "xong")

    def test_khoi_con(self):
        sd = SD([N("a", "bat_dau"), N("k", "khoi_con", so_do="khoi_kiem_tra.ailink.json")], [D("a", "k")])
        l = self.lan(sd, "Kịch bản sạch")
        self.assertEqual(l.chay(), "xong")
        self.assertEqual(l.st["nodes"]["k"]["ra"]["ket_luan"], "dat")

    def test_su_kien_cho_giao_dien(self):
        ev = []
        sd = SD([N("a", "bat_dau"), N("b", "hoi_ai", ai="gia_lap")], [D("a", "b")])
        self.lan(sd, on_event=ev.append).chay()
        tt = [(e["duong_dan"], e["trang_thai"]) for e in ev if e["loai"] == "node"]
        self.assertIn(("b", "dang_chay"), tt)
        self.assertIn(("b", "xong"), tt)
        self.assertEqual(ev[-1], {"loai": "lan", "lan": ev[-1]["lan"], "pham_vi": "", "trang_thai": "xong"})

    def test_tran_chi_phi(self):
        doi = dict(DOI_MAC_DINH)
        doi["dat"] = {"vai": [], "api": {"type": "gia_lap"}, "gia": {"vao_1m": 1e6, "ra_1m": 0}}
        sd = SD([N("a", "bat_dau"), N("x", "hoi_ai", ai="dat"), N("y", "hoi_ai", ai="dat")], [D("a", "x"), D("x", "y")])
        l = self.lan(sd, doi=DoiAI(doi=doi, home=self.home, cho_giay=[0], cham_gia_lap=0), tran_chi_phi=0.5)
        self.assertEqual(l.chay(), "dung_chi_phi")
        self.assertEqual(l.st["nodes"]["y"]["trang_thai"], "cho")


class TestDoiAI(Co):
    def test_thieu_key_roi_ve_gia_lap_va_bao(self):
        kq = self.doi.goi("xin chào", ai="claude")
        self.assertEqual(kq.ai, "gia_lap")
        self.assertTrue(any("giả lập" in c for c in kq.canh_bao))

    def test_tu_chon_theo_vai_va_du_phong(self):
        doi = {"hong": {"vai": ["kich_ban"], "api": {"type": "gia_lap", "loi_gia_lap": "chung"}},
               "tot": {"vai": ["kich_ban"], "api": {"type": "gia_lap"}}}
        d = DoiAI(doi=doi, home=self.home, cho_giay=[0], cham_gia_lap=0, thu_lai=2)
        kq = d.goi("viết", ai="hong", du_phong=["tot"])
        self.assertEqual(kq.ai, "tot")
        self.assertEqual(sum("hong: lỗi lần" in x for x in kq.nhat_ky), 3)  # 1 lần + 2 lần thử lại

    def test_het_han_muc_khong_thu_lai(self):
        doi = {"a": {"vai": [], "api": {"type": "gia_lap", "loi_gia_lap": "han_muc"}},
               "b": {"vai": [], "api": {"type": "gia_lap"}}}
        d = DoiAI(doi=doi, home=self.home, cho_giay=[0], cham_gia_lap=0, thu_lai=2)
        kq = d.goi("x", ai="a", du_phong=["b"])
        self.assertEqual(kq.ai, "b")
        self.assertEqual(sum("lỗi lần" in x for x in kq.nhat_ky), 0)

    def test_moi_ai_loi_thi_bao_loi(self):
        doi = {"a": {"vai": [], "api": {"type": "gia_lap", "loi_gia_lap": "key"}}}
        d = DoiAI(doi=doi, home=self.home, cho_giay=[0], cham_gia_lap=0)
        with self.assertRaises(providers.AIError):
            d.goi("x", ai="a")


class TestNodeMau(Co):
    def kd(self, vao, kenh=None, **cd):
        sd = SD([N("a", "bat_dau"), N("kd", "kiem_duyet", **cd)], [D("a", "kd")])
        l = self.lan(sd, vao, kenh=kenh)
        l.chay()
        return l.st["nodes"]["kd"]

    def test_kiem_duyet_dat(self):
        n = self.kd("Video kể chuyện ma ở Hội An, không có gì nhạy cảm")
        self.assertEqual(n["cong"], "dat")

    def test_kiem_duyet_chan_tu_cam_cua_kenh(self):
        n = self.kd("Hôm nay bàn chuyện chính trị nóng", kenh="vn_chuyen_la")
        self.assertEqual(n["cong"], "chan")
        self.assertEqual(n["ra"]["vi_pham"][0]["loai"], "Điều cấm của kênh")

    def test_kiem_duyet_can_xem_spam_va_sdt(self):
        n = self.kd("Sub4sub nhé, gọi 0912345678")
        self.assertEqual(n["cong"], "can_xem")
        loai = {v["loai"] for v in n["ra"]["vi_pham"]}
        self.assertEqual(loai, {"Spam / hứa hẹn quá mức", "Thông tin cá nhân"})

    def test_kiem_duyet_tieu_de_qua_dai_va_viet_hoa(self):
        sd = SD([N("t", "_test_tra", ra={"tieu_de": "BÍ ẨN " * 25, "mo_ta": "ok"}), N("kd", "kiem_duyet", dung_ai=False)],
                [D("t", "kd")])
        l = self.lan(sd)
        l.chay()
        loai = {v["loai"] for v in l.st["nodes"]["kd"]["ra"]["vi_pham"]}
        self.assertEqual(loai, {"Tiêu đề quá dài", "Tiêu đề viết hoa toàn bộ"})
        self.assertEqual(l.st["nodes"]["kd"]["cong"], "can_xem")

    def test_nguon_chua_ro_chan_dang_bai(self):
        sd = SD([N("a", "bat_dau"), N("t", "tai_video_nguon", loai_nguon="chua_ro"), N("kd", "kiem_duyet"),
                 N("d", "cho_duyet"), N("dang", "dang_bai")],
                [D("a", "t"), D("t", "kd"), D("kd", "d", "chan"), D("kd", "d", "dat"), D("kd", "d", "can_xem"),
                 D("d", "dang", "duyet")], la_con=False)
        l = self.lan(sd, "https://example.com/video")
        self.assertEqual(l.chay(), "cho_duyet")
        self.assertEqual(l.st["nodes"]["kd"]["cong"], "chan")
        self.assertTrue(any("CHƯA RÕ" in c for c in l.cho_duyet_list()[0][1]["canh_bao"]))
        l.duyet("d", "duyet")
        self.assertEqual(l.chay(), "loi")
        self.assertIn("chưa rõ", l.st["nodes"]["dang"]["loi"])

    def test_bao_cao_ai_luu_file(self):
        sd = so_do.doc_file(os.path.join(GOC, "mau", "bao_cao_sang_9h.ailink.json"))
        l = self.lan(sd)
        self.assertEqual(l.chay(), "xong")
        bc = l.st["nodes"]["bao_cao"]["ra"]
        self.assertTrue(os.path.exists(bc["file"]))
        self.assertIn("View, sub, giờ xem 24h theo kênh", bc["van_ban"])
        self.assertIn("vn_chuyen_la", bc["van_ban"])  # số liệu view đi vào báo cáo
        hop_thu = glob.glob(os.path.join(l.goc.thu_muc, "tep", "hop_thu_gia_lap.txt"))
        self.assertTrue(hop_thu)
        self.assertTrue(os.path.exists(os.path.join(self.home, "xuat", "dashboard", "kenh_moi.json")))

    def test_phan_loai_cong_rieng(self):
        sd = so_do.doc_file(os.path.join(GOC, "mau", "phan_loai_y_tuong.ailink.json"))
        l = self.lan(sd, "Top 5 bí ẩn")
        self.assertEqual(l.chay(), "xong")
        self.assertEqual(l.st["nodes"]["dai"]["trang_thai"], "bo_qua")
        self.assertEqual(l.st["nodes"]["short"]["trang_thai"], "xong")

    def test_doc_ghi_file_khong_ra_ngoai(self):
        sd = SD([N("a", "bat_dau"), N("g", "doc_ghi_file", kieu="ghi", duong_dan="../../etc/x.txt")], [D("a", "g")])
        l = self.lan(sd)
        l.chay()
        self.assertIn("ra ngoài", l.st["nodes"]["g"]["loi"])

    def test_moi_mau_chay_het_bang_gia_lap(self):
        """Tiêu chí xong giai đoạn 1: mọi sơ đồ mẫu chạy hết bằng AI giả lập (anh bấm Duyệt hết)."""
        for p in sorted(glob.glob(os.path.join(GOC, "mau", "*.ailink.json"))):
            with self.subTest(mau=os.path.basename(p)):
                l = self.lan(so_do.doc_file(p), "Bí ẩn tam giác Bermuda", kenh="vn_chuyen_la")
                tt = l.chay()
                for _ in range(5):
                    if tt != "cho_duyet":
                        break
                    for duong, _x in l.cho_duyet_list():
                        l.duyet(duong, "duyet")
                    tt = l.chay()
                self.assertEqual(tt, "xong", [(n, s["loi"]) for n, s in l.st["nodes"].items() if s["loi"]])


if __name__ == "__main__":
    unittest.main()
