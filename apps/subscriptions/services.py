"""Plan checks used by the rest of the app. Views call these, never the plan limits directly."""

from .models import Subscription


def get_subscription(user):
    # Every user gets one on sign-up (signals.py); this also covers users created before billing existed.
    subscription, _created = Subscription.objects.get_or_create(user=user)
    return subscription


def current_plan(user):
    return get_subscription(user).plan


def can_add_property(user):
    return user.properties.count() < current_plan(user).max_properties


def can_send_notices(user):
    return current_plan(user).can_send_notices


def gets_reminders(user):
    return current_plan(user).reminders
