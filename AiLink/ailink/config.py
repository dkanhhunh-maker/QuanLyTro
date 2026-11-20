import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE, "config.json")
PIPELINE_DIR = os.path.join(BASE, "pipelines")
RUNS_DIR = os.path.join(BASE, "runs")

DEFAULT = {
    "providers": {
        "claude": {"type": "anthropic", "api_key": "", "model": "claude-sonnet-5-5"},
        "gpt": {"type": "openai", "api_key": "", "model": "gpt-4o"},
        "gemini": {"type": "gemini", "api_key": "", "model": "gemini-2.0-flash"},
        "mock": {"type": "mock", "model": "mock"},
        "ollama": {"type": "openai", "api_key": "ollama", "model": "llama3",
                   "base_url": "http://localhost:11434/v1"},
    }
}


def load():
    if not os.path.exists(CONFIG_PATH):
        save(DEFAULT)
        return json.loads(json.dumps(DEFAULT))
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
