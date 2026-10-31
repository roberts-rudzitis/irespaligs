"""Landing page, pricing, legal pages and the cookie notice."""

import pytest
from django.urls import reverse


def test_landing_shows_pricing_with_vat(client, db):
    html = client.get(reverse("home")).content.decode()
    assert "4,99\xa0€" in html and "49,90\xa0€" in html
    assert "PVN" in html
    assert reverse("account_signup") in html


def test_logged_in_user_goes_to_dashboard(client, verified_user):
    client.force_login(verified_user)
    assert client.get(reverse("home")).url == reverse("dashboard")


@pytest.mark.parametrize("lang,title", [("lv", "Privātuma politika"), ("en", "Privacy policy")])
def test_privacy_policy_in_both_languages(client, db, lang, title):
    client.cookies["django_language"] = lang
    html = client.get(reverse("privacy")).content.decode()
    assert title in html
    assert "personas kod" in html  # states we don't store personal codes


@pytest.mark.parametrize("lang,title", [("lv", "Lietošanas noteikumi"), ("en", "Terms of use")])
def test_terms_in_both_languages(client, db, lang, title):
    client.cookies["django_language"] = lang
    assert title in client.get(reverse("terms")).content.decode()


def test_legal_pages_show_draft_banner_until_reviewed(client, db, settings):
    assert "message-warning" in client.get(reverse("privacy")).content.decode()
    settings.LEGAL_TEXTS_REVIEWED = True
    assert "message-warning" not in client.get(reverse("privacy")).content.decode()


def test_cookie_notice_shown_until_acknowledged(client, db):
    assert "cookie-notice" in client.get(reverse("home")).content.decode()
    response = client.post(reverse("cookie_notice_ok"), {"next": "/privacy/"})
    assert response.url == "/privacy/"
    assert "cookie-notice" not in client.get(reverse("home")).content.decode()


def test_cookie_notice_ignores_external_redirect(client, db):
    response = client.post(reverse("cookie_notice_ok"), {"next": "https://evil.example/"})
    assert response.url == "/"


def test_footer_links_on_every_page(client, db):
    html = client.get(reverse("account_login")).content.decode()
    assert reverse("privacy") in html and reverse("terms") in html
