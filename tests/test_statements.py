"""Core slice 2b: meters → monthly payment notice → PDF/email → payments."""

import datetime
from decimal import Decimal

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.rentals.models import FixedCharge, Lease, Meter, MeterReading, Property, Tenant
from apps.statements import services
from apps.statements.models import Payment, Statement

NOV = datetime.date(2026, 11, 1)


@pytest.fixture
def lease(verified_user):
    flat = Property.objects.create(owner=verified_user, name="Imantas dzīvoklis", address="Kurzemes pr. 1-10, Rīga")
    tenant = Tenant.objects.create(owner=verified_user, full_name="Jānis Bērziņš", email="janis@example.lv")
    return Lease.objects.create(
        property=flat, tenant=tenant, start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 12, 31),
        monthly_rent=Decimal("450.00"), rent_due_day=10,
    )


@pytest.fixture
def water(lease):
    return Meter.objects.create(property=lease.property, kind="cold_water", unit="m³", price_per_unit=Decimal("2.15400"))


@pytest.fixture
def landlord_client(client, verified_user):
    client.force_login(verified_user)
    return client


def test_build_statement_rent_utilities_and_fixed_charges(lease, water):
    FixedCharge.objects.create(property=lease.property, label="Apsaimniekošana", amount=Decimal("35.20"))
    FixedCharge.objects.create(property=lease.property, label="Vecā maksa", amount=Decimal("99"), is_active=False)

    statement = services.build_statement(
        lease, NOV, datetime.date(2026, 11, 10),
        [services.ReadingInput(meter=water, previous=Decimal("100.000"), current=Decimal("103.456"))],
    )

    lines = list(statement.lines.all())
    assert [line.kind for line in lines] == ["rent", "utility", "fixed"]
    # 3.456 m³ × 2.154 €/m³ = 7.444224 → 7.44
    assert lines[1].quantity == Decimal("3.456")
    assert lines[1].amount == Decimal("7.44")
    assert statement.total == Decimal("450.00") + Decimal("7.44") + Decimal("35.20")
    assert statement.status == Statement.Status.DRAFT
    assert MeterReading.objects.get(meter=water, period=NOV).value == Decimal("103.456")


def test_line_rounding_is_half_up(lease, water):
    water.price_per_unit = Decimal("0.5")
    water.save()
    # 0.005 m³... use 1.005 × 0.5 = 0.5025 → 0.50; 1.010 × 0.5 = 0.505 → 0.51 (half up)
    statement = services.build_statement(
        lease, NOV, NOV, [services.ReadingInput(meter=water, previous=Decimal("0"), current=Decimal("1.010"))]
    )
    assert statement.lines.get(kind="utility").amount == Decimal("0.51")


def test_old_statement_keeps_its_price_after_tariff_change(lease, water):
    statement = services.build_statement(
        lease, NOV, NOV, [services.ReadingInput(meter=water, previous=Decimal("0"), current=Decimal("10"))]
    )
    water.price_per_unit = Decimal("9.99")
    water.save()
    assert statement.lines.get(kind="utility").unit_price == Decimal("2.15400")


def test_new_reading_lower_than_previous_is_rejected(lease, water):
    with pytest.raises(services.StatementError):
        services.build_statement(
            lease, NOV, NOV, [services.ReadingInput(meter=water, previous=Decimal("100"), current=Decimal("99"))]
        )
    assert not Statement.objects.exists()  # rolled back


def test_only_one_statement_per_month(lease):
    services.build_statement(lease, NOV, NOV, [])
    with pytest.raises(services.StatementError):
        services.build_statement(lease, datetime.date(2026, 11, 15), NOV, [])


def test_create_via_form_prefills_previous_reading(landlord_client, lease, water):
    # The form defaults to the current month, so "previous" = a reading from an earlier month.
    earlier_month = (services.first_of_month(timezone.localdate()) - datetime.timedelta(days=1)).replace(day=1)
    MeterReading.objects.create(meter=water, period=earlier_month, value=Decimal("100"))
    url = reverse("statements:create", args=[lease.pk])
    form = landlord_client.get(url).context["form"]
    assert form.fields[f"prev_{water.pk}"].initial == Decimal("100")

    response = landlord_client.post(url, {
        "period": "11.2026", "due_date": "10.11.2026",
        f"prev_{water.pk}": "100", f"curr_{water.pk}": "105,5",
    })
    statement = Statement.objects.get()
    assert response.url == statement.get_absolute_url()
    assert statement.period == NOV
    assert statement.total == Decimal("450.00") + Decimal("11.85")  # 5.5 × 2.154 = 11.847


def test_pdf_renders(landlord_client, lease, water):
    statement = services.build_statement(lease, NOV, NOV, [])
    response = landlord_client.get(reverse("statements:pdf", args=[statement.pk]))
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_send_emails_pdf_to_tenant_and_marks_sent(landlord_client, lease, verified_user):
    verified_user.payment_details = "LV00HABA0000000000000"
    verified_user.save()
    statement = services.build_statement(lease, NOV, datetime.date(2026, 11, 10), [])
    landlord_client.post(reverse("statements:send", args=[statement.pk]))

    statement.refresh_from_db()
    assert statement.status == Statement.Status.SENT
    message = mail.outbox[0]
    assert message.to == ["janis@example.lv"]
    assert message.reply_to == [verified_user.email]
    assert "450,00" in message.body and "10.11.2026" in message.body
    assert "LV00HABA0000000000000" in message.body
    filename, content, mimetype = message.attachments[0]
    assert mimetype == "application/pdf" and content.startswith(b"%PDF")


def test_send_without_tenant_email_shows_error(landlord_client, lease):
    lease.tenant.email = ""
    lease.tenant.save()
    statement = services.build_statement(lease, NOV, NOV, [])
    landlord_client.post(reverse("statements:send", args=[statement.pk]))
    statement.refresh_from_db()
    assert statement.status == Statement.Status.DRAFT
    assert not mail.outbox


def test_partial_and_full_payments_change_state(landlord_client, lease):
    statement = services.build_statement(lease, NOV, timezone.localdate() + datetime.timedelta(days=5), [])
    statement.status = Statement.Status.SENT
    statement.save()

    landlord_client.post(reverse("statements:payment_add", args=[statement.pk]), {"paid_on": "05.11.2026", "amount": "200,00"})
    assert statement.payment_state == "partly_paid"
    assert statement.balance == Decimal("250.00")

    landlord_client.post(reverse("statements:payment_add", args=[statement.pk]), {"paid_on": "06.11.2026", "amount": "250"})
    assert statement.payment_state == "paid"
    assert not Statement.objects.unpaid().exists()


def test_overdue_notice_shows_on_dashboard(landlord_client, lease):
    statement = services.build_statement(lease, NOV, timezone.localdate() - datetime.timedelta(days=3), [])
    statement.status = Statement.Status.SENT
    statement.save()
    response = landlord_client.get(reverse("dashboard"))
    assert response.context["unpaid"] == [statement]
    assert statement.payment_state == "overdue"
    assert "450,00" in response.content.decode()


def test_negative_payment_rejected(landlord_client, lease):
    statement = services.build_statement(lease, NOV, NOV, [])
    landlord_client.post(reverse("statements:payment_add", args=[statement.pk]), {"paid_on": "05.11.2026", "amount": "-5"})
    assert not Payment.objects.exists()


def test_other_landlord_cannot_see_or_touch_notices(client, lease, water, db):
    statement = services.build_statement(lease, NOV, NOV, [])
    payment = Payment.objects.create(statement=statement, amount=Decimal("1"))
    intruder = User.objects.create_user("zaglis@example.lv", "x")
    client.force_login(intruder)
    assert client.get(reverse("statements:detail", args=[statement.pk])).status_code == 404
    assert client.get(reverse("statements:pdf", args=[statement.pk])).status_code == 404
    assert client.post(reverse("statements:send", args=[statement.pk])).status_code == 404
    assert client.post(reverse("statements:payment_add", args=[statement.pk]), {"amount": "1"}).status_code == 404
    assert client.post(reverse("statements:payment_delete", args=[payment.pk])).status_code == 404
    assert client.get(reverse("statements:create", args=[lease.pk])).status_code == 404
    assert client.get(reverse("rentals:meter_update", args=[water.pk])).status_code == 404
    assert client.get(reverse("rentals:meter_create", args=[lease.property.pk])).status_code == 404
    assert not mail.outbox


def test_add_meter_with_decimal_comma(landlord_client, lease):
    response = landlord_client.post(
        reverse("rentals:meter_create", args=[lease.property.pk]),
        {"kind": "electricity", "unit": "kWh", "price_per_unit": "0,21780", "is_active": "on"},
    )
    assert response.status_code == 302
    assert Meter.objects.get().price_per_unit == Decimal("0.21780")
