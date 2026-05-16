# keep_alive.ps1 - Keeps both bots running 24/7
# If a bot crashes, it restarts automatically after 5 seconds

$WorkDir = "C:\xampp\htdocs\BrightMind"
$LogFile = "$WorkDir\bot_log.txt"

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $msg" | Tee-Object -FilePath $LogFile -Append
}

Write-Log "=== BrightMind HR Bot Service Started ==="

while ($true) {
    # ── Worker Bot ──────────────────────────────────────────────
    $workerProc = Get-Process -Name "py" -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -like "*Worker*" -or $_.CommandLine -like "*bot.py*" }

    if (-not $workerProc) {
        Write-Log "Worker Bot not running — starting..."
        Start-Process -FilePath "py" -ArgumentList "bot.py" `
            -WorkingDirectory $WorkDir -WindowStyle Hidden
        Write-Log "Worker Bot started."
    }

    # ── Admin Bot ───────────────────────────────────────────────
    $adminProc = Get-Process -Name "py" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*admin_bot.py*" }

    if (-not $adminProc) {
        Write-Log "Admin Bot not running — starting..."
        Start-Process -FilePath "py" -ArgumentList "admin_bot.py" `
            -WorkingDirectory $WorkDir -WindowStyle Hidden
        Write-Log "Admin Bot started."
    }

    # Check every 30 seconds
    Start-Sleep -Seconds 30
}
