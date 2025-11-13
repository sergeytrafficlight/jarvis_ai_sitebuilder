import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from django.views.decorators.http import require_POST
from django.http import JsonResponse


from .models import Profile, Transaction, SiteProject
from .tools import is_valid_http_url
from .screenshot import generate_screenshort


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    sites = SiteProject.objects.filter(user=request.user)
    return render(request, "dashboard.html", {"profile": profile, "sites": sites})


@login_required
def billing_history(request):
    operations = Transaction.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "billing_history.html", {"operations": operations})


class TopupForm(forms.Form):
    amount = forms.DecimalField(min_value=1, max_digits=10, decimal_places=2, label=_lazy("Сумма пополнения (USD)"))


@login_required
def topup(request):
    if request.method == "POST":
        form = TopupForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            # Here we only redirect to a placeholder payment gateway page
            return redirect(f"/payments/redirect/?amount={amount}")
        else:
            messages.error(request, _("Пожалуйста, исправьте ошибки в форме."))
    else:
        form = TopupForm()
    return render(request, "topup.html", {"form": form})


@login_required
def payment_redirect(request):
    amount = request.GET.get("amount", "0")
    return render(request, "payment_redirect.html", {"amount": amount})

@login_required
@require_POST
def reference_screenshot(request):

    data = json.loads(request.body)
    url = data.url

    r, msg = is_valid_http_url(url)
    if not r:
        return JsonResponse({"status": False, "error": msg}, status=400)
    r, result = generate_screenshort(request.User, url)
    if not r:
        return JsonResponse({"status": False, "error": result}, status=400)

    return JsonResponse({"status": True, "img": result})

