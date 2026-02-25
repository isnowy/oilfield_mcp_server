@echo off
chcp 65001 >nul
echo ========================================
echo 启动油田MCP服务器 - 模拟数据模式
echo ========================================
echo.

REM 设置环境变量
set USE_REAL_DB=false
set DEV_MODE=true

echo 配置信息:
echo   数据源: SQLite内存模拟数据
echo   权限模式: 开发模式（跳过权限检查）
echo   监听端口: 8080
echo.
echo 提示: 按 Ctrl+C 停止服务器
echo.

REM 启动服务器
python oilfield_mcp_http_server.py

pause
