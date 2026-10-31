from django.contrib import messages
from django.db.models import RestrictedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.mixins import OwnerMixin, SavedMessageMixin
from apps.subscriptions.services import can_add_property

from .forms import FixedChargeForm, LeaseForm, MeterForm, PropertyForm, TenantForm
from .models import FixedCharge, Lease, Meter, Property, Tenant

FORM_TEMPLATE = "rentals/form.html"
DELETE_TEMPLATE = "rentals/confirm_delete.html"


# --- Properties -------------------------------------------------------------


class PropertyDetail(OwnerMixin, DetailView):
    model = Property
    template_name = "rentals/property_detail.html"


class PropertyCreate(OwnerMixin, SavedMessageMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = FORM_TEMPLATE
    extra_context = {"title": _("New property")}

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not can_add_property(request.user):
            messages.info(request, _("Your plan's property limit is reached. Upgrade to add more."))
            return redirect("billing")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class PropertyUpdate(OwnerMixin, SavedMessageMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = FORM_TEMPLATE
    extra_context = {"title": _("Edit property")}


class PropertyDelete(OwnerMixin, DeleteView):
    model = Property
    template_name = DELETE_TEMPLATE
    success_url = reverse_lazy("dashboard")


# --- Tenants ----------------------------------------------------------------


class TenantList(OwnerMixin, ListView):
    model = Tenant
    template_name = "rentals/tenant_list.html"


class TenantCreate(OwnerMixin, SavedMessageMixin, CreateView):
    model = Tenant
    form_class = TenantForm
    template_name = FORM_TEMPLATE
    extra_context = {"title": _("New tenant")}

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        # Coming from "new lease" → go back there so the new tenant can be picked.
        return self.request.GET.get("next") if self._safe_next() else reverse("rentals:tenant_list")

    def _safe_next(self):
        next_url = self.request.GET.get("next", "")
        return next_url.startswith("/") and not next_url.startswith("//")


class TenantUpdate(OwnerMixin, SavedMessageMixin, UpdateView):
    model = Tenant
    form_class = TenantForm
    template_name = FORM_TEMPLATE
    extra_context = {"title": _("Edit tenant")}


class TenantDelete(OwnerMixin, DeleteView):
    model = Tenant
    template_name = DELETE_TEMPLATE
    success_url = reverse_lazy("rentals:tenant_list")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except RestrictedError:
            messages.error(self.request, _("This tenant has leases. Delete the leases first."))
            return redirect("rentals:tenant_list")


# --- Leases -----------------------------------------------------------------


class LeaseFormMixin:
    model = Lease
    form_class = LeaseForm
    template_name = FORM_TEMPLATE

    def get_property(self):
        raise NotImplementedError

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user
        kwargs["property"] = self.get_property()
        return kwargs


class LeaseCreate(OwnerMixin, SavedMessageMixin, LeaseFormMixin, CreateView):
    extra_context = {"title": _("New lease")}

    def get_property(self):
        return get_object_or_404(Property.objects.for_owner(self.request.user), pk=self.kwargs["property_pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["new_tenant_url"] = reverse("rentals:tenant_create") + "?next=" + self.request.path
        return context


class LeaseUpdate(OwnerMixin, SavedMessageMixin, LeaseFormMixin, UpdateView):
    extra_context = {"title": _("Edit lease")}

    def get_property(self):
        return self.object.property


class LeaseDelete(OwnerMixin, DeleteView):
    model = Lease
    template_name = DELETE_TEMPLATE

    def get_success_url(self):
        return self.object.property.get_absolute_url()


# --- Meters and fixed charges (belong to a property) ------------------------


class PropertyChildCreate(OwnerMixin, SavedMessageMixin, CreateView):
    """Create something that belongs to one of the landlord's properties."""

    template_name = FORM_TEMPLATE

    def form_valid(self, form):
        form.instance.property = get_object_or_404(
            Property.objects.for_owner(self.request.user), pk=self.kwargs["property_pk"]
        )
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        get_object_or_404(Property.objects.for_owner(request.user), pk=kwargs["property_pk"])
        return super().get(request, *args, **kwargs)


class PropertyChildDelete(OwnerMixin, DeleteView):
    template_name = DELETE_TEMPLATE

    def get_success_url(self):
        return self.object.property.get_absolute_url()


class MeterCreate(PropertyChildCreate):
    model = Meter
    form_class = MeterForm
    extra_context = {"title": _("New meter")}


class MeterUpdate(OwnerMixin, SavedMessageMixin, UpdateView):
    model = Meter
    form_class = MeterForm
    template_name = FORM_TEMPLATE
    extra_context = {"title": _("Edit meter")}


class MeterDelete(PropertyChildDelete):
    model = Meter


class FixedChargeCreate(PropertyChildCreate):
    model = FixedCharge
    form_class = FixedChargeForm
    extra_context = {"title": _("New fixed charge")}


class FixedChargeUpdate(OwnerMixin, SavedMessageMixin, UpdateView):
    model = FixedCharge
    form_class = FixedChargeForm
    template_name = FORM_TEMPLATE
    extra_context = {"title": _("Edit fixed charge")}


class FixedChargeDelete(PropertyChildDelete):
    model = FixedCharge
