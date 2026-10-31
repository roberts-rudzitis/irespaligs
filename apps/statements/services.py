"""Business logic for monthly payment notices. Plain functions, easy to test."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.core.money import round_money
from apps.rentals.models import MeterReading

from .models import Statement, StatementLine


class StatementError(Exception):
    """A problem the landlord can fix (shown as a form error)."""


@dataclass
class ReadingInput:
    meter: object  # rentals.Meter
    previous: Decimal
    current: Decimal


def first_of_month(day):
    return day.replace(day=1)


def default_due_date(lease, period, today=None):
    """The lease's rent due day in the billed month; if that's already past, one week from today."""
    today = today or timezone.localdate()
    due = date(period.year, period.month, lease.rent_due_day)
    return due if due >= today else today + timedelta(days=7)


@transaction.atomic
def build_statement(lease, period, due_date, readings):
    """Create a draft payment notice: rent + metered utilities + fixed charges.

    `readings` is a list of ReadingInput, one per active meter.
    Each line is rounded to cents (ROUND_HALF_UP); the total is the sum of the rounded lines,
    so the lines on the PDF always add up to the total shown.
    """
    period = first_of_month(period)
    if Statement.objects.filter(lease=lease, period=period).exists():
        raise StatementError(_("A payment notice for this month already exists."))

    statement = Statement.objects.create(lease=lease, period=period, due_date=due_date)
    lines = [
        StatementLine(
            kind=StatementLine.Kind.RENT,
            description=_("Rent for %(month)s") % {"month": period.strftime("%m.%Y")},
            quantity=Decimal("1"),
            unit_price=lease.monthly_rent,
            amount=round_money(lease.monthly_rent),
        )
    ]

    for reading in readings:
        if reading.current < reading.previous:
            raise StatementError(
                _("%(meter)s: the new reading is lower than the previous one.") % {"meter": reading.meter}
            )
        quantity = reading.current - reading.previous
        lines.append(
            StatementLine(
                kind=StatementLine.Kind.UTILITY,
                description=str(reading.meter),
                prev_reading=reading.previous,
                curr_reading=reading.current,
                quantity=quantity,
                unit=reading.meter.unit,
                unit_price=reading.meter.price_per_unit,
                amount=round_money(quantity * reading.meter.price_per_unit),
            )
        )
        MeterReading.objects.update_or_create(
            meter=reading.meter, period=period, defaults={"value": reading.current}
        )

    for charge in lease.property.fixed_charges.filter(is_active=True):
        lines.append(
            StatementLine(
                kind=StatementLine.Kind.FIXED,
                description=charge.label,
                quantity=Decimal("1"),
                unit_price=charge.amount,
                amount=round_money(charge.amount),
            )
        )

    for position, line in enumerate(lines):
        line.statement = statement
        line.position = position
    StatementLine.objects.bulk_create(lines)

    statement.total = sum((line.amount for line in lines), Decimal("0"))
    statement.save(update_fields=["total"])
    return statement


def render_pdf(statement):
    """The payment notice as PDF bytes, in the landlord's language."""
    from weasyprint import HTML  # imported here: loading it is slow and only needed for PDFs

    landlord = statement.lease.property.owner
    with translation.override(landlord.language):
        html = render_to_string("statements/pdf.html", {"statement": statement, "landlord": landlord})
    return HTML(string=html).write_pdf()


def pdf_filename(statement):
    return f"pazinojums-{statement.number}.pdf"


def send_statement(statement):
    """Email the PDF to the tenant and mark the notice as sent."""
    tenant = statement.lease.tenant
    landlord = statement.lease.property.owner
    if not tenant.email:
        raise StatementError(_("The tenant has no email address. Add it on the tenant's page."))

    with translation.override(landlord.language):
        subject = _("Payment notice for %(month)s – %(property)s") % {
            "month": statement.period.strftime("%m.%Y"),
            "property": statement.lease.property.name,
        }
        body = render_to_string("statements/email.txt", {"statement": statement, "landlord": landlord})

    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[tenant.email],
        reply_to=[landlord.email],  # tenant's reply goes to the landlord, not to us
    )
    message.attach(pdf_filename(statement), render_pdf(statement), "application/pdf")
    message.send()

    statement.status = Statement.Status.SENT
    statement.sent_at = timezone.now()
    statement.save(update_fields=["status", "sent_at"])
