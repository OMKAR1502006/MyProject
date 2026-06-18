@echo off
REM Quick start when venv already exists (skip install/migrate)
cd /d "%~dp0"
call venv\Scripts\activate.bat 2>nul || (
  echo Run start.bat first for full setup.
  exit /b 1
)
python manage.py runserver 0.0.0.0:8000
