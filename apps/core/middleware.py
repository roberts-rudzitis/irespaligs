from django.conf import settings
from django.utils import translation


def pick_language(request):
    """Logged-in user's saved language → language cookie → Latvian.

    We deliberately ignore the browser's Accept-Language header, so Latvian
    stays the default even on a browser set to English.
    """
    candidates = []
    if request.user.is_authenticated:
        candidates.append(request.user.language)
    candidates.append(request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME))
    available = dict(settings.LANGUAGES)
    for lang in candidates:
        if lang in available:
            return lang
    return settings.LANGUAGE_CODE


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = pick_language(request)
        translation.activate(lang)
        request.LANGUAGE_CODE = lang
        response = self.get_response(request)
        response.headers.setdefault("Content-Language", lang)
        return response
