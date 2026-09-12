@echo off
cd /d "%~dp0"
echo Starting Google Flow Clip Studio (local)...
start "" "C:\Users\KJ\AppData\Local\Programs\Python\Python313\python.exe" app.py
timeout /t 2 >nul
start "" "http://localhost:5000/"
