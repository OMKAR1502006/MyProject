@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo   AgroSathi Django - One-Click Startup
echo ========================================

REM Prefer Python launcher on Windows
set PY=python
where py >nul 2>&1 && set PY=py -3

if not exist "venv\Scripts\python.exe" (
  echo [1/8] Creating virtual environment...
  %PY% -m venv venv
  if errorlevel 1 (
    echo ERROR: Install Python 3.10-3.12 from https://www.python.org/downloads/
    exit /b 1
  )
) else (
  echo [1/8] Virtual environment found.
)

call venv\Scripts\activate.bat

echo [2/8] Installing core dependencies...
python -m pip install --upgrade pip -q
pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: Core install failed.
  exit /b 1
)

echo [3/8] Installing optional ML packages (TensorFlow, OpenCV)...
pip install -r requirements-ml.txt 2>nul
if errorlevel 1 (
  echo NOTE: ML packages skipped — disease detection still works via Gemini API.
)

if not exist ".env" (
  echo [4/8] Creating .env from .env.example ...
  copy /Y .env.example .env >nul
  echo       Add API keys in .env for live weather, mandi prices, and AI chat.
) else (
  echo [4/8] .env file found.
)

echo [5/8] Preparing folders...
if not exist "agro\uploads" mkdir agro\uploads
if not exist "agro\ml\models" mkdir agro\ml\models
if not exist "staticfiles" mkdir staticfiles
if not exist "locale\hi\LC_MESSAGES" mkdir locale\hi\LC_MESSAGES

echo [6/8] Database migrations...
python manage.py migrate --noinput
if errorlevel 1 exit /b 1
python manage.py load_schemes 2>nul
python manage.py sync_mandi_prices 2>nul

echo [7/8] Translations and static files...
if exist "scripts\build_translations.py" (
  python scripts\build_translations.py
)
python manage.py compilemessages -l hi -l mr -l te 2>nul
python manage.py collectstatic --noinput

echo [7b/8] Optional TensorFlow disease model...
python scripts\build_disease_model.py 2>nul
if errorlevel 1 (
  echo NOTE: Local TF model not built — use GEMINI_API_KEY for AI disease detection.
)

echo [8/8] Verifying API keys and system check...
python scripts\verify_env.py 2>nul
python manage.py check
if errorlevel 1 (
  echo WARNING: Django check reported issues. Server may still start.
)

echo.
echo ========================================
echo   Ready: http://127.0.0.1:8000/
echo   Register at /register/ then use Dashboard
echo   API status: /api/status/ (when logged in)
echo   Press Ctrl+C to stop the server
echo ========================================
echo.
python manage.py runserver 0.0.0.0:8000

endlocal
