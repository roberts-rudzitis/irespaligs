import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.rentals.models import Lease
from apps.subscriptions.services import can_send_notices

from . import reports, services
from .forms import PaymentForm, StatementCreateForm
from .models import Payment, Statement


def _own_statement(request, pk):
    return get_object_or_404(
        Statement.objects.for_owner(request.user).select_related("lease__property", "lease__tenant"), pk=pk
    )


@login_required
def statement_create(request, lease_pk):
    lease = get_object_or_404(Lease.objects.for_owner(request.user).select_related("property"), pk=lease_pk)
    meters = lease.property.meters.filter(is_active=True)

    # The month decides which "previous reading" is pre-filled, so read it from the form if given.
    period = services.first_of_month(timezone.localdate())
    if request.method == "POST":
        try:
            period = StatementCreateForm.base_fields["period"].clean(request.POST.get("period", ""))
        except ValidationError:
            pass  # the form itself will show the error

    form = StatementCreateForm(
        request.POST or None,
        meters=meters,
        period=period,
        initial={"period": period, "due_date": services.default_due_date(lease, period)},
    )
    if request.method == "POST" and form.is_valid():
        try:
            statement = services.build_statement(
                lease, form.cleaned_data["period"], form.cleaned_data["due_date"], form.readings()
            )
        except services.StatementError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Draft created. Check it, then send it to the tenant."))
            return redirect(statement)
    return render(request, "statements/create.html", {"form": form, "lease": lease})


@login_required
def statement_detail(request, pk):
    statement = _own_statement(request, pk)
    return render(
        request,
        "statements/detail.html",
        {"statement": statement, "payment_form": PaymentForm()},
    )


def _upgrade_needed(request):
    messages.info(request, _("PDF and email notices are part of the paid plan."))
    return redirect("billing")


@login_required
def statement_pdf(request, pk):
    statement = _own_statement(request, pk)
    if not can_send_notices(request.user):
        return _upgrade_needed(request)
    response = HttpResponse(services.render_pdf(statement), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{services.pdf_filename(statement)}"'
    return response


@login_required
@require_POST
def statement_send(request, pk):
    statement = _own_statement(request, pk)
    if not can_send_notices(request.user):
        return _upgrade_needed(request)
    try:
        services.send_statement(statement)
    except services.StatementError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, _("Sent to %(email)s.") % {"email": statement.lease.tenant.email})
    return redirect(statement)


@login_required
def statement_delete(request, pk):
    statement = _own_statement(request, pk)
    if request.method == "POST":
        property_url = statement.lease.property.get_absolute_url()
        statement.delete()
        messages.success(request, _("Deleted."))
        return redirect(property_url)
    return render(request, "rentals/confirm_delete.html", {"object": statement})


@login_required
@require_POST
def payment_add(request, pk):
    statement = _own_statement(request, pk)
    form = PaymentForm(request.POST)
    if form.is_valid():
        form.instance.statement = statement
        form.save()
        messages.success(request, _("Payment recorded."))
        return redirect(statement)
    return render(request, "statements/detail.html", {"statement": statement, "payment_form": form})


@login_required
@require_POST
def payment_delete(request, pk):
    payment = get_object_or_404(Payment.objects.for_owner(request.user), pk=pk)
    statement = payment.statement
    payment.delete()
    messages.success(request, _("Payment deleted."))
    return redirect(statement)


# --- Year-end summary -------------------------------------------------------


def _selected_year(request):
    try:
        return int(request.GET.get("year", ""))
    except ValueError:
        return timezone.localdate().year


@login_required
def year_summary(request):
    year = _selected_year(request)
    rows, totals = reports.year_summary(request.user, year)
    current = timezone.localdate().year
    return render(
        request,
        "statements/year_summary.html",
        {"year": year, "rows": rows, "totals": totals, "years": range(current, current - 5, -1)},
    )


def _csv_amount(amount):
    return f"{amount:.2f}".replace(".", ",")


@login_required
def year_summary_csv(request):
    """One row per payment received, then a summary per property. Opens in Excel (semicolon, UTF-8 BOM)."""
    year = _selected_year(request)
    rows, totals = reports.year_summary(request.user, year)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="ienakumi-{year}.csv"'
    response.write("﻿")  # BOM so Excel shows Latvian letters correctly
    writer = csv.writer(response, delimiter=";")  # Latvian Excel expects ";" because "," is the decimal sign
    writer.writerow([_("Payment date"), _("Property"), _("Tenant"), _("Notice"), _("Amount"), _("Note")])
    for row in rows:
        for p in row.payments:
            writer.writerow([
                p.paid_on.strftime("%d.%m.%Y"), row.property.name, p.statement.lease.tenant.full_name,
                p.statement.number, _csv_amount(p.amount), p.note,
            ])
    writer.writerow([])
    writer.writerow([_("Property"), _("Billed rent"), _("Billed utilities and charges"), _("Received")])
    for row in rows + [totals]:
        writer.writerow([
            row.property.name if row.property else _("Total"),
            *[_csv_amount(a) for a in (row.billed_rent, row.billed_other, row.received)],
        ])
    return response


@login_required
def year_summary_pdf(request):
    from weasyprint import HTML

    year = _selected_year(request)
    rows, totals = reports.year_summary(request.user, year)
    html = render_to_string(
        "statements/year_summary_pdf.html", {"year": year, "rows": rows, "totals": totals, "landlord": request.user}
    )
    response = HttpResponse(HTML(string=html).write_pdf(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="ienakumi-{year}.pdf"'
    return response
