"""Daily email reminders. Run once a day by cron: `python manage.py send_reminders`.

Each rule returns (kind, key, text) items. Items already in ReminderLog are skipped.
A landlord gets at most one digest email per day.
"""

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.core.money import format_eur
from apps.rentals.models import Lease
from apps.statements.models import Statement

from .models import ReminderLog

# How many days after a lease starts we keep reminding about the VID notification check.
VID_REMINDER_WINDOW_DAYS = 14


def _date(d):
    return d.strftime("%d.%m.%Y")


def reading_items(user, today):
    """1st of the month: time to enter meter readings and create notices."""
    if today.day != 1:
        return []
    active = Lease.objects.for_owner(user).filter(start_date__lte=today, end_date__gte=today).count()
    if not active:
        return []
    text = _("It's a new month – enter meter readings and create payment notices for your %(count)s active lease(s).") % {"count": active}
    return [("readings", f"month:{today:%Y-%m}", text)]


def overdue_items(user, today):
    items = []
    for notice in Statement.objects.for_owner(user).unpaid().filter(due_date__lt=today).select_related("lease__property", "lease__tenant"):
        text = _("%(property)s: %(tenant)s has not fully paid the notice for %(month)s (due %(due)s). Still to pay: %(balance)s.") % {
            "property": notice.lease.property.name,
            "tenant": notice.lease.tenant.full_name,
            "month": notice.period.strftime("%m.%Y"),
            "due": _date(notice.due_date),
            "balance": format_eur(notice.balance),
        }
        items.append(("overdue", f"statement:{notice.pk}", text))
    return items


def lease_end_items(user, today):
    items = []
    leases = Lease.objects.for_owner(user).filter(end_date__gte=today, end_date__lte=today + timedelta(days=60))
    for lease in leases.select_related("property", "tenant"):
        days = (lease.end_date - today).days
        kind = "lease_end_30" if days <= 30 else "lease_end_60"
        text = _("%(property)s: the lease with %(tenant)s ends on %(date)s (in %(days)s days). Time to agree on an extension or a new tenant.") % {
            "property": lease.property.name, "tenant": lease.tenant.full_name, "date": _date(lease.end_date), "days": days,
        }
        items.append((kind, f"lease:{lease.pk}", text))
    return items


def vid_items(user, today):
    """New leases without a recorded VID notification.

    TODO: verify (VERIFY.md V2) – whether/when VID must be notified (reported: within 5 working days
    of signing, for the 10 percent regime). The text deliberately says "check", not "you must".
    """
    items = []
    leases = Lease.objects.for_owner(user).filter(
        vid_notified_on__isnull=True,
        start_date__lte=today,
        start_date__gte=today - timedelta(days=VID_REMINDER_WINDOW_DAYS),
    )
    for lease in leases.select_related("property", "tenant"):
        text = _("%(property)s: a new lease with %(tenant)s started on %(date)s. Check whether you need to notify VID (e.g. if you use the 10 percent rental income tax) – see vid.gov.lv. Record the date on the lease when done.") % {
            "property": lease.property.name, "tenant": lease.tenant.full_name, "date": _date(lease.start_date),
        }
        items.append(("vid", f"lease:{lease.pk}", text))
    return items


RULES = [
    ("remind_readings", reading_items),
    ("remind_overdue", overdue_items),
    ("remind_lease_end", lease_end_items),
    ("remind_vid", vid_items),
]


def collect_items(user, today):
    """All reminders due for this landlord today that were not sent before."""
    already_sent = set(ReminderLog.objects.filter(user=user).values_list("kind", "key"))
    items = []
    with translation.override(user.language):
        for setting_name, rule in RULES:
            if getattr(user, setting_name):
                items += [item for item in rule(user, today) if (item[0], item[1]) not in already_sent]
    return items


def send_reminders(today):
    """Send one digest email per landlord. Returns the number of emails sent."""
    sent = 0
    for user in User.objects.filter(is_active=True):
        items = collect_items(user, today)
        if not items:
            continue
        with translation.override(user.language):
            subject = _("ĪresPalīgs reminders for %(date)s") % {"date": _date(today)}
            body = render_to_string("reminders/digest.txt", {"user": user, "items": [text for _k, _key, text in items]})
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
        ReminderLog.objects.bulk_create(
            [ReminderLog(user=user, kind=kind, key=key) for kind, key, _text in items], ignore_conflicts=True
        )
        sent += 1
    return sent
