@echo off
chcp 65001 > nul
title 北航选课系统关闭器

echo.
echo =====================================
echo 🛑 北航选课系统 - 关闭器
echo =====================================
echo.

python stop_vue_system.py

echo.
echo 按任意键退出...
pause > nul