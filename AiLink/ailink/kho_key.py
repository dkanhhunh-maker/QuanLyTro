"""Kho key: Windows Credential Manager qua thư viện keyring (mã hoá theo tài khoản Windows).

Chưa cài keyring thì đọc biến môi trường AILINK_KEY_<TEN_AI> (ví dụ AILINK_KEY_CLAUDE).
Key không bao giờ ghi vào file sơ đồ, nhật ký hay cấu hình.
"""
import os

DICH_VU = "AiLink"

try:
    import keyring  # type: ignore
except Exception:  # pragma: no cover - tuỳ máy
    keyring = None


def lay(ten_ai):
    v = os.environ.get("AILINK_KEY_" + ten_ai.upper(), "")
    if v:
        return v
    if keyring is not None:
        try:
            return keyring.get_password(DICH_VU, ten_ai) or ""
        except Exception:
            return ""
    return ""


def luu(ten_ai, key):
    if keyring is None:
        raise RuntimeError("Chưa cài keyring: pip install keyring")
    keyring.set_password(DICH_VU, ten_ai, key)


def xoa(ten_ai):
    if keyring is not None:
        try:
            keyring.delete_password(DICH_VU, ten_ai)
        except Exception:
            pass


def an(key):
    """Chỉ hiện 4 ký tự cuối."""
    return ("•" * 8 + key[-4:]) if key else ""
