from django.contrib import admin

from .models import Payment, Statement, StatementLine


class StatementLineInline(admin.TabularInline):
    model = StatementLine
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = ["__str__", "status", "total", "due_date", "sent_at"]
    list_filter = ["status"]
    inlines = [StatementLineInline, PaymentInline]
