# 生产模式启动脚本
# 用于正式部署，启用严格的基于角色的权限控制

Write-Host "=" -NoNewline
for ($i = 0; $i -lt 59; $i++) { Write-Host "=" -NoNewline }
Write-Host ""
Write-Host "🚀 启动 MCP 服务器 - 生产模式"
Write-Host "=" -NoNewline
for ($i = 0; $i -lt 59; $i++) { Write-Host "=" -NoNewline }
Write-Host ""
Write-Host ""
Write-Host "🔒 权限模式：生产模式"
Write-Host "   特性：严格的基于角色的权限控制"
Write-Host "   用途：正式部署、多用户环境"
Write-Host ""
Write-Host "📌 权限角色："
Write-Host "   • admin   - 全部权限"
Write-Host "   • engineer - Block-A 的部分井"
Write-Host "   • viewer  - ZT-102 只读"
Write-Host "   • default - 受限访问（无权限）"
Write-Host ""

# 设置环境变量
$env:DEV_MODE = "false"
$env:PYTHONIOENCODING = "utf-8"

# 启动服务
Write-Host "🏃 正在启动服务..."
Write-Host ""
python oilfield_mcp_server.py
