from django.urls import path

from . import views

app_name = "rentals"

urlpatterns = [
    path("properties/new/", views.PropertyCreate.as_view(), name="property_create"),
    path("properties/<int:pk>/", views.PropertyDetail.as_view(), name="property_detail"),
    path("properties/<int:pk>/edit/", views.PropertyUpdate.as_view(), name="property_update"),
    path("properties/<int:pk>/delete/", views.PropertyDelete.as_view(), name="property_delete"),
    path("properties/<int:property_pk>/leases/new/", views.LeaseCreate.as_view(), name="lease_create"),
    path("leases/<int:pk>/edit/", views.LeaseUpdate.as_view(), name="lease_update"),
    path("leases/<int:pk>/delete/", views.LeaseDelete.as_view(), name="lease_delete"),
    path("tenants/", views.TenantList.as_view(), name="tenant_list"),
    path("tenants/new/", views.TenantCreate.as_view(), name="tenant_create"),
    path("tenants/<int:pk>/edit/", views.TenantUpdate.as_view(), name="tenant_update"),
    path("tenants/<int:pk>/delete/", views.TenantDelete.as_view(), name="tenant_delete"),
]
