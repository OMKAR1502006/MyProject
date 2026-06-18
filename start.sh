#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo "  AgroSathi Django - One-Click Startup"
echo "========================================"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" &>/dev/null; then
  PYTHON=python
fi

if [ ! -d "venv" ]; then
  echo "[1/8] Creating virtual environment..."
  "$PYTHON" -m venv venv
else
  echo "[1/8] Virtual environment found."
fi

# shellcheck source=/dev/null
source venv/bin/activate

echo "[2/8] Installing core dependencies..."
python -m pip install --upgrade pip -q
pip install -r requirements.txt

echo "[3/8] Installing optional ML packages..."
pip install -r requirements-ml.txt 2>/dev/null || echo "NOTE: ML packages skipped — use GEMINI_API_KEY for disease AI."

if [ ! -f ".env" ]; then
  echo "[4/8] Creating .env from .env.example ..."
  cp .env.example .env
  echo "      Add API keys in .env for live data."
else
  echo "[4/8] .env file found."
fi

echo "[5/8] Preparing folders..."
mkdir -p agro/uploads agro/ml/models staticfiles locale/hi/LC_MESSAGES

echo "[6/8] Database migrations..."
python manage.py migrate --noinput
python manage.py load_schemes 2>/dev/null || true
python manage.py sync_mandi_prices 2>/dev/null || true

echo "[7/8] Static files and translations..."
python manage.py compilemessages -l hi -l mr -l te 2>/dev/null || true
python scripts/build_translations.py
python manage.py collectstatic --noinput
[ -f scripts/build_translations.py ] && python scripts/build_translations.py

echo "[7b/8] Optional TensorFlow disease model..."
python scripts/build_disease_model.py 2>/dev/null || echo "NOTE: TF model skipped — use GEMINI_API_KEY for disease AI."

echo "[8/8] System check..."
python manage.py check || echo "WARNING: check reported issues."

echo ""
echo "========================================"
echo "  Ready: http://127.0.0.1:8000/"
echo "  Register at /register/"
echo "  Press Ctrl+C to stop"
echo "========================================"
echo ""
exec python manage.py runserver 0.0.0.0:8000
