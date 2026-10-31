"""Landlord: manage the tenant's readings link. Tenant: the public form behind the link."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.money import format_quantity
from apps.subscriptions.services import can_send_notices

from . import tenant_readings
from .models import Lease


@login_required
@require_POST
def readings_link(request, pk):
    lease = get_object_or_404(Lease.objects.for_owner(request.user).select_related("property", "tenant"), pk=pk)
    if not can_send_notices(request.user):
        messages.info(request, _("The tenant readings link is part of the paid plan."))
        return redirect("billing")

    action = request.POST.get("action")
    if action in ("create", "reset"):
        tenant_readings.new_link(lease)
        messages.success(request, _("New link created. The old link (if any) no longer works."))
    elif action == "remove":
        tenant_readings.remove_link(lease)
        messages.success(request, _("Link removed."))
    elif action == "send" and lease.readings_token:
        if not lease.tenant.email:
            messages.error(request, _("The tenant has no email address. Add it on the tenant's page."))
        else:
            tenant_readings.send_link_to_tenant(lease, tenant_readings.link_url(request, lease))
            messages.success(request, _("Link sent to %(email)s.") % {"email": lease.tenant.email})
    return redirect(lease.property)


class ReadingsForm(forms.Form):
    def __init__(self, *args, meters, period, **kwargs):
        super().__init__(*args, **kwargs)
        self.meters = list(meters)
        for meter in self.meters:
            last = meter.last_reading_before(period)
            this_month = meter.readings.filter(period=period).first()
            field = forms.DecimalField(
                label=f"{meter} ({meter.unit})", max_digits=14, decimal_places=3, min_value=0, localize=True,
                initial=this_month.value if this_month else None,
            )
            field.previous = last.value if last else None
            if last:
                field.help_text = _("Previous reading: %(value)s") % {"value": format_quantity(last.value)}
            self.fields[f"m{meter.pk}"] = field

    def clean(self):
        cleaned = super().clean()
        for meter in self.meters:
            value = cleaned.get(f"m{meter.pk}")
            previous = self.fields[f"m{meter.pk}"].previous
            if value is not None and previous is not None and value < previous:
                self.add_error(f"m{meter.pk}", _("This is lower than the previous reading. Please check the meter."))
        return cleaned

    def values(self):
        return {meter: self.cleaned_data[f"m{meter.pk}"] for meter in self.meters}


def tenant_readings_form(request, token):
    """Public page – anyone with the link can submit readings for this lease only."""
    lease = tenant_readings.find_lease(token)
    if lease is None or not can_send_notices(lease.property.owner):
        return render(request, "rentals/tenant_readings_invalid.html", status=404)

    period = tenant_readings.first_of_month(timezone.localdate())
    meters = lease.property.meters.filter(is_active=True)
    context = {"lease": lease, "period": period}
    if tenant_readings.month_already_billed(lease, period):
        return render(request, "rentals/tenant_readings_done.html", {**context, "already_billed": True})

    form = ReadingsForm(request.POST or None, meters=meters, period=period)
    if request.method == "POST" and form.is_valid():
        values = form.values()
        tenant_readings.save_readings(lease, period, values)
        notice_url = request.build_absolute_uri(reverse("statements:create", args=[lease.pk]))
        tenant_readings.notify_landlord(lease, period, values, notice_url)
        return render(request, "rentals/tenant_readings_done.html", context)
    return render(request, "rentals/tenant_readings_form.html", {**context, "form": form})
