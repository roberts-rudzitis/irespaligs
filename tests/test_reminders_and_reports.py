"""Core slice 2c: daily reminder digest and year-end summary."""

import datetime
from decimal import Decimal

import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.models import User
from apps.reminders.models import ReminderLog
from apps.reminders.services import send_reminders
from apps.rentals.models import Lease, Property, Tenant
from apps.statements import services
from apps.statements.models import Payment, Statement

D = datetime.date


@pytest.fixture
def lease(verified_user):
    flat = Property.objects.create(owner=verified_user, name="Imantas dzīvoklis")
    tenant = Tenant.objects.create(owner=verified_user, full_name="Jānis Bērziņš", email="janis@example.lv")
    return Lease.objects.create(
        property=flat, tenant=tenant, start_date=D(2026, 1, 1), end_date=D(2026, 12, 31),
        monthly_rent=Decimal("450.00"), vid_notified_on=D(2026, 1, 3),
    )


def sent_notice(lease, period, due):
    notice = services.build_statement(lease, period, due, [])
    notice.status = Statement.Status.SENT
    notice.save()
    return notice


# --- Reminders ---------------------------------------------------------------


def test_overdue_reminder_sent_once(lease):
    sent_notice(lease, D(2026, 10, 1), D(2026, 10, 10))
    assert send_reminders(D(2026, 10, 15)) == 1
    assert "450,00" in mail.outbox[0].body
    assert "Imantas dzīvoklis" in mail.outbox[0].body
    # Next day: nothing new → no email
    assert send_reminders(D(2026, 10, 16)) == 0
    assert len(mail.outbox) == 1


def test_no_overdue_reminder_when_paid(lease):
    notice = sent_notice(lease, D(2026, 10, 1), D(2026, 10, 10))
    Payment.objects.create(statement=notice, amount=Decimal("450.00"))
    assert send_reminders(D(2026, 10, 15)) == 0


def test_lease_end_reminders_at_60_and_30_days(lease):
    send_reminders(D(2026, 11, 1))  # 60 days before 31.12 (also the 1st → readings reminder)
    assert "31.12.2026" in mail.outbox[0].body
    send_reminders(D(2026, 11, 15))  # still in 60-day window, already sent
    assert len(mail.outbox) == 1
    send_reminders(D(2026, 12, 1))  # 30 days before
    assert len(mail.outbox) == 2
    assert ReminderLog.objects.filter(kind__startswith="lease_end").count() == 2


def test_readings_reminder_on_first_of_month_only(lease, verified_user):
    verified_user.remind_lease_end = False
    verified_user.save()
    assert send_reminders(D(2026, 5, 2)) == 0
    assert send_reminders(D(2026, 5, 1)) == 1


def test_vid_reminder_for_new_lease_without_notification(lease):
    lease.vid_notified_on = None
    lease.start_date = D(2026, 10, 25)
    lease.save()
    send_reminders(D(2026, 10, 27))
    assert "VID" in mail.outbox[0].body


def test_reminders_can_be_switched_off(lease, verified_user):
    sent_notice(lease, D(2026, 10, 1), D(2026, 10, 10))
    verified_user.remind_overdue = False
    verified_user.save()
    assert send_reminders(D(2026, 10, 15)) == 0


def test_reminder_email_in_landlords_language(lease, verified_user):
    sent_notice(lease, D(2026, 10, 1), D(2026, 10, 10))
    verified_user.language = "en"
    verified_user.save()
    send_reminders(D(2026, 10, 15))
    assert "has not fully paid" in mail.outbox[0].body


def test_reminders_only_about_own_data(lease, db):
    sent_notice(lease, D(2026, 10, 1), D(2026, 10, 10))
    other = User.objects.create_user("cits@example.lv", "x")
    send_reminders(D(2026, 10, 15))
    assert all(m.to != [other.email] for m in mail.outbox)


def test_management_command_accepts_date(lease):
    sent_notice(lease, D(2026, 10, 1), D(2026, 10, 10))
    call_command("send_reminders", "--date", "15.10.2026")
    assert len(mail.outbox) == 1


# --- Year summary ------------------------------------------------------------


def test_year_summary_totals(client, verified_user, lease):
    notice = sent_notice(lease, D(2026, 10, 1), D(2026, 10, 10))
    Payment.objects.create(statement=notice, paid_on=D(2026, 10, 9), amount=Decimal("450.00"))
    Payment.objects.create(statement=notice, paid_on=D(2027, 1, 2), amount=Decimal("1.00"))  # other year
    services.build_statement(lease, D(2026, 11, 1), D(2026, 11, 10), [])  # draft: not counted

    client.force_login(verified_user)
    response = client.get(reverse("statements:year_summary") + "?year=2026")
    row = response.context["rows"][0]
    assert row.billed_rent == Decimal("450.00")
    assert row.received == Decimal("450.00")
    assert "nevis nodokļu aprēķins" in response.content.decode()  # "not a tax calculation"


def test_year_summary_csv_uses_latvian_number_format(client, verified_user, lease):
    notice = sent_notice(lease, D(2026, 10, 1), D(2026, 10, 10))
    Payment.objects.create(statement=notice, paid_on=D(2026, 10, 9), amount=Decimal("1234.5"))
    client.force_login(verified_user)
    content = client.get(reverse("statements:year_summary_csv") + "?year=2026").content.decode("utf-8-sig")
    assert ";09.10.2026;" in content and "Jānis Bērziņš;Imantas dzīvoklis" in content
    assert "1234,50" in content


def test_year_summary_pdf(client, verified_user, lease):
    client.force_login(verified_user)
    response = client.get(reverse("statements:year_summary_pdf") + "?year=2026")
    assert response.content.startswith(b"%PDF")


def test_year_summary_only_own_properties(client, lease, db):
    intruder = User.objects.create_user("zaglis@example.lv", "x")
    client.force_login(intruder)
    response = client.get(reverse("statements:year_summary") + "?year=2026")
    assert response.context["rows"] == []


def test_vid_reminder_counts_from_signing_date(lease):
    lease.vid_notified_on = None
    lease.signed_on = D(2026, 10, 20)
    lease.start_date = D(2026, 12, 1)  # starts later than signed
    lease.save()
    send_reminders(D(2026, 10, 21))
    assert "20.10.2026" in mail.outbox[0].body
    assert "piecu darbdienu" in mail.outbox[0].body  # "within 5 working days"


# --- Leases signed before 01.05.2021 (Land Register transition, VERIFY.md L2) ----


@pytest.fixture
def old_lease(lease):
    lease.signed_on = D(2020, 9, 1)
    lease.start_date = D(2020, 9, 1)
    lease.end_date = D(2027, 8, 31)
    lease.save()
    return lease


def test_old_unregistered_lease_gets_one_reminder(old_lease):
    send_reminders(D(2026, 11, 2))
    assert "31.12.2026" in mail.outbox[0].body and "zemesgramata.lv" in mail.outbox[0].body
    send_reminders(D(2026, 11, 3))
    assert len(mail.outbox) == 1  # only once


def test_no_old_lease_warning_when_registered_or_after_deadline(old_lease):
    assert send_reminders(D(2027, 1, 5)) == 0  # transition period is over
    old_lease.registered_in_land_register = True
    old_lease.save()
    assert send_reminders(D(2026, 11, 2)) == 0


def test_old_lease_warning_on_dashboard(client, verified_user, old_lease):
    client.force_login(verified_user)
    response = client.get(reverse("dashboard"))
    assert response.context["old_leases"] == [old_lease]


def test_new_lease_gets_no_old_lease_warning(client, verified_user, lease):
    client.force_login(verified_user)
    assert client.get(reverse("dashboard")).context["old_leases"] == []
