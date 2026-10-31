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
from apps.rentals.models import Lease, Property, Tenant

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

        Lease.objects.create(
            property=imanta, tenant=janis, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
            monthly_rent=Decimal("450.00"), deposit=Decimal("450.00"), rent_due_day=10,
        )
        Lease.objects.create(
            property=studija, tenant=anna, start_date=date(2026, 6, 1), end_date=date(2027, 5, 31),
            monthly_rent=Decimal("320.00"), deposit=Decimal("320.00"), rent_due_day=5,
        )
        self.stdout.write(self.style.SUCCESS(f"Demo data created. Log in as {DEMO_EMAIL} / {DEMO_PASSWORD}"))
