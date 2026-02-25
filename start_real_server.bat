@echo off
chcp 65001 >nul
echo ========================================
echo 启动油田MCP服务器 - 真实数据库模式
echo ========================================
echo.

REM 设置环境变量
set USE_REAL_DB=true
set DEV_MODE=true

REM 数据库配置（可根据需要修改）
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=rag
set DB_USER=postgres
set DB_PASSWORD=postgres

echo 配置信息:
echo   数据源: PostgreSQL真实数据库
echo   数据库: %DB_HOST%:%DB_PORT%/%DB_NAME%
echo   权限模式: 开发模式（跳过权限检查）
echo   监听端口: 8080
echo.
echo 提示: 按 Ctrl+C 停止服务器
echo.

REM 启动服务器
python oilfield_mcp_http_server.py

pause
