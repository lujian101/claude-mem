@echo off
REM claude-mem Worker 手动启动脚本
REM 使用方法：双击此脚本启动后台服务

setlocal

REM 设置插件路径（根据你的安装位置调整）
set PLUGIN_ROOT=%USERPROFILE%\.claude\plugins\marketplaces\lujian101\plugin

REM 如果插件在其他位置，手动设置：
REM set PLUGIN_ROOT=D:\LocalDev\github\claude-mem\plugin

echo ========================================
echo claude-mem Worker 手动启动
echo ========================================
echo.

REM 检查服务是否已运行
echo [1/3] 检查服务状态...
node "%PLUGIN_ROOT%\scripts\worker-service.cjs" status 2>nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ 服务已在运行中
    echo.
    pause
    exit /b 0
)

echo [2/3] 启动后台服务...
node "%PLUGIN_ROOT%\scripts\worker-service.cjs" start

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ✗ 启动失败
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] 等待服务就绪...
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo ✓ claude-mem Worker 启动成功
echo ========================================
echo.
echo 服务信息:
node "%PLUGIN_ROOT%\scripts\worker-service.cjs" status
echo.
echo 按 Ctrl+C 可查看日志，关闭此窗口不影响服务运行
echo.

REM 保持窗口打开以便查看日志
REM 如需后台运行，注释掉下面这行
REM exit /b 0
