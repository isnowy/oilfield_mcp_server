# Meilisearch Installation Script for Windows
# This script downloads and installs Meilisearch

Write-Host "=== Meilisearch Installation Script ===" -ForegroundColor Green
Write-Host ""

# Configuration
$meilisearchVersion = "v1.11.3"
$installPath = "$env:USERPROFILE\meilisearch"
$downloadUrl = "https://github.com/meilisearch/meilisearch/releases/download/$meilisearchVersion/meilisearch-windows-amd64.exe"
$exePath = "$installPath\meilisearch.exe"

# Check if already installed
if (Test-Path $exePath) {
    Write-Host "Meilisearch is already installed at: $exePath" -ForegroundColor Yellow
    & $exePath --version
    
    $reinstall = Read-Host "Reinstall? (Y/N)"
    if ($reinstall -ne "Y" -and $reinstall -ne "y") {
        exit 0
    }
}

# Create installation directory
Write-Host "Creating installation directory: $installPath" -ForegroundColor Cyan
if (-not (Test-Path $installPath)) {
    New-Item -ItemType Directory -Path $installPath -Force | Out-Null
}

# Download Meilisearch
Write-Host "Downloading Meilisearch $meilisearchVersion..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $exePath -UseBasicParsing
    Write-Host "Download completed successfully!" -ForegroundColor Green
} catch {
    Write-Host "Download failed: $_" -ForegroundColor Red
    exit 1
}

# Verify download
if (Test-Path $exePath) {
    $fileSize = (Get-Item $exePath).Length / 1MB
    Write-Host "Downloaded file size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "Download verification failed!" -ForegroundColor Red
    exit 1
}

# Add to PATH
Write-Host "Adding Meilisearch to system PATH..." -ForegroundColor Cyan
$currentPath = [Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::User)
if ($currentPath -notlike "*$installPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$installPath", [System.EnvironmentVariableTarget]::User)
    $env:Path += ";$installPath"
    Write-Host "Added to user PATH" -ForegroundColor Green
} else {
    Write-Host "Already in PATH" -ForegroundColor Yellow
}

# Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Cyan
& $exePath --version

# Create data directory
$dataPath = "$installPath\data.ms"
if (-not (Test-Path $dataPath)) {
    Write-Host "Creating data directory: $dataPath" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
}

# Create startup script
$startScriptPath = "$installPath\start_meilisearch.bat"
$startScriptContent = @"
@echo off
cd /d "%~dp0"
echo Starting Meilisearch...
meilisearch.exe --db-path=data.ms --http-addr=127.0.0.1:7700
"@

Set-Content -Path $startScriptPath -Value $startScriptContent
Write-Host "Created startup script: $startScriptPath" -ForegroundColor Green

# Create configuration file
$configPath = "$installPath\config.toml"
$configContent = @"
# Meilisearch Configuration
db_path = "./data.ms"
http_addr = "127.0.0.1:7700"
env = "development"
max_indexing_memory = "100 MiB"
# master_key = "YOUR_MASTER_KEY_HERE"
"@

Set-Content -Path $configPath -Value $configContent
Write-Host "Created configuration file: $configPath" -ForegroundColor Green

Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Installation Details:" -ForegroundColor Cyan
Write-Host "  Executable: $exePath"
Write-Host "  Data Path: $dataPath"
Write-Host "  Config: $configPath"
Write-Host "  Startup Script: $startScriptPath"
Write-Host ""
Write-Host "To start Meilisearch:" -ForegroundColor Yellow
Write-Host "  Option 1: Run the startup script"
Write-Host "    & '$startScriptPath'"
Write-Host ""
Write-Host "  Option 2: Run directly"
Write-Host "    meilisearch --db-path='$dataPath' --http-addr=127.0.0.1:7700"
Write-Host ""
Write-Host "  Option 3: Install as Windows Service (requires admin)"
Write-Host "    See: https://www.meilisearch.com/docs/learn/cookbooks/running_production"
Write-Host ""
Write-Host "Default URL: http://localhost:7700" -ForegroundColor Green
Write-Host ""

$startNow = Read-Host "Start Meilisearch now? (Y/N)"
if ($startNow -eq "Y" -or $startNow -eq "y") {
    Write-Host ""
    Write-Host "Starting Meilisearch..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    Start-Process -FilePath $exePath -ArgumentList "--db-path=`"$dataPath`"", "--http-addr=127.0.0.1:7700" -NoNewWindow
    Start-Sleep -Seconds 2
    
    # Test connection
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:7700/health" -UseBasicParsing
        Write-Host "Meilisearch is running! Health check: OK" -ForegroundColor Green
    } catch {
        Write-Host "Meilisearch may still be starting up..." -ForegroundColor Yellow
    }
}
