import json, os, tempfile, unittest
from ailink import engine, config, providers


class T(unittest.TestCase):
    def test_pipeline_mock(self):
        pl = engine.load_pipeline(os.path.join(config.PIPELINE_DIR, "thu_nghiem.json"))
        cfg = {"providers": {"mock": {"type": "mock"}}}
        steps = []
        r = engine.run(pl, "xin chao", cfg, on_step=lambda i, s, st, t: steps.append(st), save=False)
        self.assertTrue(r["ok"])
        self.assertIn("xin chao", r["results"][0]["output"])
        self.assertIn("Buoc A nhan", r["results"][1]["output"])  # {{prev}} da thay
        self.assertEqual(steps, ["start", "done", "start", "done"])

    def test_missing_key(self):
        pl = {"steps": [{"name": "a", "provider": "claude", "prompt": "x"}]}
        cfg = {"providers": {"claude": {"type": "anthropic", "api_key": ""}}}
        r = engine.run(pl, "x", cfg, save=False)
        self.assertFalse(r["ok"])
        self.assertIn("api_key", r["results"][0]["error"])

    def test_render(self):
        self.assertEqual(engine.render("a {{x}} b {{ y }}", {"x": 1, "y": 2}), "a 1 b 2")


if __name__ == "__main__":
    unittest.main()
