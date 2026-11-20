"""Hồ sơ kênh (bản đặc tả mục 9). Mỗi kênh 1 file kenh/<ma>.json; AI đọc hồ sơ trước mọi việc.

Chưa có kênh nào trong G:\\claude\\AiLink\\kenh thì dùng hồ sơ mẫu (kenh_mau/, chỉ để minh hoạ).
"""
import glob, os
from . import config

TRUONG = ["ma", "ten", "nen_tang", "thi_truong", "ngon_ngu", "mui_gio", "ngach", "khan_gia", "giong_van",
          "dieu_cam", "loai_video", "nhip_dang", "giong_doc", "chrome_dang_bai", "muc_tieu"]


def _thu_muc(home=None):
    d = config.thu_muc("kenh", home)
    return d if glob.glob(os.path.join(d, "*.json")) else config.KENH_MAU_DIR


def danh_sach(home=None):
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(_thu_muc(home), "*.json")))


def doc(ma, home=None):
    if not ma:
        return None
    for d in (config.thu_muc("kenh", home), config.KENH_MAU_DIR):
        k = config.doc_json(os.path.join(d, f"{ma}.json"))
        if k is not None:
            k.setdefault("ma", ma)
            return k
    return None


def luu(k, home=None):
    config.ghi_json(os.path.join(config.thu_muc("kenh", home), f"{k['ma']}.json"), k)


def tom_tat(k):
    """Đoạn hồ sơ kênh gắn vào lời dặn hệ thống của AI."""
    if not isinstance(k, dict):
        return ""
    nhan = {"ten": "Kênh", "thi_truong": "Thị trường", "ngon_ngu": "Ngôn ngữ", "ngach": "Ngách",
            "khan_gia": "Khán giả", "giong_van": "Giọng văn", "dieu_cam": "Điều cấm", "loai_video": "Loại video"}
    dong = [f"{v}: {', '.join(k[t]) if isinstance(k.get(t), list) else k[t]}" for t, v in nhan.items() if k.get(t)]
    return "HỒ SƠ KÊNH (làm đúng giọng kênh này):\n" + "\n".join(dong) if dong else ""
