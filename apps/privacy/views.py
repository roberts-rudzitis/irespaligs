from django import forms
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from . import services


@login_required
def export_data(request):
    response = HttpResponse(services.export_user_data(request.user), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="irespaligs-dati-{timezone.localdate():%Y-%m-%d}.zip"'
    return response


class DeleteAccountForm(forms.Form):
    """Typing the email works for everyone, also users who log in with email codes and have no password."""

    email = forms.EmailField(label=gettext_lazy("Type your email address to confirm"))

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        if self.cleaned_data["email"].strip().lower() != self.user.email.lower():
            raise forms.ValidationError(_("This is not your account's email address."))
        return self.cleaned_data["email"]


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        services.delete_account(user)
        return redirect("account_deleted")
    return render(request, "privacy/delete_account.html", {"form": form})


def account_deleted(request):
    return render(request, "privacy/account_deleted.html")
