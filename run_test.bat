@echo off
chcp 65001 >nul
echo ============================================================
echo   油田 MCP Server 功能测试脚本
echo ============================================================
echo.

REM 检查是否有虚拟环境
if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

echo [*] 运行测试用例...
echo.

%PYTHON_CMD% test_server.py

echo.
echo ============================================================
echo   测试完成
echo ============================================================
pause
