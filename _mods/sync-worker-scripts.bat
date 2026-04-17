@echo off
chcp 65001 >nul 2>&1
:: Sync worker management scripts to ~/.claude-mem/

set "SRC=%~dp0worker-scripts"
set "DST=%USERPROFILE%\.claude-mem"

if not exist "%DST%" mkdir "%DST%"

echo.
echo  Sync worker scripts
echo  Source:  %SRC%
echo  Target:  %DST%
echo.

set COUNT=0
for %%F in ("%SRC%\*") do (
    copy /Y "%%F" "%DST%\%%~nxF" >nul
    echo   %%~nxF
    set /a COUNT+=1
)

echo.
echo  Done. Synced %COUNT% files.
echo.
pause
