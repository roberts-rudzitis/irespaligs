"""Plans and their limits – the one place to change what each plan allows.

Prices include 21% PVN. TODO: verify (VERIFY.md B1, B4) – whether we must charge PVN from
the first customer and how prices must be shown to consumers.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    max_properties: int
    can_send_notices: bool  # PDF + email to tenant
    reminders: bool


FREE = Plan("free", _("Free"), max_properties=1, can_send_notices=False, reminders=False)
STANDARD = Plan("standard", _("Standard"), max_properties=5, can_send_notices=True, reminders=True)

TRIAL_DAYS = 14
VAT_RATE = Decimal("0.21")


@dataclass(frozen=True)
class Price:
    interval: str  # "month" or "year" – matches Stripe
    gross: Decimal  # incl. PVN, what the customer pays
    label: str

    @property
    def net(self):
        return (self.gross / (1 + VAT_RATE)).quantize(Decimal("0.01"))

    @property
    def vat(self):
        return self.gross - self.net


PRICES = {
    "month": Price("month", Decimal("4.99"), _("per month")),
    "year": Price("year", Decimal("49.90"), _("per year (2 months free)")),
}
