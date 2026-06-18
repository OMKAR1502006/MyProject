"""Apply farmer preferred language from profile, session, or cookie."""

from django.conf import settings
from django.utils import translation


class UserLanguageMiddleware:
    """
    Sync language from cookie / profile to session and activate for this request.
    Runs after LocaleMiddleware; ensures cookie changes apply immediately.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        valid = dict(settings.LANGUAGES)
        lang = None

        cookie_lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if cookie_lang and cookie_lang in valid:
            lang = cookie_lang

        session_lang = request.session.get('django_language')
        if not lang and session_lang and session_lang in valid:
            lang = session_lang

        if hasattr(request, 'user') and request.user.is_authenticated and not lang:
            from agro.models import FarmerProfile
            try:
                profile = FarmerProfile.objects.get(user=request.user)
                if profile.preferred_language in valid:
                    lang = profile.preferred_language
            except FarmerProfile.DoesNotExist:
                pass

        if lang:
            request.session['django_language'] = lang
            translation.activate(lang)
            request.LANGUAGE_CODE = lang

        response = self.get_response(request)
        return response
