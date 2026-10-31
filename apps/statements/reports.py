"""Year-end income summary – helps the landlord fill in the annual declaration (EDS).

The app does NOT calculate tax. TODO: verify (VERIFY.md V1, V6) – which amounts count as
rental income (e.g. are utilities passed on to the tenant income?) is for the landlord / VID to decide;
we only show the numbers recorded in the app.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.db.models import Sum

from apps.rentals.models import Property

from .models import Payment, StatementLine


@dataclass
class PropertyYear:
    property: Property
    billed_rent: Decimal = Decimal("0")
    billed_other: Decimal = Decimal("0")  # utilities + fixed charges passed on
    received: Decimal = Decimal("0")
    payments: list = field(default_factory=list)

    @property
    def billed_total(self):
        return self.billed_rent + self.billed_other


def year_summary(user, year):
    """Per property: what was billed (by notice month) and what was received (by payment date)."""
    rows = []
    for prop in Property.objects.for_owner(user):
        lines = StatementLine.objects.filter(
            statement__lease__property=prop, statement__period__year=year, statement__status="sent"
        )
        billed_rent = lines.filter(kind=StatementLine.Kind.RENT).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        billed_all = lines.aggregate(s=Sum("amount"))["s"] or Decimal("0")
        payments = list(
            Payment.objects.filter(statement__lease__property=prop, paid_on__year=year)
            .select_related("statement__lease__tenant")
            .order_by("paid_on")
        )
        rows.append(
            PropertyYear(
                property=prop,
                billed_rent=billed_rent,
                billed_other=billed_all - billed_rent,
                received=sum((p.amount for p in payments), Decimal("0")),
                payments=payments,
            )
        )
    totals = PropertyYear(
        property=None,
        billed_rent=sum((r.billed_rent for r in rows), Decimal("0")),
        billed_other=sum((r.billed_other for r in rows), Decimal("0")),
        received=sum((r.received for r in rows), Decimal("0")),
    )
    return rows, totals
