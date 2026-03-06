@echo off
chcp 65001 >nul

REM 使用Python脚本创建表，不依赖psql命令
python setup_oil_wells_table.py

pause
