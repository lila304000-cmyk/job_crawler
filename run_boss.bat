@echo off
chcp 65001 >nul
title BOSS直聘爬虫

echo ========================================
echo   BOSS直聘爬虫
echo ========================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate" (
    call .venv\Scripts\activate
)

echo.
echo ========================================
echo   开始爬取 BOSS直聘...
echo ========================================
python main.py boss

echo.
echo ========================================
echo   BOSS直聘完成！
echo ========================================
pause