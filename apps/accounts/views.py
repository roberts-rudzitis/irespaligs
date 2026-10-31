from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "language", "payment_details"]
        widgets = {"payment_details": forms.Textarea(attrs={"rows": 3})}


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Saved."))
        response = redirect("profile")
        # Keep the language cookie in sync with the saved choice.
        response.set_cookie("django_language", request.user.language, max_age=365 * 24 * 60 * 60, samesite="Lax")
        return response
    return render(request, "accounts/profile.html", {"form": form})
