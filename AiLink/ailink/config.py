"""Đường dẫn và cấu hình chung của AiLink.

Dữ liệu người dùng nằm ở G:\\claude\\AiLink trên máy anh Hoà (hoặc biến môi trường
AILINK_HOME). Sơ đồ mẫu (mau/) và hồ sơ kênh mẫu (kenh_mau/) đi kèm app.
"""
import json, os, sys, threading

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if getattr(sys, "frozen", False):  # chạy từ AiLink.exe (PyInstaller)
    APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))

MAU_DIR = os.path.join(APP_DIR, "mau")
KENH_MAU_DIR = os.path.join(APP_DIR, "kenh_mau")


def _home():
    if os.environ.get("AILINK_HOME"):
        return os.environ["AILINK_HOME"]
    if os.name == "nt" and os.path.isdir("G:\\"):
        return "G:\\claude\\AiLink"
    return os.path.join(os.path.expanduser("~"), "AiLink")


HOME = _home()
THU_MUC = {
    "so_do": "so_do", "kenh": "kenh", "lan_chay": "lan_chay", "cache": "cache",
    "xuat": "xuat", "kich_ban_chrome": "kich_ban_chrome",
}


def thu_muc(ten, home=None):
    p = os.path.join(home or HOME, THU_MUC[ten])
    os.makedirs(p, exist_ok=True)
    return p


# Cài đặt mặc định. Trần chi phí: anh Hoà duyệt mặc định 5 USD/ngày, 100 USD/tháng (sửa được).
CAI_DAT_MAC_DINH = {
    "song_song": 4,
    "thu_lai": 2,
    "cho_thu_lai_giay": [30, 120],
    "tran_chi_phi_ngay_usd": 5.0,
    "tran_chi_phi_thang_usd": 100.0,
    "thi_truong_dau": ["VN", "US", "JP"],
    "kenh_duyet_chinh": "telegram",
    "kenh_bao_tin": ["zalo"],
    "giu_file_trung_gian_ngay": 30,
}


def doc_json(path, mac_dinh=None):
    if not os.path.exists(path):
        return json.loads(json.dumps(mac_dinh)) if mac_dinh is not None else None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ghi_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def cai_dat(home=None):
    cd = dict(CAI_DAT_MAC_DINH)
    cd.update(doc_json(os.path.join(home or HOME, "cai_dat.json"), {}) or {})
    return cd
