@echo off
chcp 65001 > nul
echo ========================================================
echo  KHOI DONG WEBSITE HOC TU VUNG TIENG TRUNG KHUNG DEN
echo  (Ho tro truy cap: May cuc bo, Mang LAN va Internet)
echo ========================================================
echo.
cd /d "%~dp0"
set PYTHON_EXE=C:\Users\user\.gemini\antigravity\scratch\chinese_vocab_env\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Khong tim thay Python tai: %PYTHON_EXE%
    pause
    exit /b 1
)

echo [1/2] Dang khoi dong may chu 0.0.0.0:8000 va Cloudflare Tunnel...
timeout /t 2 > nul
start http://127.0.0.1:8000
"%PYTHON_EXE%" server_launcher.py
pause
