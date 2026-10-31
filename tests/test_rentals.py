"""Core slice 2a: properties, tenants, leases – and that landlords only see their own data."""

import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.rentals.models import Lease, Property, Tenant


@pytest.fixture
def landlord_client(client, verified_user):
    client.force_login(verified_user)
    return client


@pytest.fixture
def flat(verified_user):
    return Property.objects.create(owner=verified_user, name="Imantas dzīvoklis", address="Rīga")


@pytest.fixture
def tenant(verified_user):
    return Tenant.objects.create(owner=verified_user, full_name="Jānis Bērziņš", email="janis@example.lv")


def make_lease(flat, tenant, start, end, rent="450.00"):
    return Lease.objects.create(property=flat, tenant=tenant, start_date=start, end_date=end, monthly_rent=Decimal(rent))


def test_create_property(landlord_client, verified_user):
    response = landlord_client.post(reverse("rentals:property_create"), {"name": "Studija", "address": "Āgenskalns"})
    assert response.status_code == 302
    assert Property.objects.get().owner == verified_user


def test_create_tenant_with_minimal_data(landlord_client, verified_user):
    response = landlord_client.post(reverse("rentals:tenant_create"), {"full_name": "Anna Ozola"})
    assert response.status_code == 302
    assert Tenant.objects.get().owner == verified_user


def test_create_lease_with_latvian_date_and_decimal_comma(landlord_client, flat, tenant):
    response = landlord_client.post(
        reverse("rentals:lease_create", args=[flat.pk]),
        {
            "tenant": tenant.pk,
            "start_date": "01.11.2026",
            "end_date": "31.10.2027",
            "monthly_rent": "450,50",
            "deposit": "450",
            "rent_due_day": "10",
        },
    )
    assert response.status_code == 302, response.context["form"].errors
    lease = Lease.objects.get()
    assert lease.start_date == datetime.date(2026, 11, 1)
    assert lease.monthly_rent == Decimal("450.50")


def test_lease_end_must_be_after_start(landlord_client, flat, tenant):
    response = landlord_client.post(
        reverse("rentals:lease_create", args=[flat.pk]),
        {"tenant": tenant.pk, "start_date": "01.11.2026", "end_date": "01.10.2026", "monthly_rent": "450", "deposit": "0", "rent_due_day": "10"},
    )
    assert response.status_code == 200
    assert "end_date" in response.context["form"].errors


def test_overlapping_leases_are_rejected(landlord_client, flat, tenant):
    make_lease(flat, tenant, datetime.date(2026, 1, 1), datetime.date(2026, 12, 31))
    response = landlord_client.post(
        reverse("rentals:lease_create", args=[flat.pk]),
        {"tenant": tenant.pk, "start_date": "01.06.2026", "end_date": "31.05.2027", "monthly_rent": "450", "deposit": "0", "rent_due_day": "10"},
    )
    assert response.status_code == 200
    assert Lease.objects.count() == 1


def test_lease_form_only_offers_own_tenants(landlord_client, flat, tenant, db):
    other = User.objects.create_user("cits@example.lv", "x")
    Tenant.objects.create(owner=other, full_name="Svešs Īrnieks")
    response = landlord_client.get(reverse("rentals:lease_create", args=[flat.pk]))
    choices = list(response.context["form"].fields["tenant"].queryset)
    assert choices == [tenant]


def test_dashboard_shows_property_rent_and_ending_soon(landlord_client, flat, tenant):
    today = timezone.localdate()
    make_lease(flat, tenant, today - datetime.timedelta(days=300), today + datetime.timedelta(days=20), rent="1234.5")
    html = landlord_client.get(reverse("dashboard")).content.decode()
    assert "Imantas dzīvoklis" in html
    assert "1\xa0234,50\xa0€" in html
    assert "Jānis Bērziņš" in html
    assert "20" in html  # "in 20 days"


def test_tenant_with_lease_cannot_be_deleted(landlord_client, flat, tenant):
    make_lease(flat, tenant, datetime.date(2026, 1, 1), datetime.date(2026, 12, 31))
    landlord_client.post(reverse("rentals:tenant_delete", args=[tenant.pk]))
    assert Tenant.objects.filter(pk=tenant.pk).exists()


@pytest.mark.parametrize(
    "url_name",
    ["rentals:property_detail", "rentals:property_update", "rentals:property_delete", "rentals:lease_create"],
)
def test_other_landlords_property_is_404(client, flat, url_name, db):
    intruder = User.objects.create_user("zaglis@example.lv", "x")
    client.force_login(intruder)
    kwargs = {"property_pk": flat.pk} if url_name == "rentals:lease_create" else {"pk": flat.pk}
    assert client.get(reverse(url_name, kwargs=kwargs)).status_code == 404


def test_other_landlords_tenant_and_lease_are_404(client, flat, tenant, db):
    lease = make_lease(flat, tenant, datetime.date(2026, 1, 1), datetime.date(2026, 12, 31))
    intruder = User.objects.create_user("zaglis@example.lv", "x")
    client.force_login(intruder)
    assert client.get(reverse("rentals:tenant_update", args=[tenant.pk])).status_code == 404
    assert client.get(reverse("rentals:lease_update", args=[lease.pk])).status_code == 404
    assert client.post(reverse("rentals:lease_delete", args=[lease.pk])).status_code == 404
    assert Lease.objects.filter(pk=lease.pk).exists()


def test_tenant_has_no_personal_code_field():
    field_names = {f.name.lower() for f in Tenant._meta.get_fields()}
    assert not any("personas" in n or "personal_code" in n for n in field_names)
