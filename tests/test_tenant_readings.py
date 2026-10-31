"""Tenant submits meter readings through a private link (no login)."""

import datetime
from decimal import Decimal

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.rentals import tenant_readings
from apps.rentals.models import Lease, Meter, MeterReading, Property, Tenant
from apps.statements import services as statement_services
from apps.subscriptions.models import Subscription


@pytest.fixture
def lease(verified_user):
    today = timezone.localdate()
    flat = Property.objects.create(owner=verified_user, name="Imantas dzīvoklis")
    tenant = Tenant.objects.create(owner=verified_user, full_name="Jānis Bērziņš", email="janis@example.lv")
    return Lease.objects.create(property=flat, tenant=tenant, start_date=today - datetime.timedelta(days=100),
                                end_date=today + datetime.timedelta(days=200), monthly_rent=Decimal("450"))


@pytest.fixture
def water(lease):
    meter = Meter.objects.create(property=lease.property, kind="cold_water", unit="m³", price_per_unit=Decimal("2"))
    last_month = (timezone.localdate().replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    MeterReading.objects.create(meter=meter, period=last_month, value=Decimal("100"))
    return meter


@pytest.fixture
def link(lease):
    return reverse("rentals:tenant_readings", args=[tenant_readings.new_link(lease)])


def test_landlord_creates_and_sends_link(client, verified_user, lease):
    client.force_login(verified_user)
    client.post(reverse("rentals:lease_readings_link", args=[lease.pk]), {"action": "create"})
    lease.refresh_from_db()
    assert len(lease.readings_token) >= 40
    client.post(reverse("rentals:lease_readings_link", args=[lease.pk]), {"action": "send"})
    assert mail.outbox[0].to == ["janis@example.lv"]
    assert lease.readings_token in mail.outbox[0].body
    assert mail.outbox[0].reply_to == [verified_user.email]


def test_property_page_shows_the_link(client, verified_user, lease, link):
    client.force_login(verified_user)
    html = client.get(lease.property.get_absolute_url()).content.decode()
    assert link in html


def test_tenant_submits_readings_without_login(client, lease, water, link):
    page = client.get(link)
    assert page.status_code == 200 and "Imantas dzīvoklis" in page.content.decode()

    response = client.post(link, {f"m{water.pk}": "103,5"})
    assert response.status_code == 200
    reading = MeterReading.objects.get(meter=water, period=timezone.localdate().replace(day=1))
    assert reading.value == Decimal("103.5") and reading.submitted_by_tenant
    assert "103,5" in mail.outbox[0].body  # landlord notified
    assert mail.outbox[0].to == [lease.property.owner.email]


def test_notice_form_is_prefilled_with_tenant_reading(client, verified_user, lease, water, link):
    client.post(link, {f"m{water.pk}": "103,5"})
    client.force_login(verified_user)
    form = client.get(reverse("statements:create", args=[lease.pk])).context["form"]
    assert form.fields[f"curr_{water.pk}"].initial == Decimal("103.5")
    assert form.fields[f"prev_{water.pk}"].initial == Decimal("100")


def test_reading_lower_than_previous_is_rejected(client, water, link):
    response = client.post(link, {f"m{water.pk}": "99"})
    assert response.context["form"].errors
    assert not MeterReading.objects.filter(value=Decimal("99")).exists()


def test_reset_link_makes_old_one_invalid(client, verified_user, lease, link):
    client.force_login(verified_user)
    client.post(reverse("rentals:lease_readings_link", args=[lease.pk]), {"action": "reset"})
    client.logout()
    assert client.get(link).status_code == 404


def test_unknown_or_ended_lease_link_is_invalid(client, lease, link):
    assert client.get(reverse("rentals:tenant_readings", args=["guess"])).status_code == 404
    lease.end_date = timezone.localdate() - datetime.timedelta(days=1)
    lease.start_date = lease.end_date - datetime.timedelta(days=300)
    lease.save()
    assert client.get(link).status_code == 404


def test_month_already_billed_blocks_changes(client, lease, water, link):
    statement_services.build_statement(lease, timezone.localdate().replace(day=1), timezone.localdate(), [])
    response = client.get(link)
    assert "form" not in response.context


def test_link_needs_paid_plan(client, verified_user, lease, link):
    Subscription.objects.filter(user=verified_user).update(status=Subscription.Status.NONE, trial_ends_at=None)
    assert client.get(link).status_code == 404
    client.force_login(verified_user)
    response = client.post(reverse("rentals:lease_readings_link", args=[lease.pk]), {"action": "reset"})
    assert response.url == reverse("billing")


def test_other_landlord_cannot_manage_link(client, lease, db):
    intruder = User.objects.create_user("zaglis@example.lv", "x")
    client.force_login(intruder)
    assert client.post(reverse("rentals:lease_readings_link", args=[lease.pk]), {"action": "create"}).status_code == 404


def test_tenant_page_does_not_leak_referrer(client, link):
    assert 'name="referrer" content="no-referrer"' in client.get(link).content.decode()
