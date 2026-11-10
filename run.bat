@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   ETF 历史回看 · 本地数据更新
echo ==========================================
python etf_history.py
echo.
echo 完成。按任意键打开页面...
pause >nul
start "" "%~dp0docs\index.html"
