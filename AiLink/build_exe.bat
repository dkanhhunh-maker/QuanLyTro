@echo off
REM Đóng gói AiLink thành AiLink.exe (cần Python 3.10+ trên Windows)
cd /d %~dp0
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --noconsole --onefile --name AiLink ^
  --add-data "ailink\ui;ailink\ui" --add-data "mau;mau" --add-data "kenh_mau;kenh_mau" app.py
echo.
echo Xong. File: dist\AiLink.exe  — chép vào G:\claude\AiLink rồi bấm đúp để mở.
pause
