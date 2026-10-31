from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import OwnedQuerySet, TimeStampedModel


class Property(TimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="properties")
    name = models.CharField(_("name"), max_length=100, help_text=_("e.g. “Flat in Imanta”"))
    address = models.CharField(_("address"), max_length=255, blank=True)
    notes = models.TextField(_("notes"), blank=True)

    owner_lookup = "owner"
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = _("property")
        verbose_name_plural = _("properties")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("rentals:property_detail", args=[self.pk])

    def current_lease(self, on_date=None):
        on_date = on_date or timezone.localdate()
        return self.leases.filter(start_date__lte=on_date, end_date__gte=on_date).select_related("tenant").first()


class Tenant(TimeStampedModel):
    """Minimal tenant data (GDPR). Never add personas kods or ID document fields."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenants")
    full_name = models.CharField(_("full name"), max_length=150)
    email = models.EmailField(_("email"), blank=True, help_text=_("Monthly statements are sent here."))
    phone = models.CharField(_("phone"), max_length=30, blank=True)

    owner_lookup = "owner"
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = _("tenant")
        verbose_name_plural = _("tenants")
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("rentals:tenant_list")


class Lease(TimeStampedModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="leases", verbose_name=_("property"))
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="leases", verbose_name=_("tenant"))
    start_date = models.DateField(_("start date"))
    # Required: residential leases must be fixed-term. TODO: verify (VERIFY.md L3)
    end_date = models.DateField(_("end date"))
    monthly_rent = models.DecimalField(_("monthly rent"), max_digits=12, decimal_places=2)
    deposit = models.DecimalField(_("deposit"), max_digits=12, decimal_places=2, default=0)
    rent_due_day = models.PositiveSmallIntegerField(
        _("rent due day"),
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text=_("Day of the month the rent is due (1–28)."),
    )
    # Used for the "notify VID" reminder. TODO: verify (VERIFY.md V2)
    vid_notified_on = models.DateField(
        _("VID notified on"),
        null=True,
        blank=True,
        help_text=_("If you chose the 10 percent rental income tax regime: the date you notified VID about this lease."),
    )

    owner_lookup = "property__owner"
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = _("lease")
        verbose_name_plural = _("leases")
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.property} – {self.tenant}"

    def get_absolute_url(self):
        return self.property.get_absolute_url()

    def clean(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError({"end_date": _("The end date must be after the start date.")})
        if self.property_id and self.start_date and self.end_date:
            # One lease per property at a time: date ranges may not overlap.
            overlapping = Lease.objects.filter(
                property_id=self.property_id, start_date__lte=self.end_date, end_date__gte=self.start_date
            ).exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(_("This property already has a lease in this period."))

    def is_active(self, on_date=None):
        on_date = on_date or timezone.localdate()
        return self.start_date <= on_date <= self.end_date

    def days_until_end(self, on_date=None):
        on_date = on_date or timezone.localdate()
        return (self.end_date - on_date).days
