"""Tenant submits meter readings through a private link – no tenant account needed.

The link contains a long random token (like a password). The landlord can reset it at any time,
which makes the old link stop working.
"""

import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import Lease, MeterReading


def first_of_month(day):
    return day.replace(day=1)


def new_link(lease):
    """Create (or replace) the secret link token."""
    lease.readings_token = secrets.token_urlsafe(32)
    lease.save(update_fields=["readings_token"])
    return lease.readings_token


def remove_link(lease):
    lease.readings_token = ""
    lease.save(update_fields=["readings_token"])


def find_lease(token, today=None):
    """The lease for a link, or None if the link is unknown or the lease is not running today."""
    if not token:
        return None
    today = today or timezone.localdate()
    return (
        Lease.objects.filter(readings_token=token, start_date__lte=today, end_date__gte=today)
        .select_related("property__owner", "tenant")
        .first()
    )


def link_url(request, lease):
    return request.build_absolute_uri(reverse("rentals:tenant_readings", args=[lease.readings_token]))


def month_already_billed(lease, period):
    return lease.statements.filter(period=period).exists()


@transaction.atomic
def save_readings(lease, period, values):
    """values: {meter: Decimal}. Overwrites earlier tenant readings for the same month."""
    for meter, value in values.items():
        MeterReading.objects.update_or_create(
            meter=meter, period=period, defaults={"value": value, "submitted_by_tenant": True}
        )


def notify_landlord(lease, period, values, notice_url):
    landlord = lease.property.owner
    with translation.override(landlord.language):
        subject = _("%(tenant)s submitted meter readings – %(property)s") % {
            "tenant": lease.tenant.full_name, "property": lease.property.name,
        }
        body = render_to_string(
            "rentals/email_readings_submitted.txt",
            {"lease": lease, "period": period, "values": values, "notice_url": notice_url},
        )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [landlord.email])


def send_link_to_tenant(lease, url):
    """Email the link to the tenant, in the landlord's language; replies go to the landlord."""
    from django.core.mail import EmailMessage

    landlord = lease.property.owner
    with translation.override(landlord.language):
        subject = _("Submit your meter readings – %(property)s") % {"property": lease.property.name}
        body = render_to_string("rentals/email_readings_link.txt", {"lease": lease, "url": url, "landlord": landlord})
    EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [lease.tenant.email], reply_to=[landlord.email]).send()
