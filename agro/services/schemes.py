"""
Government schemes — database-backed with JSON seed fallback.
"""

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / 'data' / 'schemes_india.json'


def _load_json_schemes() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, encoding='utf-8') as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get('schemes', [])
    return []


def _scheme_to_dict(obj) -> dict:
    return {
        'id': obj.scheme_id,
        'title': obj.title,
        'short': obj.short_description,
        'description': obj.description,
        'category': obj.category,
        'states': obj.states if isinstance(obj.states, list) else ['All'],
        'eligibility': obj.eligibility,
        'benefits': obj.benefits,
        'application_steps': obj.application_steps if isinstance(obj.application_steps, list) else [],
        'apply_url': obj.apply_url,
        'last_updated': obj.last_updated,
    }


def get_schemes(
    *,
    category: str = '',
    state: str = '',
    search: str = '',
) -> list[dict]:
    """Return schemes from DB when populated, else from bundled JSON."""
    from agro.models import GovernmentScheme

    qs = GovernmentScheme.objects.filter(is_active=True)
    if qs.exists():
        items = [_scheme_to_dict(s) for s in qs]
    else:
        items = _load_json_schemes()

    category_q = (category or '').strip().lower()
    state_q = (state or '').strip().lower()
    search_q = (search or '').strip().lower()

    if not (category_q or state_q or search_q):
        return items

    filtered = []
    for s in items:
        title = (s.get('title') or '').lower()
        desc = (s.get('description') or s.get('short') or '').lower()
        cat = (s.get('category') or '').lower().replace(' ', '_')
        states = [str(x).lower() for x in (s.get('states') or ['All'])]

        if category_q:
            cat_match = (
                category_q in cat
                or category_q.replace('_', ' ') in cat.replace('_', ' ')
                or category_q in title
            )
            if not cat_match:
                continue

        if state_q and state_q not in states and 'all' not in states:
            if not any(state_q in st or st in state_q for st in states):
                continue

        if search_q and search_q not in title and search_q not in desc:
            continue

        filtered.append(s)

    return filtered


def ensure_schemes_in_db() -> int:
    """Import JSON schemes into GovernmentScheme if table is empty."""
    from agro.models import GovernmentScheme

    if GovernmentScheme.objects.exists():
        return GovernmentScheme.objects.count()

    created = 0
    for row in _load_json_schemes():
        sid = row.get('id') or row.get('scheme_id')
        if not sid:
            continue
        GovernmentScheme.objects.update_or_create(
            scheme_id=sid,
            defaults={
                'title': row.get('title', ''),
                'short_description': row.get('short', ''),
                'description': row.get('description', ''),
                'category': row.get('category', 'general'),
                'states': row.get('states', ['All']),
                'eligibility': row.get('eligibility', ''),
                'benefits': row.get('benefits', ''),
                'application_steps': row.get('application_steps', []),
                'apply_url': row.get('apply_url', ''),
                'last_updated': row.get('last_updated', ''),
                'is_active': True,
            },
        )
        created += 1
    return created
