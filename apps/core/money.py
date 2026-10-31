from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
NBSP = "\xa0"


def round_money(value):
    """Round to whole cents, 0.005 → 0.01 (the way people expect, not banker's rounding)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def format_eur(value):
    """Decimal('1234.5') → '1 234,50 €' (Latvian format, non-breaking spaces)."""
    if value is None or value == "":
        return ""
    amount = round_money(value)
    sign = "-" if amount < 0 else ""
    # Python gives '1,234.50'; swap to Latvian separators.
    text = f"{abs(amount):,.2f}".replace(",", NBSP).replace(".", ",")
    return f"{sign}{text}{NBSP}€"
