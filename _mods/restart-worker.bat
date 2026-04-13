@echo off
REM claude-mem Worker 重启脚本

setlocal

set PLUGIN_ROOT=%USERPROFILE%\.claude\plugins\marketplaces\lujian101\plugin

echo ========================================
echo claude-mem Worker 重启
echo ========================================
echo.

echo [1/2] 停止现有服务...
node "%PLUGIN_ROOT%\scripts\worker-service.cjs" stop

echo.
echo [2/2] 启动服务...
node "%PLUGIN_ROOT%\scripts\worker-service.cjs" start

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ 服务重启成功
) else (
    echo.
    echo ✗ 重启失败
)

echo.
pause
