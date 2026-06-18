"""Print which API keys are configured (no secret values). Run from project root."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / '.env')

KEYS = [
    ('GEMINI_API_KEY', 'AI chat + disease vision'),
    ('AGMARKNET_API_KEY', 'Live mandi prices (data.gov.in)'),
    ('OPENWEATHER_API_KEY', 'Enhanced weather (optional)'),
    ('OPENAI_API_KEY', 'Chat fallback (optional)'),
]


def main():
    print('AgroSathi API configuration:\n')
    for name, desc in KEYS:
        val = os.getenv(name, '')
        status = 'SET' if val.strip() else 'missing'
        print(f'  {name}: {status}  — {desc}')
    print('\nWeather works without keys (Open-Meteo).')
    print('Register free keys at links in .env.example')


if __name__ == '__main__':
    main()
