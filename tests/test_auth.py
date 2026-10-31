"""Auth slice: sign-up with email verification, password login, login by email code, logout."""

import re

from django.core import mail
from django.urls import reverse

from apps.accounts.models import User

from .conftest import PASSWORD


def test_signup_sends_verification_email_and_blocks_login_until_confirmed(client, db):
    response = client.post(
        reverse("account_signup"),
        {"email": "Janis@Example.lv", "password1": PASSWORD, "password2": PASSWORD},
    )
    assert response.status_code == 302

    user = User.objects.get()
    assert user.email == "janis@example.lv"  # stored lower-case
    assert len(mail.outbox) == 1

    # Not verified yet → dashboard is not reachable
    assert client.get(reverse("dashboard")).status_code == 302

    confirm_url = re.search(r"https?://[^/]+(/accounts/confirm-email/\S+)", mail.outbox[0].body).group(1)
    client.get(confirm_url)

    client.logout()
    response = client.post(reverse("account_login"), {"login": "janis@example.lv", "password": PASSWORD})
    assert response.status_code == 302
    assert client.get(reverse("dashboard")).status_code == 200


def test_login_with_password(client, verified_user):
    response = client.post(reverse("account_login"), {"login": verified_user.email, "password": PASSWORD})
    assert response.status_code == 302
    assert response.url == reverse("dashboard")


def test_login_with_wrong_password_fails(client, verified_user):
    response = client.post(reverse("account_login"), {"login": verified_user.email, "password": "nepareiza"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_login_by_email_code(client, verified_user):
    client.post(reverse("account_request_login_code"), {"email": verified_user.email})
    assert len(mail.outbox) == 1

    # The code sits on its own line in the email
    code = re.search(r"^\s*([A-Z0-9-]{4,})\s*$", mail.outbox[0].body, re.MULTILINE).group(1)
    response = client.post(reverse("account_confirm_login_code"), {"code": code})
    assert response.status_code == 302
    assert client.get(reverse("dashboard")).status_code == 200


def test_dashboard_requires_login(client, db):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert reverse("account_login") in response.url


def test_logout(client, verified_user):
    client.force_login(verified_user)
    client.post(reverse("account_logout"))
    assert client.get(reverse("dashboard")).status_code == 302


def test_user_has_no_personal_code_field():
    # GDPR hard rule: we never store the personas kods.
    field_names = {f.name.lower() for f in User._meta.get_fields()}
    assert not any("personas" in n or "personal_code" in n for n in field_names)
