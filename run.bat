@echo off
chcp 65001 >nul
title Himalayas爬虫

cd /d "%~dp0"

echo ========================================
echo   Himalayas爬虫
echo ========================================
echo.

python -m app.crawler.himalayas

echo.
echo ========================================
echo   爬取完成！
echo ========================================
pause