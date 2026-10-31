from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.rentals.models import Lease, Property
from apps.rentals.rules import needs_land_register_warning
from apps.statements.models import Statement
from apps.subscriptions import plans

ENDING_SOON_DAYS = 60
COOKIE_NOTICE_COOKIE = "cookie_notice_ok"


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(
        request,
        "pages/home.html",
        {
            "free": plans.FREE,
            "standard": plans.STANDARD,
            "month": plans.PRICES["month"],
            "year": plans.PRICES["year"],
            "trial_days": plans.TRIAL_DAYS,
        },
    )


@login_required
def dashboard(request):
    today = timezone.localdate()
    properties = Property.objects.for_owner(request.user)
    rows = [{"property": p, "lease": p.current_lease(today)} for p in properties]
    ending_soon = (
        Lease.objects.for_owner(request.user)
        .filter(end_date__gte=today, end_date__lte=today + timedelta(days=ENDING_SOON_DAYS))
        .select_related("property", "tenant")
        .order_by("end_date")
    )
    old_leases = [
        lease for lease in Lease.objects.for_owner(request.user).select_related("property", "tenant")
        if needs_land_register_warning(lease, today)
    ]
    unpaid = list(
        Statement.objects.for_owner(request.user).unpaid().select_related("lease__property", "lease__tenant").order_by("due_date")
    )
    return render(
        request,
        "pages/dashboard.html",
        {
            "rows": rows,
            "ending_soon": ending_soon,
            "old_leases": old_leases,
            "unpaid": unpaid,
            "unpaid_total": sum(n.balance for n in unpaid),
        },
    )


def _legal_page(request, name):
    """Long legal texts are written per language (pages/legal/<name>_<lang>.html), not via .po files."""
    lang = request.LANGUAGE_CODE if request.LANGUAGE_CODE in dict(settings.LANGUAGES) else settings.LANGUAGE_CODE
    return render(request, f"pages/legal/{name}_{lang}.html", {"support_email": settings.SUPPORT_EMAIL})


def privacy(request):
    return _legal_page(request, "privacy")


def terms(request):
    return _legal_page(request, "terms")


@require_POST
def cookie_notice_ok(request):
    """Hide the cookie notice. Works without JavaScript (plain form POST)."""
    next_url = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"
    response = HttpResponseRedirect(next_url)
    response.set_cookie(COOKIE_NOTICE_COOKIE, "1", max_age=365 * 24 * 60 * 60, samesite="Lax", secure=not settings.DEBUG)
    return response


def cookie_notice(request):
    """Context processor: show the notice until it's acknowledged."""
    return {"show_cookie_notice": COOKIE_NOTICE_COOKIE not in request.COOKIES}
