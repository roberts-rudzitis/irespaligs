from django.contrib import admin

from .models import Lease, Property, Tenant


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "address", "created_at"]
    search_fields = ["name", "owner__email"]


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["full_name", "owner", "email"]
    search_fields = ["full_name", "owner__email"]


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ["property", "tenant", "start_date", "end_date", "monthly_rent"]
    list_select_related = ["property", "tenant"]
