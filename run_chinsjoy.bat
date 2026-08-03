@echo off
chcp 65001 >nul
title ChinaJoy爬虫

echo ========================================
echo   ChinaJoy爬虫
echo ========================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate" (
    call .venv\Scripts\activate
)


echo.
echo ========================================
echo   开始爬取 ChinaJoy...
echo ========================================
python main.py chinajoy

echo.
echo ========================================
echo   ChinaJoy完成！
echo ========================================
pause