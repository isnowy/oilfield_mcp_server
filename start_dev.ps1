# 开发模式启动脚本
# 用于本地开发和测试，所有用户自动拥有 admin 权限

Write-Host "=" -NoNewline
for ($i = 0; $i -lt 59; $i++) { Write-Host "=" -NoNewline }
Write-Host ""
Write-Host "🚀 启动 MCP 服务器 - 开发模式"
Write-Host "=" -NoNewline
for ($i = 0; $i -lt 59; $i++) { Write-Host "=" -NoNewline }
Write-Host ""
Write-Host ""
Write-Host "🔓 权限模式：开发模式"
Write-Host "   特性：所有用户自动拥有 admin 权限"
Write-Host "   用途：本地开发、快速测试、功能演示"
Write-Host ""
Write-Host "⚠️  注意：生产环境请使用 start_prod.ps1"
Write-Host ""

# 设置环境变量
$env:DEV_MODE = "true"
$env:PYTHONIOENCODING = "utf-8"

# 启动服务
Write-Host "🏃 正在启动服务..."
Write-Host ""
python oilfield_mcp_server.py
