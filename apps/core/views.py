from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


@require_POST
def set_language(request):
    """Switch UI language: saved on the user (so emails use it too) and in a cookie."""
    lang = request.POST.get("language")
    next_url = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"
    response = HttpResponseRedirect(next_url)
    if lang in dict(settings.LANGUAGES):
        if request.user.is_authenticated:
            request.user.language = lang
            request.user.save(update_fields=["language"])
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang,
            max_age=365 * 24 * 60 * 60,
            samesite="Lax",
            secure=not settings.DEBUG,
        )
    return response
