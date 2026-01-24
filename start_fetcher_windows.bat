@echo off
setlocal
set PATH=%PATH%;%CD%\.venv\Scripts
echo Starting AIStock Fetcher Daemon (Auto-restart enabled)...
:loop
uv run run_fetcher_daemon.py
echo Fetcher crashed with exit code %ERRORLEVEL%. Restarting in 5 seconds...
timeout /t 5
goto loop
