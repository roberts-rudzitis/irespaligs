from django import forms
from django.utils.translation import gettext_lazy as _

from .models import FixedCharge, Lease, Meter, Property, Tenant


class DateInput(forms.DateInput):
    """Plain text date field in dd.mm.yyyy – the same for every browser language."""

    def __init__(self, **kwargs):
        super().__init__(format="%d.%m.%Y", attrs={"placeholder": _("dd.mm.yyyy"), "inputmode": "numeric"})


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ["name", "address", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ["full_name", "email", "phone"]


class LeaseForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = ["tenant", "signed_on", "start_date", "end_date", "monthly_rent", "deposit", "rent_due_day", "vid_notified_on"]
        widgets = {"signed_on": DateInput(), "start_date": DateInput(), "end_date": DateInput(), "vid_notified_on": DateInput()}
        # localized: shows "450,00" and accepts both "450,00" and "450.00"
        localized_fields = ["monthly_rent", "deposit"]

    def __init__(self, *args, owner, property, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.property = property
        # Only this landlord's tenants can be chosen.
        self.fields["tenant"].queryset = Tenant.objects.for_owner(owner)


class MeterForm(forms.ModelForm):
    class Meta:
        model = Meter
        fields = ["kind", "label", "unit", "price_per_unit", "is_active"]
        localized_fields = ["price_per_unit"]


class FixedChargeForm(forms.ModelForm):
    class Meta:
        model = FixedCharge
        fields = ["label", "amount", "is_active"]
        localized_fields = ["amount"]
