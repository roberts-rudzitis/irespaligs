import pytest
from allauth.account.models import EmailAddress

from apps.accounts.models import User

PASSWORD = "Drosa-parole-2026"


@pytest.fixture(autouse=True)
def _fast_tests(settings):
    # Argon2 is deliberately slow; tests don't need that.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def verified_user(db):
    """A landlord who has signed up and confirmed their email."""
    user = User.objects.create_user("ilze@example.lv", PASSWORD)
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    return user
