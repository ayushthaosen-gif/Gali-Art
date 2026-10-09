@echo off
rem Starts the local poster tool and opens it in your browser. Close this window to stop it.
cd /d "%~dp0"
start "" http://127.0.0.1:8800
".venv\Scripts\python.exe" tool.py
pause
