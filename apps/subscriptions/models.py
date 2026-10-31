from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from . import plans


class Subscription(models.Model):
    """A landlord's plan. Changed only by the trial logic and by payment-provider webhooks."""

    class Status(models.TextChoices):
        TRIALING = "trialing", _("Free trial")
        ACTIVE = "active", _("Active")
        PAST_DUE = "past_due", _("Payment failed")  # provider keeps retrying; we keep access meanwhile
        CANCELED = "canceled", _("Cancelled")
        NONE = "none", _("Free plan")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NONE)
    interval = models.CharField(max_length=10, blank=True)  # "month" / "year"
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    # Payment provider references (Stripe today; Montonio/Paysera could be added – see providers/)
    provider = models.CharField(max_length=20, blank=True)
    provider_customer_id = models.CharField(max_length=100, blank=True, db_index=True)
    provider_subscription_id = models.CharField(max_length=100, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} – {self.status}"

    @classmethod
    def start_trial(cls, user):
        return cls.objects.create(
            user=user, status=cls.Status.TRIALING, trial_ends_at=timezone.now() + timedelta(days=plans.TRIAL_DAYS)
        )

    @property
    def in_trial(self):
        return self.status == self.Status.TRIALING and self.trial_ends_at and self.trial_ends_at > timezone.now()

    @property
    def is_paying(self):
        return self.status in (self.Status.ACTIVE, self.Status.PAST_DUE)

    @property
    def plan(self):
        return plans.STANDARD if (self.in_trial or self.is_paying) else plans.FREE

    @property
    def trial_days_left(self):
        if not self.in_trial:
            return 0
        return max(0, (self.trial_ends_at - timezone.now()).days)
