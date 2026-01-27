@echo off
echo Upgrading pip first...
chcp 65001 >nul
set PYTHONUTF8=1

python -m pip install --upgrade pip

echo.
echo Installing requirements...
python -m pip install -r requirements.txt

echo.
echo Done!
pause
