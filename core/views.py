import json
from django.http import FileResponse, Http404
from pathlib import Path
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from sitebuilder.settings import USER_FILES_ROOT
from core.tools import get_image_path_for_user, get_base_path_for_user
from django.utils import timezone
from .models import Profile, Transaction, SiteProject, MyTask

from .models import Profile, Transaction, SiteProject
from .tools import is_valid_http_url
from .screenshot import generate_screenshort
from core.task import generate_site

from core.log import *
logger.setLevel(logging.DEBUG)


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
    url = data.get('url')

    r, msg = is_valid_http_url(url)
    if not r:
        return JsonResponse({"status": False, "error": msg}, status=400)
    r, result = generate_screenshort(request.user, url)
    if not r:
        return JsonResponse({"status": False, "error": result}, status=400)

    img_url = result.image.url
    logger.debug(f"result image: {img_url}")

    return JsonResponse({"status": True, "img": img_url})


@login_required
def user_file_view(request, user_id, path):
    if request.user.id != user_id:
        raise Http404('File not found')
    base_path = get_base_path_for_user(request.user)
    file_path = Path(base_path + "/" + path)
    logger.debug(f"path {file_path} | {path} | {file_path}")
    return FileResponse(open(file_path, "rb"))

@login_required
@require_POST
def create_site_task(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)

    # Поддержим и поля из формы модалки
    prompt = (data.get("prompt") or data.get("taskPrompt") or "").strip()
    ref_url = (data.get("ref_url") or data.get("refUrl") or "").strip()
    name = (data.get("name") or "").strip()
    count = data.get("count") or data.get("siteCount") or 1

    # Валидация количества
    try:
        count = int(count)
    except Exception:
        return JsonResponse({"status": False, "error": "Некорректное количество"}, status=400)

    if count < 1 or count > 10:
        return JsonResponse({"status": False, "error": "count должен быть 1..10"}, status=400)

    # Валидация URL если указан
    if ref_url:
        ok, msg = is_valid_http_url(ref_url)
        if not ok:
            return JsonResponse({"status": False, "error": msg}, status=400)

    tasks_out = []
    base_name = name or "Сайт"
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    for i in range(count):
        suffix = f" #{i + 1}" if count > 1 else ""
        site = SiteProject.objects.create(
            user=request.user,
            name=f"{base_name} {now_str}{suffix}",
            status=SiteProject.STATUS_DRAFT,
        )

        # Запуск Celery задачи
        async_res = generate_site.apply_async(args=[site.id, prompt, ref_url])

        # Запишем задачу в MyTask
        MyTask.objects.create(
            task_id=async_res.id,
            name=f'Генерация сайта "{site.name}"',
            status="PENDING",
            user=request.user,
        )

        tasks_out.append({"task_id": async_res.id, "site_id": site.id})

    return JsonResponse({
        "status": True,
        "tasks": tasks_out
    }, status=201)







