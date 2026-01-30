@echo off
REM 启动HTTP MCP Server - Windows批处理脚本

echo ============================================================
echo 油田钻井数据MCP Server - HTTP/SSE版本
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 切换到脚本目录
cd /d %~dp0

REM 检查依赖
echo 检查依赖...
python -c "import fastapi, uvicorn, mcp" >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 缺少依赖，正在安装...
    pip install -r requirements_http.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [OK] 依赖检查完成
echo.

REM 设置环境变量
set DATABASE_URL=sqlite:///d:/work/oilMCP/oilfield.db
set LOG_LEVEL=INFO

echo 配置信息:
echo   数据库: %DATABASE_URL%
echo   端口: 8080
echo.

echo 启动服务器...
echo 按 Ctrl+C 停止服务器
echo.

REM 启动服务器
python oilfield_mcp_http_server.py

pause
