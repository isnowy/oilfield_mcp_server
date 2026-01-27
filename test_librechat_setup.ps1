# LibreChat 多角色测试配置生成脚本
# 用于生成多个 MCP 配置以便在 LibreChat 中测试不同角色

Write-Host "`n" -NoNewline
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  LibreChat 多角色测试配置生成工具" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 获取当前脚本目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverPath = Join-Path $scriptDir "oilfield_mcp_server.py"

# 检查服务器文件是否存在
if (-not (Test-Path $serverPath)) {
    Write-Host "❌ 错误：未找到 oilfield_mcp_server.py" -ForegroundColor Red
    Write-Host "   当前目录: $scriptDir" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 找到 MCP 服务器: $serverPath" -ForegroundColor Green
Write-Host ""

# 生成 LibreChat 配置文件
$configContent = @"
version: 1.1.7

# ============================================================================
# 多角色测试配置
# 用于测试不同角色的权限差异
# ============================================================================

mcpServers:
  # 🔐 管理员角色 - 全部权限
  oilfield-admin:
    command: python
    args:
      - "$serverPath"
    env:
      DEV_MODE: "false"
      USER_ROLE: "admin"
      PYTHONIOENCODING: "utf-8"
    description: "油田数据查询(管理员-全部权限)"
    disabled: false
    
  # 👷 工程师角色 - Block-A的部分井
  oilfield-engineer:
    command: python
    args:
      - "$serverPath"
    env:
      DEV_MODE: "false"
      USER_ROLE: "engineer"
      PYTHONIOENCODING: "utf-8"
    description: "油田数据查询(工程师-Block-A部分井)"
    disabled: false
    
  # 👁️ 访客角色 - 仅 ZT-102 只读
  oilfield-viewer:
    command: python
    args:
      - "$serverPath"
    env:
      DEV_MODE: "false"
      USER_ROLE: "viewer"
      PYTHONIOENCODING: "utf-8"
    description: "油田数据查询(访客-ZT-102只读)"
    disabled: false
    
  # 🚫 默认角色 - 无权限
  oilfield-default:
    command: python
    args:
      - "$serverPath"
    env:
      DEV_MODE: "false"
      USER_ROLE: "default"
      PYTHONIOENCODING: "utf-8"
    description: "油田数据查询(默认-无权限)"
    disabled: false

mcp:
  enabled: true
  timeout: 30000
  maxConnections: 10
"@

# 保存配置文件
$configPath = Join-Path $scriptDir "librechat_test_roles.yaml"
$configContent | Out-File -FilePath $configPath -Encoding UTF8

Write-Host "✅ 已生成测试配置文件: $configPath" -ForegroundColor Green
Write-Host ""

# 生成测试说明
$testGuide = @"
========================================================================
  📋 LibreChat 角色测试指南
========================================================================

1️⃣ 复制配置文件到 LibreChat
   
   将生成的配置文件复制到 LibreChat 项目目录：
   
   Copy-Item "$configPath" "C:\Projects\LibreChat\librechat.yaml"
   
   (请根据实际路径修改)

2️⃣ 重启 LibreChat
   
   cd C:\Projects\LibreChat
   npm run backend

3️⃣ 测试不同角色
   
   打开浏览器访问: http://localhost:3080
   
   在聊天界面可以选择不同的 MCP 服务:
   - oilfield-admin      (管理员)
   - oilfield-engineer   (工程师)
   - oilfield-viewer     (访客)
   - oilfield-default    (默认)

4️⃣ 执行测试查询
   
   对每个角色执行相同的查询，观察结果差异：
   
   ✓ 查询测试 1: 查询 ZT-102 井的详细信息
     预期结果:
     - admin: ✅ 成功
     - engineer: ✅ 成功
     - viewer: ✅ 成功
     - default: ❌ 拒绝
   
   ✓ 查询测试 2: 查询 ZT-105 井的详细信息
     预期结果:
     - admin: ✅ 成功
     - engineer: ✅ 成功
     - viewer: ❌ 拒绝
     - default: ❌ 拒绝
   
   ✓ 查询测试 3: 查询 XY-009 井的详细信息
     预期结果:
     - admin: ✅ 成功
     - engineer: ❌ 拒绝
     - viewer: ❌ 拒绝
     - default: ❌ 拒绝
   
   ✓ 查询测试 4: 搜索 Block-A 区块的所有井
     预期结果:
     - admin: ✅ 成功
     - engineer: ✅ 成功
     - viewer: ✅ 成功
     - default: ❌ 拒绝
   
   ✓ 查询测试 5: 搜索 Block-B 区块的所有井
     预期结果:
     - admin: ✅ 成功
     - engineer: ❌ 拒绝
     - viewer: ❌ 拒绝
     - default: ❌ 拒绝
   
   ✓ 查询测试 6: 对比 ZT-102 和 ZT-105 的钻井速度
     预期结果:
     - admin: ✅ 成功
     - engineer: ✅ 成功
     - viewer: ❌ 拒绝 (无ZT-105权限)
     - default: ❌ 拒绝

5️⃣ 记录测试结果
   
   建议创建测试记录表格，记录每个角色的查询结果。

========================================================================
  💡 测试技巧
========================================================================

• 使用完全相同的查询语句测试不同角色
• 注意观察被拒绝时的提示信息
• 确认 DEV_MODE=false（生产模式）
• 可以在不同浏览器标签页中同时打开多个角色进行对比

========================================================================
  🔗 相关命令
========================================================================

# 查看 MCP 服务器日志
Get-Content "$scriptDir\mcp_server.log" -Tail 50 -Wait

# 直接测试 Python 脚本（不依赖 LibreChat）
python "$scriptDir\test_role_permissions.py"

# 测试权限逻辑
python "$scriptDir\test_permissions.py"

========================================================================
"@

# 保存测试指南
$guidePath = Join-Path $scriptDir "LIBRECHAT_TEST_GUIDE.txt"
$testGuide | Out-File -FilePath $guidePath -Encoding UTF8

Write-Host "✅ 已生成测试指南: $guidePath" -ForegroundColor Green
Write-Host ""

# 显示测试指南
Write-Host $testGuide

# 询问是否立即运行 Python 测试
Write-Host ""
$runPythonTest = Read-Host "是否运行 Python 自动化测试验证权限逻辑？(Y/n)"

if ($runPythonTest -eq "" -or $runPythonTest -eq "Y" -or $runPythonTest -eq "y") {
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host "  运行 Python 自动化测试..." -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    $env:DEV_MODE = "false"
    python "$scriptDir\test_role_permissions.py"
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  ✅ 配置生成完成！" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "1. 将 $configPath 复制到 LibreChat 目录" -ForegroundColor White
Write-Host "2. 重启 LibreChat" -ForegroundColor White
Write-Host "3. 按照 $guidePath 中的指南进行测试" -ForegroundColor White
Write-Host ""
