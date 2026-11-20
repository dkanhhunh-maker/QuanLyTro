@echo off
REM Dong goi AiLink thanh AiLink.exe (can Python 3.10+ tren Windows)
pip install pyinstaller
pyinstaller --noconsole --onefile --name AiLink app.py
echo Xong. File: dist\AiLink.exe  (chep kem thu muc pipelines canh file exe)
pause
