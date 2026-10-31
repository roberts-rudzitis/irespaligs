from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.accounts.metrics import metrics_view
from apps.accounts.views import profile
from apps.core.views import set_language

urlpatterns = [
    path(settings.ADMIN_URL + "metrics/", metrics_view, name="admin_metrics"),
    path(settings.ADMIN_URL, admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("language/", set_language, name="set_language"),
    path("profile/", profile, name="profile"),
    path("", include("apps.privacy.urls")),
    path("", include("apps.subscriptions.urls")),
    path("", include("apps.rentals.urls")),
    path("", include("apps.statements.urls")),
    path("", include("apps.pages.urls")),
]
