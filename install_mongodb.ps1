# MongoDB Installation Script
# This script will download and install MongoDB Community Server

Write-Host "=== MongoDB Installation Script ===" -ForegroundColor Green
Write-Host ""

# Check if already installed
$mongoInstalled = Get-Command mongod -ErrorAction SilentlyContinue
if ($mongoInstalled) {
    Write-Host "MongoDB is already installed" -ForegroundColor Yellow
    mongod --version
    exit 0
}

# Method 1: Use winget (recommended)
Write-Host "Method 1: Trying to install using winget..." -ForegroundColor Cyan
$wingetAvailable = Get-Command winget -ErrorAction SilentlyContinue

if ($wingetAvailable) {
    Write-Host "Installing MongoDB using winget..." -ForegroundColor Green
    winget install -e --id MongoDB.Server --accept-package-agreements --accept-source-agreements
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "MongoDB installation successful!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Important notes:" -ForegroundColor Yellow
        Write-Host "1. Restart PowerShell or add MongoDB to PATH"
        Write-Host "2. Default MongoDB path: C:\Program Files\MongoDB\Server\<version>\bin"
        Write-Host "3. Create data directory: C:\data\db"
        Write-Host "4. Run commands to install service or start manually"
        Write-Host ""
        
        # Create data directory
        $dataPath = "C:\data\db"
        if (-not (Test-Path $dataPath)) {
            Write-Host "Creating MongoDB data directory: $dataPath" -ForegroundColor Cyan
            New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
        }
        
        exit 0
    }
}

# Method 2: Provide manual installation instructions
Write-Host ""
Write-Host "Method 2: Manual MongoDB Installation" -ForegroundColor Cyan
Write-Host ""
Write-Host "Please follow these steps:" -ForegroundColor Yellow
Write-Host "1. Visit MongoDB download page:"
Write-Host "   https://www.mongodb.com/try/download/community" -ForegroundColor Blue
Write-Host ""
Write-Host "2. Select configuration:"
Write-Host "   - Version: Current stable (e.g. 7.0.x)"
Write-Host "   - Platform: Windows"
Write-Host "   - Package: MSI"
Write-Host ""
Write-Host "3. Download and run the .msi installer"
Write-Host ""
Write-Host "4. Choose 'Complete' installation during setup"
Write-Host ""
Write-Host "5. Check 'Install MongoDB as a Service'"
Write-Host ""
Write-Host "6. Create data directory (if not created):"
Write-Host "   mkdir C:\data\db" -ForegroundColor Green
Write-Host ""
Write-Host "7. Add MongoDB bin directory to system PATH:"
Write-Host "   C:\Program Files\MongoDB\Server\<version>\bin" -ForegroundColor Green
Write-Host ""

# Try to open download page
$openBrowser = Read-Host "Open MongoDB download page? (Y/N)"
if ($openBrowser -eq "Y" -or $openBrowser -eq "y") {
    Start-Process "https://www.mongodb.com/try/download/community"
}

Write-Host ""
Write-Host "After manual installation, restart PowerShell and verify:" -ForegroundColor Cyan
Write-Host "  mongod --version" -ForegroundColor Green
