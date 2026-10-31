"""Billing slice: trial, plan limits, Stripe checkout and webhooks (Stripe is never called for real)."""

import datetime
import hashlib
import hmac
import json
import time
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.reminders.services import send_reminders
from apps.rentals.models import Lease, Property, Tenant
from apps.statements import services as statement_services
from apps.statements.models import Statement
from apps.subscriptions import plans
from apps.subscriptions.models import Subscription
from apps.subscriptions.providers import stripe_provider

WEBHOOK_SECRET = "whsec_test_secret"


@pytest.fixture(autouse=True)
def stripe_settings(settings):
    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET
    settings.STRIPE_PRICE_MONTHLY = "price_month"
    settings.STRIPE_PRICE_YEARLY = "price_year"


def end_trial(user):
    sub = user.subscription
    sub.status = Subscription.Status.NONE
    sub.trial_ends_at = timezone.now() - datetime.timedelta(days=1)
    sub.save()


def signed_post(client, event):
    """POST a webhook signed exactly the way Stripe signs it."""
    payload = json.dumps(event)
    timestamp = int(time.time())
    signature = hmac.new(WEBHOOK_SECRET.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256).hexdigest()
    return client.post(
        reverse("stripe_webhook"), payload, content_type="application/json",
        HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signature}",
    )


def stripe_subscription(user, status="active", interval="month", sub_id="sub_123", cancel=False):
    return {
        "id": sub_id, "object": "subscription", "customer": "cus_123", "status": status,
        "cancel_at_period_end": cancel, "metadata": {"user_id": str(user.pk)},
        "items": {"object": "list", "data": [{
            "current_period_end": 1798675200,  # 31.12.2026
            "price": {"id": "price_month", "recurring": {"interval": interval}},
        }]},
    }


def event(event_type, obj):
    return {"id": "evt_1", "object": "event", "type": event_type, "data": {"object": obj}}


# --- Trial and plan limits ----------------------------------------------------


def test_new_user_gets_14_day_trial_of_paid_plan(verified_user):
    sub = verified_user.subscription
    assert sub.in_trial
    assert sub.plan == plans.STANDARD
    assert 13 <= sub.trial_days_left <= 14


def test_after_trial_free_plan_allows_one_property(client, verified_user):
    end_trial(verified_user)
    client.force_login(verified_user)
    client.post(reverse("rentals:property_create"), {"name": "Pirmais"})
    response = client.post(reverse("rentals:property_create"), {"name": "Otrais"})
    assert response.url == reverse("billing")
    assert Property.objects.count() == 1


def test_free_plan_cannot_send_or_download_notices(client, verified_user):
    flat = Property.objects.create(owner=verified_user, name="Dzīvoklis")
    tenant = Tenant.objects.create(owner=verified_user, full_name="Anna", email="anna@example.lv")
    lease = Lease.objects.create(property=flat, tenant=tenant, start_date=datetime.date(2026, 1, 1),
                                 end_date=datetime.date(2026, 12, 31), monthly_rent=Decimal("300"))
    notice = statement_services.build_statement(lease, datetime.date(2026, 11, 1), datetime.date(2026, 11, 10), [])
    end_trial(verified_user)
    client.force_login(verified_user)

    assert client.post(reverse("statements:send", args=[notice.pk])).url == reverse("billing")
    assert client.get(reverse("statements:pdf", args=[notice.pk])).url == reverse("billing")
    assert not mail.outbox
    notice.refresh_from_db()
    assert notice.status == Statement.Status.DRAFT


def test_free_plan_gets_no_reminders(verified_user):
    flat = Property.objects.create(owner=verified_user, name="Dzīvoklis")
    tenant = Tenant.objects.create(owner=verified_user, full_name="Anna")
    Lease.objects.create(property=flat, tenant=tenant, start_date=datetime.date(2026, 1, 1),
                         end_date=datetime.date(2026, 12, 31), monthly_rent=Decimal("300"))
    end_trial(verified_user)
    assert send_reminders(datetime.date(2026, 11, 1)) == 0


def test_billing_page_shows_prices_with_vat(client, verified_user):
    client.force_login(verified_user)
    html = client.get(reverse("billing")).content.decode()
    assert "4,99\xa0€" in html and "49,90\xa0€" in html
    assert "PVN" in html  # "ar 21% PVN"


def test_price_net_and_vat_split():
    month = plans.PRICES["month"]
    assert month.net == Decimal("4.12")
    assert month.vat == Decimal("0.87")


# --- Checkout ----------------------------------------------------------------


def test_checkout_redirects_to_stripe(client, verified_user, monkeypatch):
    captured = {}

    class FakeSessions:
        def create(self, params):
            captured.update(params)
            return SimpleNamespace(url="https://checkout.stripe.com/c/test")

    fake_client = SimpleNamespace(v1=SimpleNamespace(checkout=SimpleNamespace(sessions=FakeSessions())))
    monkeypatch.setattr(stripe_provider, "_client", lambda: fake_client)

    client.force_login(verified_user)
    response = client.post(reverse("billing_checkout"), {"interval": "year"})
    assert response.url == "https://checkout.stripe.com/c/test"
    assert captured["line_items"] == [{"price": "price_year", "quantity": 1}]
    assert captured["client_reference_id"] == str(verified_user.pk)
    assert captured["locale"] == "lv"


def test_checkout_rejects_unknown_interval(client, verified_user):
    client.force_login(verified_user)
    assert client.post(reverse("billing_checkout"), {"interval": "week"}).status_code == 400


# --- Webhooks -----------------------------------------------------------------


def test_webhook_with_bad_signature_is_rejected(client, verified_user):
    response = client.post(
        reverse("stripe_webhook"), json.dumps(event("customer.subscription.updated", stripe_subscription(verified_user))),
        content_type="application/json", HTTP_STRIPE_SIGNATURE="t=1,v1=forged",
    )
    assert response.status_code == 400
    verified_user.subscription.refresh_from_db()
    assert verified_user.subscription.status == Subscription.Status.TRIALING


def test_subscription_webhook_activates_paid_plan(client, verified_user):
    end_trial(verified_user)
    response = signed_post(client, event("customer.subscription.created", stripe_subscription(verified_user, interval="year")))
    assert response.status_code == 200
    sub = Subscription.objects.get(user=verified_user)
    assert sub.status == Subscription.Status.ACTIVE
    assert sub.interval == "year"
    assert sub.provider_customer_id == "cus_123"
    assert sub.current_period_end.date() == datetime.date(2026, 12, 31)
    assert sub.plan == plans.STANDARD


def test_webhook_is_idempotent(client, verified_user):
    payload = event("customer.subscription.updated", stripe_subscription(verified_user))
    signed_post(client, payload)
    signed_post(client, payload)
    assert Subscription.objects.filter(user=verified_user).count() == 1


def test_failed_payment_keeps_access_then_cancel_removes_it(client, verified_user):
    end_trial(verified_user)
    signed_post(client, event("customer.subscription.updated", stripe_subscription(verified_user, status="past_due")))
    sub = Subscription.objects.get(user=verified_user)
    assert sub.status == Subscription.Status.PAST_DUE and sub.plan == plans.STANDARD

    signed_post(client, event("customer.subscription.deleted", stripe_subscription(verified_user, status="canceled")))
    sub.refresh_from_db()
    assert sub.plan == plans.FREE


def test_checkout_completed_links_customer(client, verified_user, monkeypatch):
    fake_subs = SimpleNamespace(retrieve=lambda sub_id: stripe_subscription(verified_user, sub_id=sub_id))
    monkeypatch.setattr(stripe_provider, "_client", lambda: SimpleNamespace(v1=SimpleNamespace(subscriptions=fake_subs)))
    session = {"object": "checkout.session", "mode": "subscription", "client_reference_id": str(verified_user.pk),
               "customer": "cus_123", "subscription": "sub_999"}
    signed_post(client, event("checkout.session.completed", session))
    sub = Subscription.objects.get(user=verified_user)
    assert sub.provider_subscription_id == "sub_999"
    assert sub.status == Subscription.Status.ACTIVE


def test_webhook_for_unknown_user_is_ignored(client, db):
    ghost = SimpleNamespace(pk=999999)
    sub = stripe_subscription(ghost)
    sub["customer"] = "cus_unknown"
    assert signed_post(client, event("customer.subscription.updated", sub)).status_code == 200


def test_users_without_subscription_row_get_free_plan(db):
    from apps.subscriptions.services import current_plan

    user = User.objects.create_user("vecs@example.lv", "x")
    user.subscription.delete()
    user = User.objects.get(pk=user.pk)
    assert current_plan(user) == plans.FREE
