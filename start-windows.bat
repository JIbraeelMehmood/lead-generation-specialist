@echo off
cd /d "%~dp0"
python leadfinder.py
if errorlevel 1 py leadfinder.py
pause
