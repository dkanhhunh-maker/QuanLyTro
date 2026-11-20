"""Lõi chạy nền + API cho giao diện (bản đặc tả mục 2).

Chỉ nghe 127.0.0.1. Lệnh đi bằng HTTP (JSON); trạng thái từng node đẩy lên giao diện theo thời gian
thực bằng Server-Sent Events (/api/su_kien) — cùng việc như WebSocket nhưng chỉ cần thư viện chuẩn.
"""
import glob, json, mimetypes, os, queue, re, threading, time, traceback, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from . import config, engine, so_do, kenh as kenh_mod, kho_key
from .doi_ai import DoiAI, DOI_MAC_DINH
from .nodes import danh_sach_node, NHOM

UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")


class Bus:
    """Phát sự kiện cho mọi cửa sổ giao diện đang mở."""

    def __init__(self):
        self.ds = []
        self.khoa = threading.Lock()

    def dang_ky(self):
        q = queue.Queue(maxsize=2000)
        with self.khoa:
            self.ds.append(q)
        return q

    def huy(self, q):
        with self.khoa:
            if q in self.ds:
                self.ds.remove(q)

    def phat(self, ev):
        with self.khoa:
            for q in list(self.ds):
                try:
                    q.put_nowait(ev)
                except queue.Full:
                    pass


class QuanLyLan:
    """Giữ các lần chạy đang mở; mỗi lần chạy 1 luồng riêng. Duyệt khi đang chạy thì xếp hàng."""

    def __init__(self, home, bus, doi_factory=None):
        self.home, self.bus = home, bus
        self.doi_factory = doi_factory or (lambda: DoiAI(home=home))
        self.lan = {}
        self.luong = {}
        self.cho_ap = {}
        self.khoa = threading.Lock()

    def _chay_nen(self, lan, ham):
        def chay():
            try:
                tt = ham()
                while True:
                    with self.khoa:
                        viec = self.cho_ap.pop(lan.st["id"], [])
                    if not viec:
                        break
                    for (dd, qd, gc) in viec:
                        try:
                            lan.duyet(dd, qd, gc)
                        except ValueError as e:
                            self.bus.phat({"loai": "thong_bao", "muc": "loi", "noi_dung": str(e)})
                    tt = lan.chay()
            except Exception as e:
                traceback.print_exc()
                self.bus.phat({"loai": "thong_bao", "muc": "loi", "noi_dung": f"Lỗi lõi: {e}"})
        t = threading.Thread(target=chay, daemon=True)
        with self.khoa:
            self.luong[lan.st["id"]] = t
        t.start()
        return t

    def dang_chay(self, id_lan):
        t = self.luong.get(id_lan)
        return t is not None and t.is_alive()

    def lay(self, id_lan):
        with self.khoa:
            if id_lan in self.lan:
                return self.lan[id_lan]
        l = engine.mo_lan(id_lan, home=self.home, doi=self.doi_factory(), on_event=self.bus.phat)
        with self.khoa:
            self.lan[id_lan] = l
        return l

    def chay_moi(self, data, dau_vao, kenh, nguon=""):
        sd = so_do.SoDo(data, nguon=nguon)
        cd = config.cai_dat(self.home)
        l = engine.LanChay(sd, dau_vao, kenh=kenh or None, home=self.home, doi=self.doi_factory(),
                           on_event=self.bus.phat, tran_chi_phi=cd.get("tran_chi_phi_lan_usd"))
        with self.khoa:
            self.lan[l.st["id"]] = l
        self._chay_nen(l, l.chay)
        return l.st["id"]

    def duyet(self, id_lan, duong_dan, qd, ghi_chu=""):
        l = self.lay(id_lan)
        if self.dang_chay(id_lan):
            with self.khoa:
                self.cho_ap.setdefault(id_lan, []).append((duong_dan, qd, ghi_chu))
            return "xep_hang"
        l.duyet(duong_dan, qd, ghi_chu)
        self._chay_nen(l, l.chay)
        return "dang_chay"

    def tiep(self, id_lan):
        l = self.lay(id_lan)
        if not self.dang_chay(id_lan):
            self._chay_nen(l, l.chay)

    def chay_lai(self, id_lan, nid):
        l = self.lay(id_lan)
        if self.dang_chay(id_lan):
            raise ValueError("Lần chạy đang chạy, chờ xong rồi chạy lại")
        self._chay_nen(l, lambda: l.chay_lai_tu(nid))

    def cho_duyet(self):
        kq = []
        for x in engine.danh_sach_lan(self.home, toi_da=200):
            if x["trang_thai"] != "cho_duyet":
                continue
            try:
                l = self.lay(x["id"])
            except Exception:
                continue
            for dd, xem in l.cho_duyet_list():
                kq.append({"lan": x["id"], "ten": x["ten"], "duong_dan": dd, "xem_truoc": xem,
                           "bat_dau": x["bat_dau"], "dau_vao": x.get("dau_vao")})
        return kq


def _ds_so_do(home):
    kq = []
    for nhom, d in (("mau", config.MAU_DIR), ("cua_anh", config.thu_muc("so_do", home))):
        for p in sorted(glob.glob(os.path.join(d, "*.ailink.json"))):
            try:
                data = config.doc_json(p)
                kq.append({"nhom": nhom, "file": os.path.basename(p), "ten": data.get("ten"), "mo_ta": data.get("mo_ta", "")})
            except Exception:
                kq.append({"nhom": nhom, "file": os.path.basename(p), "ten": os.path.basename(p), "mo_ta": "lỗi đọc file"})
    return kq


def _ten_file_an_toan(ten):
    ten = re.sub(r"[^\w\-. ]", "_", ten.strip(), flags=re.UNICODE).strip(" .") or "so_do"
    return ten if ten.endswith(".ailink.json") else ten + ".ailink.json"


def tao_handler(home, bus, ql):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _json(self, data, code=200):
            b = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

        def _file(self, p, ct=None):
            with open(p, "rb") as f:
                b = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ct or mimetypes.guess_type(p)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def _host_ok(self):
            h = (self.headers.get("Host") or "").split(":")[0]
            return h in ("127.0.0.1", "localhost")

        def do_GET(self):
            if not self._host_ok():
                return self._json({"loi": "chỉ mở trên máy anh"}, 403)
            u = urllib.parse.urlparse(self.path)
            q = dict(urllib.parse.parse_qsl(u.query))
            p = u.path
            try:
                if p in ("/", "/index.html"):
                    return self._file(os.path.join(UI_DIR, "index.html"), "text/html; charset=utf-8")
                if p.startswith("/ui/"):
                    f = os.path.realpath(os.path.join(UI_DIR, p[4:]))
                    if f.startswith(os.path.realpath(UI_DIR)) and os.path.isfile(f):
                        return self._file(f)
                    return self._json({"loi": "không có"}, 404)
                if p == "/api/khoi_dong":
                    cd = config.cai_dat(home)
                    return self._json({"node": danh_sach_node(), "nhom": NHOM, "so_do": _ds_so_do(home),
                                       "kenh": [kenh_mod.doc(k, home) for k in kenh_mod.danh_sach(home)],
                                       "doi_ai": _doi_an(home), "cai_dat": cd, "home": home})
                if p == "/api/so_do":
                    d = config.MAU_DIR if q.get("nhom") == "mau" else config.thu_muc("so_do", home)
                    f = os.path.join(d, os.path.basename(q["file"]))
                    return self._json(config.doc_json(f))
                if p == "/api/so_do_ds":
                    return self._json(_ds_so_do(home))
                if p == "/api/lan":
                    if q.get("id"):
                        l = ql.lay(q["id"])
                        return self._json({**l.st, "dang_chay": ql.dang_chay(q["id"]) and l.st.get("trang_thai") == "dang_chay"})
                    return self._json(engine.danh_sach_lan(home, int(q.get("toi_da", 50))))
                if p == "/api/cho_duyet":
                    return self._json(ql.cho_duyet())
                if p == "/api/kenh":
                    return self._json([kenh_mod.doc(k, home) for k in kenh_mod.danh_sach(home)])
                if p == "/api/tep":
                    f = os.path.realpath(q.get("p", ""))
                    goc = os.path.realpath(home)
                    if os.path.commonpath([goc, f]) != goc or not os.path.isfile(f):
                        return self._json({"loi": "không mở được tệp này"}, 403)
                    return self._file(f)
                if p == "/api/su_kien":
                    return self._sse()
                return self._json({"loi": "không có"}, 404)
            except Exception as e:
                traceback.print_exc()
                return self._json({"loi": str(e)}, 500)

        def do_POST(self):
            if not self._host_ok() or self.headers.get("X-AiLink") != "1":
                return self._json({"loi": "chỉ mở trên máy anh"}, 403)
            p = urllib.parse.urlparse(self.path).path
            try:
                b = self._body()
                if p == "/api/kiem":
                    try:
                        sd = so_do.SoDo(b["data"])
                        return self._json({"ok": True, "so_node": len(sd.nodes)})
                    except so_do.LoiSoDo as e:
                        return self._json({"ok": False, "loi": e.loi})
                if p == "/api/luu_so_do":
                    try:
                        so_do.SoDo(b["data"])
                    except so_do.LoiSoDo as e:
                        return self._json({"ok": False, "loi": e.loi})
                    ten = _ten_file_an_toan(b.get("file") or b["data"].get("ten", "so_do"))
                    config.ghi_json(os.path.join(config.thu_muc("so_do", home), ten), b["data"])
                    return self._json({"ok": True, "file": ten})
                if p == "/api/chay":
                    try:
                        id_lan = ql.chay_moi(b["data"], b.get("dau_vao", ""), b.get("kenh"), b.get("nguon", ""))
                    except so_do.LoiSoDo as e:
                        return self._json({"ok": False, "loi": e.loi})
                    return self._json({"ok": True, "id": id_lan})
                if p == "/api/duyet":
                    return self._json({"ok": True, "tt": ql.duyet(b["lan"], b["duong_dan"], b["quyet_dinh"], b.get("ghi_chu", ""))})
                if p == "/api/tiep":
                    ql.tiep(b["lan"])
                    return self._json({"ok": True})
                if p == "/api/chay_lai":
                    ql.chay_lai(b["lan"], b["node"])
                    return self._json({"ok": True})
                if p == "/api/kenh":
                    k = b["kenh"]
                    if not re.fullmatch(r"[a-z0-9_]{2,40}", k.get("ma", "")):
                        return self._json({"ok": False, "loi": ["Mã kênh chỉ gồm chữ thường không dấu, số, gạch dưới (2–40 ký tự)"]})
                    kenh_mod.luu(k, home)
                    return self._json({"ok": True})
                if p == "/api/cai_dat":
                    f = os.path.join(home, "cai_dat.json")
                    cd = config.doc_json(f, {}) or {}
                    cd.update({k: v for k, v in b.items() if k in config.CAI_DAT_MAC_DINH or k in ("chu_de",)})
                    config.ghi_json(f, cd)
                    return self._json({"ok": True})
                return self._json({"loi": "không có"}, 404)
            except ValueError as e:
                return self._json({"ok": False, "loi": [str(e)]}, 400)
            except Exception as e:
                traceback.print_exc()
                return self._json({"ok": False, "loi": [str(e)]}, 500)

        def _sse(self):
            q = bus.dang_ky()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                self.wfile.write(b": chao\n\n")
                self.wfile.flush()
                while True:
                    try:
                        ev = q.get(timeout=15)
                        self.wfile.write(("data: " + json.dumps(ev, ensure_ascii=False, default=str) + "\n\n").encode("utf-8"))
                    except queue.Empty:
                        self.wfile.write(b": giu\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                bus.huy(q)
                self.close_connection = True

    return H


def _doi_an(home):
    """Đội AI cho giao diện: không bao giờ gửi key, chỉ 4 ký tự cuối."""
    doi = config.doc_json(os.path.join(home, "doi_ai.json"), DOI_MAC_DINH)
    kq = {}
    for t, a in doi.items():
        k = kho_key.lay(t) if a.get("api") and a["api"].get("type") not in ("gia_lap", "mock") else ""
        kq[t] = {**{x: y for x, y in a.items() if x != "api"}, "api_kieu": (a.get("api") or {}).get("type"),
                 "model": (a.get("api") or {}).get("model"), "co_key": bool(k), "key_an": kho_key.an(k)}
    return kq


def tao_server(home=None, cong=0, doi_factory=None):
    home = home or config.HOME
    os.makedirs(home, exist_ok=True)
    bus = Bus()
    ql = QuanLyLan(home, bus, doi_factory)
    srv = ThreadingHTTPServer(("127.0.0.1", cong), tao_handler(home, bus, ql))
    srv.daemon_threads = True
    srv.ql, srv.bus, srv.home = ql, bus, home
    return srv


def chay_server(home=None, cong=8765):
    srv = tao_server(home, cong)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"
