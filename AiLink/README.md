# AiLink - noi cac AI thanh day chuyen

App Windows (Python + tkinter, khong can cai thu vien) de xau chuoi AI: ket qua AI nay thanh dau vao AI kia.

## Chay
    python app.py
Vao tab **Cai dat AI** dan API key (Claude, GPT, Gemini; Ollama chay local khong can key). Chon day chuyen, nhap chu de, bam CHAY.

## Day chuyen (pipelines/*.json)
Moi buoc: `name`, `provider`, `prompt`, tuy chon `system`, `model`.
Bien trong prompt: `{{input}}`, `{{prev}}` (buoc truoc), `{{ten_buoc}}`.
Them AI moi tuong thich OpenAI (DeepSeek, Groq, OpenRouter...) bang cach them muc `type: openai` + `base_url` vao config.json.

## Thu khong ton tien
Chon `thu_nghiem.json` (provider mock). Test: `python -m unittest test_engine`.

## Dong goi .exe
Chay `build_exe.bat` tren Windows.
