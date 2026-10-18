@echo off
cd /d "%~dp0backend"
echo ==============================================
echo Activating Python venv and starting Backend...
echo ==============================================
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
