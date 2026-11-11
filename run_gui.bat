@echo off
chcp 65001 >nul
title PDF 智能压缩桌面版

start "" pythonw "%~dp0gui.py"
if %errorlevel% neq 0 (
    python "%~dp0gui.py"
)
