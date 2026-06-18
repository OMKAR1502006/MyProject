import base64
import json
import os
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import FarmerProfileForm, FarmerRegistrationForm
from .models import (
    ChatHistory,
    CropHistory,
    CropWatchlist,
    DiseaseReport,
    FarmerProfile,
    MarketSearchHistory,
    FavoriteScheme,
    YieldPredictionHistory,
)
from .services.chat import ChatServiceError, check_rate_limit
from .services.chatbot import get_chat_reply
from .services.disease import DiseaseServiceError, predict_disease_from_image
from .services.market import MarketServiceError, fetch_market_prices, records_to_csv
from .services.schemes import ensure_schemes_in_db, get_schemes
from .services.weather import WeatherServiceError, fetch_weather


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

def home(request):
    """Modern landing page — available to all users (logged-in farmers can still visit)."""
    ensure_schemes_in_db()
    featured_schemes = get_schemes()[:6]
    return render(request, 'index.html', {'featured_schemes': featured_schemes})


def public_preview(request):
    """
    Public JSON for landing page widgets (weather + sample/live mandi preview).
    No authentication required.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'GET required'}, status=405)

    preview = {'weather': None, 'market': None}

    try:
        preview['weather'] = fetch_weather(city='Pune', language_code='en')
    except WeatherServiceError as exc:
        preview['weather'] = {'error': exc.message}

    try:
        preview['market'] = fetch_market_prices(
            crop='Wheat',
            state='Maharashtra',
            limit=5,
            page=1,
            language_code='en',
        )
    except MarketServiceError as exc:
        preview['market'] = {
            'error': exc.message,
            'records': [],
            'setup_url': 'https://data.gov.in/',
        }

    return JsonResponse(preview)


SUPPORTED_LANGUAGE_CODES = frozenset(code for code, _ in settings.LANGUAGES)


def _sync_user_language(request, lang_code: str):
    """Persist language to session, cookie, and farmer profile."""
    if lang_code not in SUPPORTED_LANGUAGE_CODES:
        return
    request.session['django_language'] = lang_code
    request.session.modified = True
    translation.activate(lang_code)
    if request.user.is_authenticated:
        profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
        if profile.preferred_language != lang_code:
            profile.preferred_language = lang_code
            profile.save(update_fields=['preferred_language'])


@require_POST
def set_language(request):
    """Switch UI language (navbar dropdown)."""
    lang = (request.POST.get('language') or '').strip()
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'

    if lang in SUPPORTED_LANGUAGE_CODES:
        _sync_user_language(request, lang)
        response = redirect(next_url)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang,
            max_age=getattr(settings, 'LANGUAGE_COOKIE_AGE', 31536000),
        )
        return response

    return redirect(next_url)


# ---------------------------------------------------------------------------
# Protected feature pages (login required)
# ---------------------------------------------------------------------------

@login_required(login_url='/login/')
def smart_advisory(request):
    return render(request, 'smart_advisory.html')


@login_required(login_url='/login/')
def disease_detection_page(request):
    return render(request, 'disease_detection.html')


@login_required(login_url='/login/')
def soil_analysis_page(request):
    return render(request, 'soil_analysis.html')


@login_required(login_url='/login/')
def weather_page(request):
    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
    return render(request, 'weather.html', {'profile': profile})


@login_required(login_url='/login/')
def market_page(request):
    watchlist = CropWatchlist.objects.filter(user=request.user)
    recent_searches = MarketSearchHistory.objects.filter(user=request.user)[:8]
    return render(request, 'market_prices.html', {
        'watchlist': watchlist,
        'recent_searches': recent_searches,
    })


@login_required(login_url='/login/')
def chatbot_page(request):
    history = ChatHistory.objects.filter(user=request.user).order_by('-created_at')[:30]
    history = list(reversed(history))
    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
    return render(request, 'chatbot.html', {
        'chat_history': history,
        'profile': profile,
    })


@login_required(login_url='/login/')
def dashboard(request):
    """Farmer dashboard with history summaries."""
    crop_history = CropHistory.objects.filter(user=request.user)[:10]
    disease_reports = DiseaseReport.objects.filter(user=request.user)[:10]
    
    try:
        yield_history = list(YieldPredictionHistory.objects.filter(user=request.user)[:10])
        yield_count = YieldPredictionHistory.objects.filter(user=request.user).count()
    except Exception:
        yield_history = []
        yield_count = 0

    try:
        favorite_schemes_count = FavoriteScheme.objects.filter(user=request.user).count()
    except Exception:
        favorite_schemes_count = 0

    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)

    context = {
        'profile': profile,
        'crop_history': crop_history,
        'disease_reports': disease_reports,
        'yield_history': yield_history,
        'crop_count': CropHistory.objects.filter(user=request.user).count(),
        'disease_count': DiseaseReport.objects.filter(user=request.user).count(),
        'yield_count': yield_count,
        'favorite_schemes_count': favorite_schemes_count,
    }
    return render(request, 'dashboard.html', context)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = FarmerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            try:
                _sync_user_language(request, user.farmer_profile.preferred_language)
            except FarmerProfile.DoesNotExist:
                pass
            messages.success(request, _('Welcome to AgroSathi! Your farmer account is ready.'))
            return redirect('dashboard')
    else:
        form = FarmerRegistrationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            try:
                _sync_user_language(request, user.farmer_profile.preferred_language)
            except FarmerProfile.DoesNotExist:
                pass
            next_url = request.GET.get('next', '/dashboard/')
            return redirect(next_url)
        error = 'Invalid username or password. Please try again.'

    return render(request, 'login.html', {'error': error})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required(login_url='/login/')
def profile_view(request):
    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = FarmerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = FarmerProfileForm(instance=profile)

    crop_history = CropHistory.objects.filter(user=request.user)[:5]
    disease_reports = DiseaseReport.objects.filter(user=request.user)[:5]

    return render(request, 'profile.html', {
        'form': form,
        'profile': profile,
        'crop_history': crop_history,
        'disease_reports': disease_reports,
    })


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@login_required(login_url='/login/')
def schemes_page(request):
    """Government schemes browser page."""
    ensure_schemes_in_db()
    return render(request, 'schemes.html')


@login_required(login_url='/login/')
def schemes(request):
    """Return government schemes from database (seeded from official JSON catalog)."""
    ensure_schemes_in_db()
    items = get_schemes(
        category=(request.GET.get('category') or request.GET.get('ministry') or '').strip(),
        state=(request.GET.get('state') or '').strip(),
        search=(request.GET.get('q') or '').strip(),
    )
    return JsonResponse({'schemes': items, 'count': len(items)})


@login_required(login_url='/login/')
def weather_api(request):
    """
    POST JSON: { "city": "Pune" } OR { "lat": 18.52, "lon": 73.86 }
    Proxies OpenWeatherMap — API key stays on server only.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    city = (payload.get('city') or '').strip()
    lat = payload.get('lat')
    lon = payload.get('lon')

    try:
        if lat is not None and lon is not None:
            lat, lon = float(lat), float(lon)
        else:
            lat, lon = None, None

        lang = (payload.get('language_code') or getattr(request, 'LANGUAGE_CODE', 'en')).split('-')[0]
        if not city and lat is None:
            try:
                profile = request.user.farmer_profile
                city = (profile.district or profile.state or '').strip()
            except FarmerProfile.DoesNotExist:
                pass
        data = fetch_weather(city=city, lat=lat, lon=lon, language_code=lang)
        return JsonResponse(data)
    except WeatherServiceError as exc:
        body = {'error': exc.message}
        if exc.details:
            body['details'] = exc.details
        return JsonResponse(body, status=exc.status)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid latitude or longitude'}, status=400)
    except Exception as exc:
        return JsonResponse({'error': 'Server error', 'details': str(exc)}, status=500)


@login_required(login_url='/login/')
def crop_advisory(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)

    try:
        data = json.loads(request.body)
        soil = data.get('soil', '').lower()
        season = data.get('season', '').lower()
        temp = float(data.get('temp', 25))
        ph = float(data.get('ph', 7))
        rainfall = float(data.get('rainfall', 500))

        crop_db = {
            ('loamy', 'monsoon'): [('Rice', 0.92), ('Maize', 0.85), ('Soybean', 0.78)],
            ('loamy', 'winter'): [('Wheat', 0.94), ('Mustard', 0.80), ('Peas', 0.72)],
            ('loamy', 'summer'): [('Sunflower', 0.88), ('Groundnut', 0.82), ('Mung Bean', 0.70)],
            ('clayey', 'monsoon'): [('Rice', 0.95), ('Jute', 0.80), ('Sugarcane', 0.75)],
            ('clayey', 'winter'): [('Wheat', 0.90), ('Chickpea', 0.78), ('Lentil', 0.72)],
            ('clayey', 'summer'): [('Cotton', 0.85), ('Groundnut', 0.75), ('Sesame', 0.68)],
            ('sandy', 'monsoon'): [('Maize', 0.80), ('Millet', 0.85), ('Groundnut', 0.75)],
            ('sandy', 'winter'): [('Barley', 0.88), ('Mustard', 0.75), ('Chickpea', 0.70)],
            ('sandy', 'summer'): [('Watermelon', 0.85), ('Muskmelon', 0.80), ('Sesame', 0.72)],
            ('black', 'monsoon'): [('Cotton', 0.95), ('Soybean', 0.85), ('Maize', 0.78)],
            ('black', 'winter'): [('Wheat', 0.90), ('Chickpea', 0.88), ('Sorghum', 0.75)],
            ('black', 'summer'): [('Sunflower', 0.85), ('Groundnut', 0.80), ('Mung Bean', 0.72)],
            ('red', 'monsoon'): [('Groundnut', 0.88), ('Rice', 0.80), ('Maize', 0.75)],
            ('red', 'winter'): [('Wheat', 0.85), ('Lentil', 0.78), ('Mustard', 0.72)],
            ('red', 'summer'): [('Groundnut', 0.90), ('Sesame', 0.82), ('Millet', 0.75)],
        }

        key = (soil, season)
        crops = crop_db.get(key, [('Wheat', 0.75), ('Rice', 0.70), ('Maize', 0.65)])

        if ph < 5.5 or ph > 8.0:
            crops = [(c, max(0.1, p - 0.15)) for c, p in crops]

        predictions = [{'crop': c, 'probability': round(p, 2)} for c, p in crops]
        note = (
            f'Based on {soil} soil, {season} season, {temp}°C, '
            f'pH {ph}, {rainfall}mm rainfall.'
        )

        # Persist top crop recommendation for logged-in farmer
        if crops:
            top_crop, top_prob = crops[0]
            CropHistory.objects.create(
                user=request.user,
                crop=top_crop,
                soil_type=soil,
                season=season,
                temperature=temp,
                ph=ph,
                rainfall=rainfall,
                probability=top_prob,
                note=note,
            )

        return JsonResponse({'predictions': predictions, 'note': note})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required(login_url='/login/')
def detect_disease(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)

    try:
        image = request.FILES.get('image')
        if not image:
            return JsonResponse({'error': 'No image uploaded'}, status=400)

        raw = image.read()
        mime = getattr(image, 'content_type', None) or 'image/jpeg'
        result = predict_disease_from_image(raw, mime=mime)

        predictions = result.get('predictions', [])
        top_solution = result.get('top_solution', [])
        top = predictions[0] if predictions else {'disease': result.get('disease', 'Unknown'), 'probability': 0.0}

        report = DiseaseReport.objects.create(
            user=request.user,
            disease=top['disease'],
            confidence=float(top.get('probability', result.get('confidence', 0))),
            image=ContentFile(raw, name=getattr(image, 'name', 'leaf.jpg')),
            treatment='\n'.join(top_solution),
        )

        image_url = None
        if report.image:
            image_url = request.build_absolute_uri(report.image.url)

        return JsonResponse({
            'predictions': predictions,
            'top_solution': top_solution,
            'report_id': report.id,
            'confidence': float(top.get('probability', result.get('confidence', 0))),
            'image_url': image_url,
            'source': result.get('source', 'unknown'),
            'note': result.get('note', ''),
        })
    except DiseaseServiceError as exc:
        return JsonResponse({'error': exc.message}, status=exc.status)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required(login_url='/login/')
def soil_analysis(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)

    try:
        data = json.loads(request.body)
        N = float(data.get('N', 0))
        P = float(data.get('P', 0))
        K = float(data.get('K', 0))
        ph = float(data.get('ph', 7))
        area_ha = float(data.get('area_ha', 1))
        units = data.get('units', 'ppm')
        soil_type = (data.get('soil_type') or 'loamy').strip().lower()
        crop_type = (data.get('crop_type') or 'wheat').strip().lower()

        crop_optimal = {
            'wheat': {'N': 50, 'P': 30, 'K': 80},
            'rice': {'N': 60, 'P': 35, 'K': 70},
            'cotton': {'N': 55, 'P': 25, 'K': 90},
            'sugarcane': {'N': 75, 'P': 40, 'K': 100},
            'maize': {'N': 55, 'P': 28, 'K': 75},
            'soybean': {'N': 40, 'P': 45, 'K': 70},
            'onion': {'N': 45, 'P': 35, 'K': 85},
            'tomato': {'N': 50, 'P': 40, 'K': 90},
        }
        optimal = crop_optimal.get(crop_type, crop_optimal['wheat'])

        soil_adjust = {
            'clayey': {'N': 1.05, 'P': 0.95, 'K': 1.0},
            'sandy': {'N': 0.9, 'P': 1.1, 'K': 1.05},
            'black': {'N': 1.0, 'P': 1.0, 'K': 1.1},
            'red': {'N': 1.0, 'P': 1.05, 'K': 0.95},
            'loamy': {'N': 1.0, 'P': 1.0, 'K': 1.0},
        }
        adj = soil_adjust.get(soil_type, soil_adjust['loamy'])
        optimal = {
            'N': round(optimal['N'] * adj['N'], 1),
            'P': round(optimal['P'] * adj['P'], 1),
            'K': round(optimal['K'] * adj['K'], 1),
        }
        factor = 2.0 if units == 'kg/ha' else 1.0
        nv, pv, kv = N / factor, P / factor, K / factor

        score = sum([
            nv >= optimal['N'],
            pv >= optimal['P'],
            kv >= optimal['K'],
            6.0 <= ph <= 7.5,
        ])

        if score >= 3:
            predicted_class = 'High Fertility'
            probabilities = {'High Fertility': 0.75, 'Medium Fertility': 0.20, 'Low Fertility': 0.05}
        elif score >= 2:
            predicted_class = 'Medium Fertility'
            probabilities = {'High Fertility': 0.20, 'Medium Fertility': 0.65, 'Low Fertility': 0.15}
        else:
            predicted_class = 'Low Fertility'
            probabilities = {'High Fertility': 0.05, 'Medium Fertility': 0.25, 'Low Fertility': 0.70}

        def deficit(val, opt, area):
            d = max(0, opt - val)
            return round(d, 1), round(d * area, 1)

        nd, nd_total = deficit(nv, optimal['N'], area_ha)
        pd_, pd_total = deficit(pv, optimal['P'], area_ha)
        kd, kd_total = deficit(kv, optimal['K'], area_ha)

        deficits = {
            'N': {'deficit_kg_per_ha': nd, 'total': nd_total},
            'P': {'deficit_kg_per_ha': pd_, 'total': pd_total},
            'K': {'deficit_kg_per_ha': kd, 'total': kd_total},
        }

        suggestions = []
        if nd > 0:
            suggestions.append({
                'nutrient': 'Nitrogen',
                'suggest_apply_kg_per_ha': nd,
                'suggest_apply_total_kg_for_area': nd_total,
                'note': 'Apply Urea or DAP',
            })
        if pd_ > 0:
            suggestions.append({
                'nutrient': 'Phosphorus',
                'suggest_apply_kg_per_ha': pd_,
                'suggest_apply_total_kg_for_area': pd_total,
                'note': 'Apply SSP or DAP',
            })
        if kd > 0:
            suggestions.append({
                'nutrient': 'Potassium',
                'suggest_apply_kg_per_ha': kd,
                'suggest_apply_total_kg_for_area': kd_total,
                'note': 'Apply MOP',
            })
        if not suggestions:
            suggestions.append({
                'nutrient': 'All nutrients',
                'suggest_apply_kg_per_ha': 0,
                'suggest_apply_total_kg_for_area': 0,
                'note': 'Soil is well balanced!',
            })

        if ph < 6.0:
            ph_advice = {
                'status': f'Acidic (pH {ph})',
                'advice': 'Apply agricultural lime @ 2-3 tonnes/ha to raise pH.',
            }
        elif ph > 7.5:
            ph_advice = {
                'status': f'Alkaline (pH {ph})',
                'advice': 'Apply gypsum or sulfur to lower pH gradually.',
            }
        else:
            ph_advice = {
                'status': f'Optimal (pH {ph})',
                'advice': 'pH is in the ideal range for most crops.',
            }

        health_score = int(score / 4 * 100)
        if health_score >= 75:
            health_label = 'Good'
            health_summary = (
                f'Soil health is good for {crop_type} on {soil_type} soil. '
                'Maintain organic matter and follow split fertilizer doses.'
            )
        elif health_score >= 50:
            health_label = 'Moderate'
            health_summary = (
                f'Soil needs improvement for {crop_type} on {soil_type} soil. '
                'Apply recommended fertilizers and monitor pH monthly.'
            )
        else:
            health_label = 'Poor'
            health_summary = (
                f'Soil is deficient for {crop_type} on {soil_type} soil. '
                'Prioritize NPK correction and soil testing after one season.'
            )

        return JsonResponse({
            'source': 'Rule-based Analysis',
            'predicted_class': predicted_class,
            'probabilities': probabilities,
            'deficits': deficits,
            'suggestions': suggestions,
            'ph_advice': ph_advice,
            'soil_type': soil_type,
            'crop_type': crop_type,
            'optimal_npk': optimal,
            'soil_health': {
                'score': health_score,
                'label': health_label,
                'summary': health_summary,
            },
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ---------------------------------------------------------------------------
# Market / mandi prices
# ---------------------------------------------------------------------------

def _market_query_params(request) -> dict:
    """Parse search filters from GET or JSON POST body."""
    if request.method == 'POST':
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = request.GET

    return {
        'crop': (payload.get('crop') or '').strip(),
        'state': (payload.get('state') or '').strip(),
        'district': (payload.get('district') or '').strip(),
        'market': (payload.get('market') or '').strip(),
        'page': int(payload.get('page') or 1),
        'limit': int(payload.get('limit') or 20),
    }


@login_required(login_url='/login/')
def market_prices_api(request):
    """
    GET or POST /api/market-prices/
    Query: crop, state, district, market, page, limit
    """
    if request.method not in ('GET', 'POST'):
        return JsonResponse({'error': 'GET or POST required'}, status=405)

    params = _market_query_params(request)

    try:
        lang = getattr(request, 'LANGUAGE_CODE', 'en')
        data = fetch_market_prices(
            crop=params['crop'],
            state=params['state'],
            district=params['district'],
            market=params['market'],
            page=params['page'],
            limit=params['limit'],
            language_code=lang,
        )

        MarketSearchHistory.objects.create(
            user=request.user,
            crop=params['crop'],
            state=params['state'],
            district=params['district'],
            market=params['market'],
            results_count=len(data.get('records', [])),
        )

        watchlist = list(
            CropWatchlist.objects.filter(user=request.user).values('crop', 'state')
        )
        data['watchlist'] = watchlist

        return JsonResponse(data)
    except Exception as exc:
        # Graceful fallback on any error/503 from external Agmarknet API
        from .services.market import (
            _load_sample_data,
            _filter_records,
            _attach_labels,
            build_insights,
            INDIAN_STATES,
        )
        
        # Load sample data
        sample_records = _load_sample_data()
        filtered = _filter_records(
            sample_records,
            crop=params['crop'],
            state=params['state'],
            district=params['district'],
            market=params['market'],
        )
        if not filtered:
            filtered = sample_records

        page = max(1, params['page'])
        limit = min(max(params['limit'], 1), 100)
        offset = (page - 1) * limit
        paginated_records = filtered[offset:offset+limit]

        # Attach labels and insights
        lang = getattr(request, 'LANGUAGE_CODE', 'en').split('-')[0]
        with translation.override(lang):
            paginated_records = _attach_labels(paginated_records)
            insights = build_insights(paginated_records)

        try:
            watchlist = list(
                CropWatchlist.objects.filter(user=request.user).values('crop', 'state')
            )
        except Exception:
            watchlist = []

        fallback_data = {
            "success": True,
            "fallback": True,
            "source": "sample_fallback",
            "filters": params,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(filtered),
                "has_more": (offset + len(paginated_records)) < len(filtered)
            },
            "records": paginated_records,
            "data": paginated_records,
            "insights": insights,
            "watchlist": watchlist,
            "states": INDIAN_STATES,
            "api_configured": False
        }
        return JsonResponse(fallback_data)


@login_required(login_url='/login/')
def market_export_csv(request):
    """Export current search results as CSV (same filters as market API)."""
    params = _market_query_params(request)
    try:
        lang = getattr(request, 'LANGUAGE_CODE', 'en')
        data = fetch_market_prices(
            crop=params['crop'],
            state=params['state'],
            district=params['district'],
            market=params['market'],
            page=1,
            limit=100,
            language_code=lang,
        )
        csv_content = records_to_csv(data.get('records', []))
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        filename = f"mandi_prices_{params['crop'] or 'all'}.csv".replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except MarketServiceError as exc:
        return JsonResponse({'error': exc.message}, status=exc.status)


@login_required(login_url='/login/')
def market_watchlist_api(request):
    """POST {action: add|remove, crop, state?} — manage favorite crops."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    action = (payload.get('action') or 'add').lower()
    crop = (payload.get('crop') or '').strip()
    state = (payload.get('state') or '').strip()

    if not crop:
        return JsonResponse({'error': 'crop is required'}, status=400)

    if action == 'remove':
        CropWatchlist.objects.filter(
            user=request.user, crop__iexact=crop, state=state
        ).delete()
    else:
        CropWatchlist.objects.get_or_create(
            user=request.user,
            crop=crop,
            state=state,
        )

    items = list(CropWatchlist.objects.filter(user=request.user).values('id', 'crop', 'state'))
    return JsonResponse({'watchlist': items})


# ---------------------------------------------------------------------------
# AI Chatbot
# ---------------------------------------------------------------------------

def _farmer_context(user) -> dict:
    profile, _ = FarmerProfile.objects.get_or_create(user=user)
    return {
        'name': user.first_name or user.username,
        'village': profile.village,
        'district': profile.district,
        'state': profile.state,
        'primary_crop': profile.primary_crop,
        'farm_size_acres': profile.farm_size_acres,
    }


def _chat_history_for_api(user, limit: int = 10) -> list[dict]:
    rows = ChatHistory.objects.filter(user=user).order_by('-created_at')[:limit]
    turns = []
    for row in reversed(list(rows)):
        turns.append({'role': 'user', 'content': row.question})
        turns.append({'role': 'assistant', 'content': row.answer})
    return turns


@login_required(login_url='/login/')
def chat_api(request):
    """
    POST /api/chat/
    JSON: { "message": "..." } or multipart with message + optional image
    Uses session language and farmer profile context.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        check_rate_limit(request.user.id)
    except ChatServiceError as exc:
        return JsonResponse({'error': exc.message}, status=exc.status)

    lang = getattr(request, 'LANGUAGE_CODE', 'en')
    if hasattr(request.user, 'farmer_profile'):
        lang = request.user.farmer_profile.preferred_language or lang
    lang = lang.split('-')[0]

    message = ''
    image_bytes = None
    image_mime = 'image/jpeg'
    image_name = 'chat_leaf.jpg'

    if request.content_type and 'multipart' in request.content_type:
        message = (request.POST.get('message') or '').strip()
        uploaded = request.FILES.get('image')
        if uploaded:
            image_bytes = uploaded.read()
            image_mime = getattr(uploaded, 'content_type', None) or image_mime
            image_name = getattr(uploaded, 'name', image_name)
    else:
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        message = (payload.get('message') or '').strip()
        lang = (payload.get('language') or lang).split('-')[0]

    try:
        history = _chat_history_for_api(request.user)
        reply, provider = get_chat_reply(
            message=message,
            language_code=lang,
            farmer_context=_farmer_context(request.user),
            history=history,
            image_bytes=image_bytes,
            image_mime=image_mime,
            use_live_context=True,
        )

        chat_image = None
        if image_bytes:
            chat_image = ContentFile(image_bytes, name=image_name)

        record = ChatHistory.objects.create(
            user=request.user,
            question=message or '[Image question]',
            answer=reply,
            language=lang,
            provider=provider,
            image=chat_image,
        )

        # Get TTS audio
        from .services.voice_cache import get_cached_voice, set_cached_voice
        from .services.tts import generate_tts

        audio_bytes = get_cached_voice(reply, lang)
        if not audio_bytes:
            audio_bytes = generate_tts(reply, lang)
            if audio_bytes:
                set_cached_voice(reply, lang, audio_bytes)

        audio_b64 = base64.b64encode(audio_bytes).decode('ascii') if audio_bytes else None

        return JsonResponse({
            'reply': reply,
            'provider': provider,
            'language': lang,
            'id': record.id,
            'created_at': record.created_at.isoformat(),
            'audio': audio_b64,
        })
    except ChatServiceError as exc:
        return JsonResponse({'error': exc.message}, status=exc.status)
    except Exception as exc:
        return JsonResponse({'error': 'Server error', 'details': str(exc)}, status=500)


@login_required(login_url='/login/')
def chatbot_api(request):
    """POST /api/chatbot/ — same as /api/chat/ with enriched farming context."""
    return chat_api(request)


@login_required(login_url='/login/')
def tts_api(request):
    """POST /api/tts/ — request or generate TTS for a specific text and language."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        payload = json.loads(request.body or '{}')
        text = payload.get('text', '').strip()
        lang = payload.get('language', 'en').strip()
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not text:
        return JsonResponse({'error': 'text is required'}, status=400)

    from .services.voice_cache import get_cached_voice, set_cached_voice
    from .services.tts import generate_tts

    audio_bytes = get_cached_voice(text, lang)
    if not audio_bytes:
        audio_bytes = generate_tts(text, lang)
        if audio_bytes:
            set_cached_voice(text, lang, audio_bytes)

    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
        return JsonResponse({'audio': audio_b64})
    return JsonResponse({'audio': None, 'message': 'Fallback to SpeechSynthesis'})



@login_required(login_url='/login/')
def chat_history_api(request):
    """GET /api/chat/history/ — recent messages for current user."""
    if request.method != 'GET':
        return JsonResponse({'error': 'GET required'}, status=405)

    rows = ChatHistory.objects.filter(user=request.user).order_by('-created_at')[:50]
    data = [
        {
            'id': r.id,
            'question': r.question,
            'answer': r.answer,
            'language': r.language,
            'provider': r.provider,
            'image_url': r.image.url if r.image else None,
            'created_at': r.created_at.isoformat(),
        }
        for r in reversed(list(rows))
    ]
    return JsonResponse({'history': data})


@login_required(login_url='/login/')
def api_status(request):
    """GET /api/status/ — which integrations are configured (no secrets exposed)."""
    import os
    from django.conf import settings as dj_settings

    def configured(name):
        return bool(os.getenv(name) or getattr(dj_settings, name, ''))

    return JsonResponse({
        'openweather': configured('OPENWEATHER_API_KEY'),
        'weather_live': True,
        'weather_note': (
            'OpenWeatherMap' if configured('OPENWEATHER_API_KEY')
            else 'Open-Meteo (no key required)'
        ),
        'agmarknet': configured('AGMARKNET_API_KEY'),
        'market_cache': Path(settings.BASE_DIR / 'agro' / 'data' / 'mandi_live_cache.json').exists(),
        'market_note': (
            'data.gov.in live' if configured('AGMARKNET_API_KEY')
            else 'sample or cached mandi data until AGMARKNET_API_KEY is set'
        ),
        'gemini': configured('GEMINI_API_KEY'),
        'gemini_key_snippet': f"{key[:8]}...{key[-6:]}" if (key := (os.getenv('GEMINI_API_KEY') or getattr(dj_settings, 'GEMINI_API_KEY', ''))) else 'none',
        'openai': configured('OPENAI_API_KEY'),
        'chat_note': (
            'Gemini/OpenAI live' if configured('GEMINI_API_KEY') or configured('OPENAI_API_KEY')
            else 'keyword assistant until GEMINI_API_KEY is set'
        ),
        'twilio': configured('TWILIO_ACCOUNT_SID'),
        'language': getattr(request, 'LANGUAGE_CODE', 'en'),
    })


def page_not_found(request, exception):
    return render(request, '404.html', status=404)


def server_error(request):
    return render(request, '500.html', status=500)


@login_required(login_url='/login/')
def yield_prediction_page(request):
    """Renders the Yield and Profit Prediction form page."""
    try:
        profile = request.user.farmer_profile
    except FarmerProfile.DoesNotExist:
        profile = None
    return render(request, 'yield_prediction.html', {'profile': profile, 'NAV_ACTIVE': 'yield_prediction'})


@login_required(login_url='/login/')
def api_yield_prediction(request):
    """POST /api/yield-prediction/ — Calculates and stores forecast metrics."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    from .services.yield_prediction import calculate_yield_and_profit, get_prediction_recommendations
    try:
        outputs = calculate_yield_and_profit(data)
        recommendations = get_prediction_recommendations(data, outputs)
        outputs['recommendations'] = recommendations
        try:
            from .models import YieldPredictionHistory
            YieldPredictionHistory.objects.create(
                user=request.user,
                crop_type=data.get('crop_type', 'Wheat'),
                farm_size_acres=float(data.get('farm_size', 1.0)),
                soil_type=data.get('soil_type', 'loamy'),
                season=data.get('season', 'winter'),
                rainfall=float(data.get('rainfall', 500)),
                temperature=float(data.get('temperature', 25)),
                seed_cost=float(data.get('seed_cost', 0)),
                fertilizer_cost=float(data.get('fertilizer_cost', 0)),
                labor_cost=float(data.get('labor_cost', 0)),
                expected_yield_tonnes=outputs['expected_yield'],
                estimated_revenue=outputs['estimated_revenue'],
                estimated_expenses=outputs['estimated_expenses'],
                estimated_profit=outputs['estimated_profit'],
                profit_margin_percent=outputs['profit_margin'],
                recommendations=recommendations
            )
        except Exception as db_exc:
            import logging
            logging.getLogger(__name__).warning(f"Database write failed for YieldPredictionHistory: {db_exc}")

        return JsonResponse(outputs)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required(login_url='/login/')
def scheme_eligibility_page(request):
    """Renders the Scheme Eligibility Checker form page."""
    try:
        profile = request.user.farmer_profile
    except FarmerProfile.DoesNotExist:
        profile = None
    return render(request, 'scheme_eligibility.html', {'profile': profile, 'NAV_ACTIVE': 'scheme_eligibility'})


@login_required(login_url='/login/')
def api_scheme_eligibility(request):
    """POST /api/schemes/eligibility/ — Calculates user scheme matches and scores."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    from .services.scheme_matcher import calculate_eligibility_scores
    try:
        results = calculate_eligibility_scores(data)
        
        # Check if each matched scheme is in the user's FavoriteScheme list
        try:
            fav_ids = set(FavoriteScheme.objects.filter(user=request.user).values_list('scheme_id', flat=True))
        except Exception:
            fav_ids = set()
        for r in results:
            r['is_favorite'] = r['scheme_id'] in fav_ids
            
        return JsonResponse({'schemes': results, 'count': len(results)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required(login_url='/login/')
def toggle_favorite_scheme(request):
    """POST /api/schemes/favorite/ — Toggles a scheme as a user favorite."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        payload = json.loads(request.body or '{}')
        scheme_id = payload.get('scheme_id', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not scheme_id:
        return JsonResponse({'error': 'scheme_id is required'}, status=400)

    try:
        fav = FavoriteScheme.objects.filter(user=request.user, scheme_id=scheme_id)
        if fav.exists():
            fav.delete()
            is_favorite = False
        else:
            FavoriteScheme.objects.create(user=request.user, scheme_id=scheme_id)
            is_favorite = True
    except Exception as e:
        return JsonResponse({'error': f'Database error: {e}. Please run migrations.'}, status=503)

    return JsonResponse({'scheme_id': scheme_id, 'is_favorite': is_favorite})


