"""Cac nha cung cap AI. Chi dung thu vien chuan (urllib) nen khong can cai them."""
import json, os, urllib.request, urllib.error


class AIError(Exception):
    pass


def _post(url, headers, body, timeout=180):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise AIError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
    except urllib.error.URLError as e:
        raise AIError(f"Loi mang: {e.reason}")


class Provider:
    def __init__(self, name, cfg):
        self.name = name
        self.cfg = cfg

    @property
    def key(self):
        return self.cfg.get("api_key", "")

    def complete(self, prompt, system="", model=None):
        raise NotImplementedError


class Anthropic(Provider):
    def complete(self, prompt, system="", model=None):
        body = {"model": model or self.cfg["model"], "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        r = _post("https://api.anthropic.com/v1/messages",
                  {"x-api-key": self.key, "anthropic-version": "2023-06-01"}, body)
        return "".join(b.get("text", "") for b in r.get("content", []))


class OpenAI(Provider):
    """Cung dung cho moi dich vu tuong thich OpenAI: Ollama, DeepSeek, Groq, OpenRouter..."""
    def complete(self, prompt, system="", model=None):
        base = self.cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        r = _post(f"{base}/chat/completions", {"Authorization": f"Bearer {self.key}"},
                  {"model": model or self.cfg["model"], "messages": msgs})
        return r["choices"][0]["message"]["content"]


class Gemini(Provider):
    def complete(self, prompt, system="", model=None):
        m = model or self.cfg["model"]
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                  {"x-goog-api-key": self.key}, body)
        try:
            return "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError):
            raise AIError(f"Gemini khong tra ket qua: {json.dumps(r)[:300]}")


class Mock(Provider):
    """Dung de thu day chuyen khong ton tien."""
    def complete(self, prompt, system="", model=None):
        return f"[{self.name}] " + prompt[:200]


TYPES = {"anthropic": Anthropic, "openai": OpenAI, "gemini": Gemini, "mock": Mock}


def build(name, cfg):
    t = cfg.get("type")
    if t not in TYPES:
        raise AIError(f"Provider '{name}': type '{t}' khong ho tro")
    if t != "mock" and not cfg.get("api_key"):
        raise AIError(f"Provider '{name}' chua co api_key (vao Cai dat)")
    return TYPES[t](name, cfg)
