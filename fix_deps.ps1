# ========================================
# Python 依赖冲突修复脚本 (PowerShell)
# ========================================

# 设置编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 切换到脚本目录
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Python 依赖冲突修复工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 是否可用
Write-Host "[信息] 检查 Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[成功] Python 版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未找到 Python，请确保 Python 已安装并添加到 PATH" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

Write-Host ""

# 检查虚拟环境
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[信息] 找到虚拟环境，正在激活..." -ForegroundColor Cyan
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "[成功] 虚拟环境已激活" -ForegroundColor Green
} else {
    Write-Host "[警告] 未找到虚拟环境" -ForegroundColor Yellow
    Write-Host ""
    $createVenv = Read-Host "是否创建新的虚拟环境? (Y/N)"
    if ($createVenv -eq "Y" -or $createVenv -eq "y") {
        Write-Host "[信息] 正在创建虚拟环境..." -ForegroundColor Cyan
        python -m venv venv
        & ".\venv\Scripts\Activate.ps1"
        Write-Host "[成功] 虚拟环境已创建并激活" -ForegroundColor Green
    } else {
        Write-Host "[警告] 继续在全局环境中操作..." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   步骤 1/4: 升级 pip" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] pip 升级失败" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}
Write-Host "[成功] pip 已升级" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   步骤 2/4: 升级 langchain-core" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

pip install --upgrade langchain-core
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] langchain-core 升级失败" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}
Write-Host "[成功] langchain-core 已升级" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   步骤 3/4: 重新安装依赖" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

pip install --upgrade -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 依赖安装失败" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}
Write-Host "[成功] 依赖已重新安装" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   步骤 4/4: 验证依赖" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

pip check
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[警告] 仍存在依赖冲突" -ForegroundColor Yellow
    Write-Host "[建议] 尝试重新创建虚拟环境:" -ForegroundColor Yellow
    Write-Host "         1. Remove-Item -Recurse -Force venv" -ForegroundColor Yellow
    Write-Host "         2. python -m venv venv" -ForegroundColor Yellow
    Write-Host "         3. .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "         4. pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "[成功] 所有依赖验证通过！" -ForegroundColor Green
    Write-Host ""
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   已安装的关键包版本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$packages = @("langchain-core", "langgraph-checkpoint", "langgraph-prebuilt", "fastmcp")
foreach ($pkg in $packages) {
    $info = pip show $pkg 2>$null | Select-String "Name:|Version:"
    if ($info) {
        Write-Host $info -ForegroundColor White
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   修复完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Green
Write-Host "  1. 测试 MCP 服务器: python oilfield_mcp_server.py" -ForegroundColor White
Write-Host "  2. 启动 LibreChat 并测试集成" -ForegroundColor White
Write-Host ""

Read-Host "按任意键退出"
