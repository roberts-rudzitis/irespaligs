import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import plans
from .providers import stripe_provider
from .services import get_subscription

log = logging.getLogger(__name__)


@login_required
def billing(request):
    subscription = get_subscription(request.user)
    if request.GET.get("success"):
        messages.success(request, _("Thank you! Your subscription will be active in a moment."))
    return render(
        request,
        "subscriptions/billing.html",
        {
            "subscription": subscription,
            "prices": plans.PRICES.values(),
            "free": plans.FREE,
            "standard": plans.STANDARD,
            "payments_configured": stripe_provider.is_configured(),
        },
    )


@login_required
@require_POST
def checkout(request):
    interval = request.POST.get("interval")
    if interval not in plans.PRICES or not stripe_provider.is_configured():
        return HttpResponseBadRequest()
    url = stripe_provider.start_checkout(
        request.user,
        interval,
        success_url=request.build_absolute_uri(reverse("billing")) + "?success=1",
        cancel_url=request.build_absolute_uri(reverse("billing")),
    )
    return redirect(url)


@login_required
@require_POST
def manage(request):
    subscription = get_subscription(request.user)
    if not subscription.provider_customer_id:
        return redirect("billing")
    return redirect(stripe_provider.manage_url(request.user, request.build_absolute_uri(reverse("billing"))))


@csrf_exempt  # Stripe can't send our CSRF token; the signature check below protects this endpoint.
@require_POST
def stripe_webhook(request):
    try:
        stripe_provider.handle_webhook(request.body, request.headers)
    except ValueError:
        log.warning("Rejected Stripe webhook with invalid signature")
        return HttpResponseBadRequest("invalid signature")
    return HttpResponse("ok")
