from decimal import Decimal

from django.db import models
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import OwnedQuerySet, TimeStampedModel
from apps.rentals.models import Lease


class StatementQuerySet(OwnedQuerySet):
    def with_paid(self):
        """Adds `paid_sum` (sum of payments; 0 if none) – used by Statement.paid_total.
        Coalesce turns SQL NULL into 0, otherwise "no payments" would not count as unpaid."""
        return self.annotate(paid_sum=Coalesce(Sum("payments__amount"), Value(Decimal("0"))))

    def unpaid(self):
        return self.with_paid().filter(status=Statement.Status.SENT).exclude(paid_sum__gte=models.F("total"))


class Statement(TimeStampedModel):
    """Monthly payment notice for one lease: rent + utilities + fixed charges.

    Wording: we call it a "payment notice" (maksājuma paziņojums), not an invoice.
    TODO: verify (VERIFY.md V5) whether a private landlord's notice needs any mandatory content.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SENT = "sent", _("Sent")

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="statements")
    period = models.DateField(_("month"))  # always the 1st of the month
    issue_date = models.DateField(_("issue date"), default=timezone.localdate)
    due_date = models.DateField(_("due date"))
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default=Status.DRAFT)
    total = models.DecimalField(_("total"), max_digits=12, decimal_places=2, default=0)
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)

    owner_lookup = "lease__property__owner"
    objects = StatementQuerySet.as_manager()

    class Meta:
        verbose_name = _("payment notice")
        verbose_name_plural = _("payment notices")
        ordering = ["-period", "-id"]
        constraints = [models.UniqueConstraint(fields=["lease", "period"], name="one_statement_per_lease_per_month")]

    def __str__(self):
        return f"{self.lease.property} {self.period:%m.%Y}"

    def get_absolute_url(self):
        return reverse("statements:detail", args=[self.pk])

    @property
    def number(self):
        # Human-friendly reference for the bank transfer, e.g. "2026-11-42"
        return f"{self.period:%Y-%m}-{self.pk}"

    @property
    def paid_total(self):
        if hasattr(self, "paid_sum"):
            return self.paid_sum or Decimal("0")
        return self.payments.aggregate(s=Sum("amount"))["s"] or Decimal("0")

    @property
    def balance(self):
        return self.total - self.paid_total

    @property
    def payment_state(self):
        """'paid', 'partly_paid', 'overdue', 'unpaid' or 'draft' – for display."""
        if self.status == self.Status.DRAFT:
            return "draft"
        if self.paid_total >= self.total:
            return "paid"
        if self.due_date < timezone.localdate():
            return "overdue"
        return "partly_paid" if self.paid_total > 0 else "unpaid"


class StatementLine(models.Model):
    """A copy ("snapshot") of the numbers at the time the notice was made."""

    class Kind(models.TextChoices):
        RENT = "rent", _("Rent")
        UTILITY = "utility", _("Utility")
        FIXED = "fixed", _("Fixed charge")
        OTHER = "other", _("Other")

    statement = models.ForeignKey(Statement, on_delete=models.CASCADE, related_name="lines")
    position = models.PositiveSmallIntegerField(default=0)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    description = models.CharField(max_length=200)
    prev_reading = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    curr_reading = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=1)
    unit = models.CharField(max_length=10, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=5)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["position"]


class Payment(TimeStampedModel):
    statement = models.ForeignKey(Statement, on_delete=models.CASCADE, related_name="payments")
    paid_on = models.DateField(_("payment date"), default=timezone.localdate)
    amount = models.DecimalField(_("amount"), max_digits=12, decimal_places=2)
    note = models.CharField(_("note"), max_length=200, blank=True)

    owner_lookup = "statement__lease__property__owner"
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ["paid_on", "id"]
