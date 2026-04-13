@echo off
REM claude-mem Worker 状态查询脚本

setlocal

set PLUGIN_ROOT=%USERPROFILE%\.claude\plugins\marketplaces\lujian101\plugin

echo ========================================
echo claude-mem Worker 状态
echo ========================================
echo.

echo 检查服务状态...
echo.

node "%PLUGIN_ROOT%\scripts\worker-service.cjs" status

echo.
echo ========================================
echo 端口占用情况:
echo.

netstat -ano | findstr :37777

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ 端口 37777 已被占用
) else (
    echo.
    echo ✗ 端口 37777 未被占用
)

echo.
echo ========================================
echo.

pause
