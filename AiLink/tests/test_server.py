"""Test API giao diện (giai đoạn 2): chạy, nhận sự kiện, duyệt, lưu sơ đồ, chặn truy cập lạ."""
import json, os, shutil, sys, tempfile, threading, time, unittest, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ailink import config  # noqa: E402
from ailink.server import tao_server  # noqa: E402
from ailink.doi_ai import DoiAI  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp()
        cls.srv = tao_server(cls.home, 0, doi_factory=lambda: DoiAI(home=cls.home, cho_giay=[0], cham_gia_lap=0, lay_key=lambda t: ""))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        shutil.rmtree(cls.home, ignore_errors=True)

    def get(self, p):
        with urllib.request.urlopen(self.url + p, timeout=10) as r:
            return json.loads(r.read())

    def post(self, p, body, header=True):
        req = urllib.request.Request(self.url + p, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **({"X-AiLink": "1"} if header else {})})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def cho(self, id_lan, tt, giay=15):
        h = time.time() + giay
        while time.time() < h:
            st = self.get(f"/api/lan?id={id_lan}")
            if not st["dang_chay"] and st["trang_thai"] == tt:
                return st
            time.sleep(0.05)
        self.fail(f"Không tới trạng thái {tt}: {st['trang_thai']}")

    def test_khoi_dong(self):
        kd = self.get("/api/khoi_dong")
        self.assertEqual(len(kd["node"]), 40)
        self.assertTrue(any(x["file"] == "short_youtube.ailink.json" for x in kd["so_do"]))
        self.assertTrue(all("api" not in a for a in kd["doi_ai"].values()))  # không lộ cấu hình key
        with urllib.request.urlopen(self.url + "/", timeout=5) as r:
            self.assertIn(b"AiLink", r.read())

    def test_chay_duyet_xong(self):
        data = self.get("/api/so_do?nhom=mau&file=short_youtube.ailink.json")
        r = self.post("/api/chay", {"data": data, "dau_vao": "Bermuda", "kenh": "vn_chuyen_la"})
        self.assertTrue(r["ok"])
        self.cho(r["id"], "cho_duyet")
        ds = [x for x in self.get("/api/cho_duyet") if x["lan"] == r["id"]]
        self.assertEqual(len(ds), 1)
        self.post("/api/duyet", {"lan": r["id"], "duong_dan": ds[0]["duong_dan"], "quyet_dinh": "duyet"})
        st = self.cho(r["id"], "xong")
        self.assertEqual(st["nodes"]["dang"]["ra"]["trang_thai"], "gia_lap_chua_dang")

    def test_so_do_loi_tra_ve_danh_sach(self):
        r = self.post("/api/kiem", {"data": {"nodes": [{"id": "a", "loai": "x"}], "day": []}})
        self.assertFalse(r["ok"])
        self.assertTrue(r["loi"])

    def test_luu_so_do(self):
        data = self.get("/api/so_do?nhom=mau&file=khoi_kiem_tra.ailink.json")
        data["ten"] = "Khối của anh"
        r = self.post("/api/luu_so_do", {"data": data})
        self.assertTrue(r["ok"])
        self.assertTrue(os.path.exists(os.path.join(self.home, "so_do", r["file"])))

    def test_chan_post_khong_co_header(self):
        with self.assertRaises(urllib.error.HTTPError) as c:
            self.post("/api/chay", {"data": {}}, header=False)
        self.assertEqual(c.exception.code, 403)

    def test_tep_ngoai_thu_muc_bi_chan(self):
        with self.assertRaises(urllib.error.HTTPError) as c:
            self.get("/api/tep?p=/etc/passwd")
        self.assertEqual(c.exception.code, 403)

    def test_su_kien_sse(self):
        nhan = []

        def nghe():
            with urllib.request.urlopen(self.url + "/api/su_kien", timeout=10) as r:
                for dong in r:
                    if dong.startswith(b"data: "):
                        nhan.append(json.loads(dong[6:]))
                        if nhan[-1].get("loai") == "lan" and nhan[-1].get("trang_thai") == "xong":
                            return
        t = threading.Thread(target=nghe, daemon=True)
        t.start()
        time.sleep(0.3)
        data = {"phien_ban": 1, "nodes": [{"id": "a", "loai": "bat_dau"}, {"id": "b", "loai": "tom_tat"}], "day": [{"tu": "a", "den": "b"}]}
        self.post("/api/chay", {"data": data, "dau_vao": "x"})
        t.join(10)
        self.assertTrue(any(e.get("duong_dan") == "b" and e.get("trang_thai") == "xong" for e in nhan))


if __name__ == "__main__":
    unittest.main()
