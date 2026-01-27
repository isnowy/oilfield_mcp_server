@echo off
chcp 65001 >nul 2>&1
REM ========================================
REM Python Dependency Conflict Fix Script
REM ========================================

cd /d "%~dp0"

echo.
echo ========================================
echo    Python Dependency Fix Tool
echo ========================================
echo.

REM Check Python availability
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python and add to PATH
    pause
    exit /b 1
)

echo [INFO] Python version:
python --version
echo.

REM Check virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Found virtual environment, activating...
    call venv\Scripts\activate.bat
    echo [SUCCESS] Virtual environment activated
) else (
    echo [WARNING] Virtual environment not found
    echo.
    echo Create new virtual environment? (Y/N)
    set /p create_venv=
    if /i "%create_venv%"=="Y" (
        echo [INFO] Creating virtual environment...
        python -m venv venv
        call venv\Scripts\activate.bat
        echo [SUCCESS] Virtual environment created and activated
    ) else (
        echo [WARNING] Continuing with global environment...
    )
)

echo.
echo ========================================
echo    Step 1/4: Upgrade pip
echo ========================================
echo.
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] pip upgrade failed
    pause
    exit /b 1
)
echo [SUCCESS] pip upgraded

echo.
echo ========================================
echo    Step 2/4: Upgrade langchain-core
echo ========================================
echo.
pip install --upgrade langchain-core
if errorlevel 1 (
    echo [ERROR] langchain-core upgrade failed
    pause
    exit /b 1
)
echo [SUCCESS] langchain-core upgraded

echo.
echo ========================================
echo    Step 3/4: Reinstall dependencies
echo ========================================
echo.
pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependencies installation failed
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies reinstalled

echo.
echo ========================================
echo    Step 4/4: Verify dependencies
echo ========================================
echo.
pip check
if errorlevel 1 (
    echo.
    echo [WARNING] Dependency conflicts still exist
    echo [SUGGESTION] Try recreating virtual environment:
    echo              1. rmdir /s /q venv
    echo              2. python -m venv venv
    echo              3. venv\Scripts\activate
    echo              4. pip install -r requirements.txt
    echo.
) else (
    echo.
    echo [SUCCESS] All dependencies verified!
    echo.
)

echo.
echo ========================================
echo    Installed Key Packages
echo ========================================
echo.
pip show langchain-core 2>nul | findstr "Name Version"
pip show langgraph-checkpoint 2>nul | findstr "Name Version"
pip show langgraph-prebuilt 2>nul | findstr "Name Version"
pip show fastmcp 2>nul | findstr "Name Version"

echo.
echo ========================================
echo    Fix Complete
echo ========================================
echo.
echo Next steps:
echo   1. Test MCP server: python oilfield_mcp_server.py
echo   2. Start LibreChat and test integration
echo.

pause
