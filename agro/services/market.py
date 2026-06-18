"""
Mandi / market prices via data.gov.in (Agmarknet-sourced dataset).
API key from AGMARKNET_API_KEY — register at https://data.gov.in/
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import requests
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _

from .cache_util import cache_get, cache_set
from .i18n_tips import MARKET_LABELS

CACHE_TTL_SECONDS = 900  # 15 minutes
MANDI_CACHE_FILE = Path(__file__).resolve().parent.parent / 'data' / 'mandi_live_cache.json'
MANDI_CACHE_MAX_AGE_HOURS = 24

# Agmarknet daily mandi prices on data.gov.in
DATA_GOV_RESOURCE_ID = '9ef84268-d588-465a-a308-a864a43d0070'
DATA_GOV_API_URL = f'https://api.data.gov.in/resource/{DATA_GOV_RESOURCE_ID}'

INDIAN_STATES = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
    'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
    'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
    'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
    'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Chandigarh', 'Puducherry',
]


class MarketServiceError(Exception):
    def __init__(self, message: str, status: int = 400, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details


def _api_key() -> str | None:
    return (
        os.getenv('AGMARKNET_API_KEY')
        or getattr(settings, 'AGMARKNET_API_KEY', None)
        or os.getenv('DATA_GOV_API_KEY')
    )


def _timeout() -> int:
    return int(getattr(settings, 'AGMARKNET_TIMEOUT', 12))


def _load_sample_data() -> list[dict]:
    path = Path(__file__).resolve().parent.parent / 'data' / 'sample_mandi_prices.json'
    if not path.exists():
        return []
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return [_normalize_record(r) for r in data.get('records', [])]


def _load_cached_live_data() -> tuple[list[dict], str | None]:
    """
    Load mandi records previously synced from data.gov.in (via manage.py sync_mandi_prices).
    Used when API key is missing or live API returns empty.
    """
    if not MANDI_CACHE_FILE.exists():
        return [], None
    try:
        with open(MANDI_CACHE_FILE, encoding='utf-8') as f:
            payload = json.load(f)
        fetched_at = payload.get('fetched_at')
        if fetched_at:
            try:
                ts = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
                age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                if age_h > MANDI_CACHE_MAX_AGE_HOURS:
                    return [], None
            except ValueError:
                pass
        records = [_normalize_record(r) for r in payload.get('records', []) if isinstance(r, dict)]
        if records:
            return records, payload.get('source', 'cached_live')
    except (json.JSONDecodeError, OSError):
        pass
    return [], None


def sync_mandi_cache(*, limit: int = 500) -> dict:
    """
    Fetch live mandi data from data.gov.in and persist to mandi_live_cache.json.
    Call from management command or startup when AGMARKNET_API_KEY is set.
    """
    if not _api_key():
        return {'ok': False, 'error': 'AGMARKNET_API_KEY not configured'}

    records, total, api_used = _fetch_from_datagov(
        crop='', state='', district='', market='', limit=limit, offset=0
    )
    if not api_used or not records:
        return {'ok': False, 'error': 'No records returned from API', 'total': total}

    MANDI_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'source': 'data.gov.in (Agmarknet)',
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'total': total,
        'records': records,
    }
    with open(MANDI_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return {'ok': True, 'count': len(records), 'total': total}


def _pick_field(record: dict, *candidates: str):
    lower_map = {str(k).lower().replace(' ', '_'): v for k, v in record.items()}
    for c in candidates:
        key = c.lower().replace(' ', '_')
        if key in lower_map and lower_map[key] not in (None, '', 'NA', 'N/A'):
            return lower_map[key]
    return None


def _to_float(val):
    if val is None:
        return None
    try:
        return float(str(val).replace(',', '').strip())
    except (TypeError, ValueError):
        return None


def _normalize_record(record: dict) -> dict:
    commodity = _pick_field(record, 'commodity', 'crop', 'Commodity')
    market = _pick_field(record, 'market', 'mandi', 'Market')
    district = _pick_field(record, 'district', 'District')
    state = _pick_field(record, 'state', 'State')
    variety = _pick_field(record, 'variety', 'Variety') or ''
    arrival = _pick_field(record, 'arrival_date', 'Arrival_Date', 'date')

    min_p = _to_float(_pick_field(record, 'min_price', 'Min_Price', 'minimum_price'))
    max_p = _to_float(_pick_field(record, 'max_price', 'Max_Price', 'maximum_price'))
    modal = _to_float(_pick_field(record, 'modal_price', 'Modal_Price', 'modal'))

    arrival_str = str(arrival or '').strip()
    return {
        'crop': str(commodity or '').strip(),
        'commodity': str(commodity or '').strip(),
        'market': str(market or '').strip(),
        'district': str(district or '').strip(),
        'state': str(state or '').strip(),
        'variety': str(variety).strip(),
        'arrival_date': arrival_str,
        'updated_at': arrival_str or datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'min_price': min_p,
        'max_price': max_p,
        'modal_price': modal,
    }


def _filter_records(
    records: list[dict],
    *,
    crop: str = '',
    state: str = '',
    district: str = '',
    market: str = '',
) -> list[dict]:
    crop_q = crop.lower().strip()
    state_q = state.lower().strip()
    district_q = district.lower().strip()
    market_q = market.lower().strip()

    out = []
    for r in records:
        if crop_q and crop_q not in (r.get('crop') or '').lower():
            continue
        if state_q and state_q not in (r.get('state') or '').lower():
            continue
        if district_q and district_q not in (r.get('district') or '').lower():
            continue
        if market_q and market_q not in (r.get('market') or '').lower():
            continue
        out.append(r)
    return out


def _demand_label(record: dict) -> str:
    """Simple demand label from price spread (proxy without historical series)."""
    modal = record.get('modal_price') or 0
    min_p = record.get('min_price') or 0
    max_p = record.get('max_price') or 0
    if not modal:
        return str(MARKET_LABELS['stable']())
    spread_pct = ((max_p - min_p) / modal * 100) if modal else 0
    if spread_pct >= 22:
        return str(MARKET_LABELS['high_demand']())
    if spread_pct <= 8:
        return str(MARKET_LABELS['low_demand']())
    return str(MARKET_LABELS['stable']())


def _attach_labels(records: list[dict]) -> list[dict]:
    enriched = []
    for r in records:
        row = dict(r)
        row['demand_label'] = _demand_label(r)
        enriched.append(row)
    return enriched


def build_insights(records: list[dict]) -> dict:
    """Best market, trend text, and selling recommendation."""
    if not records:
        return {
            'best_market': None,
            'best_modal_price': None,
            'price_trend': _('No data available for the selected filters.'),
            'recommendation': None,
            'selling_label': None,
        }

    valid = [r for r in records if r.get('modal_price')]
    if not valid:
        return {
            'best_market': None,
            'best_modal_price': None,
            'price_trend': _('Modal prices not available for this search.'),
            'recommendation': None,
            'selling_label': None,
        }

    best = max(valid, key=lambda x: x['modal_price'])
    modals = [r['modal_price'] for r in valid]
    avg_modal = mean(modals)
    best_market = best.get('market')
    best_modal = best['modal_price']

    premium_pct = ((best_modal - avg_modal) / avg_modal * 100) if avg_modal else 0

    if premium_pct >= 8:
        trend = _(
            '%(crop)s modal prices vary by market. %(market)s has the highest modal '
            'price (₹%(price)s/quintal), about %(pct)s%% above average.'
        ) % {
            'crop': best.get('crop'),
            'market': best_market,
            'price': f'{best_modal:,.0f}',
            'pct': f'{premium_pct:.0f}',
        }
        recommendation = _('Consider selling at %(market)s, %(district)s.') % {
            'market': best_market,
            'district': best.get('district'),
        }
        selling_label = str(MARKET_LABELS['good_selling_time']())
    elif premium_pct >= 3:
        trend = _('Prices are moderately favourable. Average modal ₹%(avg)s/quintal.') % {
            'avg': f'{avg_modal:,.0f}',
        }
        recommendation = _('%(market)s offers a slightly better rate than other mandis.') % {
            'market': best_market,
        }
        selling_label = str(MARKET_LABELS['stable']())
    else:
        trend = _('Prices are similar across mandis — compare transport cost before choosing.')
        recommendation = _('Monitor prices for 2–3 days before bulk sale.')
        selling_label = str(MARKET_LABELS['low_demand']())

    high_label = str(MARKET_LABELS['high_demand']())
    high_count = sum(1 for r in valid if r.get('demand_label') == high_label)
    if high_count >= len(valid) / 2:
        selling_label = str(MARKET_LABELS['good_selling_time']())

    return {
        'best_market': best_market,
        'best_modal_price': best_modal,
        'best_crop': best.get('crop'),
        'best_state': best.get('state'),
        'best_district': best.get('district'),
        'price_trend': trend,
        'recommendation': recommendation,
        'selling_label': selling_label,
        'average_modal': round(avg_modal, 2),
    }


def _fetch_from_datagov(
    *,
    crop: str = '',
    state: str = '',
    district: str = '',
    market: str = '',
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int, bool]:
    api_key = _api_key()
    if not api_key:
        return [], 0, False

    params = {
        'api-key': api_key,
        'format': 'json',
        'limit': min(limit, 100),
        'offset': max(offset, 0),
    }
    if state:
        params['filters[state]'] = _title_case_filter(state)
    if district:
        params['filters[district]'] = _title_case_filter(district)
    if market:
        params['filters[market]'] = _title_case_filter(market)
    if crop:
        params['filters[commodity]'] = crop.strip().title()

    cache_key = f'mandi:{json.dumps(params, sort_keys=True)}'
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(DATA_GOV_API_URL, params=params, timeout=_timeout())
        if resp.status_code == 403:
            raise MarketServiceError(
                'Invalid or unauthorized API key. Register at data.gov.in',
                status=502,
            )
        if resp.status_code != 200:
            raise MarketServiceError(
                'Market price API error',
                status=502,
                details=resp.text[:500],
            )
        body = resp.json()
    except requests.Timeout:
        raise MarketServiceError('Market price service timed out', status=504)
    except requests.RequestException as exc:
        raise MarketServiceError('Market price service unavailable', status=502, details=str(exc))

    raw_records = body.get('records') or body.get('data') or []
    total = int(body.get('total', len(raw_records)) or len(raw_records))
    normalized = [_normalize_record(r) for r in raw_records if isinstance(r, dict)]

    result = (normalized, total, True)
    cache_set(cache_key, result, CACHE_TTL_SECONDS)
    return result


def _title_case_filter(value: str) -> str:
    """data.gov.in filters often expect Title Case state/district names."""
    v = (value or '').strip()
    if not v:
        return v
    return ' '.join(part.capitalize() for part in v.split())


def fetch_market_prices(
    *,
    crop: str = '',
    state: str = '',
    district: str = '',
    market: str = '',
    page: int = 1,
    limit: int = 20,
    language_code: str = 'en',
) -> dict:
    """
    Fetch mandi prices with pagination, insights, and labels.
    Returns only live API or synced cache data — no demo/sample fallback.
    """
    page = max(1, page)
    limit = min(max(limit, 1), 100)
    offset = (page - 1) * limit

    source = 'sample'
    total = 0
    records: list[dict] = []
    api_used = False

    has_key = bool(_api_key())

    try:
        api_records, api_total, api_used = _fetch_from_datagov(
            crop=crop,
            state=state,
            district=district,
            market=market,
            limit=limit,
            offset=offset,
        )
        if api_used and api_records:
            records = api_records
            total = api_total
            source = 'data.gov.in (Agmarknet)'

        # Retry without filters when live API returns empty but key is configured
        if has_key and api_used and not records and (crop or state or district or market):
            api_records, api_total, api_used = _fetch_from_datagov(
                crop='',
                state='',
                district='',
                market='',
                limit=limit * 3,
                offset=0,
            )
            if api_records:
                filtered_live = _filter_records(
                    api_records, crop=crop, state=state, district=district, market=market
                )
                if filtered_live:
                    total = len(filtered_live)
                    records = filtered_live[offset: offset + limit]
                    source = 'data.gov.in (Agmarknet)'
    except MarketServiceError:
        raise

    if not records:
        if has_key:
            # Broad fetch then client-side filter (API filters are strict)
            try:
                api_records, _, api_used = _fetch_from_datagov(
                    crop='',
                    state='',
                    district='',
                    market='',
                    limit=min(500, limit * 10),
                    offset=0,
                )
                if api_used and api_records:
                    filtered_live = _filter_records(
                        api_records, crop=crop, state=state, district=district, market=market
                    )
                    if filtered_live:
                        total = len(filtered_live)
                        records = filtered_live[offset: offset + limit]
                        source = 'data.gov.in (Agmarknet)'
            except MarketServiceError:
                pass

    if not records:
        cached_records, cached_source = _load_cached_live_data()
        if cached_records:
            filtered_cached = _filter_records(
                cached_records, crop=crop, state=state, district=district, market=market
            )
            if filtered_cached or not (crop or state or district or market):
                pool = filtered_cached if filtered_cached else cached_records
                total = len(pool)
                records = pool[offset: offset + limit]
                source = cached_source or 'cached_live (Agmarknet)'

    if not records:
        if has_key and (crop or state or district or market):
            raise MarketServiceError(
                'No live mandi records found for these filters. Try another crop, state, or district.',
                status=404,
            )
        raise MarketServiceError(
            'Live mandi data is not available. Add AGMARKNET_API_KEY to .env (free at https://data.gov.in/) '
            'then run: python manage.py sync_mandi_prices',
            status=503,
        )

    lang = (language_code or 'en').split('-')[0]
    with translation.override(lang):
        records = _attach_labels(records)
        insight_records = records
        insights = build_insights(insight_records)

    return {
        'source': source,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'filters': {
            'crop': crop,
            'state': state,
            'district': district,
            'market': market,
        },
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'has_more': (offset + len(records)) < total,
        },
        'records': records,
        'insights': insights,
        'states': INDIAN_STATES,
        'api_configured': bool(_api_key()),
    }


def records_to_csv(records: list[dict]) -> str:
    """Export records as CSV string."""
    headers = [
        'crop', 'market', 'district', 'state', 'variety',
        'min_price', 'max_price', 'modal_price', 'arrival_date', 'demand_label',
    ]
    lines = [','.join(headers)]
    for r in records:
        lines.append(','.join(
            f'"{str(r.get(h, "")).replace(chr(34), "")}"' for h in headers
        ))
    return '\n'.join(lines)
