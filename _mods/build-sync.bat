@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: Interactive build-diff-sync workflow for claude-mem
:: Usage: double-click or run from terminal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "PY_CHECK=%SCRIPT_DIR%check-sync.py"

echo.
echo  ============================================
echo   claude-mem Build ^& Sync Workflow
echo  ============================================
echo.

:: Step 1: Build
echo  [Step 1/3] Build
echo  Command: npm run build
echo.
set /p CONFIRM="  Proceed with build? (y/n): "
if /i "!CONFIRM!"=="y" (
    echo.
    echo  Building...
    echo  --------------------------------------------
    cd /d "%PROJECT_DIR%"
    call npm run build
    if errorlevel 1 (
        echo.
        echo  [ERROR] Build failed! Abort.
        goto :end
    )
    echo  --------------------------------------------
    echo  Build OK.
) else (
    echo  Skipped.
)

echo.

:: Step 2: Diff
echo  [Step 2/3] Check diff
echo  Command: python _mods/check-sync.py
echo.
set /p CONFIRM="  Proceed with diff check? (y/n): "
if /i "!CONFIRM!"=="y" (
    echo.
    cd /d "%PROJECT_DIR%"
    python "%PY_CHECK%"
    echo.
) else (
    echo  Skipped.
)

echo.

:: Step 3: Sync
echo  [Step 3/3] Sync to cache + marketplace
echo  Command: python _mods/check-sync.py --sync
echo.
set /p CONFIRM="  Proceed with sync? (y/n): "
if /i "!CONFIRM!"=="y" (
    echo.
    cd /d "%PROJECT_DIR%"
    python "%PY_CHECK%" --sync
    echo.
    echo  Don't forget to run /reload-plugins in Claude Code!
) else (
    echo  Skipped.
)

echo.
:end
set /p DUMMY="  Press Enter to exit..."
