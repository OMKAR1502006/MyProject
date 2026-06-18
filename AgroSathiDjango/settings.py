"""
Django settings for AgroSathiDjango — Agro Sathi farmer platform.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Always load .env from project root (not cwd) so API keys work from any launch directory
load_dotenv(BASE_DIR / '.env')

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or os.getenv('SECRET_KEY', 'django-insecure-dev-only-change-in-production')
_debug = os.getenv('DJANGO_DEBUG') or os.getenv('DEBUG', 'True')
DEBUG = str(_debug).lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]
if DEBUG and 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

# Application
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'agro',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'agro.middleware.UserLanguageMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'AgroSathiDjango.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'agro' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'agro.context_processors.i18n_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'AgroSathiDjango.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# i18n
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('hi', 'हिन्दी'),
    ('mr', 'मराठी'),
    ('te', 'తెలుగు'),
    ('kn', 'ಕನ್ನಡ'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
LANGUAGE_COOKIE_NAME = 'agro_language'
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365

# Auth redirects
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Static & media
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'agro' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/uploads/'
MEDIA_ROOT = BASE_DIR / 'agro' / 'uploads'

# Sessions & cache (local dev)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'agrosathi-cache',
    }
}

# CSRF
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
    if o.strip()
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# API keys (server-side only)
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')
OPENWEATHER_TIMEOUT = int(os.getenv('OPENWEATHER_TIMEOUT', '8'))
AGMARKNET_API_KEY = os.getenv('AGMARKNET_API_KEY', '')
AGMARKNET_TIMEOUT = int(os.getenv('AGMARKNET_TIMEOUT', '12'))
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
OPENAI_CHAT_MODEL = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
CHAT_API_TIMEOUT = int(os.getenv('CHAT_API_TIMEOUT', '45'))
CHAT_RATE_LIMIT_PER_HOUR = int(os.getenv('CHAT_RATE_LIMIT_PER_HOUR', '30'))

# Optional TensorFlow plant disease model (.keras file)
DISEASE_MODEL_PATH = os.getenv(
    'DISEASE_MODEL_PATH',
    str(BASE_DIR / 'agro' / 'ml' / 'models' / 'plant_disease_mobilenet.keras'),
)

# Error pages
handler404 = 'agro.views.page_not_found'
handler500 = 'agro.views.server_error'
