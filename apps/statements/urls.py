from django.urls import path

from . import views

app_name = "statements"

urlpatterns = [
    path("leases/<int:lease_pk>/notices/new/", views.statement_create, name="create"),
    path("notices/<int:pk>/", views.statement_detail, name="detail"),
    path("notices/<int:pk>/pdf/", views.statement_pdf, name="pdf"),
    path("notices/<int:pk>/send/", views.statement_send, name="send"),
    path("notices/<int:pk>/delete/", views.statement_delete, name="delete"),
    path("notices/<int:pk>/payments/", views.payment_add, name="payment_add"),
    path("payments/<int:pk>/delete/", views.payment_delete, name="payment_delete"),
    path("reports/year/", views.year_summary, name="year_summary"),
    path("reports/year/csv/", views.year_summary_csv, name="year_summary_csv"),
    path("reports/year/pdf/", views.year_summary_pdf, name="year_summary_pdf"),
]
