# 启动MCP服务器 - 使用模拟数据
# 适用于开发和测试

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动油田MCP服务器 - 模拟数据模式" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置环境变量
$env:USE_REAL_DB = "false"
$env:DEV_MODE = "true"

Write-Host "配置信息:" -ForegroundColor Yellow
Write-Host "  数据源: SQLite内存模拟数据" -ForegroundColor Green
Write-Host "  权限模式: 开发模式（跳过权限检查）" -ForegroundColor Green
Write-Host "  监听端口: 8080" -ForegroundColor Green
Write-Host ""
Write-Host "提示: 按 Ctrl+C 停止服务器" -ForegroundColor Gray
Write-Host ""

# 启动服务器
python oilfield_mcp_http_server.py
