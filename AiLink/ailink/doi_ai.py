"""Đội AI: mỗi AI có vai, tay API, tay Chrome, chế độ gọi (bản đặc tả mục 3).

goi() chọn AI theo vai, thử lại, chuyển tay, chuyển AI dự phòng, và rơi về AI giả lập
khi chưa có key (mục 8). Key không bao giờ nằm trong file này: lấy từ kho_key.
"""
import os, threading, time
from . import config, providers, kho_key

DOI_MAC_DINH = {
    "claude": {"ten_hien": "Claude", "vai": ["dieu_phoi", "kich_ban", "kiem_tra", "kiem_duyet", "bao_cao"],
               "api": {"type": "anthropic", "model": "claude-sonnet-5-5"},
               "chrome": {"ho_so": "Chrome A", "url": "https://claude.ai"}, "che_do": "tu_dong", "gioi_han": 2},
    "chatgpt": {"ten_hien": "ChatGPT", "vai": ["nghien_cuu", "y_tuong", "kich_ban", "dich"],
                "api": {"type": "openai", "model": "gpt-4o"},
                "chrome": {"ho_so": "Chrome B", "url": "https://chatgpt.com"}, "che_do": "tu_dong", "gioi_han": 2},
    "gemini": {"ten_hien": "Gemini", "vai": ["video", "anh", "doc_video", "nghien_cuu", "dich"],
               "api": {"type": "gemini", "model": "gemini-2.0-flash"},
               "chrome": {"ho_so": "Chrome C", "url": "https://gemini.google.com"}, "che_do": "tu_dong", "gioi_han": 2},
    "muse": {"ten_hien": "Meta Muse", "vai": ["anh", "video"],
             "api": None, "chrome": {"ho_so": "Chrome D", "url": "https://www.meta.ai"},
             "che_do": "chi_chrome", "gioi_han": 1},
    "am_thanh": {"ten_hien": "App âm thanh", "vai": ["giong", "nhac"],
                 "api": None, "chrome": None, "che_do": "tu_dong", "gioi_han": 1},
    "gia_lap": {"ten_hien": "AI giả lập", "vai": ["*"], "api": {"type": "gia_lap"},
                "chrome": None, "che_do": "chi_api", "gioi_han": 8},
}


class KetQuaGoi:
    def __init__(self, kq, ai, tay, chi_phi, canh_bao, nhat_ky):
        self.van_ban = kq.van_ban
        self.token_vao = kq.token_vao
        self.token_ra = kq.token_ra
        self.ai, self.tay, self.chi_phi = ai, tay, chi_phi
        self.canh_bao = canh_bao
        self.nhat_ky = nhat_ky
        self.la_gia_lap = ai == "gia_lap"


class DoiAI:
    def __init__(self, doi=None, home=None, cho_phep_gia_lap=True, thu_lai=None, cho_giay=None,
                 lay_key=None):
        home = home or config.HOME
        cd = config.cai_dat(home)
        self.doi = doi if doi is not None else config.doc_json(os.path.join(home, "doi_ai.json"), DOI_MAC_DINH)
        self.cho_phep_gia_lap = cho_phep_gia_lap
        self.thu_lai = cd["thu_lai"] if thu_lai is None else thu_lai
        self.cho_giay = cd["cho_thu_lai_giay"] if cho_giay is None else cho_giay
        self.lay_key = lay_key or kho_key.lay
        self._khoa = {}
        self._khoa_lock = threading.Lock()

    def _sem(self, ten, so):
        with self._khoa_lock:
            if ten not in self._khoa:
                self._khoa[ten] = threading.Semaphore(max(1, so))
            return self._khoa[ten]

    def chon_theo_vai(self, vai):
        """'Tự chọn theo vai': AI đầu tiên có vai này và có tay dùng được."""
        co_vai = [t for t, a in self.doi.items() if t != "gia_lap" and vai in a.get("vai", [])]
        for t in co_vai:
            a = self.doi[t]
            if a.get("api") and (a["api"].get("type") in ("gia_lap", "mock") or self.lay_key(t)):
                return t
        return co_vai[0] if co_vai else "gia_lap"

    def goi(self, prompt, system="", ai="tu_chon", vai="kich_ban", che_do=None, du_phong=(),
            model=None, gia_lap=None, log=None):
        log = log or (lambda s: None)
        nhat_ky, canh_bao, loi_that = [], [], []
        dau = self.chon_theo_vai(vai) if ai in (None, "", "tu_chon") else ai
        ung_vien = [dau] + [x for x in du_phong if x != dau]
        for ten in ung_vien:
            a = self.doi.get(ten)
            if a is None:
                canh_bao.append(f"Không có AI '{ten}' trong Đội AI")
                continue
            cd = che_do or a.get("che_do", "tu_dong")
            tay_list = {"tu_dong": ["api", "chrome"], "chi_api": ["api"], "chi_chrome": ["chrome"]}.get(cd, ["api"])
            for tay in tay_list:
                if tay == "chrome":
                    if not a.get("chrome"):
                        continue
                    nhat_ky.append(f"{ten}/chrome: tay Chrome làm ở giai đoạn 4, bỏ qua")
                    continue
                if not a.get("api"):
                    continue
                t = a["api"].get("type")
                key = "" if t in ("gia_lap", "mock") else self.lay_key(ten)
                if t in providers.CAN_KEY and not key:
                    nhat_ky.append(f"{ten}/api: chưa có key")
                    continue
                prov = providers.build(ten, a["api"], key)
                kq = self._thu(prov, ten, prompt, system, model, gia_lap, nhat_ky, loi_that, canh_bao, log)
                if kq is not None:
                    return KetQuaGoi(kq, ten, tay, self.chi_phi(ten, kq), canh_bao, nhat_ky)
        if self.cho_phep_gia_lap and not loi_that:
            canh_bao.append(f"{dau}: chưa có key/tay dùng được → chạy AI giả lập")
            kq = providers.build("gia_lap", {"type": "gia_lap"}).complete(prompt, system, model, gia_lap)
            return KetQuaGoi(kq, "gia_lap", "api", 0.0, canh_bao, nhat_ky)
        raise providers.AIError("Mọi AI đều lỗi: " + " | ".join(loi_that or nhat_ky or ["không có AI nào dùng được"]))

    def _thu(self, prov, ten, prompt, system, model, gia_lap, nhat_ky, loi_that, canh_bao, log):
        sem = self._sem(ten, self.doi[ten].get("gioi_han", 2))
        for lan in range(self.thu_lai + 1):
            try:
                with sem:
                    return prov.complete(prompt, system, model, gia_lap)
            except providers.LoiHanMuc as e:
                nhat_ky.append(f"{ten}: hết hạn mức → chuyển tay/AI khác ({e})")
                loi_that.append(f"{ten}: {e}")
                return None
            except providers.LoiKey as e:
                nhat_ky.append(f"{ten}: sai key/đăng xuất, không thử lại ({e})")
                canh_bao.append(f"{ten}: sai key hoặc bị đăng xuất, anh kiểm tra lại")
                loi_that.append(f"{ten}: {e}")
                return None
            except providers.AIError as e:
                nhat_ky.append(f"{ten}: lỗi lần {lan + 1}: {e}")
                if lan < self.thu_lai:
                    cho = self.cho_giay[min(lan, len(self.cho_giay) - 1)] if self.cho_giay else 0
                    log(f"{ten} lỗi, chờ {cho}s rồi thử lại")
                    time.sleep(cho)
                else:
                    loi_that.append(f"{ten}: {e}")
        return None

    def chi_phi(self, ten, kq):
        gia = (self.doi.get(ten) or {}).get("gia") or {}
        return round(kq.token_vao / 1e6 * gia.get("vao_1m", 0) + kq.token_ra / 1e6 * gia.get("ra_1m", 0)
                     + kq.so_luong * gia.get("moi_don_vi", 0), 6)
