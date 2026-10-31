from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "interval", "trial_ends_at", "current_period_end", "cancel_at_period_end"]
    list_filter = ["status", "interval"]
    search_fields = ["user__email", "provider_customer_id", "provider_subscription_id"]
    # Changed by webhooks; editing by hand would get out of sync with Stripe.
    readonly_fields = ["provider", "provider_customer_id", "provider_subscription_id", "current_period_end"]
