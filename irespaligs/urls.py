from django.contrib import admin
from django.urls import include, path

from apps.core.views import set_language

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("language/", set_language, name="set_language"),
    path("", include("apps.pages.urls")),
]
