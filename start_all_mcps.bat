@echo off
chcp 65001 > nul
echo ========================================
echo 启动油井 MCP 服务器（2个独立服务）
echo ========================================
echo.

echo [1/2] 启动油井基础数据 MCP Server (端口 8081)...
start "油井基础数据 MCP" cmd /k "python oilfield_wells_mcp.py"
timeout /t 2 /nobreak > nul

echo [2/2] 启动油井日报系统 MCP Server (端口 8082)...
start "油井日报系统 MCP" cmd /k "python oilfield_dailyreports_mcp.py"
timeout /t 2 /nobreak > nul

echo.
echo ========================================
echo ✅ 所有 MCP 服务器已启动
echo ========================================
echo.
echo 📡 服务地址：
echo   - 油井基础数据: http://localhost:8081
echo   - 油井日报系统: http://localhost:8082
echo.
echo 💡 提示：
echo   - 关闭窗口将停止对应的服务
echo   - 按 Ctrl+C 可以停止所有服务
echo.
pause
