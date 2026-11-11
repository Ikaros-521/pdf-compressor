@echo off
chcp 65001 >nul
title PDF 自动化监控服务

echo 正在启动 PDF 自动化监控服务...
echo.

python "%~dp0watcher.py"

pause
