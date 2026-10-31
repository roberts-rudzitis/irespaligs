from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _


class OwnerMixin(LoginRequiredMixin):
    """For class-based views: only the logged-in landlord's own objects.
    Anything else gives 404 (not 403), so we don't reveal that it exists."""

    def get_queryset(self):
        return self.model.objects.for_owner(self.request.user)


class SavedMessageMixin:
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Saved."))
        return response
