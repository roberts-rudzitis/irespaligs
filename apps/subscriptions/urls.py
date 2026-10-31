from django.urls import path

from . import views

urlpatterns = [
    path("billing/", views.billing, name="billing"),
    path("billing/checkout/", views.checkout, name="billing_checkout"),
    path("billing/manage/", views.manage, name="billing_manage"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
