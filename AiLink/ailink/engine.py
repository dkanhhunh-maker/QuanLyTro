"""Chay day chuyen: moi buoc goi 1 AI, ket qua truyen cho buoc sau.

Bien dung trong prompt:  {{input}}  {{prev}}  {{ten_buoc}}
"""
import json, os, re, time
from . import config, providers


def render(tpl, ctx):
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(ctx.get(m.group(1), "")), tpl)


def load_pipeline(path):
    with open(path, encoding="utf-8") as f:
        p = json.load(f)
    names = set()
    for s in p.get("steps", []):
        for k in ("name", "provider", "prompt"):
            if k not in s:
                raise providers.AIError(f"Buoc thieu truong '{k}': {s}")
        if s["name"] in names:
            raise providers.AIError(f"Trung ten buoc: {s['name']}")
        names.add(s["name"])
    return p


def run(pipeline, user_input, cfg=None, on_step=None, save=True):
    """on_step(index, step, status, text) status: start|done|error. Tra ve dict ket qua."""
    cfg = cfg or config.load()
    ctx = {"input": user_input, "prev": user_input}
    results = []
    for i, s in enumerate(pipeline["steps"]):
        if on_step:
            on_step(i, s, "start", "")
        try:
            pcfg = cfg["providers"].get(s["provider"])
            if pcfg is None:
                raise providers.AIError(f"Khong co provider '{s['provider']}' trong cau hinh")
            prov = providers.build(s["provider"], pcfg)
            out = prov.complete(render(s["prompt"], ctx), render(s.get("system", ""), ctx),
                                s.get("model"))
        except Exception as e:
            if on_step:
                on_step(i, s, "error", str(e))
            results.append({"step": s["name"], "error": str(e)})
            _save(pipeline, user_input, results, save)
            return {"ok": False, "results": results}
        ctx[s["name"]] = out
        ctx["prev"] = out
        results.append({"step": s["name"], "provider": s["provider"], "output": out})
        if on_step:
            on_step(i, s, "done", out)
    _save(pipeline, user_input, results, save)
    return {"ok": True, "results": results}


def _save(pipeline, user_input, results, save):
    if not save:
        return
    os.makedirs(config.RUNS_DIR, exist_ok=True)
    fn = os.path.join(config.RUNS_DIR, time.strftime("%Y%m%d_%H%M%S") + ".json")
    with open(fn, "w", encoding="utf-8") as f:
        json.dump({"pipeline": pipeline.get("name"), "input": user_input, "results": results},
                  f, ensure_ascii=False, indent=2)
