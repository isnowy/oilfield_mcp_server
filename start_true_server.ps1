# 启动独立的真实数据库MCP服务器（8081端口）
# 该服务器专门用于真实数据库查询

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动油田MCP服务器 - 真实数据专用版" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置环境变量
$env:DEV_MODE = "true"

# 数据库配置（可根据需要修改）
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DB_NAME = "rag"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "postgres"

Write-Host "配置信息:" -ForegroundColor Yellow
Write-Host "  数据源: PostgreSQL真实数据库（专用）" -ForegroundColor Green
Write-Host "  数据库: $env:DB_HOST`:$env:DB_PORT/$env:DB_NAME" -ForegroundColor Green
Write-Host "  权限模式: 开发模式（跳过权限检查）" -ForegroundColor Green
Write-Host "  监听端口: 8081" -ForegroundColor Green
Write-Host ""
Write-Host "提示: 按 Ctrl+C 停止服务器" -ForegroundColor Gray
Write-Host ""

# 启动服务器
python oilfield_mcp_true_server.py
