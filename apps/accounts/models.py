from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """A landlord. Email is the login; no username.

    Data minimisation (GDPR): only email, optional name and UI language.
    Never add personas kods or ID document fields here.
    """

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(_("full name"), max_length=150, blank=True)
    language = models.CharField(
        _("language"), max_length=8, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    # Printed on payment notices so the tenant knows where to pay (the landlord's own bank account).
    payment_details = models.TextField(
        _("payment details"),
        blank=True,
        help_text=_("Shown on payment notices, e.g. recipient name, bank, IBAN."),
    )

    # Email reminders – each type can be switched off on the "My account" page.
    remind_readings = models.BooleanField(_("monthly reminder to enter meter readings"), default=True)
    remind_overdue = models.BooleanField(_("reminder when rent is overdue"), default=True)
    remind_lease_end = models.BooleanField(_("reminder 60 and 30 days before a lease ends"), default=True)
    remind_vid = models.BooleanField(_("reminder to check VID notification for new leases"), default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name or self.email

    def get_short_name(self):
        return self.full_name or self.email
