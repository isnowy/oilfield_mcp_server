@echo off
chcp 65001 > nul
echo.
echo ========================================================================
echo   角色权限自动化测试
echo ========================================================================
echo.

REM 设置生产模式
set DEV_MODE=false

REM 运行测试
python test_role_permissions.py

echo.
pause
