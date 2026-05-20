@echo off
cd /d "%~dp0"
python ".\tools\chronicle_launcher.py" open
if errorlevel 1 pause
