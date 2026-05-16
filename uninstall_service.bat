@echo off
:: Run as Administrator to remove services
set NSSM=C:\nssm\nssm.exe

echo Stopping and removing BrightMind services...
"%NSSM%" stop "BrightMind-WorkerBot"
"%NSSM%" remove "BrightMind-WorkerBot" confirm
"%NSSM%" stop "BrightMind-AdminBot"
"%NSSM%" remove "BrightMind-AdminBot" confirm
echo Done.
pause
