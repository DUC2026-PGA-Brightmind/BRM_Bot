@echo off
title BrightMind HR Bots
cd /d C:\xampp\htdocs\BrightMind

echo Starting Worker Bot...
start "Worker Bot" /min py bot.py

echo Starting Admin Bot...
start "Admin Bot" /min py admin_bot.py

echo Both bots started!
