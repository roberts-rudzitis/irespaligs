from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.subscriptions.models import Subscription

from .models import User

admin.site.site_header = "ĪresPalīgs admin"
admin.site.site_title = "ĪresPalīgs admin"
admin.site.index_title = "Support"  # Metrics: /admin/metrics/


class SubscriptionInline(admin.StackedInline):
    model = Subscription
    extra = 0
    can_delete = False
    readonly_fields = ["provider", "provider_customer_id", "provider_subscription_id", "current_period_end"]


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "full_name", "language", "plan_status", "property_count", "date_joined", "last_login"]
    list_filter = ["subscription__status", "language", "is_staff"]
    search_fields = ["email", "full_name"]
    inlines = [SubscriptionInline]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        (_("Personal info"), {"fields": ["full_name", "language", "payment_details"]}),
        (_("Reminders"), {"fields": ["remind_readings", "remind_overdue", "remind_lease_end", "remind_vid"]}),
        (_("Permissions"), {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        (_("Important dates"), {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["email", "password1", "password2"]}),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("subscription").annotate(n_properties=Count("properties"))

    @admin.display(description="Plan", ordering="subscription__status")
    def plan_status(self, user):
        sub = getattr(user, "subscription", None)
        return sub.get_status_display() if sub else "–"

    @admin.display(description="Properties", ordering="n_properties")
    def property_count(self, user):
        return user.n_properties
