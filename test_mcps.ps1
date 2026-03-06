# 快速测试 MCP 服务器
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MCP 服务器快速测试" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 测试共享模块
Write-Host "[1/3] 测试共享模块..." -ForegroundColor Yellow
try {
    python -c "from common.db import get_db_connection; from common.permissions import PermissionService; from common.utils import df_to_markdown; from common.audit import AuditLog; print('✅ 共享模块导入成功')"
    Write-Host "✅ 共享模块测试通过" -ForegroundColor Green
} catch {
    Write-Host "❌ 共享模块测试失败" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 测试油井基础数据 MCP
Write-Host "[2/3] 测试油井基础数据 MCP..." -ForegroundColor Yellow
try {
    python -c "import sys; sys.path.insert(0, '.'); from oilfield_wells_mcp import mcp_server; print('✅ 油井基础数据 MCP 加载成功')"
    Write-Host "✅ 油井基础数据 MCP 测试通过" -ForegroundColor Green
} catch {
    Write-Host "❌ 油井基础数据 MCP 测试失败" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 测试日报系统 MCP
Write-Host "[3/3] 测试日报系统 MCP..." -ForegroundColor Yellow
try {
    python -c "import sys; sys.path.insert(0, '.'); from oilfield_dailyreports_mcp import mcp_server; print('✅ 日报系统 MCP 加载成功')"
    Write-Host "✅ 日报系统 MCP 测试通过" -ForegroundColor Green
} catch {
    Write-Host "❌ 日报系统 MCP 测试失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ 所有测试通过！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "💡 下一步：" -ForegroundColor Yellow
Write-Host "  1. 运行 .\start_all_mcps.ps1 启动服务" -ForegroundColor White
Write-Host "  2. 访问 http://localhost:8081/health 检查服务状态" -ForegroundColor White
Write-Host "  3. 访问 http://localhost:8082/health 检查服务状态" -ForegroundColor White
Write-Host "  4. 在 LibreChat 中配置并测试" -ForegroundColor White
Write-Host ""
Read-Host "按任意键退出"
