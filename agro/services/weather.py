"""
OpenWeatherMap integration — server-side proxy only (API key never sent to browser).
"""

import os
from collections import Counter
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _

from .cache_util import cache_get, cache_set
from .i18n_tips import ALERT_LABELS, WEATHER_TIP_KEYS

CACHE_TTL_SECONDS = 600  # 10 minutes

ALERT_THRESHOLDS = {
    'HEAT_C': 38,
    'COLD_C': 5,
    'RAIN_PROB': 0.7,
    'RAIN_MM': 10,
}

OWM_CURRENT_URL = 'https://api.openweathermap.org/data/2.5/weather'
OWM_FORECAST_URL = 'https://api.openweathermap.org/data/2.5/forecast'
OWM_GEO_URL = 'https://api.openweathermap.org/geo/1.0/direct'
ICON_BASE = 'https://openweathermap.org/img/wn'

# Free real weather (no API key) — used when OPENWEATHER_API_KEY is not set
OPEN_METEO_FORECAST = 'https://api.open-meteo.com/v1/forecast'
OPEN_METEO_GEO = 'https://geocoding-api.open-meteo.com/v1/search'

# WMO weather code → (description, OpenWeather-style icon id for img URL)
WMO_WEATHER = {
    0: ('Clear sky', '01d'),
    1: ('Mainly clear', '02d'),
    2: ('Partly cloudy', '03d'),
    3: ('Overcast', '04d'),
    45: ('Fog', '50d'),
    48: ('Depositing rime fog', '50d'),
    51: ('Light drizzle', '09d'),
    53: ('Drizzle', '09d'),
    55: ('Dense drizzle', '09d'),
    61: ('Slight rain', '10d'),
    63: ('Moderate rain', '10d'),
    65: ('Heavy rain', '10d'),
    71: ('Slight snow', '13d'),
    73: ('Moderate snow', '13d'),
    75: ('Heavy snow', '13d'),
    80: ('Rain showers', '09d'),
    81: ('Moderate showers', '09d'),
    82: ('Violent showers', '09d'),
    95: ('Thunderstorm', '11d'),
    96: ('Thunderstorm with hail', '11d'),
    99: ('Thunderstorm with heavy hail', '11d'),
}


def _api_key() -> str | None:
    return os.getenv('OPENWEATHER_API_KEY') or getattr(settings, 'OPENWEATHER_API_KEY', None)


def _timeout() -> int:
    return int(getattr(settings, 'OPENWEATHER_TIMEOUT', 8))


def _request_get(url: str, params: dict) -> requests.Response:
    return requests.get(url, params=params, timeout=_timeout())


def geocode_city(city: str, api_key: str) -> tuple[float, float, str | None]:
    """Resolve city name to lat/lon. Returns (lat, lon, resolved_name)."""
    geo_key = f'geo:{city.lower()}'
    cached = cache_get(geo_key)
    if cached:
        return cached['lat'], cached['lon'], cached.get('name')

    resp = _request_get(OWM_GEO_URL, {'q': city, 'limit': 1, 'appid': api_key})
    if resp.status_code != 200:
        raise WeatherServiceError('Geocoding failed', status=502, details=resp.text)
    data = resp.json()
    if not isinstance(data, list) or not data:
        raise WeatherServiceError('City not found', status=404)

    lat, lon = data[0]['lat'], data[0]['lon']
    name = data[0].get('local_names', {}).get('en') or data[0].get('name')
    cache_set(geo_key, {'lat': lat, 'lon': lon, 'name': name}, CACHE_TTL_SECONDS)
    return lat, lon, name


def _current_rainfall_mm(cur: dict) -> float:
    rain = cur.get('rain') or {}
    return float(rain.get('1h') or rain.get('3h') or 0)


def _parse_current(cur: dict) -> dict:
    main = cur.get('main') or {}
    weather_list = cur.get('weather') or [{}]
    w0 = weather_list[0]
    wind = cur.get('wind') or {}
    icon = w0.get('icon', '01d')
    temp = main.get('temp')

    return {
        'temp': round(temp, 1) if temp is not None else None,
        'temp_c': round(temp, 1) if temp is not None else None,
        'humidity': main.get('humidity'),
        'rainfall_mm': round(_current_rainfall_mm(cur), 1),
        'wind_speed': round(wind.get('speed', 0), 1),
        'wind_speed_ms': round(wind.get('speed', 0), 1),
        'weather': w0.get('description', '').title(),
        'condition': w0.get('main', ''),
        'icon': icon,
        'icon_url': f'{ICON_BASE}/{icon}@2x.png',
        'feels_like': round(main.get('feels_like', temp or 0), 1) if temp else None,
        'pressure': main.get('pressure'),
    }


def _aggregate_forecast(cur: dict, fdata: dict) -> list[dict]:
    """Aggregate 3-hour forecast steps into daily bins (up to 5 days)."""
    bins: dict[str, dict] = {}

    def add_to_bin(dtt: datetime, item: dict):
        day = dtt.date().isoformat()
        if day not in bins:
            bins[day] = {
                'temps_min': [],
                'temps_max': [],
                'pops': [],
                'precip_mm': 0.0,
                'summaries': [],
                'icons': [],
            }
        b = bins[day]
        main = item.get('main') or {}
        if main.get('temp_min') is not None:
            b['temps_min'].append(main['temp_min'])
        if main.get('temp_max') is not None:
            b['temps_max'].append(main['temp_max'])
        b['pops'].append(item.get('pop', 0.0))
        rain = item.get('rain') or {}
        snow = item.get('snow') or {}
        b['precip_mm'] += float(rain.get('3h') or 0) + float(snow.get('3h') or 0)
        w = item.get('weather') or []
        if w:
            b['summaries'].append(w[0].get('main', ''))
            if w[0].get('icon'):
                b['icons'].append(w[0]['icon'])

    try:
        import time as _time
        cur_dt = datetime.fromtimestamp(cur.get('dt', _time.time()), tz=timezone.utc)
        add_to_bin(cur_dt, {
            'main': {
                'temp_min': cur.get('main', {}).get('temp'),
                'temp_max': cur.get('main', {}).get('temp'),
            },
            'pop': 0.0,
            'rain': cur.get('rain') or {},
            'weather': cur.get('weather', []),
        })
    except (TypeError, ValueError, OSError):
        pass

    for item in fdata.get('list', []):
        dt = datetime.fromtimestamp(item.get('dt', 0), tz=timezone.utc)
        add_to_bin(dt, item)

    out = []
    for d in sorted(bins.keys())[:5]:
        b = bins[d]
        tmin = round(min(b['temps_min']), 1) if b['temps_min'] else None
        tmax = round(max(b['temps_max']), 1) if b['temps_max'] else None
        pop = round(max(b['pops']) if b['pops'] else 0.0, 2)
        precip = round(b['precip_mm'], 1)
        summary = Counter(b['summaries']).most_common(1)[0][0] if b['summaries'] else None
        icon = Counter(b['icons']).most_common(1)[0][0] if b['icons'] else '01d'
        out.append({
            'date': d,
            'temp_min': tmin,
            'temp_min_c': tmin,
            'temp_max': tmax,
            'temp_max_c': tmax,
            'rain_probability': pop,
            'precip_mm': precip,
            'summary': summary,
            'weather': summary,
            'icon': icon,
            'icon_url': f'{ICON_BASE}/{icon}@2x.png',
        })
    return out


def _build_alerts(current: dict, forecast: list[dict]) -> list[dict]:
    alerts = []
    tcur = current.get('temp')

    if tcur is not None and tcur >= ALERT_THRESHOLDS['HEAT_C']:
        alerts.append({
            'type': 'danger',
            'title': str(ALERT_LABELS['heat']()),
            'msg': _('Current temperature %(temp)s°C — protect crops from heat stress.') % {'temp': tcur},
        })
    elif tcur is not None and tcur <= ALERT_THRESHOLDS['COLD_C']:
        alerts.append({
            'type': 'warning',
            'title': str(ALERT_LABELS['cold']()),
            'msg': _('Current temperature %(temp)s°C — frost risk for sensitive crops.') % {'temp': tcur},
        })

    if current.get('wind_speed', 0) >= 15:
        alerts.append({
            'type': 'warning',
            'title': str(ALERT_LABELS['high_wind']()),
            'msg': _('Wind speed %(speed)s m/s — secure nets and tall crops.') % {
                'speed': current['wind_speed'],
            },
        })

    for f in forecast:
        day = f.get('date', '')
        if f.get('temp_max_c') and f['temp_max_c'] >= ALERT_THRESHOLDS['HEAT_C']:
            alerts.append({
                'type': 'danger',
                'title': str(ALERT_LABELS['heat']()),
                'msg': _('%(day)s: High %(temp)s°C expected.') % {'day': day, 'temp': f['temp_max_c']},
            })
        if f.get('temp_min_c') and f['temp_min_c'] <= ALERT_THRESHOLDS['COLD_C']:
            alerts.append({
                'type': 'warning',
                'title': str(ALERT_LABELS['frost']()),
                'msg': _('%(day)s: Low %(temp)s°C — frost risk.') % {'day': day, 'temp': f['temp_min_c']},
            })
        if (
            f.get('rain_probability', 0) >= ALERT_THRESHOLDS['RAIN_PROB']
            or f.get('precip_mm', 0) >= ALERT_THRESHOLDS['RAIN_MM']
        ):
            alerts.append({
                'type': 'info',
                'title': str(ALERT_LABELS['rain']()),
                'msg': _(
                    '%(day)s: %(pct)s%% rain chance, %(mm)s mm expected.'
                ) % {
                    'day': day,
                    'pct': int(f['rain_probability'] * 100),
                    'mm': f.get('precip_mm', 0),
                },
            })

    return alerts


def _farming_suggestions(current: dict, forecast: list[dict]) -> list[str]:
    """Rule-based farming tips from weather data (translated via active locale)."""
    tips = []
    temp = current.get('temp')
    humidity = current.get('humidity') or 0
    rain_mm = current.get('rainfall_mm') or 0
    wind = current.get('wind_speed') or 0
    condition = (current.get('condition') or '').lower()

    if temp is not None and temp >= 35:
        tips.append(str(WEATHER_TIP_KEYS['irrigate_early']()))
    elif temp is not None and temp <= 10:
        tips.append(str(WEATHER_TIP_KEYS['delay_transplant']()))

    if humidity > 85 or 'rain' in condition:
        tips.append(str(WEATHER_TIP_KEYS['high_humidity']()))

    if rain_mm > 5:
        tips.append(str(WEATHER_TIP_KEYS['heavy_rain']()))

    max_pop = max((f.get('rain_probability', 0) for f in forecast), default=0)
    if max_pop >= 0.6:
        tips.append(str(WEATHER_TIP_KEYS['rain_harvest']()))

    if wind >= 10:
        tips.append(str(WEATHER_TIP_KEYS['strong_wind']()))

    total_precip = sum(f.get('precip_mm', 0) for f in forecast[:3])
    if total_precip < 2 and temp and temp > 30:
        tips.append(str(WEATHER_TIP_KEYS['dry_hot']()))

    if not tips:
        tips.append(str(WEATHER_TIP_KEYS['favourable']()))

    return tips


class WeatherServiceError(Exception):
    def __init__(self, message: str, status: int = 400, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details


def _wmo_to_weather(code: int) -> tuple[str, str, str]:
    desc, icon = WMO_WEATHER.get(int(code), ('Unknown', '01d'))
    return desc, icon, f'{ICON_BASE}/{icon}@2x.png'


CITY_COORDS = {
    'pune': (18.5204, 73.8567, 'Pune'),
    'mumbai': (19.0760, 72.8777, 'Mumbai'),
    'delhi': (28.6139, 77.2090, 'Delhi'),
    'bengaluru': (12.9716, 77.5946, 'Bengaluru'),
    'bangalore': (12.9716, 77.5946, 'Bengaluru'),
    'hyderabad': (17.3850, 78.4867, 'Hyderabad'),
    'chennai': (13.0827, 80.2707, 'Chennai'),
    'kolkata': (22.5726, 88.3639, 'Kolkata'),
    'nagpur': (21.1458, 79.0882, 'Nagpur'),
    'ahmedabad': (23.0225, 72.5714, 'Ahmedabad'),
    'jaipur': (26.9124, 75.7873, 'Jaipur'),
    'lucknow': (26.8467, 80.9462, 'Lucknow'),
}


def _geocode_open_meteo(city: str) -> tuple[float, float, str]:
    geo_key = f'omgeo:{city.lower().strip()}'
    cached = cache_get(geo_key)
    if cached:
        return cached['lat'], cached['lon'], cached.get('name', city)

    key = city.lower().strip()
    if key in CITY_COORDS:
        lat, lon, name = CITY_COORDS[key]
        cache_set(geo_key, {'lat': lat, 'lon': lon, 'name': name}, CACHE_TTL_SECONDS)
        return lat, lon, name

    try:
        resp = _request_get(OPEN_METEO_GEO, {'name': city, 'count': 1, 'language': 'en', 'format': 'json'})
        if resp.status_code != 200:
            raise WeatherServiceError('City geocoding failed', status=502, details=resp.text)
        data = resp.json()
        results = data.get('results') or []
        if not results:
            raise WeatherServiceError(f'City not found: {city}', status=404)
        r0 = results[0]
        lat, lon = float(r0['latitude']), float(r0['longitude'])
        name = r0.get('name', city)
        cache_set(geo_key, {'lat': lat, 'lon': lon, 'name': name}, CACHE_TTL_SECONDS)
        return lat, lon, name
    except requests.RequestException:
        for k, (lat, lon, name) in CITY_COORDS.items():
            if k in key or key in k:
                cache_set(geo_key, {'lat': lat, 'lon': lon, 'name': name}, CACHE_TTL_SECONDS)
                return lat, lon, name
        raise WeatherServiceError(f'Could not geocode city: {city}', status=502)


def _reverse_geocode_open_meteo(lat: float, lon: float) -> str:
    """Resolve coordinates to a display name."""
    key = f'omrev:{lat:.3f}:{lon:.3f}'
    cached = cache_get(key)
    if cached:
        return cached.get('name', 'Your location')

    try:
        resp = _request_get(
            'https://geocoding-api.open-meteo.com/v1/reverse',
            {'latitude': lat, 'longitude': lon, 'language': 'en', 'format': 'json'},
        )
        if resp.status_code == 200:
            results = resp.json().get('results') or []
            if results:
                r0 = results[0]
                name = r0.get('name', '')
                admin = r0.get('admin1', '')
                label = f'{name}, {admin}'.strip(', ') if admin else name
                if label:
                    cache_set(key, {'name': label}, CACHE_TTL_SECONDS)
                    return label
    except requests.RequestException:
        pass
    return 'Your location'


def _fetch_open_meteo(
    *,
    city: str,
    lat: float,
    lon: float,
    language_code: str,
) -> dict:
    """Real weather from Open-Meteo (free, no API key)."""
    lang = (language_code or 'en').split('-')[0]
    display_city = city.strip() if city else _reverse_geocode_open_meteo(lat, lon)
    today = datetime.now(timezone.utc).date().isoformat()
    cache_key = f'om:{lat:.4f}:{lon:.4f}:{today}:{lang}'
    cached = cache_get(cache_key)
    if cached:
        return cached

    params = {
        'latitude': lat,
        'longitude': lon,
        'current': 'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code',
        'daily': (
            'weather_code,temperature_2m_max,temperature_2m_min,'
            'precipitation_sum,precipitation_probability_max'
        ),
        'timezone': 'auto',
        'forecast_days': 5,
    }
    try:
        resp = _request_get(OPEN_METEO_FORECAST, params)
        if resp.status_code != 200:
            raise WeatherServiceError('Open-Meteo API error', status=502, details=resp.text[:300])
        body = resp.json()
    except requests.Timeout:
        raise WeatherServiceError('Weather service timed out. Try again.', status=504)
    except requests.RequestException as exc:
        if api_key := _api_key():
            return _fetch_openweather(
                city=display_city, lat=lat, lon=lon,
                language_code=language_code, api_key=api_key,
            )
        raise WeatherServiceError('Weather service unavailable', status=502, details=str(exc))

    cur = body.get('current') or {}
    daily = body.get('daily') or {}
    wcode = int(cur.get('weather_code', 0))
    desc, icon, icon_url = _wmo_to_weather(wcode)

    current = {
        'temp': round(float(cur.get('temperature_2m', 0)), 1),
        'temp_c': round(float(cur.get('temperature_2m', 0)), 1),
        'humidity': int(cur.get('relative_humidity_2m', 0)),
        'rainfall_mm': round(float(cur.get('precipitation', 0)), 1),
        'wind_speed': round(float(cur.get('wind_speed_10m', 0)), 1),
        'wind_speed_ms': round(float(cur.get('wind_speed_10m', 0)), 1),
        'weather': desc,
        'condition': desc,
        'icon': icon,
        'icon_url': icon_url,
        'feels_like': round(float(cur.get('temperature_2m', 0)), 1),
        'pressure': None,
    }

    forecast = []
    dates = daily.get('time') or []
    for i, d in enumerate(dates[:5]):
        code = int((daily.get('weather_code') or [0])[i])
        fdesc, ficon, ficon_url = _wmo_to_weather(code)
        tmax = (daily.get('temperature_2m_max') or [None])[i]
        tmin = (daily.get('temperature_2m_min') or [None])[i]
        precip = (daily.get('precipitation_sum') or [0])[i]
        pop = (daily.get('precipitation_probability_max') or [0])[i]
        forecast.append({
            'date': d,
            'temp_min': round(float(tmin), 1) if tmin is not None else None,
            'temp_min_c': round(float(tmin), 1) if tmin is not None else None,
            'temp_max': round(float(tmax), 1) if tmax is not None else None,
            'temp_max_c': round(float(tmax), 1) if tmax is not None else None,
            'rain_probability': round(float(pop) / 100.0, 2) if pop else 0.0,
            'precip_mm': round(float(precip), 1),
            'summary': fdesc,
            'weather': fdesc,
            'icon': ficon,
            'icon_url': ficon_url,
        })

    with translation.override(lang):
        alerts = _build_alerts(current, forecast)
        suggestions = _farming_suggestions(current, forecast)

    result = {
        'source': 'open-meteo',
        'api_note': 'Live data via Open-Meteo (real-time). Optional: OPENWEATHER_API_KEY in .env.',
        'city': display_city,
        'lat': lat,
        'lon': lon,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'current': current,
        'forecast': forecast,
        'alerts': alerts,
        'farming_suggestions': suggestions,
    }
    cache_set(cache_key, result, CACHE_TTL_SECONDS)
    return result


def _fetch_openweather(
    *,
    city: str,
    lat: float,
    lon: float,
    language_code: str,
    api_key: str,
) -> dict:
    """OpenWeatherMap when API key is configured."""
    lang = (language_code or 'en').split('-')[0]
    today = datetime.now(timezone.utc).date().isoformat()
    cache_key = f'owm:{lat:.4f}:{lon:.4f}:{today}:{lang}'
    cached = cache_get(cache_key)
    if cached:
        return cached

    owm_lang = lang if lang in ('en', 'hi') else 'en'
    params = {'lat': lat, 'lon': lon, 'units': 'metric', 'appid': api_key, 'lang': owm_lang}
    try:
        rcur = _request_get(OWM_CURRENT_URL, params)
        if rcur.status_code == 401:
            raise WeatherServiceError('Invalid OpenWeather API key', status=502)
        if rcur.status_code != 200:
            raise WeatherServiceError('Weather API error', status=502, details=rcur.text)
        cur = rcur.json()

        rf = _request_get(OWM_FORECAST_URL, params)
        if rf.status_code != 200:
            raise WeatherServiceError('Forecast API error', status=502, details=rf.text)
        fdata = rf.json()
    except requests.Timeout:
        raise WeatherServiceError('Weather service timed out. Try again.', status=504)
    except requests.RequestException as exc:
        raise WeatherServiceError('Weather service unavailable', status=502, details=str(exc))

    current = _parse_current(cur)
    forecast = _aggregate_forecast(cur, fdata)
    with translation.override(lang):
        alerts = _build_alerts(current, forecast)
        suggestions = _farming_suggestions(current, forecast)

    result = {
        'source': 'openweather',
        'city': city or cur.get('name') or 'Unknown',
        'lat': lat,
        'lon': lon,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'current': current,
        'forecast': forecast,
        'alerts': alerts,
        'farming_suggestions': suggestions,
    }
    cache_set(cache_key, result, CACHE_TTL_SECONDS)
    return result


def fetch_weather(
    *,
    city: str = '',
    lat: float | None = None,
    lon: float | None = None,
    language_code: str = 'en',
) -> dict:
    """
    Fetch current weather + 5-day forecast.
    Uses OpenWeatherMap if OPENWEATHER_API_KEY is set, else Open-Meteo (free, real data).
    """
    api_key = _api_key()
    resolved_city = city.strip() if city else ''

    if resolved_city and (lat is None or lon is None):
        if api_key:
            lat, lon, geo_name = geocode_city(resolved_city, api_key)
            resolved_city = geo_name or resolved_city
        else:
            lat, lon, geo_name = _geocode_open_meteo(resolved_city)
            resolved_city = geo_name or resolved_city

    if lat is None or lon is None:
        if not resolved_city:
            resolved_city = 'Pune'
        if api_key:
            lat, lon, geo_name = geocode_city(resolved_city, api_key)
            resolved_city = geo_name or resolved_city
        else:
            lat, lon, geo_name = _geocode_open_meteo(resolved_city)
            resolved_city = geo_name or resolved_city

    lat, lon = float(lat), float(lon)

    if api_key:
        return _fetch_openweather(
            city=resolved_city,
            lat=lat,
            lon=lon,
            language_code=language_code,
            api_key=api_key,
        )
    return _fetch_open_meteo(
        city=resolved_city,
        lat=lat,
        lon=lon,
        language_code=language_code,
    )
