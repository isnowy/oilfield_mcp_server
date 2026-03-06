# 启动所有 MCP 服务器
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动油井 MCP 服务器（2个独立服务）" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置环境变量
$env:DEV_MODE = "true"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DB_NAME = "rag"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "postgres"

Write-Host "[1/2] 启动油井基础数据 MCP Server (端口 8081)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python oilfield_wells_mcp.py"
Start-Sleep -Seconds 2

Write-Host "[2/2] 启动油井日报系统 MCP Server (端口 8082)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python oilfield_dailyreports_mcp.py"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ 所有 MCP 服务器已启动" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📡 服务地址：" -ForegroundColor White
Write-Host "  - 油井基础数据: http://localhost:8081" -ForegroundColor White
Write-Host "  - 油井日报系统: http://localhost:8082" -ForegroundColor White
Write-Host ""
Write-Host "💡 提示：" -ForegroundColor Yellow
Write-Host "  - 关闭窗口将停止对应的服务" -ForegroundColor Yellow
Write-Host "  - 使用 Get-Process | Where-Object {`$_.MainWindowTitle -like '*MCP*'} | Stop-Process 停止所有服务" -ForegroundColor Yellow
Write-Host ""
Read-Host "按任意键退出"
