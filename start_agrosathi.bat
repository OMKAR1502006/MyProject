@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title AgroSathi — Smart Farming Platform
color 0A

echo.
echo  ============================================
echo    AgroSathi — One-Click Startup
echo  ============================================
echo.

if not exist "venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  py -3 -m venv venv 2>nul || python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install google-generativeai -q
pip install -r requirements-ml.txt 2>nul

if not exist ".env" (
  echo Creating .env from .env.example...
  copy /Y .env.example .env >nul
  echo.
  echo  IMPORTANT: Edit .env and add:
  echo    GEMINI_API_KEY     - https://aistudio.google.com/apikey
  echo    AGMARKNET_API_KEY  - https://data.gov.in/
  echo.
)

if not exist "agro\uploads" mkdir agro\uploads
if not exist "agro\ml\models" mkdir agro\ml\models
if not exist "staticfiles" mkdir staticfiles

echo Running migrations...
python manage.py migrate --noinput
python manage.py load_schemes 2>nul
python manage.py sync_mandi_prices 2>nul
python scripts\build_translations.py
python manage.py collectstatic --noinput
python scripts\verify_env.py 2>nul
python manage.py check

echo.
echo  Starting server at http://127.0.0.1:8000/
echo  Opening browser...
echo.

start "" "http://127.0.0.1:8000/"
python manage.py runserver 0.0.0.0:8000

endlocal
