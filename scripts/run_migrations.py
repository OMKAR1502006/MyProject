"""
Helper script to run Django checks and migrations internally.
Run from project root: python scripts/run_migrations.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Set up Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AgroSathiDjango.settings')

import django
from django.core.management import call_command

def main():
    print("=== Running Django System Check and Migrations ===")
    
    # Initialize Django
    django.setup()
    
    # 1. Run system checks
    print("\nRunning 'python manage.py check'...")
    try:
        call_command('check')
        print("[OK] System check passed!")
    except Exception as exc:
        print(f"[ERROR] System check failed: {exc}")
        sys.exit(1)
        
    # 2. Run makemigrations
    print("\nRunning 'python manage.py makemigrations'...")
    try:
        call_command('makemigrations')
        print("[OK] makemigrations executed successfully!")
    except Exception as exc:
        print(f"[ERROR] makemigrations failed: {exc}")
        sys.exit(1)
        
    # 3. Run migrate
    print("\nRunning 'python manage.py migrate'...")
    try:
        call_command('migrate')
        print("[OK] migrate executed successfully! Database is up to date.")
    except Exception as exc:
        print(f"[ERROR] migrate failed: {exc}")
        sys.exit(1)

if __name__ == '__main__':
    main()
