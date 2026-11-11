@echo off
chcp 65001 >nul
title PDF 快捷拖拽压缩工具

if "%~1"=="" (
    echo ======================================================
    echo           PDF 智能快捷压缩工具 (拖拽模式)
    echo ======================================================
    echo.
    echo 使用方法：
    echo   1. 在 Windows 资源管理器中选中一个或多个 PDF 文件（或文件夹）。
    echo   2. 直接鼠标拖拽到本文件 (compress_drop.bat) 图标上方松开。
    echo   3. 程序将自动进行平衡模式压缩，并输出到同目录下的 *_compressed.pdf。
    echo.
    echo 提示: 您也可以将本批处理发送快捷方式到桌面或“发送到 (SendTo)”菜单。
    echo ======================================================
    echo.
    pause
    exit /b
)

echo 正在启动 PDF 压缩处理，请稍候...
echo.

python "%~dp0cli.py" %*

echo.
echo 处理完成！按任意键退出...
pause >nul
