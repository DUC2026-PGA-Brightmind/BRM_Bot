@echo off
:: install_service.bat
:: Run this as Administrator to install bots as Windows Services
:: Requires NSSM: https://nssm.cc/download

set WORKDIR=C:\xampp\htdocs\BrightMind
set NSSM=C:\nssm\nssm.exe
set PY=py

echo ============================================
echo  Installing BrightMind HR Bots as Services
echo ============================================

:: Check NSSM exists
if not exist "%NSSM%" (
    echo ERROR: NSSM not found at %NSSM%
    echo Download from: https://nssm.cc/download
    echo Extract nssm.exe to C:\nssm\
    pause
    exit /b 1
)

:: Install Worker Bot Service
echo Installing Worker Bot service...
"%NSSM%" install "BrightMind-WorkerBot" "%PY%" "bot.py"
"%NSSM%" set "BrightMind-WorkerBot" AppDirectory "%WORKDIR%"
"%NSSM%" set "BrightMind-WorkerBot" DisplayName "BrightMind Worker Bot"
"%NSSM%" set "BrightMind-WorkerBot" Description "HR Telegram Worker Bot"
"%NSSM%" set "BrightMind-WorkerBot" Start SERVICE_AUTO_START
"%NSSM%" set "BrightMind-WorkerBot" AppStdout "%WORKDIR%\logs\worker_bot.log"
"%NSSM%" set "BrightMind-WorkerBot" AppStderr "%WORKDIR%\logs\worker_bot_err.log"
"%NSSM%" set "BrightMind-WorkerBot" AppRestartDelay 5000

:: Install Admin Bot Service
echo Installing Admin Bot service...
"%NSSM%" install "BrightMind-AdminBot" "%PY%" "admin_bot.py"
"%NSSM%" set "BrightMind-AdminBot" AppDirectory "%WORKDIR%"
"%NSSM%" set "BrightMind-AdminBot" DisplayName "BrightMind Admin Bot"
"%NSSM%" set "BrightMind-AdminBot" Description "HR Telegram Admin Bot"
"%NSSM%" set "BrightMind-AdminBot" Start SERVICE_AUTO_START
"%NSSM%" set "BrightMind-AdminBot" AppStdout "%WORKDIR%\logs\admin_bot.log"
"%NSSM%" set "BrightMind-AdminBot" AppStderr "%WORKDIR%\logs\admin_bot_err.log"
"%NSSM%" set "BrightMind-AdminBot" AppRestartDelay 5000

:: Start services
echo Starting services...
"%NSSM%" start "BrightMind-WorkerBot"
"%NSSM%" start "BrightMind-AdminBot"

echo.
echo ============================================
echo  Done! Both bots are now running as services
echo  They will auto-start on Windows boot
echo ============================================
pause
