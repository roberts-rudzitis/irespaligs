from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.rentals.models import Lease, Property
from apps.statements.models import Statement

ENDING_SOON_DAYS = 60


def home(request):
    # Placeholder until the landing-page slice; logged-in users go straight to work.
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "pages/home.html")


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
    unpaid = list(
        Statement.objects.for_owner(request.user).unpaid().select_related("lease__property", "lease__tenant").order_by("due_date")
    )
    return render(
        request,
        "pages/dashboard.html",
        {
            "rows": rows,
            "ending_soon": ending_soon,
            "unpaid": unpaid,
            "unpaid_total": sum(n.balance for n in unpaid),
        },
    )
