@echo off
chcp 65001 >nul
title HiredChina爬虫

echo ========================================
echo   HiredChina爬虫
echo ========================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate" (
    call .venv\Scripts\activate
)

echo.
echo ========================================
echo   开始爬取 HiredChina...
echo ========================================
python main.py hiredchina

echo.
echo ========================================
echo   HiredChina完成！
echo ========================================
pause