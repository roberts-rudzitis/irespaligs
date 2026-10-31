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
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT, related_name="leases", verbose_name=_("tenant"))
    # The VID notification deadline counts from signing (VERIFY.md V2), which can be before the start.
    signed_on = models.DateField(_("signed on"), null=True, blank=True, help_text=_("Leave empty if same as the start date."))
    start_date = models.DateField(_("start date"))
    # Required: residential leases are fixed-term (Dzīvojamo telpu īres likums, Art. 9; VERIFY.md L3)
    end_date = models.DateField(_("end date"))
    monthly_rent = models.DecimalField(_("monthly rent"), max_digits=12, decimal_places=2)
    deposit = models.DecimalField(_("deposit"), max_digits=12, decimal_places=2, default=0)
    rent_due_day = models.PositiveSmallIntegerField(
        _("rent due day"),
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text=_("Day of the month the rent is due (1–28)."),
    )
    # Used for the "notify VID" reminder (VERIFY.md V2, verified 31.10.2026)
    vid_notified_on = models.DateField(
        _("VID notified on"),
        null=True,
        blank=True,
        help_text=_("If you pay the 10 percent rental income tax without registering a business: the date you notified VID in EDS (due within 5 working days of signing)."),
    )
    # Secret part of the tenant's "submit readings" link (no login). Empty = no link.
    readings_token = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    # Registered leases bind a new owner of the dwelling (Dzīvojamo telpu īres likums, Art. 28; VERIFY.md L1)
    registered_in_land_register = models.BooleanField(_("registered in the Land Register"), default=False)

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
        if self.signed_on and self.start_date and self.signed_on > self.start_date:
            raise ValidationError({"signed_on": _("The signing date can't be after the start date.")})
        # Dzīvojamo telpu īres likums, Art. 12(1): deposit max. two months' rent (VERIFY.md L4)
        if self.deposit is not None and self.monthly_rent is not None and self.deposit > 2 * self.monthly_rent:
            raise ValidationError({"deposit": _("By law the deposit may not exceed two months' rent.")})
        if self.property_id and self.start_date and self.end_date:
            # One lease per property at a time: date ranges may not overlap.
            overlapping = Lease.objects.filter(
                property_id=self.property_id, start_date__lte=self.end_date, end_date__gte=self.start_date
            ).exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(_("This property already has a lease in this period."))

    # A method, not @property: inside this class the name `property` is the ForeignKey field.
    def signing_date(self):
        return self.signed_on or self.start_date

    def is_active(self, on_date=None):
        on_date = on_date or timezone.localdate()
        return self.start_date <= on_date <= self.end_date

    def days_until_end(self, on_date=None):
        on_date = on_date or timezone.localdate()
        return (self.end_date - on_date).days


class Meter(TimeStampedModel):
    """A utility meter in a property. The price is the landlord's own tariff.
    Statement lines copy the price, so changing it never alters old statements."""

    class Kind(models.TextChoices):
        COLD_WATER = "cold_water", _("Cold water")
        HOT_WATER = "hot_water", _("Hot water")
        ELECTRICITY = "electricity", _("Electricity")
        HEAT = "heat", _("Heating")
        GAS = "gas", _("Gas")
        OTHER = "other", _("Other")

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="meters")
    kind = models.CharField(_("type"), max_length=20, choices=Kind.choices)
    label = models.CharField(_("label"), max_length=60, blank=True, help_text=_("e.g. “Kitchen”, if there are several"))
    unit = models.CharField(_("unit"), max_length=10, help_text=_("e.g. m³, kWh, MWh"))
    price_per_unit = models.DecimalField(_("price per unit"), max_digits=12, decimal_places=5)
    is_active = models.BooleanField(_("in use"), default=True)

    owner_lookup = "property__owner"
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = _("meter")
        verbose_name_plural = _("meters")
        ordering = ["kind", "label"]

    def __str__(self):
        name = self.get_kind_display()
        return f"{name} ({self.label})" if self.label else name

    def get_absolute_url(self):
        return self.property.get_absolute_url()

    def last_reading_before(self, period):
        return self.readings.filter(period__lt=period).order_by("-period").first()


class MeterReading(TimeStampedModel):
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name="readings")
    period = models.DateField(_("month"), help_text=_("Always the 1st day of the month."))
    value = models.DecimalField(_("reading"), max_digits=14, decimal_places=3)
    submitted_by_tenant = models.BooleanField(default=False)

    owner_lookup = "meter__property__owner"
    objects = OwnedQuerySet.as_manager()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["meter", "period"], name="one_reading_per_meter_per_month")]
        ordering = ["-period"]


class FixedCharge(TimeStampedModel):
    """A fixed monthly amount passed on to the tenant, e.g. building management or waste."""

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="fixed_charges")
    label = models.CharField(_("description"), max_length=100, help_text=_("e.g. “Building management”"))
    amount = models.DecimalField(_("amount"), max_digits=12, decimal_places=2)
    is_active = models.BooleanField(_("in use"), default=True)

    owner_lookup = "property__owner"
    objects = OwnedQuerySet.as_manager()

    class Meta:
        verbose_name = _("fixed charge")
        verbose_name_plural = _("fixed charges")
        ordering = ["label"]

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        return self.property.get_absolute_url()
