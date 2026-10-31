"""Latvian is the default language; English is available; Latvian formats everywhere."""

import datetime
from decimal import Decimal

from django.template import Context, Template
from django.urls import reverse
from django.utils import formats, translation

from apps.core.money import format_eur, round_money


def test_home_is_latvian_by_default(client, db):
    response = client.get(reverse("home"))
    assert response["Content-Language"] == "lv"
    assert "Īre, komunālie maksājumi un īrnieki – vienuviet" in response.content.decode()


def test_browser_language_is_ignored(client, db):
    response = client.get(reverse("home"), HTTP_ACCEPT_LANGUAGE="en-US,en")
    assert response["Content-Language"] == "lv"


def test_switch_to_english_sets_cookie(client, db):
    response = client.post(reverse("set_language"), {"language": "en", "next": "/"})
    assert response.status_code == 302
    response = client.get(reverse("home"))
    assert "Rent, utilities and tenants – in one place" in response.content.decode()


def test_language_choice_is_saved_on_user(client, verified_user):
    client.force_login(verified_user)
    client.post(reverse("set_language"), {"language": "en", "next": "/"})
    verified_user.refresh_from_db()
    assert verified_user.language == "en"


def test_set_language_ignores_unknown_language_and_external_redirect(client, db):
    response = client.post(reverse("set_language"), {"language": "xx", "next": "https://evil.example"})
    assert response.url == "/"
    assert "django_language" not in response.cookies


def test_login_page_is_translated_to_latvian(client, db):
    # allauth ships its own Latvian translations
    response = client.get(reverse("account_login"))
    assert response.status_code == 200
    assert 'lang="lv"' in response.content.decode()


def test_eur_formatting():
    assert format_eur(Decimal("1234.5")) == "1\xa0234,50\xa0€"
    assert format_eur(Decimal("0")) == "0,00\xa0€"
    assert format_eur(Decimal("-12.345")) == "-12,35\xa0€"
    assert format_eur(Decimal("1000000")) == "1\xa0000\xa0000,00\xa0€"
    assert format_eur(None) == ""


def test_round_money_is_half_up_not_bankers():
    assert round_money(Decimal("0.125")) == Decimal("0.13")
    assert round_money(Decimal("2.675")) == Decimal("2.68")


def test_eur_template_filter():
    html = Template("{% load money %}{{ x|eur }}").render(Context({"x": Decimal("4.99")}))
    assert html == "4,99\xa0€"


def test_dates_are_dd_mm_yyyy_in_both_languages():
    day = datetime.date(2026, 3, 5)
    for lang in ("lv", "en"):
        with translation.override(lang):
            assert formats.date_format(day, "SHORT_DATE_FORMAT") == "05.03.2026"
            assert formats.number_format(Decimal("12.5"), 2) == "12,50"


def test_quantity_formatting_drops_trailing_zeros():
    from apps.core.money import format_quantity

    assert format_quantity(Decimal("120.400")) == "120,4"
    assert format_quantity(Decimal("8450.000")) == "8450"
    assert format_quantity(Decimal("2.15400")) == "2,154"
    assert format_quantity(None) == ""
