@echo off
chcp 65001 >nul
echo ============================================================
echo   油田钻井数据查询 MCP Server 启动脚本
echo ============================================================
echo.

REM 检查是否有虚拟环境
if exist "venv\Scripts\python.exe" (
    echo [√] 发现虚拟环境，使用虚拟环境的Python
    set PYTHON_CMD=venv\Scripts\python.exe
) else (
    echo [!] 未发现虚拟环境，使用系统Python
    set PYTHON_CMD=python
)

echo.
echo [*] Python路径: %PYTHON_CMD%
echo.

REM 检查依赖
echo [*] 检查依赖包...
%PYTHON_CMD% -c "import fastmcp" 2>nul
if errorlevel 1 (
    echo [!] 未安装 fastmcp，正在安装依赖...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [×] 依赖安装失败！
        pause
        exit /b 1
    )
) else (
    echo [√] 依赖包已安装
)

echo.
echo [*] 启动 MCP Server...
echo.

%PYTHON_CMD% oilfield_mcp_server.py

echo.
echo [!] 服务器已停止
pause
