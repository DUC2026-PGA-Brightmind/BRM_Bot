@echo off
echo ============================================
echo  BrightMind HR Bot Status
echo ============================================
echo.

:: Check if py processes are running
tasklist /FI "IMAGENAME eq py.exe" 2>NUL | find /I "py.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [RUNNING] Python bots are active
    tasklist /FI "IMAGENAME eq py.exe"
) else (
    echo [STOPPED] No Python bots running
)

echo.
echo ============================================
echo  Windows Services Status
echo ============================================
sc query "BrightMind-WorkerBot" 2>NUL || echo WorkerBot service not installed
sc query "BrightMind-AdminBot" 2>NUL || echo AdminBot service not installed

echo.
pause
