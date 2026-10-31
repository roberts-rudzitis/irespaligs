from django.urls import path

from . import tenant_views, views

app_name = "rentals"

urlpatterns = [
    path("properties/new/", views.PropertyCreate.as_view(), name="property_create"),
    path("properties/<int:pk>/", views.PropertyDetail.as_view(), name="property_detail"),
    path("properties/<int:pk>/edit/", views.PropertyUpdate.as_view(), name="property_update"),
    path("properties/<int:pk>/delete/", views.PropertyDelete.as_view(), name="property_delete"),
    path("properties/<int:property_pk>/leases/new/", views.LeaseCreate.as_view(), name="lease_create"),
    path("leases/<int:pk>/edit/", views.LeaseUpdate.as_view(), name="lease_update"),
    path("leases/<int:pk>/delete/", views.LeaseDelete.as_view(), name="lease_delete"),
    path("properties/<int:property_pk>/meters/new/", views.MeterCreate.as_view(), name="meter_create"),
    path("meters/<int:pk>/edit/", views.MeterUpdate.as_view(), name="meter_update"),
    path("meters/<int:pk>/delete/", views.MeterDelete.as_view(), name="meter_delete"),
    path("properties/<int:property_pk>/charges/new/", views.FixedChargeCreate.as_view(), name="charge_create"),
    path("charges/<int:pk>/edit/", views.FixedChargeUpdate.as_view(), name="charge_update"),
    path("charges/<int:pk>/delete/", views.FixedChargeDelete.as_view(), name="charge_delete"),
    path("leases/<int:pk>/readings-link/", tenant_views.readings_link, name="lease_readings_link"),
    path("r/<str:token>/", tenant_views.tenant_readings_form, name="tenant_readings"),  # public, for tenants
    path("tenants/", views.TenantList.as_view(), name="tenant_list"),
    path("tenants/new/", views.TenantCreate.as_view(), name="tenant_create"),
    path("tenants/<int:pk>/edit/", views.TenantUpdate.as_view(), name="tenant_update"),
    path("tenants/<int:pk>/delete/", views.TenantDelete.as_view(), name="tenant_delete"),
]
