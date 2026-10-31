from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def home(request):
    # Placeholder until the landing-page slice; logged-in users go straight to work.
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "pages/home.html")


@login_required
def dashboard(request):
    return render(request, "pages/dashboard.html")
