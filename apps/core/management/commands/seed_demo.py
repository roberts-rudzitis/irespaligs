"""Create a demo landlord with sample data for local development.

    docker compose run --rm web python manage.py seed_demo

Login: demo@example.lv / demo-parole-2026 (development only).
"""

from datetime import date
from decimal import Decimal

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.rentals.models import FixedCharge, Lease, Meter, MeterReading, Property, Tenant
from apps.statements.models import Payment, Statement
from apps.statements.services import ReadingInput, build_statement

DEMO_EMAIL = "demo@example.lv"
DEMO_PASSWORD = "demo-parole-2026"


class Command(BaseCommand):
    help = "Create a demo landlord with sample properties (DEBUG only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DJANGO_DEBUG=1.")

        User.objects.filter(email=DEMO_EMAIL).delete()  # start fresh each time
        user = User.objects.create_user(DEMO_EMAIL, DEMO_PASSWORD, full_name="Ilze Demo")
        EmailAddress.objects.create(user=user, email=DEMO_EMAIL, verified=True, primary=True)

        imanta = Property.objects.create(owner=user, name="Imantas dzīvoklis", address="Kurzemes prospekts 1-10, Rīga")
        studija = Property.objects.create(owner=user, name="Studija Āgenskalnā", address="Kalnciema iela 2-5, Rīga")
        Property.objects.create(owner=user, name="Garāža", address="Rīga")

        janis = Tenant.objects.create(owner=user, full_name="Jānis Bērziņš", email="janis@example.lv", phone="+371 20000000")
        anna = Tenant.objects.create(owner=user, full_name="Anna Ozola", email="anna@example.lv")

        imanta_lease = Lease.objects.create(
            property=imanta, tenant=janis, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
            monthly_rent=Decimal("450.00"), deposit=Decimal("450.00"), rent_due_day=10,
        )
        cold = Meter.objects.create(property=imanta, kind="cold_water", unit="m³", price_per_unit=Decimal("2.154"))
        hot = Meter.objects.create(property=imanta, kind="hot_water", unit="m³", price_per_unit=Decimal("6.80"))
        power = Meter.objects.create(property=imanta, kind="electricity", unit="kWh", price_per_unit=Decimal("0.2178"))
        FixedCharge.objects.create(property=imanta, label="Apsaimniekošana", amount=Decimal("35.20"))
        FixedCharge.objects.create(property=imanta, label="Atkritumu izvešana", amount=Decimal("6.15"))
        for meter, value in [(cold, "120.400"), (hot, "61.250"), (power, "8450")]:
            MeterReading.objects.create(meter=meter, period=date(2026, 9, 1), value=Decimal(value))

        user.payment_details = "Ilze Demo\nLV00HABA0000000000000 (Swedbank)"
        user.save()
        october = build_statement(
            imanta_lease, date(2026, 10, 1), date(2026, 10, 10),
            [
                ReadingInput(meter=cold, previous=Decimal("120.400"), current=Decimal("124.150")),
                ReadingInput(meter=hot, previous=Decimal("61.250"), current=Decimal("63.100")),
                ReadingInput(meter=power, previous=Decimal("8450"), current=Decimal("8612")),
            ],
        )
        october.status = Statement.Status.SENT
        october.save()
        Payment.objects.create(statement=october, paid_on=date(2026, 10, 9), amount=Decimal("450.00"), note="Pārskaitījums")
        Lease.objects.create(
            property=studija, tenant=anna, start_date=date(2026, 6, 1), end_date=date(2027, 5, 31),
            monthly_rent=Decimal("320.00"), deposit=Decimal("320.00"), rent_due_day=5,
        )
        self.stdout.write(self.style.SUCCESS(f"Demo data created. Log in as {DEMO_EMAIL} / {DEMO_PASSWORD}"))
