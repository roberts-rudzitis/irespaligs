"""Numbers for the 3-month success metric (SPEC.md §5). Staff only: /admin/metrics/."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Exists, F, Min, OuterRef
from django.shortcuts import render
from django.utils import timezone

from apps.statements.models import Statement
from apps.subscriptions import plans
from apps.subscriptions.models import Subscription

from .models import User


def _percent(part, whole):
    return round(100 * part / whole) if whole else 0


def collect_metrics(now=None):
    now = now or timezone.now()
    landlords = User.objects.filter(is_staff=False)
    total = landlords.count()

    # Activation: created their first payment notice within 7 days of signing up.
    first_notice = (
        landlords.annotate(first=Min("properties__leases__statements__created_at"))
        .filter(first__isnull=False, first__lte=F("date_joined") + timedelta(days=7))
        .count()
    )
    # Retention: active in the last 30 days (created a notice).
    recent = Statement.objects.filter(lease__property__owner=OuterRef("pk"), created_at__gte=now - timedelta(days=30))
    active_30 = landlords.filter(Exists(recent)).count()

    subs = Subscription.objects.filter(user__is_staff=False)
    paying = subs.filter(status__in=[Subscription.Status.ACTIVE, Subscription.Status.PAST_DUE])
    monthly = paying.filter(interval="month").count()
    yearly = paying.filter(interval="year").count()
    # Monthly recurring revenue, excluding PVN (what the business actually earns)
    mrr = monthly * plans.PRICES["month"].net + yearly * plans.PRICES["year"].net / 12

    return {
        "total": total,
        "new_7_days": landlords.filter(date_joined__gte=now - timedelta(days=7)).count(),
        "in_trial": subs.filter(status=Subscription.Status.TRIALING, trial_ends_at__gt=now).count(),
        "paying": paying.count(),
        "past_due": subs.filter(status=Subscription.Status.PAST_DUE).count(),
        "monthly": monthly,
        "yearly": yearly,
        "mrr_net": Decimal(mrr).quantize(Decimal("0.01")),
        "activated": first_notice,
        "activation_pct": _percent(first_notice, total),
        "active_30": active_30,
        "goal_paying": 30,
    }


@staff_member_required
def metrics_view(request):
    return render(request, "admin/metrics.html", {"m": collect_metrics(), "title": "Metrics"})
