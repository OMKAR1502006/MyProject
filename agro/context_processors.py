"""Template context for i18n, client-side translations, and navbar."""

from django.conf import settings
from django.urls import resolve, Resolver404
from django.utils import translation

from .i18n_js import get_js_translations


def i18n_context(request):
    lang = translation.get_language() or settings.LANGUAGE_CODE
    lang_key = lang.split('-')[0] if lang else 'en'
    languages = getattr(settings, 'LANGUAGES', [('en', 'English')])

    nav_active = ''
    try:
        match = resolve(request.path_info)
        nav_active = match.url_name or ''
    except Resolver404:
        nav_active = ''

    return {
        'CURRENT_LANGUAGE': lang,
        'CURRENT_LANGUAGE_CODE': lang_key,
        'AVAILABLE_LANGUAGES': languages,
        'js_translations': get_js_translations(),
        'NAV_ACTIVE': nav_active,
    }
