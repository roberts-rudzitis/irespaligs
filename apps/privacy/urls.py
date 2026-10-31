from django.urls import path

from . import views

urlpatterns = [
    path("profile/export/", views.export_data, name="export_data"),
    path("profile/delete/", views.delete_account, name="delete_account"),
    path("account-deleted/", views.account_deleted, name="account_deleted"),
]
