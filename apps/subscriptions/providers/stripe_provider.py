"""Stripe: Checkout for subscribing, Customer Portal for managing, webhooks for status changes.

We never see card data – Stripe hosts the payment pages.
"""

import logging
from datetime import datetime, timezone as dt_timezone

import stripe
from django.conf import settings

from ..models import Subscription

log = logging.getLogger(__name__)

PROVIDER = "stripe"

# Stripe subscription status → our status
STATUS_MAP = {
    "trialing": Subscription.Status.ACTIVE,  # we run our own no-card trial; a Stripe trial still means "paid plan"
    "active": Subscription.Status.ACTIVE,
    "past_due": Subscription.Status.PAST_DUE,
    "unpaid": Subscription.Status.CANCELED,
    "canceled": Subscription.Status.CANCELED,
    "incomplete": Subscription.Status.NONE,
    "incomplete_expired": Subscription.Status.CANCELED,
    "paused": Subscription.Status.CANCELED,
}


def is_configured():
    return bool(settings.STRIPE_SECRET_KEY)


def _client():
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def _price_id(interval):
    return {"month": settings.STRIPE_PRICE_MONTHLY, "year": settings.STRIPE_PRICE_YEARLY}[interval]


def start_checkout(user, interval, success_url, cancel_url):
    subscription = user.subscription
    params = {
        "mode": "subscription",
        "line_items": [{"price": _price_id(interval), "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(user.pk),
        "locale": "lv" if user.language == "lv" else "en",
        "metadata": {"user_id": str(user.pk)},
        "subscription_data": {"metadata": {"user_id": str(user.pk)}},
    }
    if subscription.provider_customer_id:
        params["customer"] = subscription.provider_customer_id
    else:
        params["customer_email"] = user.email
    session = _client().v1.checkout.sessions.create(params=params)
    return session.url


def manage_url(user, return_url):
    session = _client().v1.billing_portal.sessions.create(
        params={"customer": user.subscription.provider_customer_id, "return_url": return_url}
    )
    return session.url


def _timestamp(value):
    return datetime.fromtimestamp(value, tz=dt_timezone.utc) if value else None


def _period_end(stripe_sub):
    # Newer Stripe API versions keep the period on the subscription items.
    items = (stripe_sub.get("items") or {}).get("data") or []
    if items and items[0].get("current_period_end"):
        return _timestamp(items[0]["current_period_end"])
    return _timestamp(stripe_sub.get("current_period_end"))


def _as_dict(obj):
    return obj.to_dict() if hasattr(obj, "to_dict") else obj


def _apply_subscription(stripe_sub):
    """Copy a Stripe subscription object onto our Subscription row. Safe to run twice (idempotent)."""
    subscription = Subscription.objects.filter(provider_subscription_id=stripe_sub["id"]).first()
    if subscription is None:
        user_id = (stripe_sub.get("metadata") or {}).get("user_id")
        subscription = Subscription.objects.filter(user_id=user_id).first() if user_id else None
    if subscription is None:
        subscription = Subscription.objects.filter(provider_customer_id=stripe_sub.get("customer")).first()
    if subscription is None:
        log.warning("Stripe subscription %s does not match any user", stripe_sub["id"])
        return

    items = (stripe_sub.get("items") or {}).get("data") or []
    price = items[0].get("price", {}) if items else {}
    subscription.provider = PROVIDER
    subscription.provider_customer_id = stripe_sub.get("customer") or subscription.provider_customer_id
    subscription.provider_subscription_id = stripe_sub["id"]
    subscription.status = STATUS_MAP.get(stripe_sub.get("status"), Subscription.Status.NONE)
    subscription.interval = (price.get("recurring") or {}).get("interval", subscription.interval)
    subscription.current_period_end = _period_end(stripe_sub)
    subscription.cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end"))
    subscription.save()


def handle_webhook(payload, headers):
    """Verify Stripe's signature, then update our records. Raises ValueError if the signature is bad."""
    try:
        event = stripe.Webhook.construct_event(
            payload, headers.get("Stripe-Signature"), settings.STRIPE_WEBHOOK_SECRET
        ).to_dict()  # plain dicts are simpler to read than Stripe objects
    except (stripe.SignatureVerificationError, ValueError) as error:
        raise ValueError("Invalid Stripe webhook") from error

    data = event["data"]["object"]
    if event["type"] == "checkout.session.completed" and data.get("mode") == "subscription":
        user_id = data.get("client_reference_id")
        Subscription.objects.filter(user_id=user_id).update(
            provider=PROVIDER,
            provider_customer_id=data.get("customer") or "",
            provider_subscription_id=data.get("subscription") or "",
        )
        if data.get("subscription"):
            _apply_subscription(_as_dict(_client().v1.subscriptions.retrieve(data["subscription"])))
    elif event["type"] in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        _apply_subscription(data)


def delete_customer(customer_id):
    """Deleting a Stripe customer also cancels their subscriptions immediately."""
    _client().v1.customers.delete(customer_id)
