"""GDPR (export / delete) and the staff admin pages."""

import datetime
import io
import json
import zipfile
from decimal import Decimal

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.urls import reverse

from apps.accounts.models import User
from apps.reminders.models import ReminderLog
from apps.rentals.models import Lease, Meter, MeterReading, Property, Tenant
from apps.statements import services as statement_services
from apps.statements.models import Payment, Statement, StatementLine
from apps.subscriptions.models import Subscription
from apps.subscriptions.providers import stripe_provider


@pytest.fixture
def full_account(verified_user):
    """A landlord with one of everything."""
    flat = Property.objects.create(owner=verified_user, name="Imantas dzīvoklis")
    tenant = Tenant.objects.create(owner=verified_user, full_name="Jānis Bērziņš", email="janis@example.lv", phone="+371 2000")
    lease = Lease.objects.create(property=flat, tenant=tenant, start_date=datetime.date(2026, 1, 1),
                                 end_date=datetime.date(2026, 12, 31), monthly_rent=Decimal("450"))
    meter = Meter.objects.create(property=flat, kind="cold_water", unit="m³", price_per_unit=Decimal("2"))
    notice = statement_services.build_statement(
        lease, datetime.date(2026, 10, 1), datetime.date(2026, 10, 10),
        [statement_services.ReadingInput(meter=meter, previous=Decimal("1"), current=Decimal("3"))],
    )
    Payment.objects.create(statement=notice, amount=Decimal("100"))
    ReminderLog.objects.create(user=verified_user, kind="overdue", key=f"statement:{notice.pk}")
    return verified_user


def test_export_contains_all_my_data_and_no_password(client, full_account):
    other = User.objects.create_user("cits@example.lv", "x")
    Tenant.objects.create(owner=other, full_name="Svešs Īrnieks")

    client.force_login(full_account)
    response = client.get(reverse("export_data"))
    assert response["Content-Type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    assert {"account.json", "properties.csv", "tenants.csv", "leases.csv", "meters.csv", "meter_readings.csv",
            "payment_notices.csv", "payment_notice_lines.csv", "payments.csv"} <= names

    account = json.loads(archive.read("account.json"))
    assert account["email"] == full_account.email
    assert "password" not in account
    tenants = archive.read("tenants.csv").decode("utf-8-sig")
    assert "Jānis Bērziņš" in tenants
    assert "Svešs Īrnieks" not in tenants  # never another landlord's data


def test_delete_account_requires_typing_own_email(client, full_account):
    client.force_login(full_account)
    client.post(reverse("delete_account"), {"email": "wrong@example.lv"})
    assert User.objects.filter(pk=full_account.pk).exists()


def test_delete_account_removes_everything(client, full_account):
    other = User.objects.create_user("cits@example.lv", "x")
    other_flat = Property.objects.create(owner=other, name="Cits")
    client.force_login(full_account)
    response = client.post(reverse("delete_account"), {"email": "ILZE@example.lv"})  # case doesn't matter

    assert response.url == reverse("account_deleted")
    assert not User.objects.filter(pk=full_account.pk).exists()
    for model in (Tenant, Lease, Meter, MeterReading, Statement, StatementLine, Payment, ReminderLog, EmailAddress):
        assert not model.objects.exists(), model  # the other landlord has none of these
    assert Property.objects.get() == other_flat  # other landlords untouched
    assert Subscription.objects.filter(user=other).exists()
    assert mail.outbox[-1].to == ["ilze@example.lv"]
    assert "_auth_user_id" not in client.session


def test_delete_account_also_deletes_stripe_customer(client, verified_user, settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    sub = verified_user.subscription
    sub.provider_customer_id = "cus_123"
    sub.save()
    deleted = []
    monkeypatch.setattr(stripe_provider, "delete_customer", deleted.append)
    client.force_login(verified_user)
    client.post(reverse("delete_account"), {"email": verified_user.email})
    assert deleted == ["cus_123"]


def test_delete_account_still_works_if_stripe_is_down(client, verified_user, settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    sub = verified_user.subscription
    sub.provider_customer_id = "cus_123"
    sub.save()

    def broken(_customer_id):
        raise ConnectionError("Stripe unreachable")

    monkeypatch.setattr(stripe_provider, "delete_customer", broken)
    client.force_login(verified_user)
    client.post(reverse("delete_account"), {"email": verified_user.email})
    assert not User.objects.filter(pk=verified_user.pk).exists()


# --- Admin -------------------------------------------------------------------


@pytest.fixture
def staff_client(client, db):
    staff = User.objects.create_superuser("admin@example.lv", "admin-parole-123")
    client.force_login(staff)
    return client


def test_metrics_page_is_staff_only(client, verified_user):
    client.force_login(verified_user)
    response = client.get(reverse("admin_metrics"))
    assert response.status_code == 302  # redirected to admin login


def test_metrics_counts(staff_client, full_account):
    paying = User.objects.create_user("maksa@example.lv", "x")
    Subscription.objects.filter(user=paying).update(status=Subscription.Status.ACTIVE, interval="month")
    response = staff_client.get(reverse("admin_metrics"))
    m = response.context["m"]
    assert m["total"] == 2  # staff not counted
    assert m["paying"] == 1
    assert m["in_trial"] == 1
    assert m["activated"] == 1  # full_account created a notice right after signing up
    assert m["mrr_net"] == Decimal("4.12")


def test_admin_user_list_loads(staff_client, full_account):
    response = staff_client.get(reverse("admin:accounts_user_changelist"))
    assert response.status_code == 200
    assert full_account.email in response.content.decode()
