#!/usr/bin/env python
"""Quick smoke test for AgroSathi APIs (run: python scripts/smoke_test.py)."""
import json
import os
import sys

import django

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AgroSathiDjango.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client


def main():
    user, _ = User.objects.get_or_create(username='smoke_test_farmer')
    user.set_password('smoke123')
    user.save()

    c = Client()
    assert c.login(username='smoke_test_farmer', password='smoke123'), 'login failed'

    r = c.post(
        '/api/weather/',
        data=json.dumps({'city': 'Pune'}),
        content_type='application/json',
    )
    w = r.json()
    print('weather:', r.status_code, w.get('source'), w.get('current', {}).get('temp'))

    r2 = c.get('/api/schemes/')
    print('schemes:', r2.status_code, r2.json().get('count'))

    r3 = c.get('/api/market-prices/?crop=Wheat&state=Maharashtra')
    print('market:', r3.status_code, r3.json().get('source'))

    r4 = c.post(
        '/api/chat/',
        data=json.dumps({'message': 'when to irrigate wheat?'}),
        content_type='application/json',
    )
    print('chat:', r4.status_code, r4.json().get('provider'))

    r5 = c.get('/disease/')
    html = r5.content.decode()
    print('disease page:', r5.status_code, 'selectPhotoBtn' in html, 'fileInput' in html)

    return 0 if all(x < 400 for x in [r.status_code, r2.status_code, r3.status_code, r4.status_code, r5.status_code]) else 1


if __name__ == '__main__':
    raise SystemExit(main())
