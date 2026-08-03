@echo off
chcp 65001 >nul
title Himalayas爬虫

echo ========================================
echo   Himalayas爬虫
echo ========================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate" (
    call .venv\Scripts\activate
)

echo.
echo ========================================
echo   开始爬取 Himalayas...
echo ========================================
python -m app.crawler.himalayas

echo.
echo ========================================
echo   Himalayas完成！
echo ========================================
pause