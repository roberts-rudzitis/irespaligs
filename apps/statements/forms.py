from datetime import date

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.rentals.forms import DateInput

from .models import Payment
from .services import ReadingInput


class MonthField(forms.Field):
    """Month entered as mm.yyyy (e.g. 11.2026) → date(2026, 11, 1)."""

    def __init__(self, **kwargs):
        super().__init__(widget=forms.TextInput(attrs={"placeholder": _("mm.yyyy"), "maxlength": 7}), **kwargs)

    def prepare_value(self, value):
        return value.strftime("%m.%Y") if isinstance(value, date) else value

    def to_python(self, value):
        value = (value or "").strip()
        if not value:
            return None
        try:
            month, year = value.split(".")
            return date(int(year), int(month), 1)
        except ValueError:
            raise forms.ValidationError(_("Enter the month as mm.yyyy, e.g. 11.2026."))


class StatementCreateForm(forms.Form):
    """Month, due date and one previous/current reading pair per active meter."""

    period = MonthField(label=_("Month"))
    due_date = forms.DateField(label=_("Due date"), widget=DateInput())

    def __init__(self, *args, meters, period, **kwargs):
        super().__init__(*args, **kwargs)
        self.meters = list(meters)
        for meter in self.meters:
            last = meter.last_reading_before(period)
            self.fields[f"prev_{meter.pk}"] = forms.DecimalField(
                label=_("%(meter)s – previous reading (%(unit)s)") % {"meter": meter, "unit": meter.unit},
                max_digits=14, decimal_places=3, min_value=0, localize=True,
                initial=last.value if last else None,
            )
            self.fields[f"curr_{meter.pk}"] = forms.DecimalField(
                label=_("%(meter)s – current reading (%(unit)s)") % {"meter": meter, "unit": meter.unit},
                max_digits=14, decimal_places=3, min_value=0, localize=True,
            )

    def readings(self):
        return [
            ReadingInput(
                meter=meter,
                previous=self.cleaned_data[f"prev_{meter.pk}"],
                current=self.cleaned_data[f"curr_{meter.pk}"],
            )
            for meter in self.meters
        ]


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["paid_on", "amount", "note"]
        widgets = {"paid_on": DateInput()}
        localized_fields = ["amount"]

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError(_("The amount must be greater than zero."))
        return amount
