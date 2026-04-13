@echo off
REM claude-mem Worker 手动停止脚本

setlocal

set PLUGIN_ROOT=%USERPROFILE%\.claude\plugins\marketplaces\lujian101\plugin

echo ========================================
echo claude-mem Worker 手动停止
echo ========================================
echo.

echo 正在停止后台服务...
node "%PLUGIN_ROOT%\scripts\worker-service.cjs" stop

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ 服务已停止
) else (
    echo.
    echo ✗ 停止失败或服务未运行
)

echo.
pause
