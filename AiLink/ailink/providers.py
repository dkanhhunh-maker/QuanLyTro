"""Tay API của từng AI. Chỉ dùng thư viện chuẩn (urllib).

Mỗi provider trả về KetQuaAI(van_ban, token_vao, token_ra). Lỗi được phân loại để
engine biết nên thử lại, chuyển tay hay báo anh ngay (bản đặc tả mục 8).
"""
import json, urllib.request, urllib.error


class AIError(Exception):
    """Lỗi chung, thử lại được."""


class LoiHanMuc(AIError):
    """429 / hết quota: bỏ qua thử lại, chuyển tay hoặc AI dự phòng."""


class LoiKey(AIError):
    """Sai key, bị đăng xuất: không thử lại, báo anh."""


class ChuaHoTro(AIError):
    """Tay này chưa làm (ví dụ tay Chrome trước giai đoạn 4)."""


class KetQuaAI:
    def __init__(self, van_ban, token_vao=0, token_ra=0, so_luong=0):
        self.van_ban = van_ban
        self.token_vao = token_vao
        self.token_ra = token_ra
        self.so_luong = so_luong  # số ảnh / giây video ... cho node không phải chữ


def uoc_token(s):
    return max(1, len(s or "") // 4)


def _post(url, headers, body, timeout=180):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
        if e.code == 429:
            raise LoiHanMuc(msg)
        if e.code in (401, 403):
            raise LoiKey(msg)
        raise AIError(msg)
    except urllib.error.URLError as e:
        raise AIError(f"Lỗi mạng: {e.reason}")


class Provider:
    def __init__(self, ten, cfg, key=""):
        self.ten = ten
        self.cfg = cfg
        self.key = key

    def complete(self, prompt, system="", model=None, gia_lap=None):
        raise NotImplementedError


class Anthropic(Provider):
    def complete(self, prompt, system="", model=None, gia_lap=None):
        body = {"model": model or self.cfg.get("model", "claude-sonnet-5-5"), "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        r = _post("https://api.anthropic.com/v1/messages",
                  {"x-api-key": self.key, "anthropic-version": "2023-06-01"}, body)
        u = r.get("usage", {})
        return KetQuaAI("".join(b.get("text", "") for b in r.get("content", [])),
                        u.get("input_tokens", 0), u.get("output_tokens", 0))


class OpenAI(Provider):
    """Dùng cho mọi dịch vụ kiểu OpenAI: ChatGPT, Ollama, DeepSeek, Groq, OpenRouter..."""
    def complete(self, prompt, system="", model=None, gia_lap=None):
        base = self.cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        r = _post(f"{base}/chat/completions", {"Authorization": f"Bearer {self.key}"},
                  {"model": model or self.cfg.get("model", "gpt-4o"), "messages": msgs})
        u = r.get("usage", {})
        return KetQuaAI(r["choices"][0]["message"]["content"],
                        u.get("prompt_tokens", 0), u.get("completion_tokens", 0))


class Gemini(Provider):
    def complete(self, prompt, system="", model=None, gia_lap=None):
        m = model or self.cfg.get("model", "gemini-2.0-flash")
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                  {"x-goog-api-key": self.key}, body)
        try:
            txt = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError):
            raise AIError(f"Gemini không trả kết quả: {json.dumps(r)[:300]}")
        u = r.get("usageMetadata", {})
        return KetQuaAI(txt, u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0))


class GiaLap(Provider):
    """AI giả lập: chạy thử mọi vai, không tốn tiền.

    Node có thể đưa hàm gia_lap(prompt) để trả kết quả giống thật (JSON chấm điểm,
    báo cáo...). Không có thì trả lại đầu lệnh để thấy biến đã thay đúng.
    """
    def complete(self, prompt, system="", model=None, gia_lap=None):
        if self.cfg.get("loi_gia_lap"):  # dùng trong test xử lý lỗi
            loai = self.cfg["loi_gia_lap"]
            raise {"han_muc": LoiHanMuc, "key": LoiKey}.get(loai, AIError)(f"Lỗi giả lập: {loai}")
        if gia_lap is not None:
            out = gia_lap(prompt)
            txt = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        else:
            txt = f"[{self.ten}] " + prompt[:300]
        return KetQuaAI(txt, uoc_token(system + prompt), uoc_token(txt))


TYPES = {"anthropic": Anthropic, "openai": OpenAI, "gemini": Gemini, "mock": GiaLap, "gia_lap": GiaLap}
CAN_KEY = {"anthropic", "openai", "gemini"}


def build(ten, cfg, key=""):
    t = cfg.get("type")
    if t not in TYPES:
        raise AIError(f"AI '{ten}': kiểu '{t}' chưa hỗ trợ")
    return TYPES[t](ten, cfg, key)
