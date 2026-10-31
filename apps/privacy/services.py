"""GDPR: export everything we hold about a landlord, and delete it all."""

import csv
import io
import json
import logging
import zipfile

from django.conf import settings
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.rentals.models import FixedCharge, Lease, Meter, MeterReading, Property, Tenant
from apps.statements.models import Payment, Statement, StatementLine
from apps.subscriptions.providers import stripe_provider

log = logging.getLogger(__name__)

# Never exported: password hash, internal permission flags.
USER_FIELDS = [
    "email", "full_name", "language", "payment_details", "date_joined", "last_login",
    "remind_readings", "remind_overdue", "remind_lease_end", "remind_vid",
]


def _csv(queryset, fields):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(fields)
    for row in queryset.values_list(*fields):
        writer.writerow(row)
    return "﻿" + buffer.getvalue()  # BOM so Excel shows Latvian letters


def export_user_data(user):
    """A ZIP file (bytes) with everything this landlord has stored, as CSV and JSON."""
    tables = {
        "properties.csv": (Property.objects.for_owner(user), ["id", "name", "address", "notes", "created_at"]),
        "tenants.csv": (Tenant.objects.for_owner(user), ["id", "full_name", "email", "phone", "created_at"]),
        "leases.csv": (Lease.objects.for_owner(user), [
            "id", "property_id", "tenant_id", "start_date", "end_date", "monthly_rent", "deposit",
            "rent_due_day", "vid_notified_on",
        ]),
        "meters.csv": (Meter.objects.for_owner(user), ["id", "property_id", "kind", "label", "unit", "price_per_unit", "is_active"]),
        "meter_readings.csv": (MeterReading.objects.for_owner(user), ["id", "meter_id", "period", "value"]),
        "fixed_charges.csv": (FixedCharge.objects.for_owner(user), ["id", "property_id", "label", "amount", "is_active"]),
        "payment_notices.csv": (Statement.objects.for_owner(user), [
            "id", "lease_id", "period", "issue_date", "due_date", "status", "total", "sent_at",
        ]),
        "payment_notice_lines.csv": (
            StatementLine.objects.filter(statement__lease__property__owner=user),
            ["statement_id", "position", "kind", "description", "prev_reading", "curr_reading", "quantity", "unit", "unit_price", "amount"],
        ),
        "payments.csv": (Payment.objects.for_owner(user), ["id", "statement_id", "paid_on", "amount", "note"]),
    }
    account = {field: getattr(user, field) for field in USER_FIELDS}
    subscription = getattr(user, "subscription", None)
    if subscription:
        account["subscription"] = {
            "status": subscription.status, "interval": subscription.interval,
            "trial_ends_at": subscription.trial_ends_at, "current_period_end": subscription.current_period_end,
        }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("account.json", json.dumps(account, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2))
        for filename, (queryset, fields) in tables.items():
            archive.writestr(filename, _csv(queryset, fields))
        archive.writestr("README.txt", _(
            "Your ĪresPalīgs data, exported on %(date)s. CSV files use ';' as separator and open in Excel."
        ) % {"date": timezone.localdate().strftime("%d.%m.%Y")})
    return buffer.getvalue()


def delete_account(user):
    """Delete the landlord and all their data. Also deletes the Stripe customer (cancels any subscription).

    TODO: verify (VERIFY.md G2) – whether we must keep our own billing records (invoices) for accounting;
    Stripe keeps its invoices independently of this deletion.
    """
    email, language = user.email, user.language
    subscription = getattr(user, "subscription", None)
    if subscription and subscription.provider_customer_id and stripe_provider.is_configured():
        try:
            stripe_provider.delete_customer(subscription.provider_customer_id)
        except Exception:  # never block a deletion request because Stripe is unreachable
            log.exception("Could not delete Stripe customer %s – delete it manually", subscription.provider_customer_id)

    with transaction.atomic():
        user.delete()  # cascades to properties, tenants, leases, notices, payments, reminders, subscription

    with translation.override(language):
        send_mail(
            _("Your ĪresPalīgs account has been deleted"),
            _("Your account and all its data have been deleted. Thank you for using ĪresPalīgs."),
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
