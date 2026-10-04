@echo off
chcp 65001 > nul
echo ========================================================
echo  DAY MA NGUON LEN GITHUB REPOSITORY: going-chinese
echo  URL: https://github.com/thanhhuyen-design/going-chinese
echo ========================================================
echo.
cd /d "%~dp0"
set PATH=C:\Program Files\Git\cmd;C:\Program Files\Git\bin;%PATH%

echo [1/2] Dang kiem tra trang thai Git...
git status --short

echo.
echo [2/2] Dang day ma nguon len nhanh main...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo  THANH CONG! Ma nguon da duoc day len GitHub thanh cong.
    echo  Kiem tra tai: https://github.com/thanhhuyen-design/going-chinese
    echo ========================================================
) else (
    echo.
    echo [THONG BAO] Neu trinh duyet mo ra cua so xac thuc GitHub,
    echo ban vui long bam "Authorize" de hoan tat.
)

pause
