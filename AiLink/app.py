"""AiLink — mở giao diện. Chạy: python app.py   (hoặc AiLink.exe)

Lõi chạy nền trong cùng tiến trình; giao diện mở trong cửa sổ riêng (pywebview).
Chưa cài pywebview thì mở bằng trình duyệt mặc định ở http://127.0.0.1:8765.
"""
import sys, time, webbrowser
from ailink import config
from ailink.server import chay_server


def main():
    cong = 8765
    if "--cong" in sys.argv:
        cong = int(sys.argv[sys.argv.index("--cong") + 1])
    try:
        srv, url = chay_server(cong=cong)
    except OSError:
        srv, url = chay_server(cong=0)  # cổng 8765 bận thì lấy cổng khác
    print(f"AiLink đang chạy: {url}  (dữ liệu: {config.HOME})")
    try:
        import webview  # pywebview
    except ImportError:
        webview = None
    if webview is not None and "--trinh-duyet" not in sys.argv:
        webview.create_window("AiLink — Điều phối AI", url, width=1440, height=900, min_size=(900, 600))
        webview.start()
        return
    webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
